import logging
import json
from typing import Any, Dict

def get_logger(name: str) -> logging.Logger:
    """
    Создает и возвращает настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень логирования
    from app.core.config import settings
    logger.setLevel(settings.LOG_LEVEL)
    
    # Добавляем обработчик для консоли с человекочитаемым форматом
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    logger.addHandler(console_handler)
    
    return logger 