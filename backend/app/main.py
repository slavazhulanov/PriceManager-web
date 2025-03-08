from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import time
import logging
import logging.config
import sys
from typing import Callable
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.responses import JSONResponse
import traceback

from app.api.api import api_router
from app.core.config import settings
from app.services.file_service import cleanup_old_files
from app.services.file_cache import clear_old_cache, get_cache_stats

# Настройка логирования
settings.setup_logs_directory()
logging_config = settings.get_logging_config()
logging.config.dictConfig(logging_config)

logger = logging.getLogger("app.main")

# Инициализация планировщика
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер жизненного цикла приложения
    """
    # Запуск приложения
    start_time = time.time()
    logger.info(f"Запуск приложения {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Режим отладки: {'включен' if settings.DEBUG else 'выключен'}")
    logger.info(f"Уровень логирования: {settings.LOG_LEVEL}")
    
    # Настройка и запуск планировщика
    logger.info("Инициализация планировщика задач")
    
    # Планировщик очистки кеша каждый час
    scheduler.add_job(
        clear_old_cache,
        'interval',
        hours=1,
        kwargs={"max_age": 3600}  # 1 час
    )
    
    # Планировщик очистки старых файлов в Supabase каждый день
    scheduler.add_job(
        cleanup_old_files,
        'interval',
        days=1,
        kwargs={"max_age_days": 7}  # 7 дней
    )
    
    scheduler.start()
    logger.info("Планировщик задач запущен")
    
    # Логируем информацию о запуске
    logger.info(f"Приложение запущено за {time.time() - start_time:.2f} секунд")
    
    yield
    
    # Остановка приложения
    logger.info("Остановка планировщика задач")
    scheduler.shutdown()
    
    logger.info("Приложение остановлено")

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# Middleware для установки уникального идентификатора запроса
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

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

# Добавление middleware CORS
origins = settings.parse_cors_origins()
logger.info(f"Настройка CORS для доменов: {origins}")

# Валидация и фильтрация CORS origins для продакшн
valid_origins = []
for origin in origins:
    # Проверка на потенциально опасные символы в origin
    if '*' in origin and not origin.startswith('https://*.'):
        logger.warning(f"Потенциально небезопасный CORS origin с wildcard: {origin}")
    
    # Проверка на использование HTTPS в продакшн
    if settings.DEBUG is False and origin.startswith('http://') and not origin.startswith('http://localhost'):
        logger.warning(f"Небезопасный HTTP origin в режиме продакшн: {origin}")
    else:
        valid_origins.append(origin)

logger.info(f"Итоговый список CORS origins: {valid_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=valid_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# Включаем роутер API
app.include_router(api_router, prefix=settings.API_V1_STR)

# Добавляем маршрут диагностики для проверки состояния приложения
@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности приложения
    """
    # Базовая информация о состоянии приложения
    health_info = {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "cache": get_cache_stats()
    }
    
    return health_info

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Глобальный обработчик исключений
    """
    error_id = uuid.uuid4()
    
    # Подробное логирование ошибки с уникальным идентификатором
    logger.error(
        f"Необработанное исключение [ID: {error_id}]: {str(exc)}", 
        exc_info=True,
        extra={
            "error_id": str(error_id),
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Формируем сообщение об ошибке для клиента в зависимости от режима отладки
    if settings.DEBUG:
        error_message = f"Внутренняя ошибка сервера: {str(exc)}"
        error_details = {"traceback": str(traceback.format_exc())}
    else:
        error_message = "Внутренняя ошибка сервера. Обратитесь к администратору."
        error_details = {"error_id": str(error_id)}
    
    return JSONResponse(
        status_code=500, 
        content={
            "error": error_message,
            "details": error_details
        }
    )

# Инициализация при запуске
@app.on_event("startup")
async def startup_event():
    logger.info("Инициализация завершена, приложение готово к обработке запросов")

@app.get("/")
async def root():
    logger.info("Запрос к корневому эндпоинту")
    return {"message": "PriceManager API работает"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск сервера...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 