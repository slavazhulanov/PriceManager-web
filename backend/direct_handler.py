import json
import datetime

# Простая функция для генерации стандартизованного ответа
def response(status_code, body, headers=None):
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

# Функция-обработчик для Vercel
def handler(event, context):
    """
    Минимальный обработчик для Vercel, без классов, чтобы избежать ошибок с BaseHTTPRequestHandler
    """
    try:
        # Получаем метод и путь запроса
        method = event.get('method', '')
        path = event.get('path', '')
        
        # Обработка OPTIONS запросов (CORS preflight)
        if method == 'OPTIONS':
            return response(200, '')
        
        # Обработка запроса на URL для загрузки файла
        if path == '/api/v1/files/upload_url' and method == 'POST':
            # Создаем тестовый ответ
            test_response = {
                'uploadUrl': 'https://example.com/upload-test',
                'fileInfo': {
                    'id': 'test-id-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                    'original_filename': 'test-file.csv'
                }
            }
            return response(200, test_response)
        
        # Обработка запроса на регистрацию файла
        if path == '/api/v1/files/register' and method == 'POST':
            # Получаем тело запроса
            body = {}
            if 'body' in event:
                try:
                    body = json.loads(event['body']) if event['body'] else {}
                except:
                    pass
            
            # Берем fileInfo из запроса или создаем тестовый
            file_info = body.get('fileInfo', {
                'id': 'register-test-id',
                'original_filename': 'registered-file.csv'
            })
            
            return response(200, file_info)
        
        # Обработка запроса проверки здоровья
        if path == '/api/health' or path == '/api/v1/health':
            return response(200, {
                'status': 'ok',
                'timestamp': datetime.datetime.now().isoformat()
            })
        
        # Обработка всех других запросов
        return response(404, {
            'error': 'Not found',
            'path': path,
            'method': method
        })
        
    except Exception as e:
        # Обработка ошибок
        return response(500, {
            'error': str(e)
        }) 