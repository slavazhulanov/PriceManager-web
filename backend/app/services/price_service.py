import os
import uuid
import pandas as pd
import io
from typing import List, Dict, Any
from app.models.file import FileInfo, PriceUpdate
from app.services.file_service import get_file_content, read_file, save_file
from app.core.config import settings

def update_prices(updates: List[PriceUpdate], store_file: FileInfo) -> List[PriceUpdate]:
    """
    Обновление цен в прайс-листе магазина и возвращение списка обновленных цен
    """
    # В этой версии мы просто возвращаем полученные обновления,
    # в реальном приложении здесь может быть логика проверки и обработки
    return updates

def save_updated_file(store_file: FileInfo, updates: List[PriceUpdate]) -> Dict[str, Any]:
    """
    Сохранение обновленного прайс-листа магазина
    """
    # Получаем содержимое файла
    file_content = get_file_content(store_file.stored_filename)
    if not file_content:
        raise ValueError("Не удалось получить содержимое файла")
    
    # Определяем расширение файла
    file_extension = os.path.splitext(store_file.stored_filename)[1]
    
    # Чтение файла
    df = read_file(
        file_content,
        file_extension, 
        store_file.encoding, 
        store_file.separator
    )
    
    # Получение имени колонки с артикулом и ценой
    article_col = store_file.column_mapping.article_column
    price_col = store_file.column_mapping.price_column
    
    # Преобразуем артикулы в строки для соответствия
    df[article_col] = df[article_col].astype(str)
    
    # Обновление цен
    for update in updates:
        article = update.article
        new_price = update.new_price
        
        # Найти индексы строк с соответствующим артикулом
        indices = df[df[article_col] == article].index
        
        # Обновить цены в этих строках
        for idx in indices:
            df.at[idx, price_col] = new_price
    
    # Создание нового имени файла с обновленными ценами
    new_filename = f"updated_{uuid.uuid4()}{file_extension}"
    
    # Сохранение файла в байтовый поток
    output = io.BytesIO()
    
    if file_extension.lower() in ['.xlsx', '.xls']:
        df.to_excel(output, index=False)
    else:
        df.to_csv(output, index=False, sep=store_file.separator, encoding=store_file.encoding)
    
    # Получаем содержимое байтового потока
    output.seek(0)
    updated_content = output.getvalue()
    
    # Сохранение файла
    save_file(new_filename, updated_content)
    
    # Создаем URL для скачивания
    download_url = f"/uploads/{new_filename}"
    
    return {
        "filename": new_filename,
        "download_url": download_url,
        "count": len(updates)
    } 