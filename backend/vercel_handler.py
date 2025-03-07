import json

# Прямой обработчик для Vercel Serverless Functions
def handler(event, context):
    # Преобразуем запрос Vercel в формат для API
    path = event.get("path", "/")
    http_method = event.get("httpMethod", "GET")
    
    # Простой маршрутизатор
    if path == "/" and http_method == "GET":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": "PriceManager API работает"})
        }
    elif path.startswith("/api/v1") and http_method == "GET":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"message": "PriceManager API v1"})
        }
    else:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": "Not found"})
        }