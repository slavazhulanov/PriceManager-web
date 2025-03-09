import json
import logging
import datetime
import os
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_api")

# Определяем класс для обработки HTTP запросов
class BaseHTTPRequestHandler:
    def __init__(self, *args, **kwargs):
        pass

# Наследуемся от базового класса
class VercelHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        pass
    
    def do_POST(self):
        pass
    
    def do_OPTIONS(self):
        pass

# Функция-обработчик для Vercel Serverless Functions
def handler(event, context):
    """
    Обработчик запросов API для Vercel
    """
    try:
        logger.info(f"Входящий запрос: {event.get('method')} {event.get('path')}")
        
        # Стандартные CORS заголовки
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        # Обработка OPTIONS (preflight CORS)
        if event.get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Получение пути и метода
        path = event.get('path', '')
        method = event.get('method', '')
        
        # Проверка здоровья API
        if path == '/api/health':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'status': 'ok',
                    'timestamp': datetime.datetime.now().isoformat()
                })
            }
        
        # Обработка запроса на получение URL для загрузки файла
        if path == '/api/v1/files/upload_url' and method == 'POST':
            try:
                body = {}
                if 'body' in event:
                    try:
                        body = json.loads(event['body']) if event['body'] else {}
                    except Exception as e:
                        logger.warning(f"Не удалось распарсить body запроса: {str(e)}")
                
                file_name = body.get('fileName', f'unknown-{uuid.uuid4()}.csv')
                file_type = body.get('fileType', 'unknown')
                
                # Тестовый URL и информация о файле
                file_id = str(uuid.uuid4())
                stored_filename = f"{file_id}_{file_name}"
                upload_url = "https://storage.example.com/upload/" + stored_filename
                
                file_info = {
                    'id': file_id,
                    'original_filename': file_name,
                    'stored_filename': stored_filename,
                    'file_type': file_type,
                    'encoding': 'utf-8',
                    'separator': ','
                }
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'uploadUrl': upload_url,
                        'fileInfo': file_info
                    })
                }
            except Exception as e:
                logger.error(f"Ошибка при обработке запроса upload_url: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Ошибка при обработке запроса: {str(e)}'
                    })
                }
        
        # Обработка запроса на регистрацию загруженного файла
        if path == '/api/v1/files/register' and method == 'POST':
            try:
                body = {}
                if 'body' in event:
                    try:
                        body = json.loads(event['body']) if event['body'] else {}
                    except:
                        logger.warning(f"Не удалось распарсить body запроса")
                
                file_info = body.get('fileInfo', {})
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(file_info)
                }
            except Exception as e:
                logger.error(f"Ошибка при обработке запроса register: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Ошибка при обработке запроса: {str(e)}'
                    })
                }
        
        # Обработка неизвестных маршрутов
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Маршрут не найден',
                'path': path,
                'method': method,
                'timestamp': datetime.datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Необработанная ошибка: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Внутренняя ошибка сервера: {str(e)}'
            })
        } 