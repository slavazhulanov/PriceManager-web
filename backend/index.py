import json
import logging
import datetime 
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vercel_api")

# ==========================================================================
# Реализуем поддержку для внутреннего механизма Vercel
# ==========================================================================

# Этот класс необходим для совместимости с Vercel
class BaseHTTPRequestHandler:
    def __init__(self, *args, **kwargs):
        pass
    
    # Все методы, которые Vercel может ожидать
    def handle(self):
        pass
    
    def setup(self):
        pass
    
    def finish(self):
        pass
    
    def do_GET(self):
        pass
    
    def do_POST(self):
        pass
    
    def do_OPTIONS(self):
        pass

# Создаем обработчик, который наследуется от BaseHTTPRequestHandler
class VercelHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        # Заглушка для метода GET
        pass
    
    def do_POST(self):
        # Заглушка для метода POST
        pass
    
    def do_OPTIONS(self):
        # Заглушка для метода OPTIONS
        pass

# ==========================================================================
# Экспортируем необходимые объекты для Vercel
# ==========================================================================

# Экспорт класса для Vercel
Handler = VercelHandler

# ==========================================================================
# Основная функция обработчика
# ==========================================================================

def handler(event, context):
    """
    Функция обработчик для запросов в среде Vercel
    """
    try:
        logger.info(f"Получен запрос: {event.get('method')} {event.get('path')}")
        
        # Заголовки CORS
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        # Обработка OPTIONS запросов
        if event.get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Получаем путь и метод
        path = event.get('path', '')
        method = event.get('method', '')
        
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
                
                # Создаем тестовый URL и информацию о файле
                file_id = str(uuid.uuid4())
                upload_url = f"https://example.com/upload/{file_id}"
                
                response_data = {
                    'uploadUrl': upload_url,
                    'fileInfo': {
                        'id': file_id,
                        'original_filename': file_name,
                        'stored_filename': f"{file_id}_{file_name}",
                        'file_type': file_type,
                        'encoding': 'utf-8',
                        'separator': ','
                    }
                }
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(response_data)
                }
            except Exception as e:
                logger.error(f"Ошибка при обработке upload_url: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Внутренняя ошибка: {str(e)}'
                    })
                }
        
        # Обработка запроса на регистрацию файла
        if path == '/api/v1/files/register' and method == 'POST':
            try:
                body = {}
                if 'body' in event:
                    try:
                        body = json.loads(event['body']) if event['body'] else {}
                    except:
                        pass
                
                file_info = body.get('fileInfo', {
                    'id': str(uuid.uuid4()),
                    'original_filename': 'test-file.csv'
                })
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(file_info)
                }
            except Exception as e:
                logger.error(f"Ошибка при обработке register: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Внутренняя ошибка: {str(e)}'
                    })
                }
        
        # Общий обработчик для неизвестных маршрутов
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
                'error': f'Серверная ошибка: {str(e)}'
            })
        } 