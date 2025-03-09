import http.server
import json
import os
import logging
import traceback
import datetime
from http.server import BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('vercel_handler')

def generate_response(status_code, body, headers=None):
    """
    Генерирует стандартизованный ответ для Vercel serverless функции
    """
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'message': 'GET запрос успешно обработан',
            'path': self.path,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        """Обработка POST запросов"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            data = {'raw': post_data}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'message': 'POST запрос успешно обработан',
            'path': self.path,
            'data': data,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Обработка OPTIONS запросов (для CORS)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def handler(event, context):
    """
    Основная функция-обработчик запросов Vercel
    
    :param event: событие запроса
    :param context: контекст выполнения
    :return: ответ в формате, ожидаемом Vercel
    """
    try:
        logger.info(f"Получен запрос: {event.get('method')} {event.get('path')}")
        
        # Проверка на запрос проверки здоровья
        if event.get('path') == '/api/health':
            return generate_response(200, {'status': 'ok', 'timestamp': datetime.datetime.now().isoformat()})
        
        # Получаем метод и путь запроса
        method = event.get('method', '')
        path = event.get('path', '')
        
        # Обрабатываем запросы к API
        if path.startswith('/api/'):
            # Чистый путь без префикса /api
            api_path = path[4:] if path.startswith('/api/') else path
            
            if method == 'OPTIONS':
                # Обработка preflight CORS запросов
                return generate_response(200, {})
            elif method == 'GET':
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
