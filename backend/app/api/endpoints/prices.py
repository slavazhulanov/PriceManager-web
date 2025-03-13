from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Request
from app.models.file import FileInfo, PriceUpdate
from app.services import file_service
from app.core.config import settings
import logging
import os
import uuid
import pandas as pd

router = APIRouter()
logger = logging.getLogger("app.api.prices")

@router.post("/update", response_model=List[PriceUpdate])
async def update_store_prices(
    request: Request,
    updates: List[PriceUpdate] = Body(...),
    store_file: FileInfo = Body(...)
):
    """
    Обновление цен в прайс-листе магазина
    """
    # Получаем идентификатор запроса
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"[{request_id}] Запрос на обновление {len(updates)} цен в файле {store_file.stored_filename}")
    
    # Проверка типа файла
    if store_file.file_type != "store":
        logger.error(f"[{request_id}] Указан неверный тип файла: {store_file.file_type}")
        raise HTTPException(
            status_code=400,
            detail="Указан неверный тип файла. Необходимо указать файл магазина"
        )
    
    # Проверка наличия сопоставления колонок
    if not store_file.column_mapping:
        logger.error(f"[{request_id}] Не указано сопоставление колонок для файла {store_file.stored_filename}")
        raise HTTPException(
            status_code=400,
            detail="Не указано сопоставление колонок для файла"
        )
    
    # Проверка корректности обновлений цен
    invalid_updates = []
    for i, update in enumerate(updates):
        if update.new_price <= 0:
            invalid_updates.append({
                "index": i,
                "article": update.article,
                "new_price": update.new_price,
                "error": "Новая цена должна быть положительной"
            })
    
    if invalid_updates:
        logger.error(f"[{request_id}] Найдены некорректные обновления цен: {invalid_updates}")
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Найдены некорректные обновления цен",
                "invalid_updates": invalid_updates
            }
        )
    
    # Выполнение обновления цен
    try:
        updated_prices = update_prices(updates, store_file)
        logger.info(f"[{request_id}] Успешно обновлено {len(updated_prices)} цен")
        return updated_prices
    except Exception as e:
        logger.error(f"[{request_id}] Ошибка при обновлении цен: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении цен: {str(e)}"
        )

@router.post("/save", response_model=Dict)
async def save_updated_file(
    request: Request,
    store_file: FileInfo = Body(...),
    updates: List[PriceUpdate] = Body(...)
):
    """
    Сохранение обновленного файла с новыми ценами
    """
    try:
        # Определяем, находимся ли мы в облачной среде (Vercel)
        is_vercel = settings.IS_VERCEL
        
        # Генерируем имя файла
        real_filename = f"updated_{uuid.uuid4()}.csv"
        logger.info(f"Генерируем файл: {real_filename}")
        
        # Создаем DataFrame с обновленными данными
        df = pd.DataFrame({
            "Артикул": [update.article for update in updates],
            "Наименование товара": [update.store_name for update in updates],
            "Цена магазина": [update.new_price for update in updates]
        })
        
        # Получаем байты для сохранения
        file_bytes = file_service.dataframe_to_bytes(
            df, 
            '.csv', 
            'UTF-8-SIG', 
            ','
        )
        
        # Сохраняем файл с помощью универсальной функции
        save_path = file_service.save_file(real_filename, file_bytes)
        logger.info(f"Файл успешно сохранен: {save_path}")
        
        # В зависимости от типа пути возвращаем результат
        # Для Supabase будет полный URL, для локального хранилища - путь
        if save_path.startswith('http'):
            # Supabase URL
            download_url = save_path
        else:
            # Локальный путь
            download_url = f"/api/v1/files/download/{real_filename}"
            
        return {
            "filename": real_filename,
            "download_url": download_url,
            "count": len(updates)
        }
    except Exception as e:
        logger.error(f"Ошибка при сохранении обновленного файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении обновленного файла: {str(e)}")

def update_prices(updates: List[PriceUpdate], store_file: FileInfo) -> List[PriceUpdate]:
    """
    Обновляет цены в соответствии с полученными данными
    
    Args:
        updates: Список обновлений цен
        store_file: Информация о файле магазина
        
    Returns:
        List[PriceUpdate]: Список обновленных цен
    """
    # Здесь может быть логика обновления цен
    # В текущей реализации просто возвращаем полученные обновления
    return updates 