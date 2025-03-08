import pandas as pd
import numpy as np
import logging
import time
import traceback
from typing import List, Dict, Any, Tuple, Optional
from app.services.file_service import (
    get_file_content, 
    read_file, 
    detect_encoding, 
    detect_separator,
    dataframe_to_bytes,
    save_file
)

logger = logging.getLogger("app.services.comparison")

def compare_files(
    original_filename: str,
    new_filename: str,
    id_column: str,
    price_column: str,
    quantity_column: Optional[str] = None,
    threshold: float = 10.0
) -> dict:
    """
    Сравнивает цены в двух файлах и возвращает результаты сравнения.
    
    Args:
        original_filename (str): Имя исходного файла
        new_filename (str): Имя нового файла
        id_column (str): Название колонки с идентификаторами товаров
        price_column (str): Название колонки с ценами
        quantity_column (Optional[str]): Название колонки с количеством (опционально)
        threshold (float): Пороговое значение для изменения цены в процентах
        
    Returns:
        dict: Результаты сравнения
    """
    start_time = time.time()
    
    logger.info(f"Начало сравнения файлов: {original_filename} и {new_filename}")
    logger.info(f"Параметры сравнения: id_column={id_column}, price_column={price_column}, "
                f"quantity_column={quantity_column}, threshold={threshold}%")
    
    try:
        # Получаем данные из файлов
        original_content = get_file_content(original_filename)
        new_content = get_file_content(new_filename)
        
        if not original_content or not new_content:
            error_msg = f"Не удалось получить содержимое файлов: " \
                        f"original_content={'получено' if original_content else 'не получено'}, " \
                        f"new_content={'получено' if new_content else 'не получено'}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Определяем кодировку и разделитель
        original_ext = original_filename.split('.')[-1]
        new_ext = new_filename.split('.')[-1]
        
        original_encoding = detect_encoding(original_content)
        new_encoding = detect_encoding(new_content)
        
        original_separator = detect_separator(original_content, original_encoding)
        new_separator = detect_separator(new_content, new_encoding)
        
        # Читаем данные
        original_df = read_file(original_content, f".{original_ext}", original_encoding, original_separator)
        new_df = read_file(new_content, f".{new_ext}", new_encoding, new_separator)
        
        # Проверяем наличие необходимых колонок
        for df, name, cols in [
            (original_df, "оригинальном", [id_column, price_column]),
            (new_df, "новом", [id_column, price_column])
        ]:
            missing_cols = [col for col in cols if col not in df.columns]
            if missing_cols:
                error_msg = f"В {name} файле отсутствуют необходимые колонки: {', '.join(missing_cols)}"
                logger.error(error_msg)
                return {"error": error_msg}
                
        if quantity_column and quantity_column not in original_df.columns:
            logger.warning(f"Колонка с количеством '{quantity_column}' отсутствует в оригинальном файле")
            
        if quantity_column and quantity_column not in new_df.columns:
            logger.warning(f"Колонка с количеством '{quantity_column}' отсутствует в новом файле")
        
        # Преобразуем колонки с ценами к числовому формату
        for df in [original_df, new_df]:
            df[price_column] = pd.to_numeric(df[price_column], errors='coerce')
            
            # Заменяем NaN на 0
            df[price_column] = df[price_column].fillna(0)
            
            # Если есть колонка с количеством, преобразуем её тоже
            if quantity_column and quantity_column in df.columns:
                df[quantity_column] = pd.to_numeric(df[quantity_column], errors='coerce')
                df[quantity_column] = df[quantity_column].fillna(0)
        
        # Объединяем датафреймы по ID
        result_df = pd.merge(
            original_df, 
            new_df, 
            on=id_column, 
            how='outer', 
            suffixes=('_original', '_new')
        )
        
        # Создаем колонки для сравнения
        result_df['price_original'] = result_df[f"{price_column}_original"]
        result_df['price_new'] = result_df[f"{price_column}_new"]
        
        # Заполняем пропущенные значения
        result_df['price_original'] = result_df['price_original'].fillna(0)
        result_df['price_new'] = result_df['price_new'].fillna(0)
        
        # Добавляем колонку с количеством, если указана
        if quantity_column:
            # Если колонка с количеством есть в обоих файлах
            if quantity_column in original_df.columns and quantity_column in new_df.columns:
                result_df['quantity_original'] = result_df[f"{quantity_column}_original"]
                result_df['quantity_new'] = result_df[f"{quantity_column}_new"]
                
                # Заполняем пропущенные значения
                result_df['quantity_original'] = result_df['quantity_original'].fillna(0)
                result_df['quantity_new'] = result_df['quantity_new'].fillna(0)
            # Если колонка с количеством есть только в оригинальном файле
            elif quantity_column in original_df.columns:
                result_df['quantity_original'] = result_df[f"{quantity_column}_original"]
                result_df['quantity_new'] = 0
                
                # Заполняем пропущенные значения
                result_df['quantity_original'] = result_df['quantity_original'].fillna(0)
            # Если колонка с количеством есть только в новом файле
            elif quantity_column in new_df.columns:
                result_df['quantity_original'] = 0
                result_df['quantity_new'] = result_df[f"{quantity_column}_new"]
                
                # Заполняем пропущенные значения
                result_df['quantity_new'] = result_df['quantity_new'].fillna(0)
        
        # Вычисляем разницу в цене
        result_df['price_diff'] = result_df['price_new'] - result_df['price_original']
        
        # Вычисляем процентное изменение цены
        # Избегаем деления на 0
        result_df['price_diff_percent'] = np.where(
            result_df['price_original'] > 0,
            (result_df['price_diff'] / result_df['price_original']) * 100,
            np.where(
                result_df['price_new'] > 0,
                100,  # Если было 0, а стало что-то - это 100% рост
                0     # Если было 0 и осталось 0 - это 0% изменение
            )
        )
        
        # Округляем значения
        result_df['price_original'] = result_df['price_original'].round(2)
        result_df['price_new'] = result_df['price_new'].round(2)
        result_df['price_diff'] = result_df['price_diff'].round(2)
        result_df['price_diff_percent'] = result_df['price_diff_percent'].round(2)
        
        # Определяем значимые изменения
        result_df['significant_change'] = abs(result_df['price_diff_percent']) >= threshold
        
        # Определяем тип изменения
        result_df['change_type'] = 'без изменений'
        
        # Новые товары
        mask_new = result_df['price_original'].isna() | ((result_df['price_original'] == 0) & (result_df['price_new'] > 0))
        result_df.loc[mask_new, 'change_type'] = 'новый'
        
        # Удаленные товары
        mask_deleted = result_df['price_new'].isna() | ((result_df['price_new'] == 0) & (result_df['price_original'] > 0))
        result_df.loc[mask_deleted, 'change_type'] = 'удален'
        
        # Увеличение цены
        mask_increased = (result_df['price_diff'] > 0) & (result_df['significant_change']) & (~mask_new) & (~mask_deleted)
        result_df.loc[mask_increased, 'change_type'] = 'повышение'
        
        # Уменьшение цены
        mask_decreased = (result_df['price_diff'] < 0) & (result_df['significant_change']) & (~mask_new) & (~mask_deleted)
        result_df.loc[mask_decreased, 'change_type'] = 'понижение'
        
        # Подсчет статистики
        total_products = len(result_df)
        increased_count = len(result_df[result_df['change_type'] == 'повышение'])
        decreased_count = len(result_df[result_df['change_type'] == 'понижение'])
        new_count = len(result_df[result_df['change_type'] == 'новый'])
        removed_count = len(result_df[result_df['change_type'] == 'удален'])
        unchanged_count = len(result_df[result_df['change_type'] == 'без изменений'])
        
        # Формируем имя файла с результатами
        timestamp = int(time.time())
        result_filename = f"comparison_result_{timestamp}.csv"
        
        # Сохраняем результаты в файл
        result_content = dataframe_to_bytes(result_df, '.csv', 'utf-8', ';')
        result_file_url = save_file(result_filename, result_content)
        
        execution_time = time.time() - start_time
        logger.info(f"Сравнение завершено за {execution_time:.2f} секунд. "
                    f"Всего товаров: {total_products}, с изменениями: {increased_count + decreased_count + new_count + removed_count}")
        
        # Формируем итоговый результат
        result = {
            "status": "success",
            "statistics": {
                "total_products": total_products,
                "increased_count": increased_count,
                "decreased_count": decreased_count,
                "new_count": new_count,
                "removed_count": removed_count,
                "unchanged_count": unchanged_count,
                "execution_time": execution_time
            },
            "result_file": {
                "filename": result_filename,
                "url": result_file_url
            }
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при сравнении файлов: {str(e)}")
        logger.debug(traceback.format_exc())
        return {"error": f"Ошибка при сравнении файлов: {str(e)}"}

def update_prices(
    original_filename: str,
    comparison_result_filename: str,
    price_column: str,
    id_column: str,
    selected_ids: List[str],
    update_all: bool = False
) -> dict:
    """
    Обновляет цены в исходном файле на основе результатов сравнения
    
    Args:
        original_filename (str): Имя исходного файла
        comparison_result_filename (str): Имя файла с результатами сравнения
        price_column (str): Название колонки с ценами
        id_column (str): Название колонки с идентификаторами товаров
        selected_ids (List[str]): Список идентификаторов товаров для обновления
        update_all (bool): Флаг для обновления всех товаров
        
    Returns:
        dict: Результаты обновления
    """
    start_time = time.time()
    
    logger.info(f"Начало обновления цен в файле {original_filename}")
    logger.info(f"Параметры обновления: price_column={price_column}, id_column={id_column}, "
                f"selected_ids={len(selected_ids) if selected_ids else 0}, update_all={update_all}")
    
    try:
        # Получаем данные из файлов
        original_content = get_file_content(original_filename)
        comparison_content = get_file_content(comparison_result_filename)
        
        if not original_content or not comparison_content:
            error_msg = f"Не удалось получить содержимое файлов: " \
                        f"original_content={'получено' if original_content else 'не получено'}, " \
                        f"comparison_content={'получено' if comparison_content else 'не получено'}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Определяем кодировку и разделитель
        original_ext = original_filename.split('.')[-1]
        
        original_encoding = detect_encoding(original_content)
        comparison_encoding = detect_encoding(comparison_content)
        
        original_separator = detect_separator(original_content, original_encoding)
        comparison_separator = detect_separator(comparison_content, comparison_encoding)
        
        # Читаем данные
        original_df = read_file(original_content, f".{original_ext}", original_encoding, original_separator)
        comparison_df = read_file(comparison_content, ".csv", comparison_encoding, comparison_separator)
        
        # Проверяем наличие необходимых колонок
        for df, name, cols in [
            (original_df, "оригинальном", [id_column, price_column]),
            (comparison_df, "сравнительном", [id_column, 'price_new'])
        ]:
            missing_cols = [col for col in cols if col not in df.columns]
            if missing_cols:
                error_msg = f"В {name} файле отсутствуют необходимые колонки: {', '.join(missing_cols)}"
                logger.error(error_msg)
                return {"error": error_msg}
        
        # Создаем копию оригинального датафрейма для обновления
        updated_df = original_df.copy()
        
        # Подготавливаем данные для объединения
        comparison_result = comparison_df[[id_column, 'price_new', 'change_type']].copy()
        
        # Определяем, какие товары обновлять
        if update_all:
            # Обновляем все товары
            logger.info("Обновление всех товаров")
            rows_to_update = comparison_result
        else:
            # Обновляем только выбранные товары
            logger.info(f"Обновление выбранных товаров: {len(selected_ids)} шт.")
            rows_to_update = comparison_result[comparison_result[id_column].isin(selected_ids)]
        
        # Создаем словарь для быстрого поиска новых цен
        price_updates = dict(zip(rows_to_update[id_column], rows_to_update['price_new']))
        
        # Обновляем цены
        updated_count = 0
        for idx, row in updated_df.iterrows():
            product_id = row[id_column]
            if product_id in price_updates:
                updated_df.at[idx, price_column] = price_updates[product_id]
                updated_count += 1
        
        # Формируем имя файла с результатами
        timestamp = int(time.time())
        result_filename = f"updated_{timestamp}_{original_filename}"
        
        # Сохраняем результаты в файл
        result_content = dataframe_to_bytes(updated_df, f".{original_ext}", original_encoding, original_separator)
        result_file_url = save_file(result_filename, result_content)
        
        execution_time = time.time() - start_time
        logger.info(f"Обновление завершено за {execution_time:.2f} секунд. Обновлено {updated_count} товаров.")
        
        # Формируем итоговый результат
        result = {
            "status": "success",
            "statistics": {
                "total_products": len(original_df),
                "updated_count": updated_count,
                "execution_time": execution_time
            },
            "result_file": {
                "filename": result_filename,
                "url": result_file_url
            }
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при обновлении цен: {str(e)}")
        logger.debug(traceback.format_exc())
        return {"error": f"Ошибка при обновлении цен: {str(e)}"} 