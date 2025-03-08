import os
import pandas as pd
from typing import List, Dict, Any
from app.models.file import FileInfo, ComparisonResult
from app.services.file_service import get_file_content, read_file, save_file
from app.core.config import settings
import logging
import traceback

logger = logging.getLogger("app.services.comparison")

def compare_files(supplier_file: FileInfo, store_file: FileInfo) -> ComparisonResult:
    """
    Сравнение прайс-листов поставщика и магазина
    """
    logger.info(f"Начало сравнения файлов: {supplier_file.stored_filename} и {store_file.stored_filename}")
    
    # Получаем содержимое файлов
    logger.info(f"Получение содержимого файла поставщика: {supplier_file.stored_filename}")
    supplier_content = get_file_content(supplier_file.stored_filename)
    
    # Если файл не найден, проверяем, не является ли он мок-файлом
    if not supplier_content and "mock_" in supplier_file.stored_filename:
        logger.warning(f"Не удалось получить мок-файл поставщика: {supplier_file.stored_filename}. Попытка создания нового файла.")
        try:
            # Создаем базовый пример файла
            sample_content = "article,name,price,quantity\n1001,Product 1,100.00,10\n1002,Product 2,200.00,20\n1003,Product 3,300.00,30".encode('utf-8')
            # Сохраняем файл в Supabase
            save_file(supplier_file.stored_filename, sample_content)
            # Повторно пытаемся получить содержимое
            supplier_content = get_file_content(supplier_file.stored_filename)
            logger.info(f"Создан и получен мок-файл поставщика: {supplier_file.stored_filename}")
        except Exception as e:
            logger.error(f"Не удалось создать мок-файл поставщика: {str(e)}")
    
    logger.info(f"Получение содержимого файла магазина: {store_file.stored_filename}")
    store_content = get_file_content(store_file.stored_filename)
    
    # Если файл не найден, проверяем, не является ли он мок-файлом
    if not store_content and "mock_" in store_file.stored_filename:
        logger.warning(f"Не удалось получить мок-файл магазина: {store_file.stored_filename}. Попытка создания нового файла.")
        try:
            # Создаем базовый пример файла
            sample_content = "article,name,price,quantity\n1001,Product 1,150.00,5\n1002,Product 2,250.00,15\n1004,Product 4,400.00,25".encode('utf-8')
            # Сохраняем файл в Supabase
            save_file(store_file.stored_filename, sample_content)
            # Повторно пытаемся получить содержимое
            store_content = get_file_content(store_file.stored_filename)
            logger.info(f"Создан и получен мок-файл магазина: {store_file.stored_filename}")
        except Exception as e:
            logger.error(f"Не удалось создать мок-файл магазина: {str(e)}")
    
    if not supplier_content:
        error_msg = f"ОШИБКА: Не удалось получить содержимое файла поставщика: {supplier_file.stored_filename}"
        logger.error(error_msg)
        logger.error(f"Оригинальное имя файла: {supplier_file.original_filename}")
        logger.error(f"URL файла: {supplier_file.file_url}")
        logger.error(f"Проверьте существование файла в Supabase и политики доступа")
        raise ValueError(f"Не удалось получить содержимое файла поставщика: {supplier_file.original_filename}")
        
    if not store_content:
        error_msg = f"ОШИБКА: Не удалось получить содержимое файла магазина: {store_file.stored_filename}"
        logger.error(error_msg)
        logger.error(f"Оригинальное имя файла: {store_file.original_filename}")
        logger.error(f"URL файла: {store_file.file_url}")
        logger.error(f"Проверьте существование файла в Supabase и политики доступа")
        raise ValueError(f"Не удалось получить содержимое файла магазина: {store_file.original_filename}")
    
    logger.info(f"Оба файла успешно загружены: {supplier_file.stored_filename} ({len(supplier_content)} байт) и {store_file.stored_filename} ({len(store_content)} байт)")
    
    # Определяем расширения файлов
    supplier_extension = os.path.splitext(supplier_file.stored_filename)[1]
    store_extension = os.path.splitext(store_file.stored_filename)[1]
    
    logger.info(f"Расширения файлов: поставщик - {supplier_extension}, магазин - {store_extension}")
    
    try:
        # Чтение файлов
        logger.info(f"Чтение файла поставщика с кодировкой {supplier_file.encoding}, разделителем '{supplier_file.separator}'")
        supplier_df = read_file(
            supplier_content,
            supplier_extension, 
            supplier_file.encoding, 
            supplier_file.separator
        )
        
        logger.info(f"Чтение файла магазина с кодировкой {store_file.encoding}, разделителем '{store_file.separator}'")
        store_df = read_file(
            store_content,
            store_extension, 
            store_file.encoding, 
            store_file.separator
        )
        
        logger.info(f"Файлы успешно прочитаны. Размеры: поставщик - {len(supplier_df)} строк, магазин - {len(store_df)} строк")
        
        # Логируем информацию о колонках
        logger.info(f"Колонки файла поставщика: {', '.join(supplier_df.columns.tolist())}")
        logger.info(f"Колонки файла магазина: {', '.join(store_df.columns.tolist())}")
    except Exception as e:
        logger.error(f"ОШИБКА при чтении файлов: {str(e)}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        raise ValueError(f"Ошибка при обработке файлов: {str(e)}")
    
    # Получение имен колонок с артикулами и ценами
    supplier_article_col = supplier_file.column_mapping.article_column
    supplier_price_col = supplier_file.column_mapping.price_column
    supplier_name_col = supplier_file.column_mapping.name_column
    
    store_article_col = store_file.column_mapping.article_column
    store_price_col = store_file.column_mapping.price_column
    store_name_col = store_file.column_mapping.name_column
    
    logger.info(f"Используемые колонки - Поставщик: артикул='{supplier_article_col}', цена='{supplier_price_col}', наименование='{supplier_name_col}'")
    logger.info(f"Используемые колонки - Магазин: артикул='{store_article_col}', цена='{store_price_col}', наименование='{store_name_col}'")
    
    # Проверка существования колонок
    missing_cols = []
    for col_name in [supplier_article_col, supplier_price_col]:
        if col_name not in supplier_df.columns:
            missing_cols.append(f"колонка '{col_name}' отсутствует в файле поставщика")
    
    for col_name in [store_article_col, store_price_col]:
        if col_name not in store_df.columns:
            missing_cols.append(f"колонка '{col_name}' отсутствует в файле магазина")
    
    if missing_cols:
        error_message = f"Ошибка сопоставления колонок: {', '.join(missing_cols)}"
        logger.error(error_message)
        raise ValueError(error_message)
    
    # Сопоставление по артикулам
    # Преобразуем артикулы в строки для соответствия
    logger.info("Преобразование артикулов в строки для корректного сравнения")
    supplier_df[supplier_article_col] = supplier_df[supplier_article_col].astype(str)
    store_df[store_article_col] = store_df[store_article_col].astype(str)
    
    # Результаты сравнения
    matches = []
    missing_in_store = []
    missing_in_supplier = []
    
    # Создаем словарь артикулов магазина для быстрого поиска
    logger.info("Создание словаря артикулов магазина для оптимизации поиска")
    store_articles_dict = {}
    for _, store_row in store_df.iterrows():
        store_article = store_row[store_article_col]
        store_articles_dict[store_article] = store_row
    
    # Поиск совпадающих артикулов
    logger.info("Начало сопоставления товаров по артикулам")
    
    match_count = 0
    missing_in_store_count = 0
    
    for idx, (_, supplier_row_data) in enumerate(supplier_df.iterrows()):
        if idx % 1000 == 0 and idx > 0:
            logger.info(f"Обработано {idx} товаров поставщика. Найдено совпадений: {match_count}, отсутствуют в магазине: {missing_in_store_count}")
        
        supplier_article = supplier_row_data[supplier_article_col]
        supplier_price = supplier_row_data[supplier_price_col]
        supplier_name = supplier_row_data.get(supplier_name_col) if supplier_name_col else None
        
        # Проверка наличия артикула в словаре магазина
        if supplier_article in store_articles_dict:
            store_row = store_articles_dict[supplier_article]
            store_price = store_row[store_price_col]
            store_name = store_row.get(store_name_col) if store_name_col else None
            
            # Проверка на числовые значения цен
            try:
                # Очистка и преобразование строк цен в числа
                supplier_price_str = str(supplier_price).replace(',', '.').strip()
                store_price_str = str(store_price).replace(',', '.').strip()
                
                # Удаление нечисловых символов (кроме точки)
                supplier_price_str = ''.join(c for c in supplier_price_str if c.isdigit() or c == '.')
                store_price_str = ''.join(c for c in store_price_str if c.isdigit() or c == '.')
                
                supplier_price_float = float(supplier_price_str)
                store_price_float = float(store_price_str)
                
                price_diff = supplier_price_float - store_price_float
                
                # Вычисление разницы в процентах с обработкой деления на ноль
                if store_price_float != 0:
                    price_diff_percent = price_diff / store_price_float * 100
                else:
                    # Если цена в магазине равна нулю, но цена поставщика не нулевая
                    if supplier_price_float > 0:
                        price_diff_percent = 100  # 100% разница (считаем как полное увеличение)
                    else:
                        price_diff_percent = 0
                    logger.warning(f"Нулевая цена в магазине для артикула {supplier_article}, процентная разница установлена в {price_diff_percent}")
                
                matches.append({
                    "article": supplier_article,
                    "supplier_price": supplier_price_float,
                    "store_price": store_price_float,
                    "price_diff": price_diff,
                    "price_diff_percent": price_diff_percent,
                    "supplier_name": supplier_name,
                    "store_name": store_name,
                })
                
                match_count += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка конвертации цен для артикула {supplier_article}: {str(e)}. Поставщик: '{supplier_price}', Магазин: '{store_price}'")
        else:
            try:
                missing_in_store.append({
                    "article": supplier_article,
                    "supplier_price": float(str(supplier_price).replace(',', '.').strip()),
                    "supplier_name": supplier_name,
                })
                missing_in_store_count += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка конвертации цены поставщика для артикула {supplier_article}: {str(e)}. Значение: '{supplier_price}'")
    
    logger.info(f"Завершено сопоставление товаров поставщика. Всего: {len(supplier_df)}, совпадений: {match_count}, отсутствуют в магазине: {missing_in_store_count}")
    
    # Поиск артикулов, которые есть в магазине, но нет у поставщика
    missing_in_supplier_count = 0
    logger.info("Поиск товаров, отсутствующих у поставщика")
    
    # Создаем словарь артикулов поставщика для быстрого поиска
    supplier_articles_set = set(supplier_df[supplier_article_col].tolist())
    
    for idx, (_, store_row_data) in enumerate(store_df.iterrows()):
        if idx % 1000 == 0 and idx > 0:
            logger.info(f"Обработано {idx} товаров магазина. Отсутствуют у поставщика: {missing_in_supplier_count}")
        
        store_article = store_row_data[store_article_col]
        
        # Проверка, есть ли артикул у поставщика
        if store_article not in supplier_articles_set:
            store_price = store_row_data[store_price_col]
            store_name = store_row_data.get(store_name_col) if store_name_col else None
            
            try:
                missing_in_supplier.append({
                    "article": store_article,
                    "store_price": float(str(store_price).replace(',', '.').strip()),
                    "store_name": store_name,
                })
                missing_in_supplier_count += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка конвертации цены магазина для артикула {store_article}: {str(e)}. Значение: '{store_price}'")
    
    logger.info(f"Завершен поиск товаров, отсутствующих у поставщика. Всего: {missing_in_supplier_count}")
    
    # Сортировка результатов по разнице в процентах
    logger.info("Сортировка результатов по разнице в процентах")
    matches.sort(key=lambda x: abs(x["price_diff_percent"]), reverse=True)
    
    # Создание результата
    result = ComparisonResult(
        matches=matches,
        missing_in_store=missing_in_store,
        missing_in_supplier=missing_in_supplier
    )
    
    logger.info(f"Сравнение завершено успешно. Найдено: совпадений - {len(matches)}, товаров без аналогов в магазине - {len(missing_in_store)}, товаров без аналогов у поставщика - {len(missing_in_supplier)}")
    
    return result 