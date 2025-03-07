import sys
import os

# Добавляем путь к директории backend в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Напрямую создаем FastAPI приложение здесь
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

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

# Подключаем Mangum для поддержки AWS Lambda и Vercel
from mangum import Mangum
handler = Mangum(app)