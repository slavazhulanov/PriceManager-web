from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import pandas as pd
import io
from supabase import create_client
import time
import traceback
import cgi
import uuid
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("vercel_handler")

# Функция для получения Supabase клиента
def get_supabase_client():
    """
    Инициализация клиента Supabase
    """
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        logger.info(f"Инициализация Supabase клиента: URL={supabase_url[:20] if supabase_url else 'None'}..., KEY={supabase_key[:10] if supabase_key else 'None'}...")
        
        if not supabase_url or not supabase_key:
            logger.error(f"Отсутствуют переменные окружения SUPABASE_URL или SUPABASE_KEY")
            return None
        
        client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase клиент успешно инициализирован")
        return client
    except Exception as e:
        logger.error(f"Не удалось инициализировать Supabase клиент: {str(e)}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        return None

# Функция для получения содержимого файла из Supabase
def get_file_content(stored_filename):
    """
    Получение содержимого файла из Supabase Storage
    """
    try:
        logger.info(f"[GET_FILE] Запрос файла: {stored_filename}")
        
        # Кеширование файлов в памяти для быстрого доступа
        if not hasattr(get_file_content, 'file_cache'):
            get_file_content.file_cache = {}
            logger.info(f"[GET_FILE] Инициализирован кеш файлов")
        
        # Проверяем кеш
        if stored_filename in get_file_content.file_cache:
            cache_size = len(get_file_content.file_cache[stored_filename])
            logger.info(f"[GET_FILE] Файл найден в кеше: {stored_filename}, размер: {cache_size} байт")
            return get_file_content.file_cache[stored_filename]
        
        # Получаем клиент Supabase
        supabase = get_supabase_client()
        if not supabase:
            logger.error(f"[GET_FILE] Не удалось получить клиент Supabase")
            return None
        
        bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
        folder = os.environ.get("SUPABASE_FOLDER", "uploads")
        
        # Получаем файл из Supabase Storage
        file_path = f"{folder}/{stored_filename}" if folder else stored_filename
        
        try:
            # Получаем файл через API
            response = supabase.storage.from_(bucket_name).download(file_path)
            
            # Сохраняем в кеш
            if response:
                get_file_content.file_cache[stored_filename] = response
                logger.info(f"[GET_FILE] Файл получен и сохранен в кеше: {stored_filename}, размер: {len(response)} байт")
            else:
                logger.warning(f"[GET_FILE] Получен пустой ответ при загрузке файла: {stored_filename}")
            
            return response
        except Exception as download_error:
            logger.error(f"[GET_FILE] Ошибка при загрузке файла: {str(download_error)}")
            logger.error(f"[GET_FILE] Трассировка: {traceback.format_exc()}")
            return None
            
    except Exception as e:
        logger.error(f"[GET_FILE] Ошибка при получении файла: {str(e)}")
        logger.error(f"[GET_FILE] Трассировка: {traceback.format_exc()}")
        return None

# Функция для чтения и анализа файла
def read_file(file_content, extension, encoding, separator):
    """
    Чтение файла из содержимого с учетом расширения и кодировки
    """
    try:
        if extension in ['.xlsx', '.xls']:
            # Для Excel-файлов
            df = pd.read_excel(io.BytesIO(file_content))
            return df
        else:  # CSV
            # Проверка исходных данных
            logger.info(f"Чтение CSV-файла с кодировкой {encoding} и разделителем '{separator}'")
            
            try:
                df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
                return df
            except Exception as e:
                logger.error(f"Ошибка при чтении CSV файла: {str(e)}")
                return None
                
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {str(e)}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        return None

# HTTP-обработчик для Vercel Serverless Function
class VercelHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Обработка OPTIONS запросов для CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(''.encode())

    def do_GET(self):
        """Обработка GET запросов"""
        try:
            # Базовая обработка GET запросов
            if self.path == '/' or self.path == '/api':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write('{"message": "PriceManager API работает"}'.encode())
            elif self.path.startswith('/api/v1'):
                # Обработка API запросов
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write('{"message": "API v1 endpoint"}'.encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write('{"error": "Not found"}'.encode())
        except Exception as e:
            logger.error(f"Ошибка при обработке GET запроса: {str(e)}")
            logger.error(f"Трассировка: {traceback.format_exc()}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Internal server error: {str(e)}"}).encode())

    def do_POST(self):
        """Обработка POST запросов"""
        try:
            # Базовая обработка POST запросов
            if self.path.startswith('/api/v1'):
                # Обработка API запросов
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"message": "POST to API v1"}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write('{"error": "Not found"}'.encode())
        except Exception as e:
            logger.error(f"Ошибка при обработке POST запроса: {str(e)}")
            logger.error(f"Трассировка: {traceback.format_exc()}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Internal server error: {str(e)}"}).encode())

# Функция-обработчик для Vercel
def handler(event, context):
    """
    Основная функция-обработчик для Vercel Serverless
    Должна возвращать класс, который является подклассом BaseHTTPRequestHandler
    """
    return VercelHandler
