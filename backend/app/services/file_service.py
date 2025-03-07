import os
import pandas as pd
import chardet
import io
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from app.core.config import settings

# Инициализация клиента Supabase, если включены настройки для облачного хранилища
supabase_client: Optional[Client] = None
if settings.USE_CLOUD_STORAGE and settings.SUPABASE_URL and settings.SUPABASE_KEY:
    supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def detect_encoding(file_content: bytes) -> str:
    """
    Определение кодировки файла из содержимого
    """
    result = chardet.detect(file_content[:10000])  # Чтение первых 10000 байт для определения кодировки
    return result['encoding'] or 'utf-8'

def detect_separator(file_content: bytes, encoding: str) -> str:
    """
    Определение разделителя в CSV-файле из содержимого
    """
    text = file_content.decode(encoding, errors='replace')
    first_line = text.split('\n')[0]
    
    # Проверка наиболее распространенных разделителей
    separators = [',', ';', '\t', '|']
    counts = {sep: first_line.count(sep) for sep in separators}
    
    # Выбор разделителя с наибольшим количеством вхождений
    max_separator = max(counts.items(), key=lambda x: x[1])
    
    if max_separator[1] > 0:
        return max_separator[0]
    
    # Если не удалось определить разделитель, по умолчанию используем запятую
    return ','

def get_columns(file_content: bytes, extension: str, encoding: str, separator: str) -> List[str]:
    """
    Получение списка колонок из содержимого файла
    """
    try:
        if extension.lower() in ['.xlsx', '.xls']:
            # Для Excel-файлов
            df = pd.read_excel(io.BytesIO(file_content))
        elif extension.lower() == '.csv':
            # Для CSV-файлов
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
        else:
            # Пробуем прочитать как CSV
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
        
        return df.columns.tolist()
    except Exception as e:
        # В случае ошибки возвращаем пустой список
        print(f"Ошибка при чтении файла: {str(e)}")
        return []

def read_file(file_content: bytes, extension: str, encoding: str, separator: str) -> pd.DataFrame:
    """
    Чтение содержимого файла в DataFrame
    """
    if extension.lower() in ['.xlsx', '.xls']:
        return pd.read_excel(io.BytesIO(file_content))
    elif extension.lower() == '.csv':
        return pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
    else:
        # Пробуем прочитать как CSV
        return pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)

def save_file(filename: str, file_content: bytes) -> str:
    """
    Сохранение файла в хранилище
    
    В случае локального хранилища - сохраняет на диск
    В случае облачного хранилища (Supabase) - загружает в бакет
    
    Возвращает путь или URL к сохраненному файлу
    """
    if not settings.USE_CLOUD_STORAGE:
        # Сохранение в локальное хранилище
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
            
        return file_path
    else:
        # Сохранение в Supabase Storage
        if not supabase_client:
            raise ValueError("Supabase client не инициализирован")
        
        # Формируем путь к файлу в Supabase
        file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
        
        # Загружаем файл в Supabase Storage
        response = supabase_client.storage.from_(settings.SUPABASE_BUCKET).upload(
            file_path,
            file_content,
            {"content-type": "application/octet-stream"}
        )
        
        # Возвращаем публичный URL для доступа к файлу
        public_url = supabase_client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
        
        return public_url

def get_file_content(filename: str) -> Optional[bytes]:
    """
    Получение содержимого файла из хранилища
    
    В случае локального хранилища - читает с диска
    В случае облачного хранилища (Supabase) - загружает из бакета
    
    Возвращает содержимое файла в виде байтов
    """
    try:
        if not settings.USE_CLOUD_STORAGE:
            # Чтение из локального хранилища
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            
            if not os.path.exists(file_path):
                return None
                
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            # Чтение из Supabase Storage
            if not supabase_client:
                raise ValueError("Supabase client не инициализирован")
            
            # Формируем путь к файлу в Supabase
            file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
            
            # Загружаем содержимое файла
            response = supabase_client.storage.from_(settings.SUPABASE_BUCKET).download(file_path)
            
            return response
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {str(e)}")
        return None 