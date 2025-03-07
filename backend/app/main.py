from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.api import api_router
from app.core.config import settings

app = FastAPI(
    title="PriceManager API",
    description="API для работы с прайс-листами",
    version="1.0.0"
)

# Настройка CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров
app.include_router(api_router, prefix="/api")

# Создаем директорию для временных файлов, если её нет
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Подключаем статическую директорию для загруженных файлов
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {"message": "PriceManager API работает"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 