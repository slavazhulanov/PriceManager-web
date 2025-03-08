import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator

# Определение базового каталога проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Инициализация логгера
logger = logging.getLogger("app.core.config")

class Settings(BaseSettings):
    # Базовые настройки приложения
    APP_NAME: str = "Price Manager API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API для управления ценами и сравнения файлов"
    
    # Настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False  # По умолчанию выключен отладочный режим
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = []
    
    # Настройки Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_BUCKET: str = "price-files"
    SUPABASE_FOLDER: str = "uploads"
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Настройки планировщика
    CLEANUP_INTERVAL: int = 86400  # Интервал очистки кеша в секундах (по умолчанию 1 день)
    
    # Дополнительные настройки
    TIMEZONE: str = "Europe/Moscow"
    
    # Базовый каталог
    BASE_DIR: str = BASE_DIR
    
    # Базовые настройки API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PriceManager"
    
    # Настройки JWT
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Настройки файлов
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # Настройки базы данных
    DATABASE_URL: str = f"sqlite:///./app.db"
    
    # Настройки хранилища
    # В Vercel всегда USE_CLOUD_STORAGE=true для работы с Supabase
    IS_VERCEL: bool = os.environ.get("VERCEL") == "1"
    # Всегда используем Supabase Storage
    USE_CLOUD_STORAGE: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию логирования на основе текущих настроек
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.LOG_FORMAT,
                },
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                    "timestamp": True
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default" if not self.DEBUG else "json",
                    "level": self.LOG_LEVEL,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json",
                    "filename": "logs/app.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 3,
                    "level": self.LOG_LEVEL,
                },
            },
            "loggers": {
                "app": {
                    "handlers": ["console", "file"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
                "app.services": {
                    "handlers": ["console", "file"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
                "app.api": {
                    "handlers": ["console", "file"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["console"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
                "fastapi": {
                    "handlers": ["console"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                }
            },
            "root": {
                "handlers": ["console"],
                "level": self.LOG_LEVEL,
            }
        }
    
    def parse_cors_origins(self) -> List[str]:
        """
        Парсит настройки CORS_ORIGINS в список строк
        """
        if isinstance(self.CORS_ORIGINS, str):
            try:
                # Пробуем распарсить как JSON
                return json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                # Если не получилось, разделяем по запятой
                return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

    def setup_logs_directory(self) -> None:
        """
        Создает директорию для логов, если она не существует
        """
        logs_dir = Path("logs")
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)

    # Валидация важных настроек безопасности
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v):
        if not v and os.environ.get("VERCEL") == "1":
            raise ValueError("SECRET_KEY должен быть установлен в продакшн окружении")
        if len(v) < 32:
            logger.warning("SECRET_KEY слишком короткий для продакшн! Рекомендуется использовать ключ длиной не менее 32 символов")
        return v

settings = Settings()

# Логируем информацию о конфигурации
logger.info(f"Начальная инициализация конфигурации")
logger.info(f"Окружение: {'Vercel (продакшен)' if settings.IS_VERCEL else 'Локальное'}")
logger.info(f"Использование Supabase Storage: Да")

# Для работы с Supabase нужны URL и ключ
if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    logger.warning(f"Не указаны SUPABASE_URL или SUPABASE_KEY!")
    logger.warning(f"Операции с файлами в Supabase будут недоступны")
else:
    logger.info(f"Настройки Supabase: URL={settings.SUPABASE_URL}, Bucket={settings.SUPABASE_BUCKET}, Folder={settings.SUPABASE_FOLDER}")

# Создаем директорию для демо данных
demo_data_dir = os.path.join(settings.BASE_DIR, 'demo_data')
os.makedirs(demo_data_dir, exist_ok=True)
logger.info(f"Создана директория для демо данных: {demo_data_dir}") 