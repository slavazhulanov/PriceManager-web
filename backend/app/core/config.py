import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator

# Определение базового каталога проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    # Базовые настройки приложения
    APP_NAME: str = "Price Manager API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API для управления ценами и сравнения файлов"
    
    # Настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = False  # По умолчанию выключен отладочный режим
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Настройки Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "price-manager")
    SUPABASE_FOLDER: str = os.getenv("SUPABASE_FOLDER", "files")
    
    # Настройки логирования
    LOG_LEVEL: str = "DEBUG"  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR: str = "logs"
    
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
    IS_VERCEL: str = os.getenv("VERCEL", "0")
    # Всегда используем Supabase Storage
    USE_CLOUD_STORAGE: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
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
            print("WARNING: SECRET_KEY слишком короткий для продакшн! Рекомендуется использовать ключ длиной не менее 32 символов")
        return v

    # Валидатор для CORS_ORIGINS
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

settings = Settings()

# Создаем директорию для демо данных
demo_data_dir = os.path.join(settings.BASE_DIR, 'demo_data')
os.makedirs(demo_data_dir, exist_ok=True)

# Для отладки
if settings.DEBUG:
    print(f"Настройки приложения: {settings.dict()}") 