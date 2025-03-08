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
    Сохраняет обновленный файл с новыми ценами и возвращает ссылку для скачивания.
    
    Args:
        store_file: Информация о файле магазина
        updates: Список обновлений цен
    
    Returns:
        Dict: Информация о сохраненном файле (имя, URL для скачивания, количество обновлений)
    """
    logger.info(f"Получен запрос на сохранение обновленного файла с {len(updates)} обновлениями")
    
    try:
        # Определяем, находимся ли мы в облачной среде (Vercel)
        is_vercel = settings.IS_VERCEL
        
        # Проверяем, является ли файл моком
        is_mock_file = "mock_" in store_file.stored_filename if store_file.stored_filename else False
        
        if is_mock_file:
            logger.warning(f"Обнаружен мок-файл: {store_file.stored_filename}")
            
            # Генерируем реальное имя файла вместо мок-имени
            real_filename = f"updated_{uuid.uuid4()}.csv"
            logger.info(f"Генерируем файл на основе моковых данных: {real_filename}")
            
            # Создаем базовый пример файла
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
            
            try:
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
                # Если произошла ошибка при сохранении в Supabase
                logger.error(f"Ошибка при сохранении файла в Supabase: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Не удалось сохранить обновленный файл: {str(e)}"
                )
        
        # Для не-мок файлов идем обычным путем
        # Получаем содержимое исходного файла
        original_content = file_service.get_file_content(store_file.stored_filename)
        if not original_content:
            logger.error(f"Не удалось найти исходный файл: {store_file.stored_filename}")
            raise HTTPException(status_code=404, detail="Исходный файл не найден")
        
        # Читаем данные из исходного файла
        df = file_service.read_file(
            original_content,
            os.path.splitext(store_file.stored_filename)[1],
            store_file.encoding,
            store_file.separator
        )
        
        # Обновляем цены для выбранных товаров
        price_column = store_file.column_mapping.price_column
        article_column = store_file.column_mapping.article_column
        
        # Преобразуем артикулы к строковому типу для надежного сравнения
        df[article_column] = df[article_column].astype(str)
        
        # Создаем словарь для быстрого поиска
        updates_dict = {str(item.article): item.new_price for item in updates}
        
        # Обновляем цены
        count = 0
        for article, new_price in updates_dict.items():
            mask = df[article_column] == article
            if mask.any():
                df.loc[mask, price_column] = new_price
                count += 1
        
        logger.info(f"Обновлено {count} из {len(updates)} позиций")
        
        # Генерируем имя для обновленного файла
        new_filename = f"updated_{uuid.uuid4()}.{store_file.stored_filename.split('.')[-1]}"
        
        # Сохраняем обновленный файл
        file_bytes = file_service.dataframe_to_bytes(
            df, 
            os.path.splitext(new_filename)[1], 
            store_file.encoding, 
            store_file.separator
        )
        
        try:
            # Сохраняем файл с помощью универсальной функции
            save_path = file_service.save_file(new_filename, file_bytes)
            logger.info(f"Файл успешно сохранен: {save_path}")
            
            # В зависимости от типа пути возвращаем результат
            if save_path.startswith('http'):
                # Supabase URL
                download_url = save_path
            else:
                # Локальный путь
                download_url = f"/api/v1/files/download/{new_filename}"
                
            return {
                "filename": new_filename,
                "download_url": download_url,
                "count": count
            }
        except Exception as e:
            # Если произошла ошибка при сохранении в Supabase
            logger.error(f"Ошибка при сохранении файла в Supabase: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Не удалось сохранить обновленный файл: {str(e)}"
            )
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
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