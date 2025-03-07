import os
import pandas as pd
from typing import List, Dict, Any
from app.models.file import FileInfo, ComparisonResult
from app.services.file_service import get_file_content, read_file
from app.core.config import settings

def compare_files(supplier_file: FileInfo, store_file: FileInfo) -> ComparisonResult:
    """
    Сравнение прайс-листов поставщика и магазина
    """
    # Получаем содержимое файлов
    supplier_content = get_file_content(supplier_file.stored_filename)
    store_content = get_file_content(store_file.stored_filename)
    
    if not supplier_content or not store_content:
        raise ValueError("Не удалось получить содержимое файлов")
    
    # Определяем расширения файлов
    supplier_extension = os.path.splitext(supplier_file.stored_filename)[1]
    store_extension = os.path.splitext(store_file.stored_filename)[1]
    
    # Чтение файлов
    supplier_df = read_file(
        supplier_content,
        supplier_extension, 
        supplier_file.encoding, 
        supplier_file.separator
    )
    
    store_df = read_file(
        store_content,
        store_extension, 
        store_file.encoding, 
        store_file.separator
    )
    
    # Получение имен колонок с артикулами и ценами
    supplier_article_col = supplier_file.column_mapping.article_column
    supplier_price_col = supplier_file.column_mapping.price_column
    supplier_name_col = supplier_file.column_mapping.name_column
    
    store_article_col = store_file.column_mapping.article_column
    store_price_col = store_file.column_mapping.price_column
    store_name_col = store_file.column_mapping.name_column
    
    # Сопоставление по артикулам
    # Преобразуем артикулы в строки для соответствия
    supplier_df[supplier_article_col] = supplier_df[supplier_article_col].astype(str)
    store_df[store_article_col] = store_df[store_article_col].astype(str)
    
    # Результаты сравнения
    matches = []
    missing_in_store = []
    missing_in_supplier = []
    
    # Поиск совпадающих артикулов
    for _, supplier_row in supplier_df.iterrows():
        supplier_article = supplier_row[supplier_article_col]
        supplier_price = supplier_row[supplier_price_col]
        supplier_name = supplier_row.get(supplier_name_col) if supplier_name_col else None
        
        # Поиск соответствующего артикула в магазине
        store_matches = store_df[store_df[store_article_col] == supplier_article]
        
        if not store_matches.empty:
            store_row = store_matches.iloc[0]
            store_price = store_row[store_price_col]
            store_name = store_row.get(store_name_col) if store_name_col else None
            
            matches.append({
                "article": supplier_article,
                "supplier_price": float(supplier_price),
                "store_price": float(store_price),
                "price_diff": float(supplier_price) - float(store_price),
                "price_diff_percent": (float(supplier_price) - float(store_price)) / float(store_price) * 100 if float(store_price) != 0 else 0,
                "supplier_name": supplier_name,
                "store_name": store_name,
            })
        else:
            missing_in_store.append({
                "article": supplier_article,
                "supplier_price": float(supplier_price),
                "supplier_name": supplier_name,
            })
    
    # Поиск артикулов, которые есть в магазине, но нет у поставщика
    for _, store_row in store_df.iterrows():
        store_article = store_row[store_article_col]
        store_price = store_row[store_price_col]
        store_name = store_row.get(store_name_col) if store_name_col else None
        
        # Проверка, есть ли артикул у поставщика
        supplier_matches = supplier_df[supplier_df[supplier_article_col] == store_article]
        
        if supplier_matches.empty:
            missing_in_supplier.append({
                "article": store_article,
                "store_price": float(store_price),
                "store_name": store_name,
            })
    
    # Сортировка результатов по разнице в процентах
    matches.sort(key=lambda x: abs(x["price_diff_percent"]), reverse=True)
    
    return ComparisonResult(
        matches=matches,
        missing_in_store=missing_in_store,
        missing_in_supplier=missing_in_supplier
    ) 