import sys
import os

# Добавляем путь к директории backend в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Напрямую создаем FastAPI приложение здесь
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json

# Создаем приложение FastAPI
app = FastAPI(
    title="PriceManager API",
    description="API для работы с прайс-листами",
    version="1.0.0"
)

# Настройка CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все для Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем базовый маршрут для проверки работоспособности
@app.get("/")
async def root():
    return {"message": "PriceManager API работает"}

@app.get("/api/v1")
async def api_root():
    return {"message": "PriceManager API v1"}

# Прямой обработчик для Vercel Serverless Functions
async def handler(request, context):
    # Преобразуем запрос Vercel в формат для FastAPI
    path = request.get("path", "/")
    http_method = request.get("httpMethod", "GET")
    headers = request.get("headers", {})
    query_params = request.get("queryStringParameters", {})
    body = request.get("body", "")
    
    # Простой маршрутизатор
    if path == "/" and http_method == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "PriceManager API работает"})
        }
    elif path.startswith("/api/v1") and http_method == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "PriceManager API v1"})
        }
    else:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Not found"})
        }