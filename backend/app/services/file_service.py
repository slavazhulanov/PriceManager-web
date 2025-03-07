import os
import pandas as pd
import chardet
import io
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from app.core.config import settings
from app.services.file_cache import cache_file_content, get_cached_content
import logging
import traceback

logger = logging.getLogger("app.services.file")

# Инициализация клиента Supabase, если включены настройки для облачного хранилища
supabase_client: Optional[Client] = None
if settings.USE_CLOUD_STORAGE and settings.SUPABASE_URL and settings.SUPABASE_KEY:
    logger.info("Инициализация Supabase клиента для облачного хранилища")
    supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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
    Сохранение файла в хранилище
    
    В случае локального хранилища - сохраняет на диск
    В случае облачного хранилища (Supabase) - загружает в бакет
    
    Возвращает путь или URL к сохраненному файлу
    """
    logger.info(f"Сохранение файла: {filename}, размер: {len(file_content)} байт")
    
    # Кешируем содержимое файла в памяти
    try:
        cache_file_content(filename, file_content)
        logger.info(f"Файл {filename} успешно кеширован в памяти")
    except Exception as e:
        logger.error(f"Ошибка при кешировании файла {filename}: {str(e)}")
    
    if not settings.USE_CLOUD_STORAGE:
        # Сохранение в локальное хранилище
        try:
            logger.info(f"Сохранение в локальное хранилище: {settings.UPLOAD_DIR}")
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Файл успешно сохранен по пути: {file_path}")
            
            # Проверяем наличие файла после сохранения
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Проверка файла: {file_path} существует, размер: {file_size} байт")
            else:
                logger.error(f"Проверка файла: {file_path} не существует после сохранения!")
                
            return file_path
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла в локальное хранилище: {str(e)}")
            logger.debug(traceback.format_exc())
            raise ValueError(f"Не удалось сохранить файл: {str(e)}")
    else:
        # Сохранение в Supabase Storage
        if not supabase_client:
            logger.error("Supabase client не инициализирован")
            raise ValueError("Supabase client не инициализирован")
        
        # Формируем путь к файлу в Supabase
        file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
        logger.info(f"Сохранение в Supabase Storage: {file_path}")
        
        try:
            # Загружаем файл в Supabase
            supabase_client.storage.from_(settings.SUPABASE_BUCKET).upload(
                file_path,
                file_content,
                {"content-type": "application/octet-stream"}
            )
            
            # Получаем публичный URL
            public_url = supabase_client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
            logger.info(f"Файл успешно загружен в Supabase, URL: {public_url}")
            
            return public_url
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла в Supabase: {str(e)}")
            logger.debug(traceback.format_exc())
            raise ValueError(f"Не удалось сохранить файл в облачное хранилище: {str(e)}")

def get_file_content(filename: str) -> Optional[bytes]:
    """
    Получение содержимого файла из хранилища
    
    В случае локального хранилища - читает с диска
    В случае облачного хранилища (Supabase) - загружает из бакета
    
    Возвращает содержимое файла в виде байтов
    """
    logger.info(f"Запрошено содержимое файла: {filename}")
    
    # Сначала пытаемся получить из кеша
    cached_content = get_cached_content(filename)
    if cached_content:
        logger.info(f"Файл {filename} получен из кеша, размер: {len(cached_content)} байт")
        return cached_content
    
    # Если в кеше нет, пробуем из хранилища
    try:
        if not settings.USE_CLOUD_STORAGE:
            # Чтение из локального хранилища
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            logger.info(f"Чтение файла из локального хранилища: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                
                # Проверим, есть ли что-то вообще в директории
                try:
                    dir_contents = os.listdir(settings.UPLOAD_DIR)
                    logger.info(f"Содержимое директории {settings.UPLOAD_DIR}: {', '.join(dir_contents) if dir_contents else 'пусто'}")
                except Exception as dir_err:
                    logger.error(f"Ошибка при чтении директории {settings.UPLOAD_DIR}: {str(dir_err)}")
                
                return None
                
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    logger.info(f"Файл успешно прочитан из локального хранилища, размер: {len(content)} байт")
                    # Кешируем содержимое
                    cache_file_content(filename, content)
                    return content
            except Exception as read_err:
                logger.error(f"Ошибка при чтении файла {file_path}: {str(read_err)}")
                logger.debug(traceback.format_exc())
                return None
        else:
            # Чтение из Supabase Storage
            if not supabase_client:
                logger.error("Supabase client не инициализирован")
                raise ValueError("Supabase client не инициализирован")
            
            # Формируем путь к файлу в Supabase
            file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
            logger.info(f"Чтение файла из Supabase Storage: {file_path}")
            
            try:
                # Загружаем содержимое файла
                content = supabase_client.storage.from_(settings.SUPABASE_BUCKET).download(file_path)
                logger.info(f"Файл успешно загружен из Supabase, размер: {len(content)} байт")
                
                # Кешируем содержимое
                cache_file_content(filename, content)
                return content
            except Exception as supabase_err:
                logger.error(f"Ошибка при загрузке файла из Supabase: {str(supabase_err)}")
                logger.debug(traceback.format_exc())
                return None
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении содержимого файла {filename}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None 