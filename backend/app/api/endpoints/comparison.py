from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body, Request
from app.models.file import FileInfo, ComparisonResult
from app.services.comparison_service import compare_files
import os
from app.core.config import settings
import logging
import json
import traceback
from pydantic import BaseModel
from app.services.file_service import get_file_content
from app.services.file_cache import get_cached_content

logger = logging.getLogger("app.comparison")

router = APIRouter()

# Определяем модель для запроса сравнения на основе формата, отправляемого с фронтенда
class ComparisonRequest(BaseModel):
    supplier_file: Optional[FileInfo] = None
    store_file: Optional[FileInfo] = None
    # Поля, которые используются в api.ts
    file1Id: Optional[str] = None
    file2Id: Optional[str] = None
    identifierColumn: Optional[str] = None
    valueColumn: Optional[str] = None
    matchType: Optional[str] = None

# Глобальный кэш файлов для сохранения зарегистрированных файлов
# Будем хранить их по ID, чтобы потом находить
file_registry = {}

@router.post("/compare", response_model=ComparisonResult)
async def compare_price_lists(
    request: Request,
    compare_request: ComparisonRequest = Body(...)
):
    """
    Сравнение прайс-листов поставщика и магазина
    """
    try:
        logger.info(f"Получен запрос на сравнение файлов: {compare_request}")
        
        # Проверяем, какой формат запроса используется
        supplier_file = compare_request.supplier_file
        store_file = compare_request.store_file
        
        # Если используется формат с file1Id и file2Id (из api.ts)
        if not supplier_file and not store_file and compare_request.file1Id and compare_request.file2Id:
            file1_id = compare_request.file1Id
            file2_id = compare_request.file2Id
            
            logger.info(f"Используется формат запроса с ID файлов: file1Id={file1_id}, file2Id={file2_id}")
            
            # Проверяем наличие файлов в реестре
            if file1_id in file_registry and file2_id in file_registry:
                supplier_file = file_registry[file1_id]
                store_file = file_registry[file2_id]
                logger.info(f"Файлы найдены в реестре: supplier={supplier_file.original_filename}, store={store_file.original_filename}")
            else:
                # Это заглушка, в реальности нужно искать файлы в базе данных или другом хранилище
                # Создаем моковые объекты для тестирования
                logger.warning(f"Файлы не найдены в реестре, используем заглушечные данные")
                
                # Пример заглушечных данных для теста
                supplier_file = FileInfo(
                    id=file1_id,
                    original_filename=f"supplier_{file1_id}.csv",
                    stored_filename=f"file_{file1_id}.csv", 
                    file_type=FileType.SUPPLIER,
                    encoding="utf-8",
                    separator=",",
                    column_mapping={
                        "article_column": "Артикул",
                        "price_column": "Цена",
                        "name_column": "Наименование"
                    }
                )
                
                store_file = FileInfo(
                    id=file2_id,
                    original_filename=f"store_{file2_id}.csv",
                    stored_filename=f"file_{file2_id}.csv",
                    file_type=FileType.STORE,
                    encoding="utf-8",
                    separator=",",
                    column_mapping={
                        "article_column": "Артикул",
                        "price_column": "Цена", 
                        "name_column": "Наименование"
                    }
                )
                
                logger.warning(f"Созданы заглушечные объекты файлов для сравнения")
        
        # Если не указаны файлы для сравнения
        if not supplier_file or not store_file:
            logger.error("Не предоставлены файлы для сравнения")
            raise HTTPException(
                status_code=400, 
                detail="Необходимо предоставить два файла для сравнения: supplier_file и store_file или file1Id и file2Id."
            )
            
        # Проверяем типы файлов
        if supplier_file.file_type != "supplier" or store_file.file_type != "store":
            logger.error(f"Неверные типы файлов: supplier={supplier_file.file_type}, store={store_file.file_type}")
            raise HTTPException(
                status_code=400, 
                detail=f"Неверные типы файлов: supplier_file должен иметь тип 'supplier', store_file должен иметь тип 'store'."
            )
        
        # Проверяем наличие маппинга колонок
        logger.info(f"Проверка маппинга колонок перед сравнением:")
        logger.info(f"Маппинг поставщика: {supplier_file.column_mapping}")
        logger.info(f"Маппинг магазина: {store_file.column_mapping}")
        
        if not supplier_file.column_mapping or not store_file.column_mapping:
            logger.error("Отсутствует маппинг колонок для одного из файлов")
            raise HTTPException(
                status_code=400,
                detail="Необходимо настроить сопоставление колонок для обоих файлов перед сравнением."
            )
            
        # Выполняем сравнение
        result = compare_files(supplier_file, store_file)
        
        logger.info(f"Сравнение успешно выполнено")
        return result
    except ValueError as ve:
        logger.error(f"Ошибка валидации при сравнении файлов: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Ошибка при сравнении файлов: {str(e)}")
        logger.error(f"Полная ошибка: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сравнении файлов: {str(e)}")

# Добавляем метод для регистрации файла в реестре после загрузки
def register_file(file_info: FileInfo):
    """
    Регистрирует файл в реестре для последующего использования по ID
    """
    if file_info and file_info.id:
        file_registry[file_info.id] = file_info
        logger.info(f"Файл зарегистрирован в реестре: id={file_info.id}, filename={file_info.original_filename}")
    else:
        logger.warning(f"Попытка зарегистрировать файл без ID: {file_info}") 