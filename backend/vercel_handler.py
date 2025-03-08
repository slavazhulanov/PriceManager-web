from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import traceback
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("vercel_handler")

# Простая функция для генерации ответа
def generate_response(status_code, body, headers=None):
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

# HTTP обработчик для Vercel
class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        try:
            # Базовые эндпоинты
            if self.path == '/' or self.path == '/api':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'PriceManager API работает'}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode())
        except Exception as e:
            logger.error(f"Ошибка при обработке GET запроса: {str(e)}")
            logger.error(traceback.format_exc())
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Internal server error: {str(e)}'}).encode())

    def do_POST(self):
        """Обработка POST запросов"""
        try:
            if self.path.startswith('/api'):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'API endpoint'}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode())
        except Exception as e:
            logger.error(f"Ошибка при обработке POST запроса: {str(e)}")
            logger.error(traceback.format_exc())
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Internal server error: {str(e)}'}).encode())

    def do_OPTIONS(self):
        """Обработка OPTIONS запросов для CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(''.encode())

# Обработчик для Vercel Serverless Functions
def handler(event, context):
    """
    Обработчик запросов в формате AWS Lambda для Vercel
    """
    try:
        logger.info(f"Получен запрос: метод={event.get('httpMethod', 'unknown')}, путь={event.get('path', 'unknown')}")
        
        # Получаем метод и путь из события
        method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        
        # Обработка CORS preflight запросов
        if method == 'OPTIONS':
            return generate_response(200, '')
            
        # Базовый health check
        if path == '/' or path == '/api':
            return generate_response(200, {'message': 'PriceManager API работает', 'timestamp': str(datetime.now())})
            
        # API эндпоинты
        if path.startswith('/api/v1'):
            if method == 'GET':
                return generate_response(200, {'message': 'API GET endpoint', 'path': path})
            elif method == 'POST':
                # Получаем body запроса, если есть
                body = {}
                if 'body' in event:
                    try:
                        body = json.loads(event['body']) if event['body'] else {}
                    except:
                        logger.warning(f"Не удалось распарсить body запроса: {event.get('body')}")
                
                return generate_response(200, {'message': 'API POST endpoint', 'path': path, 'received_data': body})
        
        # Если запрос не совпал ни с одним маршрутом
        return generate_response(404, {'error': 'Not found', 'path': path})
        
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}")
        logger.error(traceback.format_exc())
        return generate_response(500, {'error': f'Internal server error: {str(e)}'})
