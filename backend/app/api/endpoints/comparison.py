from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Request
from app.models.file import FileInfo, ComparisonResult
from app.services.comparison_service import compare_files
import os
from app.core.config import settings
import logging
import json
import traceback

logger = logging.getLogger("app.comparison")

router = APIRouter()

@router.post("/compare", response_model=ComparisonResult)
async def compare_price_lists(
    request: Request,
    supplier_file: FileInfo = Body(...),
    store_file: FileInfo = Body(...)
):
    """
    Сравнение двух прайс-листов (поставщика и магазина)
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else "unknown"
    
    logger.info(f"[{request_id}] Получен запрос на сравнение файлов")
    logger.info(f"[{request_id}] Файл поставщика: {supplier_file.original_filename} (сохранен как {supplier_file.stored_filename})")
    logger.info(f"[{request_id}] Файл магазина: {store_file.original_filename} (сохранен как {store_file.stored_filename})")
    
    # Проверяем наличие маппинга колонок
    if not supplier_file.column_mapping:
        logger.error(f"[{request_id}] Не указано сопоставление колонок для файла поставщика")
        logger.debug(f"[{request_id}] Данные файла поставщика: {json.dumps(supplier_file.dict(), default=str)}")
    else:
        logger.info(f"[{request_id}] Маппинг колонок файла поставщика: article={supplier_file.column_mapping.article_column}, price={supplier_file.column_mapping.price_column}, name={supplier_file.column_mapping.name_column}")
    
    if not store_file.column_mapping:
        logger.error(f"[{request_id}] Не указано сопоставление колонок для файла магазина")
        logger.debug(f"[{request_id}] Данные файла магазина: {json.dumps(store_file.dict(), default=str)}")
    else:
        logger.info(f"[{request_id}] Маппинг колонок файла магазина: article={store_file.column_mapping.article_column}, price={store_file.column_mapping.price_column}, name={store_file.column_mapping.name_column}")
    
    # Проверка типов файлов
    if supplier_file.file_type != "supplier" or store_file.file_type != "store":
        error_msg = f"Неверные типы файлов. Необходимо указать файл поставщика и файл магазина"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] Получены типы: поставщик={supplier_file.file_type}, магазин={store_file.file_type}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    # Проверка наличия сопоставления колонок
    if not supplier_file.column_mapping or not store_file.column_mapping:
        error_msg = "Не указано сопоставление колонок для файлов"
        logger.error(f"[{request_id}] {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    try:
        logger.info(f"[{request_id}] Запуск сравнения файлов")
        # Выполнение сравнения
        result = compare_files(supplier_file, store_file)
        
        # Логирование результатов
        if result:
            matches_count = len(result.matches) if result.matches else 0
            missing_in_store_count = len(result.missing_in_store) if result.missing_in_store else 0
            missing_in_supplier_count = len(result.missing_in_supplier) if result.missing_in_supplier else 0
            
            logger.info(f"[{request_id}] Сравнение успешно завершено:")
            logger.info(f"[{request_id}] Совпадающих товаров: {matches_count}")
            logger.info(f"[{request_id}] Товаров, отсутствующих в магазине: {missing_in_store_count}")
            logger.info(f"[{request_id}] Товаров, отсутствующих у поставщика: {missing_in_supplier_count}")
        else:
            logger.warning(f"[{request_id}] Сравнение завершено, но результат пустой")
        
        return result
    except ValueError as e:
        error_msg = f"Ошибка при сравнении файлов: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] Трассировка: {traceback.format_exc()}")
        
        # Проверяем содержимое директории uploads
        logger.info(f"[{request_id}] Содержимое директории {settings.UPLOAD_DIR}:")
        try:
            upload_contents = os.listdir(settings.UPLOAD_DIR)
            logger.info(f"[{request_id}] Файлы: {', '.join(upload_contents) if upload_contents else 'пусто'}")
        except Exception as dir_err:
            logger.error(f"[{request_id}] Ошибка при чтении директории: {str(dir_err)}")
        
        raise HTTPException(
            status_code=404,
            detail=f"Не удалось найти файлы для сравнения. Проверьте, что файлы загружены корректно. Ошибка: {str(e)}"
        )
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при сравнении файлов: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] Трассировка: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Произошла внутренняя ошибка сервера: {str(e)}"
        ) 