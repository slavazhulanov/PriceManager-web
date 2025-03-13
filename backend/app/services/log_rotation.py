import os
import gzip
import shutil
from datetime import datetime, timedelta
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

def compress_log_file(file_path: str) -> None:
    """
    Сжимает лог-файл в gzip формат
    """
    try:
        with open(file_path, 'rb') as f_in:
            with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logger.info(f"Файл {file_path} успешно сжат")
    except Exception as e:
        logger.error(f"Ошибка при сжатии файла {file_path}: {str(e)}")

def rotate_logs() -> None:
    """
    Ротация лог-файлов:
    - Сжимает файлы старше 1 дня
    - Удаляет сжатые файлы старше 30 дней
    """
    try:
        logs_dir = Path(settings.LOG_DIR)
        if not logs_dir.exists():
            logger.warning(f"Директория логов {logs_dir} не существует")
            return

        current_date = datetime.now()
        
        # Обрабатываем все файлы в директории логов
        for file_path in logs_dir.glob("*.log"):
            try:
                # Получаем дату из имени файла
                file_date_str = file_path.stem.split("-")[-1]  # Формат: YYYY-MM-DD
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                
                # Если файл старше 1 дня - сжимаем
                if current_date - file_date > timedelta(days=1):
                    compress_log_file(str(file_path))
                    
            except (ValueError, IndexError):
                logger.warning(f"Не удалось определить дату из имени файла: {file_path}")
                continue
        
        # Удаляем старые сжатые файлы
        for file_path in logs_dir.glob("*.log.gz"):
            try:
                # Получаем дату из имени файла
                file_date_str = file_path.stem.split("-")[-1]  # Формат: YYYY-MM-DD
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                
                # Если файл старше 30 дней - удаляем
                if current_date - file_date > timedelta(days=30):
                    os.remove(file_path)
                    logger.info(f"Удален старый лог-файл: {file_path}")
                    
            except (ValueError, IndexError):
                logger.warning(f"Не удалось определить дату из имени файла: {file_path}")
                continue
                
    except Exception as e:
        logger.error(f"Ошибка при ротации логов: {str(e)}")

def get_logs_stats() -> dict:
    """
    Возвращает статистику по лог-файлам
    """
    try:
        logs_dir = Path(settings.LOG_DIR)
        if not logs_dir.exists():
            return {
                "status": "error",
                "message": "Директория логов не существует"
            }

        stats = {
            "total_size": 0,
            "files_count": 0,
            "compressed_files_count": 0,
            "oldest_file": None,
            "newest_file": None,
            "files": []
        }
        
        # Собираем информацию о файлах
        for file_path in logs_dir.glob("*.*"):
            if file_path.suffix in ['.log', '.gz']:
                file_stat = file_path.stat()
                file_info = {
                    "name": file_path.name,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "compressed": file_path.suffix == '.gz'
                }
                
                stats["files"].append(file_info)
                stats["total_size"] += file_stat.st_size
                
                if file_path.suffix == '.gz':
                    stats["compressed_files_count"] += 1
                else:
                    stats["files_count"] += 1
                
                # Обновляем информацию о самом старом и новом файле
                modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                if not stats["oldest_file"] or modified_time < datetime.fromisoformat(stats["oldest_file"]["modified"]):
                    stats["oldest_file"] = file_info
                if not stats["newest_file"] or modified_time > datetime.fromisoformat(stats["newest_file"]["modified"]):
                    stats["newest_file"] = file_info
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики логов: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        } 