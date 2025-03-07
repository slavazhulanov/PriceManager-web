from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import time
import logging
import sys
from typing import Callable
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.api import api_router
from app.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("app")

# Middleware для установки уникального идентификатора запроса
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app = FastAPI(
    title="PriceManager API",
    description="API для работы с прайс-листами",
    version="1.0.0"
)

# Добавляем middleware для request_id
app.add_middleware(RequestIDMiddleware)

# Middleware для логирования запросов и времени выполнения
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.info(f"[{request_id}] Начало запроса {request.method} {request.url.path}")
    
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[{request_id}] Завершено {request.method} {request.url.path} - Статус: {response.status_code}, Время: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[{request_id}] Ошибка при обработке {request.method} {request.url.path} - {str(e)}, Время: {process_time:.4f}s")
        raise

# Настройка CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров
logger.info(f"Подключение API роутера с префиксом {settings.API_V1_STR}")
app.include_router(api_router, prefix=settings.API_V1_STR)

# Проверка состояния системы при запуске
@app.on_event("startup")
async def startup_event():
    logger.info("=== Запуск приложения PriceManager API ===")
    
    # Создаем директорию для временных файлов, если её нет
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Проверка директории для загрузки файлов: {settings.UPLOAD_DIR}")
    
    # Проверка содержимого директории
    try:
        files = os.listdir(settings.UPLOAD_DIR)
        logger.info(f"Содержимое директории {settings.UPLOAD_DIR}: {len(files)} файлов")
        
        if files:
            for idx, file in enumerate(files[:10]):  # Логируем только первые 10 файлов
                file_path = os.path.join(settings.UPLOAD_DIR, file)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    logger.info(f"Файл {idx+1}/{len(files)}: {file} ({file_size} байт)")
            
            if len(files) > 10:
                logger.info(f"... и еще {len(files) - 10} файлов")
    except Exception as e:
        logger.error(f"Ошибка при проверке директории {settings.UPLOAD_DIR}: {str(e)}")
    
    # Проверка настроек
    logger.info(f"Настройки приложения:")
    logger.info(f"- API префикс: {settings.API_V1_STR}")
    logger.info(f"- CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"- Использование облачного хранилища: {'Да' if settings.USE_CLOUD_STORAGE else 'Нет'}")
    logger.info(f"- Максимальный размер загружаемого файла: {settings.MAX_UPLOAD_SIZE / (1024*1024):.2f} МБ")
    
    logger.info("=== Приложение PriceManager API запущено успешно ===")

# Создаем директорию для временных файлов
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Подключаем статическую директорию для загруженных файлов
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
logger.info(f"Статическая директория '/uploads' подключена")

@app.get("/")
async def root():
    logger.info("Запрос к корневому эндпоинту")
    return {"message": "PriceManager API работает"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск сервера...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 