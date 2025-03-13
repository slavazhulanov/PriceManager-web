import os
import pandas as pd
import chardet
import io
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
from app.core.config import settings
from app.services.file_cache import cache_file_content, get_cached_content, clear_old_cache
import logging
import traceback
import httpx
import csv
from app.core.logger import get_logger
import requests

logger = get_logger("app.services.file_service")

# Инициализация клиента Supabase
supabase_client: Optional[Client] = None

def init_supabase_client() -> Optional[Client]:
    """
    Инициализация клиента Supabase с обработкой ошибок
    
    Returns:
        Optional[Client]: Клиент Supabase или None в случае ошибки
    """
    global supabase_client
    
    if supabase_client:
        return supabase_client
        
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.error("Не указаны SUPABASE_URL или SUPABASE_KEY")
        return None
        
    try:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        bucket_name = settings.SUPABASE_BUCKET
        folder_name = settings.SUPABASE_FOLDER
        
        # Проверяем наличие service_role ключа
        service_key = settings.SUPABASE_SERVICE_KEY
        
        logger.info(f"Инициализация Supabase клиента: URL={url}, Bucket={bucket_name}")
        logger.info(f"Используемый ключ API: {key[:10]}...{key[-5:]} (скрыт для безопасности)")
        
        if service_key:
            logger.info(f"Service role ключ доступен: {service_key[:10]}...{service_key[-5:]} (скрыт для безопасности)")
        
        # Создаем клиент с обычным ключом для основных операций
        client = create_client(url, key)
        
        # Проверяем наличие бакета через list_buckets
        try:
            # Если есть service_role ключ, используем его для проверки бакетов
            if service_key:
                logger.info("Используем service_role ключ для проверки бакетов")
                # Формируем URL для запроса к Supabase Storage API
                storage_url = f"{url}/storage/v1/bucket"
                
                # Заголовки для запроса с service_role ключом
                headers = {
                    "Content-Type": "application/json",
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}"
                }
                
                # Получаем список бакетов
                response = requests.get(storage_url, headers=headers)
                if response.status_code == 200:
                    buckets = response.json()
                    logger.info(f"Найдены бакеты: {[b['name'] for b in buckets]}")
                    bucket_exists = any(b['name'] == bucket_name for b in buckets)
                    
                    # Если бакет не существует, создаем его
                    if not bucket_exists:
                        logger.warning(f"Бакет {bucket_name} не найден, пытаемся создать")
                        
                        # Данные для создания бакета
                        data = {
                            "id": bucket_name,
                            "name": bucket_name,
                            "public": False,
                            "file_size_limit": 52428800  # 50MB в байтах
                        }
                        
                        # Отправляем запрос на создание бакета
                        create_response = requests.post(storage_url, headers=headers, json=data)
                        
                        if create_response.status_code == 200 or create_response.status_code == 201:
                            logger.info(f"Бакет {bucket_name} успешно создан")
                            bucket_exists = True
                        else:
                            logger.error(f"Ошибка при создании бакета: {create_response.text}")
                else:
                    logger.error(f"Ошибка при получении списка бакетов: {response.text}")
            else:
                buckets = client.storage.list_buckets()
                bucket_exists = any(b['name'] == bucket_name for b in buckets)
            
            if bucket_exists:
                logger.info(f"Бакет {bucket_name} найден")
                supabase_client = client
                
                # Проверяем доступность папки uploads
                try:
                    logger.info("Проверяем доступность папки uploads")
                    # Создаем папку uploads локально, если она не существует
                    if not os.path.exists('uploads'):
                        os.makedirs('uploads', exist_ok=True)
                        logger.info("Папка uploads создана локально")
                    
                    # Проверка работоспособности Supabase Storage
                    test_path = bucket_name + "/" + folder_name
                    try:
                        # Просто пытаемся получить список файлов
                        client.storage.from_(bucket_name).list(folder_name)
                        logger.info(f"Доступ к папке {test_path} подтвержден")
                    except Exception as e:
                        # Если не получилось, логируем ошибку
                        error_str = str(e)
                        logger.warning(f"Не удалось проверить доступ к папке {test_path}: {error_str}")
                        # Но продолжаем работу
                except Exception as e:
                    error_str = str(e)
                    logger.warning(f"Не удалось проверить папку uploads: {error_str}")
                    logger.warning("Это может вызвать проблемы при сохранении файлов")
                
                logger.info(f"Supabase клиент успешно инициализирован, используется бакет {bucket_name}")
                return client
            else:
                logger.error(f"Бакет {bucket_name} не найден и не удалось его создать")
                return None
        except Exception as bucket_error:
            logger.warning(f"Не удалось проверить бакет {bucket_name}: {str(bucket_error)}")
            logger.warning("Это может вызвать проблемы при сохранении файлов")
            
            # Даже если проверка не удалась, продолжаем работу с клиентом
            # так как фактическая работа с бакетом будет проверена при первой операции
        
        logger.info(f"Supabase клиент успешно инициализирован, используется бакет {bucket_name}")
        supabase_client = client
        return client
    except Exception as e:
        logger.error(f"Ошибка при инициализации Supabase клиента: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        return None

# Инициализируем клиент при запуске
init_supabase_client()

# Планировщик очистки старых файлов в Supabase
async def cleanup_old_files(max_age_days: int = 7):
    """
    Удаляет файлы старше указанного количества дней из Supabase
    """
    client = init_supabase_client()
    if not client:
        logger.error("Не удалось инициализировать Supabase клиент для очистки файлов")
        return
        
    try:
        # Получаем список файлов
        files = client.storage.from_(settings.SUPABASE_BUCKET).list(settings.SUPABASE_FOLDER)
        logger.info(f"Найдено {len(files)} файлов для проверки на старость")
        
        # Получаем дату, старше которой файлы нужно удалить
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        # Удаляем старые файлы
        # Примечание: Supabase не предоставляет информацию о дате создания файла через API,
        # поэтому мы используем соглашение об именовании файлов
        for file in files:
            file_path = file.get('name', '')
            
            # Определяем, является ли файл временным (содержит 'temp' или 'updated' в имени)
            is_temp = 'temp_' in file_path or 'updated_' in file_path
            
            if is_temp:
                try:
                    path = f"{settings.SUPABASE_FOLDER}/{file_path}"
                    client.storage.from_(settings.SUPABASE_BUCKET).remove([path])
                    logger.info(f"Удален старый файл из Supabase: {path}")
                    deleted_count += 1
                except Exception as del_err:
                    logger.warning(f"Не удалось удалить файл {file_path}: {str(del_err)}")
        
        logger.info(f"Очистка старых файлов завершена, удалено {deleted_count} файлов")
    except Exception as e:
        logger.error(f"Ошибка при очистке старых файлов в Supabase: {str(e)}")
        logger.debug(traceback.format_exc())

def detect_encoding(file_content: bytes) -> str:
    """
    Определение кодировки файла
    """
    if not file_content:
        return 'utf-8'
    
    encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1', 'iso-8859-1']
    
    # Проверка на UTF-8 BOM
    if file_content.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    
    # Проверка каждой кодировки
    for encoding in encodings_to_try:
        try:
            file_content.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    
    # Если не удалось определить кодировку, используем chardet
    try:
        import chardet
        result = chardet.detect(file_content)
        if result['confidence'] > 0.7:
            return result['encoding']
    except ImportError:
        pass
    
    # Если ничего не помогло, используем UTF-8 по умолчанию
    return 'utf-8'

def detect_separator(file_content: bytes, encoding: str) -> str:
    """
    Определение разделителя в CSV-файле из содержимого
    """
    logger.info(f"Определение разделителя в файле с кодировкой {encoding}")
    try:
        text = file_content.decode(encoding, errors='replace')
        first_line = text.split('\n')[0]
        
        # Проверка наиболее распространенных разделителей
        separators = [',', ';', '\t', '|']
        counts = {sep: first_line.count(sep) for sep in separators}
        
        # Логируем количество вхождений каждого разделителя
        for sep, count in counts.items():
            logger.debug(f"Разделитель '{sep}': {count} вхождений")
        
        # Выбор разделителя с наибольшим количеством вхождений
        max_separator = max(counts.items(), key=lambda x: x[1])
        
        if max_separator[1] > 0:
            logger.info(f"Обнаружен разделитель: '{max_separator[0]}' ({max_separator[1]} вхождений)")
            return max_separator[0]
        
        # Если не удалось определить разделитель, по умолчанию используем запятую
        logger.warning("Не удалось определить разделитель, используется запятая по умолчанию")
        return ','
    except Exception as e:
        logger.error(f"Ошибка при определении разделителя: {str(e)}")
        logger.debug(traceback.format_exc())
        return ','

def get_columns(file_content: bytes, extension: str, encoding: str, separator: str) -> List[str]:
    """
    Получение списка колонок из содержимого файла
    """
    logger.info(f"Извлечение колонок из файла (расширение: {extension}, кодировка: {encoding}, разделитель: '{separator}')")
    try:
        if extension.lower() in ['.xlsx', '.xls']:
            # Для Excel-файлов
            logger.info("Чтение Excel-файла")
            df = pd.read_excel(io.BytesIO(file_content))
        elif extension.lower() == '.csv':
            # Для CSV-файлов
            logger.info("Чтение CSV-файла")
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
        else:
            # Пробуем прочитать как CSV
            logger.warning(f"Неизвестное расширение файла: {extension}, пробуем прочитать как CSV")
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
        
        columns = df.columns.tolist()
        logger.info(f"Найдено {len(columns)} колонок: {', '.join(columns)}")
        return columns
    except Exception as e:
        logger.error(f"Ошибка при извлечении колонок: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Не удалось прочитать колонки из файла: {str(e)}")

def read_file(file_content: bytes, extension: str, encoding: str, separator: str) -> pd.DataFrame:
    """
    Чтение содержимого файла в pandas DataFrame
    
    Args:
        file_content: Бинарное содержимое файла
        extension: Расширение файла (.csv, .xlsx и т.д.)
        encoding: Кодировка файла
        separator: Разделитель для CSV файлов
        
    Returns:
        pd.DataFrame: Данные из файла
    """
    logger.info(f"Чтение файла с расширением {extension}, кодировкой {encoding}, разделителем '{separator}'")
    
    if not file_content:
        logger.error("Получено пустое содержимое файла для чтения")
        raise ValueError("Невозможно прочитать файл: пустое содержимое")
    
    try:
        if extension.lower() in ['.csv', '.txt']:
            # Для CSV и TXT файлов, пробуем несколько подходов
            try:
                # Стандартное чтение CSV
                df = pd.read_csv(
                    io.BytesIO(file_content), 
                    encoding=encoding, 
                    sep=separator,
                    engine='python',  # Более гибкий парсер
                    on_bad_lines='skip',  # Пропускаем строки с ошибками (заменено с error_bad_lines=False)
                    low_memory=False  # Избегаем предупреждения memory
                )
            except Exception as e:
                logger.warning(f"Ошибка при стандартном чтении CSV: {str(e)}, пробуем альтернативные методы")
                
                # Пробуем с более строгими параметрами
                try:
                    df = pd.read_csv(
                        io.BytesIO(file_content), 
                        encoding=encoding, 
                        sep=separator,
                        quoting=csv.QUOTE_NONE,  # Отключаем кавычки
                        on_bad_lines='skip'  # Заменено с error_bad_lines=False
                    )
                except Exception as e2:
                    logger.warning(f"Вторая попытка чтения CSV не удалась: {str(e2)}")
                    
                    # Последняя попытка с декодированием строки
                    try:
                        text_content = file_content.decode(encoding, errors='replace')
                        df = pd.read_csv(
                            io.StringIO(text_content),
                            sep=separator,
                            on_bad_lines='skip'  # Заменено с error_bad_lines=False
                        )
                    except Exception as e3:
                        logger.error(f"Все попытки чтения CSV файла не удались: {str(e3)}")
                        raise ValueError(f"Не удалось прочитать CSV файл: {str(e3)}")
        
        elif extension.lower() in ['.xlsx', '.xls']:
            # Для Excel файлов
            try:
                df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl' if extension.lower() == '.xlsx' else 'xlrd')
            except Exception as e:
                logger.error(f"Ошибка при чтении Excel файла: {str(e)}")
                
                # Попытка использовать альтернативные движки
                try:
                    if extension.lower() == '.xlsx':
                        logger.info("Попытка использовать xlrd для чтения XLSX")
                        df = pd.read_excel(io.BytesIO(file_content), engine='xlrd')
                    else:
                        logger.info("Попытка использовать openpyxl для чтения XLS")
                        df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
                except Exception as e2:
                    logger.error(f"Альтернативные движки для Excel не помогли: {str(e2)}")
                    raise ValueError(f"Не удалось прочитать Excel файл: {str(e2)}")
        
        else:
            logger.error(f"Неподдерживаемый формат файла: {extension}")
            raise ValueError(f"Неподдерживаемый формат файла: {extension}")
        
        # Проверка на пустой DataFrame
        if df.empty:
            logger.warning("Файл прочитан, но данные отсутствуют")
            raise ValueError("Файл не содержит данных")
        
        # Логируем информацию о прочитанных данных
        logger.info(f"Файл успешно прочитан. Размер: {len(df)} строк, {len(df.columns)} колонок")
        logger.debug(f"Колонки: {', '.join(df.columns.tolist())}")
        logger.debug(f"Типы данных: {df.dtypes}")
        
        # Предобработка данных - обрезаем пробелы в строковых колонках
        for col in df.select_dtypes(include=['object']).columns:
            try:
                df[col] = df[col].str.strip()
            except Exception:
                pass  # Игнорируем ошибки, так как некоторые колонки могут быть не строками
        
        return df
        
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        raise ValueError(f"Не удалось прочитать файл: {str(e)}")

def save_file(filename: str, file_content: bytes) -> str:
    """
    Сохранение файла в Supabase Storage
    
    Args:
        filename: Имя файла
        file_content: Содержимое файла
        
    Returns:
        URL файла в Supabase
    """
    logger.info(f"Запрос на сохранение файла: {filename}, размер: {len(file_content)} байт")
    
    # Очистка имени файла
    filename = sanitize_filename(filename)
    
    # Подключение к Supabase
    try:
        # Проверка конфигурации Supabase
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.warning("Настройки для Supabase не найдены, сохранение в локальное хранилище")
            return save_file_locally(filename, file_content)
        
        # Получаем существующий клиент или создаем новый
        client = init_supabase_client()
        if not client:
            logger.warning("Не удалось инициализировать Supabase клиент, сохранение в локальное хранилище")
            return save_file_locally(filename, file_content)
        
        try:
            # Формируем путь к файлу в Supabase
            file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
            logger.info(f"Сохранение в Supabase Storage: {file_path}")
            
            # Проверка содержимого на вредоносный код (базовая проверка)
            if len(file_content) > 0 and is_potentially_dangerous(file_content[:4096]):
                logger.warning(f"Обнаружено потенциально опасное содержимое в файле {filename}")
                raise ValueError("Обнаружено потенциально опасное содержимое в файле")
            
            # Загружаем файл в Supabase
            client.storage.from_(settings.SUPABASE_BUCKET).upload(
                file_path,
                file_content,
                {"content-type": "application/octet-stream"}
            )
            
            # Получаем публичный URL
            cloud_url = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
            logger.info(f"Файл успешно загружен в Supabase, URL: {cloud_url}")
            return cloud_url
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла в Supabase: {str(e)}")
            logger.error(f"Полная ошибка: {traceback.format_exc()}")
            
            # В случае ошибки пытаемся сохранить в локальное хранилище
            logger.info("Пытаемся сохранить файл в локальное хранилище")
            return save_file_locally(filename, file_content)
    except Exception as e:
        logger.error(f"Критическая ошибка при сохранении файла: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        raise ValueError(f"Не удалось сохранить файл: {str(e)}")

def save_file_locally(filename: str, file_content: bytes) -> str:
    """
    Сохранение файла в локальное хранилище
    """
    try:
        # Создаем директорию, если не существует
        uploads_dir = os.path.join(settings.UPLOADS_DIR)
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Полный путь к файлу
        file_path = os.path.join(uploads_dir, filename)
        
        # Записываем содержимое в файл
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Файл успешно сохранен локально: {file_path}")
        
        # Возвращаем относительный путь для доступа через API
        return f"/api/v1/files/download/{filename}"
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла локально: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        raise ValueError(f"Не удалось сохранить файл локально: {str(e)}")

def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от потенциально опасных символов
    """
    # Удаляем недопустимые символы в имени файла
    import re
    
    # Получаем расширение файла
    base, ext = os.path.splitext(filename)
    
    # Очищаем базовое имя от спецсимволов, оставляя только буквы, цифры, - и _
    base = re.sub(r'[^\w\-_]', '', base)
    
    # Ограничиваем длину имени
    if len(base) > 50:
        base = base[:50]
    
    # Собираем имя файла
    safe_filename = f"{base}{ext}"
    
    if safe_filename != filename:
        logger.info(f"Имя файла очищено: '{filename}' -> '{safe_filename}'")
    
    return safe_filename

def is_potentially_dangerous(content_sample: bytes) -> bool:
    """
    Базовая проверка содержимого файла на потенциально опасный код
    """
    try:
        # Проверка на наличие исполняемых заголовков
        executable_headers = [
            b'MZ',       # Windows PE
            b'\x7fELF',  # ELF (Linux)
            b'\xca\xfe\xba\xbe',  # Java class
            b'\xCF\xFA\xED\xFE',  # Mach-O binary (macOS)
        ]
        
        for header in executable_headers:
            if content_sample.startswith(header):
                return True
        
        # Проверка на наличие потенциально опасных скриптовых фрагментов
        dangerous_patterns = [
            b'<script', b'eval(', b'exec(',
            b'Runtime.getRuntime().exec',
            b'ProcessBuilder',
            b'os.system'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content_sample.lower():
                return True
        
        return False
    except Exception:
        # В случае ошибки считаем безопасным, чтобы не блокировать работу
        return False

def get_file_content(filename: str) -> Optional[bytes]:
    """
    Получение содержимого файла из Supabase Storage
    """
    logger.info(f"Запрос содержимого файла: {filename}")
    
    # Проверяем кеш первым делом для всех файлов
    cached_content = get_cached_content(filename)
    if cached_content:
        logger.info(f"Файл {filename} найден в кеше, размер: {len(cached_content)} байт")
        return cached_content
    
    # Попытка получить из Supabase
    try:
        # Инициализация клиента Supabase
        client = init_supabase_client()
        if not client:
            logger.error(f"Не удалось инициализировать клиент Supabase для получения файла {filename}")
            return None
        
        # Полный путь к файлу в Supabase
        bucket = settings.SUPABASE_BUCKET
        folder = settings.SUPABASE_FOLDER
        file_path = f"{folder}/{filename}" if folder else filename
        
        # Рассчитываем таймаут в зависимости от среды
        is_vercel = os.environ.get("VERCEL") == "1"
        vercel_timeout = 3.0  # в Vercel используем короткий таймаут, чтобы избежать лимита 10 секунд
        default_timeout = 20.0
        timeout = vercel_timeout if is_vercel else default_timeout
        
        logger.info(f"Попытка получения файла из Supabase: бакет={bucket}, путь={file_path}" + 
                  (f", таймаут={timeout}с (Vercel)" if is_vercel else f", таймаут={timeout}с"))
        
        # Сначала пробуем API метод с меньшим таймаутом для Vercel
        # В Vercel у нас всего 10 секунд на весь запрос
        try:
            # Пытаемся получить файл через API
            logger.debug(f"Скачивание файла через API: {file_path}")
            response = client.storage.from_(bucket).download(file_path)
            if response:
                logger.info(f"Файл {filename} успешно получен через API, размер: {len(response)} байт")
                # Сохраняем в кеш
                cache_file_content(filename, response)
                return response
            else:
                logger.warning(f"API вернул пустой ответ для файла {filename}")
        except Exception as api_error:
            # Логируем ошибку API
            logger.error(f"Ошибка при получении файла через API: {str(api_error)}")
            logger.error(f"Детали ошибки API: {traceback.format_exc()}")
            
            # В Vercel проверяем, сколько времени осталось до таймаута
            # Если осталось мало времени, пропускаем запрос по публичному URL
            if is_vercel:
                logger.warning("Vercel среда: пропускаем попытку доступа через публичный URL")
                return None
            
            # Попробуем получить через публичный URL
            try:
                logger.info(f"Попытка получения файла через публичный URL: {filename}")
                public_url = client.storage.from_(bucket).get_public_url(file_path)
                logger.debug(f"Публичный URL: {public_url}")
                
                with httpx.Client(timeout=timeout) as http_client:
                    response = http_client.get(public_url)
                    if response.status_code == 200:
                        content = response.content
                        logger.info(f"Файл {filename} успешно получен через публичный URL, размер: {len(content)} байт")
                        # Сохраняем в кеш
                        cache_file_content(filename, content)
                        return content
                    else:
                        logger.error(f"Ошибка при получении через публичный URL. Статус: {response.status_code}, тело: {response.text[:200]}")
            except Exception as url_error:
                logger.error(f"Ошибка при получении файла через публичный URL: {str(url_error)}")
                logger.error(f"Детали ошибки URL: {traceback.format_exc()}")
    
    except Exception as e:
        logger.error(f"Ошибка при получении файла {filename}: {str(e)}")
        logger.error(f"Детали общей ошибки: {traceback.format_exc()}")
    
    logger.error(f"Не удалось получить содержимое файла {filename} ни одним из методов")
    return None

def dataframe_to_bytes(df: pd.DataFrame, extension: str, encoding: str, separator: str) -> bytes:
    """
    Преобразование DataFrame в байты для сохранения в файл
    
    Args:
        df (pd.DataFrame): DataFrame для преобразования
        extension (str): Расширение файла (.csv, .xlsx и т.д.)
        encoding (str): Кодировка для текстовых файлов
        separator (str): Разделитель для CSV-файлов
        
    Returns:
        bytes: Содержимое файла в виде байтов
    """
    logger.info(f"Преобразование DataFrame ({len(df)} строк, {len(df.columns)} колонок) в байты")
    buffer = io.BytesIO()
    
    try:
        if extension.lower() in ['.xlsx', '.xls']:
            # Для Excel-файлов
            logger.info("Сохранение в формате Excel")
            df.to_excel(buffer, index=False, engine='openpyxl')
        elif extension.lower() == '.csv':
            # Для CSV-файлов
            logger.info(f"Сохранение в формате CSV (кодировка: {encoding}, разделитель: '{separator}')")
            df.to_csv(buffer, index=False, encoding=encoding, sep=separator)
        else:
            # По умолчанию сохраняем как CSV
            logger.warning(f"Неизвестное расширение файла: {extension}, сохраняем как CSV")
            df.to_csv(buffer, index=False, encoding=encoding, sep=separator)
        
        buffer.seek(0)
        content = buffer.getvalue()
        logger.info(f"DataFrame успешно преобразован в байты, размер: {len(content)} байт")
        return content
    except Exception as e:
        logger.error(f"Ошибка при преобразовании DataFrame в байты: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Не удалось преобразовать DataFrame в байты: {str(e)}")

def check_bucket_exists(bucket_name: str) -> bool:
    """Проверяет существование бакета в Supabase."""
    try:
        buckets = supabase_client.storage.list_buckets()
        logger.info(f"Найдены бакеты: {[b['name'] for b in buckets]}")
        return any(bucket['name'] == bucket_name for bucket in buckets)
    except Exception as e:
        logger.error(f"Ошибка при проверке бакета: {str(e)}")
        return False 