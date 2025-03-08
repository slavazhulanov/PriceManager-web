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
    Сравнение прайс-листов поставщика и магазина
    """
    try:
        # Логируем информацию о запросе
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"
        
        logger.info(f"[{request_id}] Запрос на сравнение файлов от {client_ip}: "
                   f"supplier={supplier_file.stored_filename}, store={store_file.stored_filename}")
        
        # Проверяем, существуют ли мок-файлы, и создаем их при необходимости
        if "mock_" in supplier_file.stored_filename:
            logger.info(f"[{request_id}] Проверка мок-файла поставщика: {supplier_file.stored_filename}")
            content = get_file_content(supplier_file.stored_filename)
            if not content:
                logger.warning(f"[{request_id}] Мок-файл поставщика не найден, создаем новый: {supplier_file.stored_filename}")
                sample_content = "article,name,price,quantity\n1001,Product 1,100.00,10\n1002,Product 2,200.00,20\n1003,Product 3,300.00,30".encode('utf-8')
                try:
                    save_file(supplier_file.stored_filename, sample_content)
                    logger.info(f"[{request_id}] Мок-файл поставщика создан: {supplier_file.stored_filename}")
                except Exception as e:
                    logger.error(f"[{request_id}] Ошибка при создании мок-файла поставщика: {str(e)}")
            
        if "mock_" in store_file.stored_filename:
            logger.info(f"[{request_id}] Проверка мок-файла магазина: {store_file.stored_filename}")
            content = get_file_content(store_file.stored_filename)
            if not content:
                logger.warning(f"[{request_id}] Мок-файл магазина не найден, создаем новый: {store_file.stored_filename}")
                sample_content = "article,name,price,quantity\n1001,Product 1,150.00,5\n1002,Product 2,250.00,15\n1004,Product 4,400.00,25".encode('utf-8')
                try:
                    save_file(store_file.stored_filename, sample_content)
                    logger.info(f"[{request_id}] Мок-файл магазина создан: {store_file.stored_filename}")
                except Exception as e:
                    logger.error(f"[{request_id}] Ошибка при создании мок-файла магазина: {str(e)}")
        
        # Выполняем сравнение
        result = compare_files(supplier_file, store_file)
        
        logger.info(f"[{request_id}] Сравнение успешно выполнено")
        return result
    except ValueError as ve:
        logger.error(f"Ошибка валидации при сравнении файлов: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Ошибка при сравнении файлов: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сравнении файлов: {str(e)}") 