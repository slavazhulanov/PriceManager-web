from typing import Dict, Any, Optional
import time
import logging
import sys
from collections import OrderedDict

logger = logging.getLogger("app.services.file_cache")

# Максимальный размер кеша и время жизни файлов в кеше
MAX_CACHE_SIZE_MB = 200  # Максимальный размер кеша в МБ
MAX_CACHE_ENTRIES = 20    # Максимальное количество файлов в кеше
DEFAULT_CACHE_TTL = 3600  # Время жизни файла в кеше (1 час)

# Используем OrderedDict для поддержки LRU (Least Recently Used) функциональности
file_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

# Текущий размер кеша в байтах
current_cache_size = 0

def cache_file_content(filename: str, content: bytes) -> None:
    """
    Сохраняет содержимое файла в кеше с учетом ограничений размера
    """
    global current_cache_size, file_cache
    
    content_size = len(content)
    content_size_mb = content_size / (1024 * 1024)
    
    # Проверяем, не превышает ли размер файла максимально допустимый размер кеша
    if content_size_mb > MAX_CACHE_SIZE_MB:
        logger.warning(
            f"Файл {filename} слишком большой для кеширования: {content_size_mb:.2f} МБ > {MAX_CACHE_SIZE_MB} МБ"
        )
        return
    
    # Проверяем, есть ли файл уже в кеше
    if filename in file_cache:
        # Удаляем старую версию из размера кеша
        current_cache_size -= len(file_cache[filename]["content"])
        
    # Освобождаем место в кеше, если нужно
    while (current_cache_size + content_size) / (1024 * 1024) > MAX_CACHE_SIZE_MB or len(file_cache) >= MAX_CACHE_ENTRIES:
        if not file_cache:
            break
        # Удаляем самый старый элемент (LRU)
        oldest_key, oldest_value = file_cache.popitem(last=False)
        removed_size = len(oldest_value["content"])
        current_cache_size -= removed_size
        logger.info(
            f"Удален файл из кеша (LRU): {oldest_key}, освобождено {removed_size / (1024 * 1024):.2f} МБ, "
            f"текущий размер кеша: {current_cache_size / (1024 * 1024):.2f} МБ"
        )
    
    # Добавляем файл в кеш
    logger.info(f"Кеширование файла: {filename}, размер: {content_size_mb:.2f} МБ")
    file_cache[filename] = {
        "content": content,
        "timestamp": time.time(),
        "size": content_size
    }
    
    # Перемещаем файл в конец OrderedDict (обновляем LRU)
    file_cache.move_to_end(filename)
    
    # Обновляем текущий размер кеша
    current_cache_size += content_size
    
    # Логируем состояние кеша
    logger.info(
        f"Файл {filename} добавлен в кеш, текущий размер кеша: {current_cache_size / (1024 * 1024):.2f} МБ, "
        f"количество файлов: {len(file_cache)}"
    )

def get_cached_content(filename: str) -> Optional[bytes]:
    """
    Получает содержимое файла из кеша, если оно там есть и не устарело
    """
    if filename in file_cache:
        cache_entry = file_cache[filename]
        current_time = time.time()
        
        # Проверяем, не устарел ли кеш
        if current_time - cache_entry["timestamp"] <= DEFAULT_CACHE_TTL:
            # Перемещаем файл в конец OrderedDict (обновляем LRU)
            file_cache.move_to_end(filename)
            
            content_size_mb = len(cache_entry["content"]) / (1024 * 1024)
            logger.info(f"Получен файл из кеша: {filename}, размер: {content_size_mb:.2f} МБ")
            return cache_entry["content"]
        else:
            # Удаляем устаревшую запись
            content = file_cache.pop(filename)
            global current_cache_size
            current_cache_size -= len(content["content"])
            logger.info(f"Файл {filename} удален из кеша из-за истечения TTL ({DEFAULT_CACHE_TTL} сек)")
    
    return None

def clear_old_cache(max_age: int = DEFAULT_CACHE_TTL) -> None:
    """
    Очищает кеш от устаревших файлов
    
    Args:
        max_age (int): Максимальное время жизни файла в кеше в секундах
    """
    global current_cache_size, file_cache
    
    if not file_cache:
        logger.info("Кеш пуст, очистка не требуется")
        return
        
    current_time = time.time()
    keys_to_remove = []
    freed_size = 0
    
    # Находим устаревшие файлы
    for filename, cache_entry in file_cache.items():
        if current_time - cache_entry["timestamp"] > max_age:
            keys_to_remove.append(filename)
            freed_size += len(cache_entry["content"])
    
    # Удаляем устаревшие файлы
    for filename in keys_to_remove:
        file_cache.pop(filename)
    
    # Обновляем размер кеша
    current_cache_size -= freed_size
    
    if keys_to_remove:
        logger.info(
            f"Очистка кеша: удалено {len(keys_to_remove)} устаревших файлов, "
            f"освобождено {freed_size / (1024 * 1024):.2f} МБ, "
            f"текущий размер кеша: {current_cache_size / (1024 * 1024):.2f} МБ"
        )
    else:
        logger.debug("Очистка кеша: устаревших файлов не найдено")

def get_cache_stats() -> Dict[str, Any]:
    """
    Возвращает статистику по кешу для отладки
    """
    return {
        "entries_count": len(file_cache),
        "total_size_mb": current_cache_size / (1024 * 1024),
        "max_size_mb": MAX_CACHE_SIZE_MB,
        "files": [{
            "name": filename,
            "size_mb": len(cache_entry["content"]) / (1024 * 1024),
            "age_seconds": time.time() - cache_entry["timestamp"]
        } for filename, cache_entry in file_cache.items()]
    } 