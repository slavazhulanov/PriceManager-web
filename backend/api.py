import json
import logging
import datetime
import os
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_api")

def handler(event, context):
    """
    Минимальный обработчик запросов API для Vercel
    """
    logger.info(f"Обработка запроса: {event.get('method')} {event.get('path')}")
    
    # Стандартные заголовки CORS
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    # Обработка OPTIONS (preflight CORS requests)
    if event.get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Получаем путь и метод
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
    
    # Обработка upload_url запроса для загрузки файлов
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
            
            # Генерация имени файла для хранения
            stored_filename = f"{uuid.uuid4()}_{file_name}"
            
            # В реальной реализации здесь был бы код для генерации URL для загрузки файла
            # Для демонстрации используем тестовые данные
            upload_url = "https://storage.example.com/upload/" + stored_filename
            
            file_info = {
                'id': str(uuid.uuid4()),
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
            
            # В реальном приложении здесь был бы код для сохранения информации о файле
            # Возвращаем полученную информацию о файле
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
    
    # Стандартный ответ для прочих запросов
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