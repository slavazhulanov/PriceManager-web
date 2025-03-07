from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from app.models.file import FileInfo, PriceUpdate
from app.services.price_service import update_prices, save_updated_file

router = APIRouter()

@router.post("/update", response_model=List[PriceUpdate])
async def update_store_prices(
    updates: List[PriceUpdate] = Body(...),
    store_file: FileInfo = Body(...)
):
    """
    Обновление цен в прайс-листе магазина
    """
    # Проверка типа файла
    if store_file.file_type != "store":
        raise HTTPException(
            status_code=400,
            detail="Указан неверный тип файла. Необходимо указать файл магазина"
        )
    
    # Проверка наличия сопоставления колонок
    if not store_file.column_mapping:
        raise HTTPException(
            status_code=400,
            detail="Не указано сопоставление колонок для файла"
        )
    
    # Выполнение обновления цен
    updated_prices = update_prices(updates, store_file)
    
    return updated_prices

@router.post("/save")
async def save_updated_prices(
    store_file: FileInfo = Body(...),
    updates: List[PriceUpdate] = Body(...)
):
    """
    Сохранение обновленного прайс-листа магазина
    """
    # Сохранение обновленного файла
    result = save_updated_file(store_file, updates)
    
    return {
        "filename": result["filename"],
        "download_url": f"/uploads/{result['filename']}",
        "count": len(updates)
    } 