from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger("app.services.file_cache")

# Простой кеш для хранения содержимого файлов
file_cache: Dict[str, Dict[str, Any]] = {}

def cache_file_content(filename: str, content: bytes) -> None:
    """
    Сохраняет содержимое файла в кеше
    """
    logger.info(f"Кеширование файла: {filename}, размер: {len(content)} байт")
    file_cache[filename] = {
        "content": content,
        "timestamp": time.time()
    }
    logger.info(f"Файл {filename} добавлен в кеш, текущий размер кеша: {len(file_cache)} файлов")

def get_cached_content(filename: str) -> Optional[bytes]:
    """
    Получает содержимое файла из кеша
    """
    file_data = file_cache.get(filename)
    if file_data:
        logger.info(f"Файл {filename} найден в кеше, размер: {len(file_data['content'])} байт, возраст: {time.time() - file_data['timestamp']:.1f} сек")
        return file_data["content"]
    
    logger.info(f"Файл {filename} не найден в кеше")
    return None

def clear_old_cache(max_age: int = 3600) -> None:
    """
    Очищает старые записи из кеша
    max_age - максимальное время хранения записи в секундах (по умолчанию 1 час)
    """
    logger.info(f"Очистка кеша, текущий размер: {len(file_cache)} файлов")
    current_time = time.time()
    old_keys = [k for k, v in file_cache.items() if current_time - v["timestamp"] > max_age]
    
    for key in old_keys:
        file_size = len(file_cache[key]["content"]) if "content" in file_cache[key] else "Неизвестно"
        del file_cache[key]
        logger.info(f"Устаревший файл {key} удален из кеша (размер: {file_size} байт)")
    
    logger.info(f"Очистка кеша завершена, удалено {len(old_keys)} файлов, осталось: {len(file_cache)} файлов") 