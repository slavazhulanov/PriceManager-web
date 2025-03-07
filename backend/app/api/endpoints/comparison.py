from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from app.models.file import FileInfo, ComparisonResult
from app.services.comparison_service import compare_files

router = APIRouter()

@router.post("/compare", response_model=ComparisonResult)
async def compare_price_lists(
    supplier_file: FileInfo = Body(...),
    store_file: FileInfo = Body(...)
):
    """
    Сравнение двух прайс-листов (поставщика и магазина)
    """
    # Проверка типов файлов
    if supplier_file.file_type != "supplier" or store_file.file_type != "store":
        raise HTTPException(
            status_code=400,
            detail="Неверные типы файлов. Необходимо указать файл поставщика и файл магазина"
        )
    
    # Проверка наличия сопоставления колонок
    if not supplier_file.column_mapping or not store_file.column_mapping:
        raise HTTPException(
            status_code=400,
            detail="Не указано сопоставление колонок для файлов"
        )
    
    # Выполнение сравнения
    result = compare_files(supplier_file, store_file)
    
    return result 