#!/usr/bin/env python
import os
import sys
import uvicorn
from app.core.config import settings

# Установка порта для бэкенда
PORT = 8000

# Запуск приложения с конфигурацией
if __name__ == "__main__":
    # Переопределение порта из параметров командной строки, если они есть
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            print(f"Ошибка: неверный формат порта. Используется порт по умолчанию {PORT}")
    
    # Обновляем настройки порта
    os.environ["PORT"] = str(PORT)
    
    # Запуск сервера
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=PORT,
        reload=False
    ) 