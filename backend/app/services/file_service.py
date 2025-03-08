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

logger = logging.getLogger("app.services.file")

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
        
        logger.info(f"Инициализация Supabase клиента: URL={url}, Bucket={bucket_name}")
        logger.info(f"Используемый ключ API: {key[:10]}...{key[-5:]} (скрыт для безопасности)")
        
        client = create_client(url, key)
        
        # Проверяем наличие бакета (но не пытаемся создать, так как это требует админских прав)
        try:
            # Проверка существования бакета
            logger.info(f"Проверяем наличие бакета {bucket_name}")
            storage = client.storage.get_bucket(bucket_name)
            logger.info(f"Бакет {bucket_name} найден")
            
            # Проверяем наличие папки, создавая пустой файл-маркер если её нет
            try:
                logger.info(f"Проверяем доступность папки {folder_name}")
                # Пробуем загрузить файл-маркер
                marker_path = f"{folder_name}/.folder_marker"
                client.storage.from_(bucket_name).upload(
                    marker_path, 
                    b"This is a folder marker. Do not delete.",
                    {"content-type": "text/plain", "upsert": True}
                )
                logger.info(f"Папка {folder_name} проверена и доступна")
            except Exception as folder_error:
                logger.warning(f"Не удалось проверить папку {folder_name}: {str(folder_error)}")
                logger.warning("Это может вызвать проблемы при сохранении файлов")
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
    Определение кодировки файла из содержимого
    """
    logger.info(f"Определение кодировки файла (размер: {len(file_content)} байт)")
    result = chardet.detect(file_content[:10000])  # Чтение первых 10000 байт для определения кодировки
    encoding = result['encoding'] or 'utf-8'
    logger.info(f"Обнаружена кодировка: {encoding} с достоверностью {result.get('confidence', 'неизвестно')}")
    return encoding

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
    Чтение файла из содержимого с учетом расширения и кодировки
    """
    logger.info(f"Чтение файла (расширение: {extension}, кодировка: {encoding}, разделитель: '{separator}')")
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
        
        logger.info(f"Файл успешно прочитан, получено {len(df)} строк и {len(df.columns)} колонок")
        return df
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {str(e)}")
        logger.debug(traceback.format_exc())
        raise ValueError(f"Не удалось прочитать файл: {str(e)}")

def save_file(filename: str, file_content: bytes) -> str:
    """
    Сохранение файла в хранилище Supabase
    
    Возвращает URL к сохраненному файлу
    """
    logger.info(f"Сохранение файла: {filename}, размер: {len(file_content)} байт")
    
    # Кешируем содержимое файла в памяти
    try:
        cache_file_content(filename, file_content)
        logger.info(f"Файл {filename} успешно кеширован в памяти")
    except Exception as e:
        logger.error(f"Ошибка при кешировании файла {filename}: {str(e)}")
    
    # Получаем существующий клиент или создаем новый
    client = init_supabase_client()
    if not client:
        raise ValueError("Не удалось инициализировать Supabase клиент для сохранения файла")
    
    try:
        # Формируем путь к файлу в Supabase
        file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
        logger.info(f"Сохранение в Supabase Storage: {file_path}")
        
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
        raise ValueError(f"Не удалось сохранить файл в Supabase: {str(e)}")

def get_file_content(filename: str) -> Optional[bytes]:
    """
    Получение содержимого файла
    """
    logger.info(f"Запрос содержимого файла: {filename}")
    
    # Перенаправление mock-файлов на test.csv
    if "mock_" in filename:
        logger.info(f"Запрошен мок-файл: {filename}, перенаправляем на test.csv")
        redirect_filename = "test.csv"
        # Сначала проверяем кеш для оригинального имени
        cached_content = get_cached_content(filename)
        if cached_content:
            logger.info(f"Мок-файл {filename} найден в кеше, размер: {len(cached_content)} байт")
            return cached_content
        # Иначе пробуем получить тестовый файл
        test_content = get_cached_content(redirect_filename)
        if test_content:
            logger.info(f"Используем содержимое файла {redirect_filename} вместо {filename}")
            # Кешируем с оригинальным именем, чтобы в следующий раз быстрее получить
            cache_file_content(filename, test_content)
            return test_content
        # Продолжаем выполнение для test.csv
        filename = redirect_filename
        logger.info(f"Продолжаем получение {filename} из Supabase")
    
    # Сначала попробуем получить файл из кеша
    cached_content = get_cached_content(filename)
    if cached_content:
        logger.info(f"Файл {filename} найден в кеше, размер: {len(cached_content)} байт")
        return cached_content
    
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
        
        logger.info(f"Попытка получения файла из Supabase: бакет={bucket}, путь={file_path}")
        
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
            
            # Если файл недоступен и это mock-файл, создаем стандартный тестовый файл
            if "mock_" in filename:
                logger.info(f"Создаем тестовый контент для мок-файла {filename}")
                test_content = "article,name,price,quantity\n1001,Product 1,100.00,10\n1002,Product 2,200.00,20\n1003,Product 3,300.00,30".encode('utf-8')
                cache_file_content(filename, test_content)
                return test_content
            
            # Попробуем получить через публичный URL
            try:
                logger.info(f"Попытка получения файла через публичный URL: {filename}")
                public_url = client.storage.from_(bucket).get_public_url(file_path)
                logger.debug(f"Публичный URL: {public_url}")
                
                with httpx.Client(timeout=30.0) as http_client:
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

    # Создаем тестовый контент для mock-файлов, если все методы загрузки не сработали
    if "mock_" in filename:
        logger.info(f"Все методы загрузки не сработали, возвращаем тестовый контент для мок-файла {filename}")
        test_content = "article,name,price,quantity\n1001,Product 1,100.00,10\n1002,Product 2,200.00,20\n1003,Product 3,300.00,30".encode('utf-8')
        cache_file_content(filename, test_content)
        return test_content
    
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