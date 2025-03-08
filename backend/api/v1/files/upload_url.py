import os
import json
import time
import uuid
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("supabase_upload_url")

def get_supabase_client():
    """
    Инициализация клиента Supabase
    """
    from supabase import create_client
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    logger.info(f"Инициализация Supabase клиента: URL={supabase_url[:20] if supabase_url else None}...")
    
    if not supabase_url or not supabase_key:
        logger.error(f"Отсутствуют переменные окружения SUPABASE_URL или SUPABASE_KEY")
        return None
    try:
        client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase клиент успешно инициализирован")
        return client
    except Exception as e:
        logger.error(f"Не удалось инициализировать Supabase клиент: {str(e)}")
        return None

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Обработка CORS preflight запросов"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def do_POST(self):
        """Обработка POST запросов для генерации URL загрузки"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Парсим JSON данные
            data = json.loads(post_data)
            file_name = data.get('fileName')
            file_type = data.get('fileType')
            
            if not file_name:
                raise ValueError("Поле fileName обязательно")
                
            # Генерируем уникальное имя файла для хранения
            timestamp = int(time.time())
            file_extension = os.path.splitext(file_name)[1].lower()
            stored_filename = f"file_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
            
            # Инициализируем Supabase клиент
            client = get_supabase_client()
            if not client:
                raise ValueError("Не удалось инициализировать Supabase клиент")
            
            # Получаем настройки хранилища
            bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
            folder = os.environ.get("SUPABASE_FOLDER", "uploads")
            
            # Формируем путь к файлу в Supabase
            file_path = f"{folder}/{stored_filename}" if folder else stored_filename
            
            # Генерируем URL для загрузки с клиента напрямую
            logger.info(f"Генерация URL для загрузки файла: {file_path}")
            signed_url = client.storage.from_(bucket_name).create_signed_upload_url(file_path)
            
            # Формируем ответ
            response_data = {
                "uploadUrl": signed_url["signed_url"],
                "fileInfo": {
                    "stored_filename": stored_filename,
                    "original_filename": file_name,
                    "file_type": file_type,
                    "path": file_path,
                    "bucket": bucket_name
                }
            }
            
            logger.info(f"URL для загрузки успешно сгенерирован: {stored_filename}")
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            logger.error(f"Ошибка при генерации URL для загрузки: {str(e)}")
            
            # Отправляем ответ с ошибкой
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            error_msg = {"error": f"Ошибка при генерации URL для загрузки: {str(e)}"}
            self.wfile.write(json.dumps(error_msg).encode()) 