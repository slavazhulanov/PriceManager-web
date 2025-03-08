import os
import json
import time
import uuid
import logging
import traceback
from http.server import BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("register_file")

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

def detect_encoding(content):
    """
    Определение кодировки файла
    """
    try:
        import chardet
        result = chardet.detect(content)
        encoding = result['encoding']
        confidence = result['confidence']
        logger.info(f"Определена кодировка: {encoding} (уверенность: {confidence:.2f})")
        return encoding or 'utf-8'
    except Exception as e:
        logger.error(f"Ошибка при определении кодировки: {str(e)}")
        return 'utf-8'  # по умолчанию

def detect_separator(content, encoding):
    """
    Определение разделителя в CSV файле
    """
    try:
        sample = content[:4096].decode(encoding)
        
        # Подсчитываем количество разных разделителей
        separators = {',': 0, ';': 0, '\t': 0, '|': 0}
        
        for separator in separators.keys():
            # Берем первую строку (предполагаемый заголовок)
            if '\n' in sample:
                first_line = sample.split('\n')[0]
                separators[separator] = first_line.count(separator)
        
        # Определяем наиболее вероятный разделитель
        max_count = max(separators.values())
        best_separator = ','  # по умолчанию
        
        for sep, count in separators.items():
            if count == max_count and max_count > 0:
                best_separator = sep
                break
        
        logger.info(f"Определен разделитель: '{best_separator}'")
        return best_separator
    except Exception as e:
        logger.error(f"Ошибка при определении разделителя: {str(e)}")
        return ','  # по умолчанию

def get_file_content(stored_filename):
    """
    Получение содержимого файла из Supabase Storage
    """
    try:
        logger.info(f"Запрос файла: {stored_filename}")
        
        supabase = get_supabase_client()
        if not supabase:
            logger.error(f"Не удалось инициализировать Supabase клиент для файла {stored_filename}")
            return None
        
        bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
        folder = os.environ.get("SUPABASE_FOLDER", "uploads")
        
        # Получаем файл из Supabase Storage
        file_path = f"{folder}/{stored_filename}" if folder else stored_filename
        
        try:
            response = supabase.storage.from_(bucket_name).download(file_path)
            logger.info(f"Файл получен из Supabase, размер: {len(response)} байт")
            return response
        except Exception as e:
            logger.error(f"Ошибка при получении файла из Supabase: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Критическая ошибка при получении файла: {str(e)}")
        logger.error(f"Полная трассировка:\n{traceback.format_exc()}")
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
        """Обработка POST запросов для регистрации загруженного файла"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Парсим JSON данные
            data = json.loads(post_data)
            file_info = data.get('fileInfo')
            
            if not file_info or not file_info.get('stored_filename'):
                raise ValueError("Отсутствует информация о файле")
                
            stored_filename = file_info.get('stored_filename')
            original_filename = file_info.get('original_filename')
            file_type = file_info.get('file_type')
            
            logger.info(f"Регистрация файла: {stored_filename} (оригинал: {original_filename})")
            
            # Получаем содержимое файла для определения кодировки и разделителя
            file_content = get_file_content(stored_filename)
            
            if not file_content:
                raise ValueError(f"Не удалось получить содержимое файла {stored_filename}")
                
            # Определяем кодировку и разделитель
            encoding = detect_encoding(file_content)
            separator = detect_separator(file_content, encoding)
            
            # Формируем ответ с полной информацией о файле
            file_info_response = {
                "id": f"file-{uuid.uuid4()}",
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "file_type": file_type,
                "encoding": encoding,
                "separator": separator
            }
            
            logger.info(f"Файл успешно зарегистрирован: {stored_filename}")
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(file_info_response).encode())
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации файла: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Отправляем ответ с ошибкой
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            error_msg = {"error": f"Ошибка при регистрации файла: {str(e)}"}
            self.wfile.write(json.dumps(error_msg).encode()) 