def application(environ, start_response):
    """WSGI-совместимое приложение для Vercel."""
    
    # Получаем путь из запроса
    path = environ.get('PATH_INFO', '')
    
    # Определяем ответы для разных маршрутов
    if path == '/':
        status = '200 OK'
        headers = [
            ('Content-type', 'application/json'),
        ]
        response_body = '{"message": "PriceManager API работает"}'
    elif path.startswith('/api/v1'):
        status = '200 OK'
        headers = [
            ('Content-type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type'),
        ]
        response_body = '{"message": "PriceManager API v1"}'
    else:
        status = '404 Not Found'
        headers = [
            ('Content-type', 'application/json'),
        ]
        response_body = '{"error": "Not found"}'
    
    # Отправляем ответ
    start_response(status, headers)
    return [response_body.encode()] 