import uvicorn
import os
from app.core.config import settings

if __name__ == "__main__":
    # Для продакшн используем конфигурацию из переменных окружения
    # Отключаем режим перезагрузки (reload) в продакшн среде
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 