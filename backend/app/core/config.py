import os
from typing import List
from pydantic_settings import BaseSettings

# Определение базового каталога проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    # Базовый каталог
    BASE_DIR: str = BASE_DIR
    
    # Базовые настройки API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PriceManager"
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "https://*.vercel.app"]
    
    # Настройки JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Настройки файлов
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # Настройки базы данных
    DATABASE_URL: str = f"sqlite:///./app.db"
    
    # Настройки хранилища
    USE_CLOUD_STORAGE: bool = False
    
    # Настройки Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET: str = "price-manager"
    SUPABASE_FOLDER: str = "uploads"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Создаем директорию для загруженных файлов, если не используем облачное хранилище
if not settings.USE_CLOUD_STORAGE:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Создаем директорию для демо данных
demo_data_dir = os.path.join(settings.BASE_DIR, 'demo_data')
os.makedirs(demo_data_dir, exist_ok=True) 