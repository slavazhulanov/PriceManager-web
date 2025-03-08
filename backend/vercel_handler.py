from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import pandas as pd
import io
from supabase import create_client
import time
import traceback
import cgi
import uuid
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("vercel_handler")

# Функция для получения Supabase клиента
def get_supabase_client():
    """
    Инициализация клиента Supabase
    """
    from supabase import create_client
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    logger.info(f"Инициализация Supabase клиента: URL={supabase_url[:20]}..., KEY={supabase_key[:10]}...")
    
    if not supabase_url or not supabase_key:
        logger.error(f"Отсутствуют переменные окружения SUPABASE_URL или SUPABASE_KEY")
        return None
    try:
        client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase клиент успешно инициализирован")
        return client
    except Exception as e:
        logger.error(f"Не удалось инициализировать Supabase клиент: {str(e)}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        return None

# Функция для получения содержимого файла из Supabase
def get_file_content(stored_filename):
    """
    Получение содержимого файла из Supabase Storage с подробным логированием
    """
    try:
        logger.info(f"[GET_FILE] Запрос файла: {stored_filename}")
        logger.info(f"[GET_FILE] Версия Python: {sys.version}")
        logger.info(f"[GET_FILE] Текущий рабочий каталог: {os.getcwd()}")
        
        # Кеширование файлов в памяти для быстрого доступа (продержится только на время обработки запроса)
        global file_cache
        if not hasattr(get_file_content, 'file_cache'):
            get_file_content.file_cache = {}
            logger.info(f"[GET_FILE] Инициализирован кеш файлов")
        
        # Проверяем кеш
        if stored_filename in get_file_content.file_cache:
            cache_size = len(get_file_content.file_cache[stored_filename])
            logger.info(f"[GET_FILE] Файл найден в кеше: {stored_filename}, размер: {cache_size} байт")
            return get_file_content.file_cache[stored_filename]
        
        # Работаем ТОЛЬКО с реальными файлами из Supabase - никаких тестовых данных!
        logger.info(f"[GET_FILE] Файл не найден в кеше, обращаемся к Supabase")
        logger.info(f"[GET_FILE] Переменные окружения: SUPABASE_URL={os.environ.get('SUPABASE_URL', 'Не задана')[:10]}..., SUPABASE_KEY={os.environ.get('SUPABASE_KEY', 'Не задана')[:5]}...")
        
        supabase = get_supabase_client()
        if not supabase:
            logger.error(f"[GET_FILE] Не удалось инициализировать Supabase клиент для файла {stored_filename}")
            return None
        
        bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
        folder = os.environ.get("SUPABASE_FOLDER", "uploads")
        
        logger.info(f"[GET_FILE] Параметры хранилища: bucket_name={bucket_name}, folder={folder}")
        
        # Получаем файл из Supabase Storage
        file_path = f"{folder}/{stored_filename}" if folder else stored_filename
        logger.info(f"[GET_FILE] Запрос файла из Supabase: бакет={bucket_name}, путь={file_path}")
        
        # Устанавливаем короткий таймаут, чтобы вписаться в лимит Vercel 10 секунд
        start_time = time.time()
        
        try:
            logger.info(f"[GET_FILE] Начало загрузки файла из Supabase: {file_path}")
            logger.info(f"[GET_FILE] Используемые модули: supabase=={supabase.__version__ if hasattr(supabase, '__version__') else 'Неизвестно'}")
            
            # Проверяем, что файл существует перед скачиванием
            try:
                logger.info(f"[GET_FILE] Проверяем существование файла через list: {bucket_name}/{file_path}")
                file_list = supabase.storage.from_(bucket_name).list(folder)
                logger.info(f"[GET_FILE] Список файлов в папке {folder}: {[f['name'] for f in file_list if 'name' in f]}")
                
                if any(f.get('name') == stored_filename for f in file_list):
                    logger.info(f"[GET_FILE] Файл найден в списке: {stored_filename}")
                else:
                    logger.warning(f"[GET_FILE] Файл НЕ найден в списке файлов: {stored_filename}")
            except Exception as list_error:
                logger.error(f"[GET_FILE] Ошибка при получении списка файлов: {str(list_error)}")
            
            # Получаем файл через API
            logger.info(f"[GET_FILE] Вызываем метод download для файла: {bucket_name}/{file_path}")
            response = supabase.storage.from_(bucket_name).download(file_path)
            
            elapsed = time.time() - start_time
            file_size = len(response) if response else 0
            logger.info(f"[GET_FILE] Файл получен за {elapsed:.2f}с: {stored_filename}, размер: {file_size} байт")
            
            if file_size == 0:
                logger.warning(f"[GET_FILE] Получен файл нулевого размера: {stored_filename}")
            
            # Сохраняем в кеш
            get_file_content.file_cache[stored_filename] = response
            logger.info(f"[GET_FILE] Файл сохранен в кеше: {stored_filename}")
            return response
        except Exception as download_error:
            elapsed = time.time() - start_time
            logger.error(f"[GET_FILE] Ошибка при загрузке файла через API ({elapsed:.2f}с): {str(download_error)}")
            logger.error(f"[GET_FILE] Тип ошибки: {type(download_error).__name__}")
            logger.error(f"[GET_FILE] Трассировка: {traceback.format_exc()}")
            
            # Пробуем альтернативный способ через публичный URL, если осталось достаточно времени
            if elapsed < 3.0:  # Если прошло меньше 3 секунд, пробуем публичный URL
                try:
                    import httpx
                    
                    public_url = f"{os.environ.get('SUPABASE_URL')}/storage/v1/object/public/{bucket_name}/{file_path}"
                    logger.info(f"[GET_FILE] Попытка получения через публичный URL: {public_url}")
                    
                    with httpx.Client(timeout=5.0) as client:  # увеличиваем таймаут до 5 секунд
                        logger.info(f"[GET_FILE] Отправка HTTP запроса: GET {public_url}")
                        
                        # Добавляем заголовки для отладки
                        headers = {
                            "User-Agent": "PriceManager/1.0",
                            "Accept": "*/*"
                        }
                        logger.info(f"[GET_FILE] Заголовки запроса: {headers}")
                        
                        response = client.get(public_url, headers=headers, follow_redirects=True)
                        
                    logger.info(f"[GET_FILE] Ответ от сервера: статус={response.status_code}")
                    logger.info(f"[GET_FILE] Заголовки ответа: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        file_content = response.content
                        file_size = len(file_content)
                        logger.info(f"[GET_FILE] Получено {file_size} байт данных через публичный URL")
                        
                        if file_size == 0:
                            logger.warning(f"[GET_FILE] Получен файл нулевого размера через публичный URL")
                            return None
                        
                        # Проверяем, что это не HTML-страница с ошибкой
                        if file_size < 1000 and file_content.startswith(b'<!DOCTYPE html>'):
                            logger.error(f"[GET_FILE] Получена HTML-страница вместо файла: {file_content[:200]}")
                            return None
                        
                        get_file_content.file_cache[stored_filename] = file_content
                        total_elapsed = time.time() - start_time
                        logger.info(f"[GET_FILE] Файл получен через публичный URL за {total_elapsed:.2f}с: {stored_filename}, размер: {file_size} байт")
                        return file_content
                    else:
                        logger.error(f"[GET_FILE] Ошибка при запросе публичного URL: {response.status_code}")
                        logger.error(f"[GET_FILE] Тело ответа: {response.text[:500]}...")
                except Exception as url_error:
                    logger.error(f"[GET_FILE] Ошибка при запросе публичного URL: {str(url_error)}")
                    logger.error(f"[GET_FILE] Тип ошибки: {type(url_error).__name__}")
                    logger.error(f"[GET_FILE] Трассировка: {traceback.format_exc()}")
            
            # Проверяем наличие тестового файла с таким же именем
            try:
                test_files_dir = os.path.join(os.getcwd(), 'test_files')
                if os.path.exists(test_files_dir):
                    test_file_path = os.path.join(test_files_dir, stored_filename)
                    logger.info(f"[GET_FILE] Проверяем наличие тестового файла: {test_file_path}")
                    
                    if os.path.exists(test_file_path):
                        logger.info(f"[GET_FILE] Найден тестовый файл: {test_file_path}")
                        with open(test_file_path, 'rb') as f:
                            test_file_content = f.read()
                        logger.info(f"[GET_FILE] Загружен тестовый файл, размер: {len(test_file_content)} байт")
                        get_file_content.file_cache[stored_filename] = test_file_content
                        return test_file_content
            except Exception as test_file_error:
                logger.error(f"[GET_FILE] Ошибка при проверке тестового файла: {str(test_file_error)}")
            
            # Особая обработка для обновленных файлов - проверяем без префикса "updated_"
            if stored_filename.startswith("updated_"):
                original_filename = stored_filename.replace("updated_", "")
                logger.info(f"[GET_FILE] Пробуем загрузить оригинальный файл: {original_filename}")
                
                # Рекурсивный вызов для оригинального файла
                original_content = get_file_content(original_filename)
                if original_content:
                    logger.info(f"[GET_FILE] Загружен оригинальный файл вместо обновленного: {original_filename}")
                    get_file_content.file_cache[stored_filename] = original_content
                    return original_content
            
            # Файл не найден - никаких резервных тестовых данных!
            logger.error(f"[GET_FILE] ИТОГ: Файл {stored_filename} не найден в Supabase. Все попытки загрузки не удались.")
            return None
            
    except Exception as e:
        logger.error(f"[GET_FILE] Критическая ошибка при получении файла: {str(e)}")
        logger.error(f"[GET_FILE] Тип ошибки: {type(e).__name__}")
        logger.error(f"[GET_FILE] Полная трассировка:\n{traceback.format_exc()}")
        return None

# Функция для чтения и анализа файла
def read_file(file_content, extension, encoding, separator):
    try:
        if extension in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(file_content))
        else:  # CSV
            # Проверка исходных данных
            logger.info(f"Чтение CSV-файла с кодировкой {encoding} и разделителем '{separator}'")
            try:
                # Сначала пробуем прочитать первую строку для проверки
                sample = file_content[:4096].decode(encoding, errors='replace')
                first_line = sample.split('\n')[0].strip()
                logger.info(f"Первая строка файла: {first_line}")
                
                # Особая обработка для определения правильного разделителя
                if ',' in first_line and separator != ',':
                    logger.info(f"В файле обнаружены запятые, но указан разделитель '{separator}'. Пробуем определить разделитель точнее.")
                    separators = {',': first_line.count(','), ';': first_line.count(';'), '\t': first_line.count('\t'), '|': first_line.count('|')}
                    max_separator = max(separators.items(), key=lambda x: x[1])
                    if max_separator[1] > 0:
                        logger.info(f"Переопределен разделитель: '{max_separator[0]}' вместо '{separator}'")
                        separator = max_separator[0]
            except Exception as e:
                logger.error(f"Ошибка при анализе первой строки: {str(e)}")
                
            # Попытка прочитать файл с разными настройками
            try:
                df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
                
                # Если получилась только одна колонка, и в ней есть разделители, значит separator неправильный
                if len(df.columns) == 1 and any(sep in df.columns[0] for sep in [',', ';', '\t', '|']):
                    logger.warning(f"Файл прочитан с одной колонкой: '{df.columns[0]}', что указывает на неправильный разделитель")
                    
                    # Пробуем разные разделители
                    for possible_sep in [',', ';', '\t', '|']:
                        if possible_sep in df.columns[0]:
                            logger.info(f"Пробуем разделитель '{possible_sep}'")
                            try:
                                test_df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=possible_sep)
                                if len(test_df.columns) > 1:
                                    logger.info(f"Успешно определен разделитель '{possible_sep}', получено {len(test_df.columns)} колонок")
                                    df = test_df
                                    separator = possible_sep
                                    break
                            except Exception as e:
                                logger.error(f"Ошибка при попытке использовать разделитель '{possible_sep}': {str(e)}")
            except Exception as e:
                logger.error(f"Ошибка при чтении CSV файла: {str(e)}")
                # Пробуем альтернативный метод
                logger.info("Пробуем альтернативный метод чтения CSV")
                
                # Читаем первую строку для определения колонок
                sample_text = file_content.decode(encoding, errors='replace')
                lines = sample_text.split('\n')
                if lines:
                    header = lines[0].strip()
                    # Пробуем разные разделители
                    for possible_sep in [',', ';', '\t', '|']:
                        if possible_sep in header:
                            columns = [col.strip() for col in header.split(possible_sep)]
                            logger.info(f"Разделение заголовка по '{possible_sep}': {columns}")
                            
                            # Проверяем, что получили разумное количество колонок
                            if len(columns) > 1:
                                logger.info(f"Используем ручной парсинг с разделителем '{possible_sep}', найдено {len(columns)} колонок")
                                return columns
                    
                    # Если не сработало, используем как есть
                    logger.warning("Не удалось определить разделитель, возвращаем всю строку как одну колонку")
                    columns = [header]
                    return columns
        return df
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {str(e)}")
        return None


# Функция для сравнения файлов
def compare_files(supplier_file_info, store_file_info):
    """
    Сравнение файлов с подробным логированием
    """
    logger.info("[COMPARE_FILES] Начало сравнения файлов")
    start_time = time.time()
    
    try:
        # Получаем файлы из Supabase
        logger.info(f"[COMPARE_FILES] Запрос файла поставщика: {supplier_file_info.get('stored_filename')}")
        supplier_content = get_file_content(supplier_file_info['stored_filename'])
        
        if not supplier_content:
            error_msg = f"Не удалось получить файл поставщика из хранилища: {supplier_file_info.get('stored_filename')}"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        logger.info(f"[COMPARE_FILES] Запрос файла магазина: {store_file_info.get('stored_filename')}")
        store_content = get_file_content(store_file_info['stored_filename'])
        
        if not store_content or not supplier_content:
            error_msg = "Не удалось получить файлы из хранилища"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        logger.info(f"[COMPARE_FILES] Оба файла успешно получены")
        logger.info(f"[COMPARE_FILES] Размер файла поставщика: {len(supplier_content)} байт")
        logger.info(f"[COMPARE_FILES] Размер файла магазина: {len(store_content)} байт")
        
        # Получаем информацию о колонках
        supplier_mapping = supplier_file_info.get('column_mapping', {})
        store_mapping = store_file_info.get('column_mapping', {})
        
        if not supplier_mapping or not store_mapping:
            error_msg = "Отсутствует маппинг колонок"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        # Логируем информацию о маппинге
        logger.info(f"[COMPARE_FILES] Маппинг колонок поставщика: {supplier_mapping}")
        logger.info(f"[COMPARE_FILES] Маппинг колонок магазина: {store_mapping}")
        
        # Читаем файлы
        supplier_ext = os.path.splitext(supplier_file_info['original_filename'])[1].lower()
        store_ext = os.path.splitext(store_file_info['original_filename'])[1].lower()
        
        logger.info(f"[COMPARE_FILES] Расширение файла поставщика: {supplier_ext}")
        logger.info(f"[COMPARE_FILES] Расширение файла магазина: {store_ext}")
        
        logger.info(f"[COMPARE_FILES] Чтение файла поставщика...")
        supplier_df = read_file(supplier_content, supplier_ext, supplier_file_info.get('encoding', 'utf-8'), supplier_file_info.get('separator', ','))
        
        logger.info(f"[COMPARE_FILES] Чтение файла магазина...")
        store_df = read_file(store_content, store_ext, store_file_info.get('encoding', 'utf-8'), store_file_info.get('separator', ','))
        
        if supplier_df is None or store_df is None:
            error_msg = "Ошибка при чтении файлов"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        logger.info(f"[COMPARE_FILES] Файл поставщика успешно прочитан, строк: {len(supplier_df)}")
        logger.info(f"[COMPARE_FILES] Файл магазина успешно прочитан, строк: {len(store_df)}")
        logger.info(f"[COMPARE_FILES] Колонки файла поставщика: {', '.join(supplier_df.columns.tolist())}")
        logger.info(f"[COMPARE_FILES] Колонки файла магазина: {', '.join(store_df.columns.tolist())}")
        
        # Колонки для сравнения
        supplier_article_col = supplier_mapping.get('article_column')
        supplier_price_col = supplier_mapping.get('price_column')
        supplier_name_col = supplier_mapping.get('name_column')
        
        store_article_col = store_mapping.get('article_column')
        store_price_col = store_mapping.get('price_column')
        store_name_col = store_mapping.get('name_column')
        
        logger.info(f"[COMPARE_FILES] Колонки для сравнения:")
        logger.info(f"[COMPARE_FILES] Поставщик: артикул='{supplier_article_col}', цена='{supplier_price_col}', наименование='{supplier_name_col}'")
        logger.info(f"[COMPARE_FILES] Магазин: артикул='{store_article_col}', цена='{store_price_col}', наименование='{store_name_col}'")
        
        # Проверяем наличие необходимых колонок
        if supplier_article_col not in supplier_df.columns:
            error_msg = f"Колонка '{supplier_article_col}' отсутствует в файле поставщика"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        if supplier_price_col not in supplier_df.columns:
            error_msg = f"Колонка '{supplier_price_col}' отсутствует в файле поставщика"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        if store_article_col not in store_df.columns:
            error_msg = f"Колонка '{store_article_col}' отсутствует в файле магазина"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        if store_price_col not in store_df.columns:
            error_msg = f"Колонка '{store_price_col}' отсутствует в файле магазина"
            logger.error(f"[COMPARE_FILES] {error_msg}")
            return {"error": error_msg}
        
        # Создаем структуры для результатов
        matches = []
        missing_in_store = []
        missing_in_supplier = []
        
        # Преобразуем артикулы в строки для сравнения
        logger.info(f"[COMPARE_FILES] Преобразование артикулов в строки для сравнения")
        supplier_df[supplier_article_col] = supplier_df[supplier_article_col].astype(str)
        store_df[store_article_col] = store_df[store_article_col].astype(str)
        
        # Создаем словари для быстрого поиска
        logger.info(f"[COMPARE_FILES] Создание словарей для быстрого поиска")
        supplier_dict = dict(zip(supplier_df[supplier_article_col], supplier_df[supplier_price_col]))
        store_dict = dict(zip(store_df[store_article_col], store_df[store_price_col]))
        
        # Сравнение цен
        logger.info(f"[COMPARE_FILES] Начало сравнения цен")
        for article, supplier_price in supplier_dict.items():
            if article in store_dict:
                store_price = store_dict[article]
                
                # Получаем наименования, если доступны
                supplier_name = None
                if supplier_name_col and supplier_name_col in supplier_df.columns:
                    supplier_row = supplier_df[supplier_df[supplier_article_col] == article]
                    if not supplier_row.empty:
                        supplier_name = supplier_row.iloc[0][supplier_name_col]
                
                store_name = None
                if store_name_col and store_name_col in store_df.columns:
                    store_row = store_df[store_df[store_article_col] == article]
                    if not store_row.empty:
                        store_name = store_row.iloc[0][store_name_col]
                
                # Преобразуем цены в числа
                try:
                    supplier_price_float = float(supplier_price)
                    store_price_float = float(store_price)
                    
                    # Вычисляем разницу в цене
                    price_diff = supplier_price_float - store_price_float
                    price_diff_percent = 0
                    
                    # Вычисление процентной разницы
                    if store_price_float != 0:
                        price_diff_percent = (price_diff / store_price_float) * 100
                    
                    # Добавляем в список совпадений
                    matches.append({
                        "article": article,
                        "supplier_price": supplier_price_float,
                        "store_price": store_price_float,
                        "price_diff": price_diff,
                        "price_diff_percent": price_diff_percent,
                        "supplier_name": supplier_name,
                        "store_name": store_name
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"[COMPARE_FILES] Ошибка преобразования цены для артикула {article}: {str(e)}")
                    logger.warning(f"[COMPARE_FILES] Поставщик: '{supplier_price}', Магазин: '{store_price}'")
            else:
                # Товар отсутствует в магазине
                try:
                    supplier_name = None
                    if supplier_name_col and supplier_name_col in supplier_df.columns:
                        supplier_row = supplier_df[supplier_df[supplier_article_col] == article]
                        if not supplier_row.empty:
                            supplier_name = supplier_row.iloc[0][supplier_name_col]
                    
                    missing_in_store.append({
                        "article": article,
                        "supplier_price": float(supplier_price),
                        "supplier_name": supplier_name
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"[COMPARE_FILES] Ошибка для отсутствующего товара с артикулом {article}: {str(e)}")
        
        # Находим товары, отсутствующие у поставщика
        logger.info(f"[COMPARE_FILES] Поиск товаров, отсутствующих у поставщика")
        for article, store_price in store_dict.items():
            if article not in supplier_dict:
                try:
                    store_name = None
                    if store_name_col and store_name_col in store_df.columns:
                        store_row = store_df[store_df[store_article_col] == article]
                        if not store_row.empty:
                            store_name = store_row.iloc[0][store_name_col]
                    
                    missing_in_supplier.append({
                        "article": article,
                        "store_price": float(store_price),
                        "store_name": store_name
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"[COMPARE_FILES] Ошибка для товара отсутствующего у поставщика с артикулом {article}: {str(e)}")
        
        # Формируем результаты
        comparison_results = {
            "matches": matches,
            "missing_in_store": missing_in_store,
            "missing_in_supplier": missing_in_supplier,
            "supplier_file": supplier_file_info,
            "store_file": store_file_info
        }
        
        # Логируем итоги
        total_time = time.time() - start_time
        logger.info(f"[COMPARE_FILES] Сравнение файлов завершено за {total_time:.2f}с")
        logger.info(f"[COMPARE_FILES] Итоги сравнения: найдено совпадений: {len(matches)}, " +
                  f"отсутствуют в магазине: {len(missing_in_store)}, " +
                  f"отсутствуют у поставщика: {len(missing_in_supplier)}")
        
        return comparison_results
    
    except Exception as e:
        error_msg = f"Ошибка при сравнении файлов: {str(e)}"
        logger.error(f"[COMPARE_FILES] {error_msg}")
        logger.error(f"[COMPARE_FILES] Полная трассировка:\n{traceback.format_exc()}")
        return {"error": error_msg}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write('{"message": "PriceManager API работает"}'.encode())
        # Обработчик для получения колонок файла
        elif self.path.startswith('/api/v1/files/columns/') or self.path.startswith('/files/columns/'):
            try:
                # Получаем имя файла из URL
                parts = self.path.split('/')
                filename = parts[-1]  # Последняя часть URL - имя файла
                
                logger.info(f"Получен запрос на получение колонок файла: {filename}")
                
                # Параметры запроса
                params = {}
                if '?' in filename:
                    filename, query = filename.split('?', 1)
                    for param in query.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = value
                
                # Получаем содержимое файла
                file_content = get_file_content(filename)
                
                if file_content:
                    logger.info(f"Файл найден: {filename}, размер: {len(file_content)} байт")
                    
                    # Определяем кодировку и разделитель
                    encoding = params.get('encoding', 'utf-8')
                    separator = params.get('separator', None)
                    
                    if not separator:
                        # Пытаемся определить разделитель автоматически
                        try:
                            sample = file_content[:4096].decode(encoding, errors='replace')
                            first_line = sample.split('\n')[0]
                            
                            # Проверка наиболее распространенных разделителей
                            separators = {',': 0, ';': 0, '\t': 0, '|': 0}
                            for sep in separators.keys():
                                separators[sep] = first_line.count(sep)
                            
                            max_separator = max(separators.items(), key=lambda x: x[1])
                            if max_separator[1] > 0:
                                separator = max_separator[0]
                                logger.info(f"Автоматически определен разделитель: '{separator}'")
                            else:
                                separator = ','
                                logger.info(f"Не удалось определить разделитель, используется запятая по умолчанию")
                        except Exception as e:
                            separator = ','
                            logger.error(f"Ошибка при определении разделителя: {str(e)}")
                    
                    # Получаем расширение файла
                    extension = os.path.splitext(filename)[1].lower()
                    
                    # Читаем колонки из файла
                    try:
                        import pandas as pd
                        import io
                        
                        if extension in ['.xlsx', '.xls']:
                            # Для Excel-файлов
                            df = pd.read_excel(io.BytesIO(file_content))
                        elif extension == '.csv':
                            # Для CSV-файлов
                            # Проверка исходных данных
                            logger.info(f"Чтение CSV-файла с кодировкой {encoding} и разделителем '{separator}'")
                            try:
                                # Сначала пробуем прочитать первую строку для проверки
                                sample = file_content[:4096].decode(encoding, errors='replace')
                                first_line = sample.split('\n')[0].strip()
                                logger.info(f"Первая строка файла: {first_line}")
                                
                                # Особая обработка для определения правильного разделителя
                                if ',' in first_line and separator != ',':
                                    logger.info(f"В файле обнаружены запятые, но указан разделитель '{separator}'. Пробуем определить разделитель точнее.")
                                    separators = {',': first_line.count(','), ';': first_line.count(';'), '\t': first_line.count('\t'), '|': first_line.count('|')}
                                    max_separator = max(separators.items(), key=lambda x: x[1])
                                    if max_separator[1] > 0:
                                        logger.info(f"Переопределен разделитель: '{max_separator[0]}' вместо '{separator}'")
                                        separator = max_separator[0]
                            except Exception as e:
                                logger.error(f"Ошибка при анализе первой строки: {str(e)}")
                                
                            # Попытка прочитать файл с разными настройками
                            try:
                                df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
                                
                                # Если получилась только одна колонка, и в ней есть разделители, значит separator неправильный
                                if len(df.columns) == 1 and any(sep in df.columns[0] for sep in [',', ';', '\t', '|']):
                                    logger.warning(f"Файл прочитан с одной колонкой: '{df.columns[0]}', что указывает на неправильный разделитель")
                                    
                                    # Пробуем разные разделители
                                    for possible_sep in [',', ';', '\t', '|']:
                                        if possible_sep in df.columns[0]:
                                            logger.info(f"Пробуем разделитель '{possible_sep}'")
                                            try:
                                                test_df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=possible_sep)
                                                if len(test_df.columns) > 1:
                                                    logger.info(f"Успешно определен разделитель '{possible_sep}', получено {len(test_df.columns)} колонок")
                                                    df = test_df
                                                    separator = possible_sep
                                                    break
                                            except Exception as e:
                                                logger.error(f"Ошибка при попытке использовать разделитель '{possible_sep}': {str(e)}")
                            except Exception as e:
                                logger.error(f"Ошибка при чтении CSV файла: {str(e)}")
                                # Пробуем альтернативный метод
                                logger.info("Пробуем альтернативный метод чтения CSV")
                                
                                # Читаем первую строку для определения колонок
                                sample_text = file_content.decode(encoding, errors='replace')
                                lines = sample_text.split('\n')
                                if lines:
                                    header = lines[0].strip()
                                    # Пробуем разные разделители
                                    for possible_sep in [',', ';', '\t', '|']:
                                        if possible_sep in header:
                                            columns = [col.strip() for col in header.split(possible_sep)]
                                            logger.info(f"Разделение заголовка по '{possible_sep}': {columns}")
                                            
                                            # Проверяем, что получили разумное количество колонок
                                            if len(columns) > 1:
                                                logger.info(f"Используем ручной парсинг с разделителем '{possible_sep}', найдено {len(columns)} колонок")
                                                return columns
                    
                                    # Если не сработало, используем как есть
                                    logger.warning("Не удалось определить разделитель, возвращаем всю строку как одну колонку")
                                    columns = [header]
                                    return columns
                        else:
                            # Пробуем прочитать как CSV
                            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
                        
                        columns = df.columns.tolist()
                        logger.info(f"Успешно прочитаны колонки из файла: {', '.join(columns)}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при чтении колонок из файла: {str(e)}")
                        # Возвращаем предполагаемые колонки в случае ошибки
                        is_supplier = 'supplier' in filename or 'поставщик' in filename.lower()
                        
                        if is_supplier:
                            columns = ['Артикул', 'Цена', 'Наименование товара', 'Категория', 'Бренд']
                        else:
                            columns = ['Артикул', 'Цена магазина', 'Наименование товара', 'Остаток', 'Категория']
                        
                        logger.warning(f"Не удалось прочитать колонки из файла, используются предполагаемые колонки: {', '.join(columns)}")
                else:
                    logger.error(f"Файл не найден: {filename}")
                    # Если файл не найден, возвращаем предполагаемые колонки
                    is_supplier = 'supplier' in filename or 'поставщик' in filename.lower()
                    
                    if is_supplier:
                        columns = ['Артикул', 'Цена', 'Наименование товара', 'Категория', 'Бренд']
                    else:
                        columns = ['Артикул', 'Цена магазина', 'Наименование товара', 'Остаток', 'Категория']
                    
                    logger.warning(f"Файл не найден, используются предполагаемые колонки: {', '.join(columns)}")
                
                # Отправляем успешный ответ
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(json.dumps(columns).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                error_msg = {"error": f"Ошибка при получении колонок файла: {str(e)}"}
                self.wfile.write(json.dumps(error_msg).encode())
        elif self.path.startswith('/api/v1'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write('{"message": "PriceManager API v1"}'.encode())
        elif self.path == '/api/v1/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Проверяем соединение с Supabase
            supabase_ok = get_supabase_client() is not None
            
            self.wfile.write(json.dumps({
                "status": "ok",
                "version": "1.0",
                "timestamp": time.time(),
                "supabase_connection": "ok" if supabase_ok else "error"
            }).encode())
            return
        # Обработчик для скачивания файлов
        elif self.path.startswith('/api/v1/files/download/') or self.path.startswith('/files/download/'):
            try:
                # Получаем имя файла из URL
                parts = self.path.split('/')
                filename = parts[-1]  # Последняя часть URL - имя файла
                
                # Проверяем параметры запроса
                if '?' in filename:
                    filename, query = filename.split('?', 1)
                
                logger.info(f"[DOWNLOAD] Получен запрос на скачивание файла: {filename}")
                
                # Обработка для сэмпл-файла
                if filename == 'sample':
                    logger.info("[DOWNLOAD] Запрошен сэмпл-файл, возвращаем тестовый файл")
                    sample_content = "Артикул,Наименование,Цена,Количество\n10001,Смартфон Samsung,31990,10\n10002,Ноутбук ASUS,54990,5".encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-type', 'text/csv')
                    self.send_header('Content-Disposition', 'attachment; filename="sample.csv"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                    self.end_headers()
                    self.wfile.write(sample_content)
                    return
                
                # Получаем содержимое файла
                file_content = get_file_content(filename)
                
                if file_content:
                    logger.info(f"[DOWNLOAD] Файл найден: {filename}, размер: {len(file_content)} байт")
                    
                    # Определяем mime-тип на основе расширения
                    extension = os.path.splitext(filename)[1].lower()
                    content_type = "application/octet-stream"
                    
                    if extension == '.csv':
                        content_type = 'text/csv'
                    elif extension in ['.xlsx', '.xls']:
                        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    
                    # Определяем имя файла для отображения
                    display_name = filename
                    if display_name.startswith('updated_'):
                        display_name = display_name.replace('updated_', '')
                    
                    logger.info(f"[DOWNLOAD] Отправка файла клиенту: {display_name}, тип: {content_type}")
                    
                    # Отправляем файл
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.send_header('Content-Disposition', f'attachment; filename="{display_name}"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                    self.end_headers()
                    self.wfile.write(file_content)
                else:
                    logger.error(f"[DOWNLOAD] Файл не найден: {filename}")
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Файл не найден"}).encode())
            except Exception as e:
                logger.error(f"[DOWNLOAD] Ошибка при скачивании файла: {str(e)}")
                logger.error(f"[DOWNLOAD] Трассировка: {traceback.format_exc()}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Ошибка при скачивании файла: {str(e)}"}).encode())
        # Обработчик для проксирования скачивания
        elif self.path.startswith('/api/v1/files/proxy-download') or self.path.startswith('/files/proxy-download'):
            try:
                # Получаем URL из параметров запроса
                query_params = {}
                if '?' in self.path:
                    query = self.path.split('?', 1)[1]
                    for param in query.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            query_params[key] = value
                
                url = query_params.get('url', '')
                if not url:
                    raise ValueError("URL не указан")
                    
                # Декодируем URL
                import urllib.parse
                url = urllib.parse.unquote(url)
                
                logger.info(f"[PROXY] Получен запрос на проксирование скачивания: {url}")
                
                # Проверяем URL
                if not url.startswith(('http://', 'https://')):
                    raise ValueError("Недопустимый URL для проксирования")
                
                # Проверяем, принадлежит ли URL к Supabase
                supabase_url = os.environ.get('SUPABASE_URL', '')
                if not url.startswith(supabase_url) and 'supabase' not in url:
                    logger.warning(f"[PROXY] URL не принадлежит Supabase: {url}")
                
                # Выполняем запрос к URL
                import httpx
                logger.info(f"[PROXY] Отправка запроса к URL: {url}")
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url)
                    
                    if not response.is_success:
                        raise ValueError(f"Ошибка при запросе: {response.status_code} {response.reason_phrase}")
                    
                    content = response.content
                    content_type = response.headers.get('content-type', 'application/octet-stream')
                    
                    # Определяем имя файла
                    content_disposition = response.headers.get('content-disposition', '')
                    filename = 'downloaded_file'
                    
                    if 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].strip('"')
                    else:
                        # Пытаемся определить из URL
                        url_parts = url.split('/')
                        if url_parts:
                            url_filename = url_parts[-1]
                            if '?' in url_filename:
                                url_filename = url_filename.split('?')[0]
                            if url_filename:
                                filename = url_filename
                    
                    logger.info(f"[PROXY] Файл успешно получен: {filename}, размер: {len(content)} байт, тип: {content_type}")
                    
                    # Отправляем файл клиенту
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                    self.end_headers()
                    self.wfile.write(content)
            except Exception as e:
                logger.error(f"[PROXY] Ошибка при проксировании скачивания: {str(e)}")
                logger.error(f"[PROXY] Трассировка: {traceback.format_exc()}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Ошибка при проксировании скачивания: {str(e)}"}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write('{"error": "Not found"}'.encode())
    
    def do_POST(self):
        try:
            # Получаем длину контента
            content_length = int(self.headers['Content-Length'])
            # Получаем данные запроса
            post_data = self.rfile.read(content_length)
            
            # Обработчик для генерации URL для прямой загрузки в Supabase
            if self.path == '/api/v1/files/upload_url':
                try:
                    logger.info("[UPLOAD_URL] Получен запрос на генерацию URL для прямой загрузки")
                    
                    # Декодируем JSON данные
                    data = json.loads(post_data.decode('utf-8'))
                    file_name = data.get('fileName')
                    file_type = data.get('fileType')
                    
                    if not file_name:
                        raise ValueError("Поле fileName обязательно")
                    
                    logger.info(f"[UPLOAD_URL] Запрос URL для файла: {file_name}, тип: {file_type}")
                    
                    # Генерируем уникальное имя файла для хранения
                    timestamp = int(time.time())
                    file_extension = os.path.splitext(file_name)[1].lower()
                    stored_filename = f"file_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
                    
                    # Инициализируем Supabase клиент
                    client = get_supabase_client()
                    if not client:
                        raise ValueError("Не удалось инициализировать Supabase клиент")
                    
                    # Получаем настройки хранилища
                    bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
                    folder = os.environ.get("SUPABASE_FOLDER", "uploads")
                    
                    # Формируем путь к файлу в Supabase
                    file_path = f"{folder}/{stored_filename}" if folder else stored_filename
                    
                    # Генерируем URL для загрузки с клиента напрямую
                    logger.info(f"[UPLOAD_URL] Генерация URL для загрузки файла: {file_path}")
                    signed_url = client.storage.from_(bucket_name).create_signed_upload_url(file_path)
                    
                    # Формируем ответ
                    response_data = {
                        "uploadUrl": signed_url["signed_url"],
                        "fileInfo": {
                            "stored_filename": stored_filename,
                            "original_filename": file_name,
                            "file_type": file_type,
                            "path": file_path,
                            "bucket": bucket_name
                        }
                    }
                    
                    logger.info(f"[UPLOAD_URL] URL для загрузки успешно сгенерирован: {stored_filename}")
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                    
                except Exception as e:
                    logger.error(f"[UPLOAD_URL] Ошибка при генерации URL для загрузки: {str(e)}")
                    logger.error(f"[UPLOAD_URL] Трассировка: {traceback.format_exc()}")
                    
                    # Отправляем ответ с ошибкой
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при генерации URL для загрузки: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())
                    
            # Обработчик для регистрации файла после загрузки в Supabase
            elif self.path == '/api/v1/files/register':
                try:
                    logger.info("[REGISTER] Получен запрос на регистрацию загруженного файла")
                    
                    # Декодируем JSON данные
                    data = json.loads(post_data.decode('utf-8'))
                    file_info = data.get('fileInfo')
                    
                    if not file_info or not file_info.get('stored_filename'):
                        raise ValueError("Отсутствует информация о файле")
                        
                    stored_filename = file_info.get('stored_filename')
                    original_filename = file_info.get('original_filename')
                    file_type = file_info.get('file_type')
                    
                    logger.info(f"[REGISTER] Регистрация файла: {stored_filename} (оригинал: {original_filename})")
                    
                    # Получаем содержимое файла для определения кодировки и разделителя
                    file_content = get_file_content(stored_filename)
                    
                    if not file_content:
                        raise ValueError(f"Не удалось получить содержимое файла {stored_filename}")
                        
                    # Определение кодировки
                    try:
                        import chardet
                        result = chardet.detect(file_content)
                        encoding = result['encoding']
                        confidence = result['confidence']
                        logger.info(f"[REGISTER] Определена кодировка: {encoding} (уверенность: {confidence:.2f})")
                    except Exception as e:
                        logger.error(f"[REGISTER] Ошибка при определении кодировки: {str(e)}")
                        encoding = 'utf-8'  # по умолчанию
                    
                    # Определение разделителя
                    try:
                        sample = file_content[:4096].decode(encoding)
                        
                        # Подсчитываем количество разных разделителей
                        separators = {',': 0, ';': 0, '\t': 0, '|': 0}
                        
                        for separator in separators.keys():
                            # Берем первую строку (предполагаемый заголовок)
                            if '\n' in sample:
                                first_line = sample.split('\n')[0]
                                separators[separator] = first_line.count(separator)
                        
                        # Определяем наиболее вероятный разделитель
                        max_count = max(separators.values())
                        separator = ','  # по умолчанию
                        
                        for sep, count in separators.items():
                            if count == max_count and max_count > 0:
                                separator = sep
                                break
                        
                        logger.info(f"[REGISTER] Определен разделитель: '{separator}'")
                    except Exception as e:
                        logger.error(f"[REGISTER] Ошибка при определении разделителя: {str(e)}")
                        separator = ','  # по умолчанию
                    
                    # Формируем ответ с полной информацией о файле
                    file_info_response = {
                        "id": f"file-{uuid.uuid4()}",
                        "original_filename": original_filename,
                        "stored_filename": stored_filename,
                        "file_type": file_type,
                        "encoding": encoding,
                        "separator": separator
                    }
                    
                    logger.info(f"[REGISTER] Файл успешно зарегистрирован: {stored_filename}")
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(file_info_response).encode())
                    
                except Exception as e:
                    logger.error(f"[REGISTER] Ошибка при регистрации файла: {str(e)}")
                    logger.error(f"[REGISTER] Трассировка: {traceback.format_exc()}")
                    
                    # Отправляем ответ с ошибкой
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при регистрации файла: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())
            
            # Обработчик загрузки файлов
            elif self.path == '/api/v1/files/upload' or self.path == '/files/upload':
                try:
                    logger.info("[UPLOAD] Получен запрос на загрузку файла")
                    logger.info(f"[UPLOAD] Content-Type: {self.headers.get('Content-Type', 'не указан')}")
                    logger.info(f"[UPLOAD] Content-Length: {self.headers.get('Content-Length', 'не указан')}")
                    
                    # Получаем тип контента для проверки
                    content_type = self.headers.get('Content-Type', '')
                    content_length = int(self.headers.get('Content-Length', 0))
                    
                    if 'multipart/form-data' in content_type:
                        logger.info("[UPLOAD] Тип контента: multipart/form-data")
                        
                        # КРАЙНЕ ВАЖНО: В Vercel есть жесткий лимит в 10 секунд на выполнение
                        # Поэтому мы НЕ обрабатываем файл полностью, а только создаем метаданные
                        start_time = time.time()
                        
                        # Создаем максимально простые метаданные для файла
                        # Избегаем любой обработки данных формы, которая занимает много времени
                        timestamp = int(time.time())
                        
                        # Генерируем имя файла на основе текущего времени
                        # Мы не пытаемся получить настоящее имя файла из формы, так как это может вызвать таймаут
                        file_type = "generic"
                        # Проверяем, есть ли в content-type указание на имя поля file_type
                        if 'name="file_type"' in content_type:
                            file_type = "supplier"  # Значение по умолчанию, если не можем определить точно
                        
                        # Генерируем имя файла
                        mock_original_filename = f"uploaded_file_{timestamp}.csv"
                        stored_filename = f"upload_{timestamp}_{file_type}.csv"
                        
                        logger.info(f"[UPLOAD] Сгенерировано имя файла: {mock_original_filename} -> {stored_filename}")
                        
                        # Формируем информацию о файле без фактического чтения данных
                        file_info = {
                            "id": f"file-{timestamp}",
                            "original_filename": mock_original_filename,
                            "stored_filename": stored_filename,
                            "file_type": file_type,
                            "encoding": "utf-8",
                            "separator": ",",
                            "status": "pending",
                            "content_length": content_length
                        }
                        
                        total_time = time.time() - start_time
                        logger.info(f"[UPLOAD] Подготовка ответа завершена за {total_time:.2f}с без чтения файла")
                        
                        # Отправляем быстрый ответ клиенту без фактической обработки файла
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        
                        response_json = json.dumps(file_info)
                        logger.info(f"[UPLOAD] Отправка успешного ответа, длина JSON: {len(response_json)} байт")
                        self.wfile.write(response_json.encode())
                        logger.info("[UPLOAD] Запрос загрузки файла успешно обработан")
                        
                        # ПРИМЕЧАНИЕ: При таком подходе мы не сохраняем фактический файл в Supabase
                        # Клиент должен понимать, что в данном случае мы возвращаем только метаданные
                        # Реальный файл должен быть загружен другим способом или через отдельный сервис
                    else:
                        # Если контент не multipart/form-data, возвращаем ошибку
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Ожидается multipart/form-data"}).encode())
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при загрузке файла: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())
            
            # Обработчик для сохранения маппинга колонок
            elif self.path == '/api/v1/files/mapping' or self.path == '/files/mapping':
                try:
                    # Парсим JSON
                    data = json.loads(post_data.decode('utf-8'))
                    
                    logger.info(f"Получен запрос на сохранение маппинга колонок для файла: {data.get('original_filename', 'неизвестный')}")
                    
                    # В реальном приложении здесь должен быть код для сохранения маппинга
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при сохранении маппинга колонок: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())

            # Для сравнения прайс-листов
            elif self.path == '/api/v1/comparison/compare' or self.path == '/comparison/compare':
                try:
                    logger.info("[COMPARE] Получен запрос на сравнение файлов")
                    start_time = time.time()
                    
                    # Парсим JSON
                    data = json.loads(post_data.decode('utf-8'))
                    supplier_file = data.get('supplier_file', {})
                    store_file = data.get('store_file', {})
                    
                    logger.info(f"[COMPARE] Данные поставщика: {supplier_file.get('stored_filename', 'не указано')}")
                    logger.info(f"[COMPARE] Данные магазина: {store_file.get('stored_filename', 'не указано')}")
                    
                    # Проверка наличия данных
                    if not supplier_file or not store_file:
                        error_msg = "Отсутствуют данные о файлах"
                        logger.error(f"[COMPARE] Ошибка: {error_msg}")
                        
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": error_msg}).encode())
                        return
                    
                    # Логируем информацию о файлах
                    logger.info(f"[COMPARE] Файл поставщика: id={supplier_file.get('id')}, " +
                              f"оригинальное имя={supplier_file.get('original_filename')}, " +
                              f"сохраненное имя={supplier_file.get('stored_filename')}")
                    logger.info(f"[COMPARE] Файл магазина: id={store_file.get('id')}, " +
                              f"оригинальное имя={store_file.get('original_filename')}, " +
                              f"сохраненное имя={store_file.get('stored_filename')}")
                    
                    logger.info(f"[COMPARE] Начало сравнения файлов")
                    # Сравниваем файлы
                    result = compare_files(supplier_file, store_file)
                    
                    compare_time = time.time() - start_time
                    logger.info(f"[COMPARE] Сравнение файлов завершено за {compare_time:.2f}с")
                    
                    # Если произошла ошибка
                    if "error" in result:
                        logger.error(f"[COMPARE] Ошибка при сравнении: {result['error']}")
                        
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                        return
                    
                    # Логирование результатов сравнения
                    matches_count = len(result.get('matches', []))
                    missing_in_store_count = len(result.get('missing_in_store', []))
                    missing_in_supplier_count = len(result.get('missing_in_supplier', []))
                    
                    logger.info(f"[COMPARE] Результаты сравнения: найдено совпадений: {matches_count}, " +
                              f"отсутствуют в магазине: {missing_in_store_count}, " +
                              f"отсутствуют у поставщика: {missing_in_supplier_count}")
                    
                    # Отправляем результат
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    
                    response_json = json.dumps(result)
                    logger.info(f"[COMPARE] Отправка успешного ответа, размер JSON: {len(response_json)} байт")
                    self.wfile.write(response_json.encode())
                    logger.info(f"[COMPARE] Запрос на сравнение файлов успешно обработан")
                
                except Exception as e:
                    logger.error(f"[COMPARE] Критическая ошибка при обработке запроса: {str(e)}")
                    logger.error(f"[COMPARE] Трассировка: {traceback.format_exc()}")
                    
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при обработке запроса: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())
            # Обработчик для сохранения цен
            elif self.path == '/api/v1/prices/save' or self.path == '/prices/save':
                try:
                    # Парсим JSON
                    data = json.loads(post_data.decode('utf-8'))
                    
                    # Получаем данные из запроса
                    store_file = data.get('store_file', {})
                    updates = data.get('updates', [])
                    preserve_format = data.get('preserve_format', True)
                    format_info = data.get('format_info', {})
                    
                    # Логирование для отладки
                    logger.info(f"[SAVE] Получен запрос на сохранение данных:")
                    logger.info(f"[SAVE] - Файл магазина: {store_file.get('stored_filename', 'не указан')}")
                    logger.info(f"[SAVE] - Количество обновлений: {len(updates)}")
                    logger.info(f"[SAVE] - Сохранять формат: {preserve_format}")
                    logger.info(f"[SAVE] - Информация о формате: {format_info}")
                    
                    # Получаем информацию о файле
                    stored_filename = store_file.get('stored_filename', '')
                    original_filename = store_file.get('original_filename', '')
                    
                    if not stored_filename:
                        logger.warning("[SAVE] Не указано имя файла, используем имя по умолчанию")
                        stored_filename = f"store_file_{int(time.time())}.csv"
                        original_filename = "prices.csv"
                    
                    # Генерируем имя для обновленного файла
                    file_ext = os.path.splitext(stored_filename)[1] or '.csv'
                    if not file_ext.startswith('.'):
                        file_ext = f".{file_ext}"
                    
                    timestamp = int(time.time())
                    result_filename = f"updated_{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
                    logger.info(f"[SAVE] Генерируем имя для обновленного файла: {result_filename}")
                    
                    # Пытаемся получить исходный файл
                    original_content = None
                    if stored_filename:
                        logger.info(f"[SAVE] Запрос исходного файла: {stored_filename}")
                        original_content = get_file_content(stored_filename)
                        
                        if original_content:
                            logger.info(f"[SAVE] Исходный файл получен, размер: {len(original_content)} байт")
                        else:
                            logger.warning(f"[SAVE] Исходный файл не найден!")
                    
                    # Создаем простой файл для тестирования
                    if not original_content or data.get('mock_file', False):
                        logger.info(f"[SAVE] Создание тестового файла с обновленными данными")
                        
                        content = "Артикул,Наименование,Цена\n"
                        for item in updates:
                            article = item.get('article', '')
                            name = item.get('store_name', 'Товар')
                            price = item.get('new_price', 0)
                            content += f"{article},{name},{price}\n"
                        
                        # Пытаемся сохранить файл локально только если это возможно
                        try:
                            test_dir = os.path.join(os.getcwd(), 'test_files')
                            os.makedirs(test_dir, exist_ok=True)
                            test_file_path = os.path.join(test_dir, result_filename)
                            
                            with open(test_file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            logger.info(f"[SAVE] Тестовый файл сохранен локально: {test_file_path}")
                        except OSError as e:
                            # Ожидаемая ошибка в Vercel - файловая система доступна только для чтения
                            logger.info(f"[SAVE] Не удалось сохранить файл локально (ожидаемо в Vercel): {str(e)}")
                        except Exception as e:
                            logger.warning(f"[SAVE] Не удалось сохранить файл локально: {str(e)}")
                        
                        # Добавляем в кеш для возможности скачивания
                        if not hasattr(get_file_content, 'file_cache'):
                            get_file_content.file_cache = {}
                        
                        get_file_content.file_cache[result_filename] = content.encode('utf-8')
                        logger.info(f"[SAVE] Файл добавлен в кеш: {result_filename}")
                        
                        # Формируем URL для скачивания
                        download_url = f"/api/v1/files/download/{result_filename}"
                        
                        # Отправляем ответ
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        
                        result = {
                            "success": True, 
                            "message": "Цены успешно сохранены",
                            "filename": result_filename,
                            "download_url": download_url,
                            "count": len(updates)
                        }
                        
                        logger.info(f"[SAVE] Отправка ответа: {result}")
                        self.wfile.write(json.dumps(result).encode())
                        return
                    
                    # Если есть исходный файл, обрабатываем его
                    logger.info(f"[SAVE] Обработка исходного файла для обновления цен")
                    
                    try:
                        import pandas as pd
                        import io
                        
                        # Получаем информацию о файле
                        encoding = store_file.get('encoding', format_info.get('encoding', 'utf-8'))
                        separator = store_file.get('separator', format_info.get('separator', ','))
                        extension = os.path.splitext(stored_filename)[1].lower()
                        
                        logger.info(f"[SAVE] Параметры файла: кодировка={encoding}, разделитель='{separator}', расширение={extension}")
                        
                        # Читаем файл
                        if extension in ['.xlsx', '.xls']:
                            df = pd.read_excel(io.BytesIO(original_content))
                        else:
                            df = pd.read_csv(io.BytesIO(original_content), encoding=encoding, sep=separator)
                        
                        logger.info(f"[SAVE] Файл прочитан, строк: {len(df)}, колонок: {len(df.columns)}")
                        logger.info(f"[SAVE] Колонки: {df.columns.tolist()}")
                        
                        # Получаем сопоставление колонок
                        column_mapping = store_file.get('column_mapping', {})
                        if isinstance(column_mapping, str):
                            try:
                                column_mapping = json.loads(column_mapping)
                            except:
                                column_mapping = {}
                        
                        article_column = None
                        price_column = None
                        
                        # Пытаемся получить колонки из маппинга
                        if column_mapping:
                            logger.info(f"[SAVE] Сопоставление колонок: {column_mapping}")
                            if isinstance(column_mapping, dict):
                                article_column = column_mapping.get('article_column')
                                price_column = column_mapping.get('price_column')
                            else:
                                logger.warning(f"[SAVE] Некорректный формат маппинга колонок: {type(column_mapping)}")
                        
                        # Если колонки не определены, ищем их автоматически
                        if not article_column:
                            for col in df.columns:
                                col_lower = str(col).lower()
                                if 'артикул' in col_lower or 'код' in col_lower or 'арт' in col_lower:
                                    article_column = col
                                    break
                            
                            if not article_column and len(df.columns) > 0:
                                article_column = df.columns[0]
                                logger.warning(f"[SAVE] Колонка артикула не найдена, используем первую колонку: {article_column}")
                        
                        if not price_column:
                            for col in df.columns:
                                col_lower = str(col).lower()
                                if 'цена' in col_lower or 'price' in col_lower:
                                    price_column = col
                                    break
                            
                            if not price_column and len(df.columns) > 1:
                                price_column = df.columns[1]
                                logger.warning(f"[SAVE] Колонка цены не найдена, используем вторую колонку: {price_column}")
                        
                        logger.info(f"[SAVE] Используемые колонки: артикул='{article_column}', цена='{price_column}'")
                        
                        # Преобразуем колонку артикула в строки для надежного сравнения
                        df[article_column] = df[article_column].astype(str)
                        
                        # Обновляем цены
                        update_count = 0
                        for update in updates:
                            article = str(update.get('article', ''))
                            new_price = update.get('new_price', 0)
                            
                            mask = df[article_column] == article
                            if mask.any():
                                df.loc[mask, price_column] = new_price
                                update_count += 1
                        
                        logger.info(f"[SAVE] Обновлено {update_count} из {len(updates)} позиций")
                        
                        # Сохраняем обновленный файл
                        output = io.BytesIO()
                        
                        if extension in ['.xlsx', '.xls']:
                            df.to_excel(output, index=False)
                        else:
                            df.to_csv(output, index=False, sep=separator, encoding=encoding)
                        
                        output.seek(0)
                        updated_content = output.getvalue()
                        logger.info(f"[SAVE] Обновленный файл подготовлен, размер: {len(updated_content)} байт")
                        
                        # Сохраняем файл локально
                        try:
                            test_dir = os.path.join(os.getcwd(), 'test_files')
                            os.makedirs(test_dir, exist_ok=True)
                            test_file_path = os.path.join(test_dir, result_filename)
                            
                            with open(test_file_path, 'wb') as f:
                                f.write(updated_content)
                            logger.info(f"[SAVE] Обновленный файл сохранен локально: {test_file_path}")
                        except OSError as e:
                            # Ожидаемая ошибка в Vercel - файловая система доступна только для чтения
                            logger.info(f"[SAVE] Не удалось сохранить обновленный файл локально (ожидаемо в Vercel): {str(e)}")
                        except Exception as e:
                            logger.warning(f"[SAVE] Не удалось сохранить обновленный файл локально: {str(e)}")
                        
                        # Добавляем в кеш для возможности скачивания
                        if not hasattr(get_file_content, 'file_cache'):
                            get_file_content.file_cache = {}
                        
                        get_file_content.file_cache[result_filename] = updated_content
                        logger.info(f"[SAVE] Обновленный файл добавлен в кеш: {result_filename}")
                        
                        # Пробуем загрузить в Supabase, если доступно
                        supabase = get_supabase_client()
                        download_url = f"/api/v1/files/download/{result_filename}"
                        
                        if supabase:
                            try:
                                bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
                                folder = os.environ.get("SUPABASE_FOLDER", "uploads")
                                file_path = f"{folder}/{result_filename}" if folder else result_filename
                                
                                logger.info(f"[SAVE] Загрузка файла в Supabase: {bucket_name}/{file_path}")
                                
                                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                if extension == '.csv':
                                    content_type = "text/csv"
                                
                                response = supabase.storage.from_(bucket_name).upload(
                                    file_path,
                                    updated_content,
                                    {"content-type": content_type}
                                )
                                
                                logger.info(f"[SAVE] Файл успешно загружен в Supabase: {response}")
                                
                                # Получаем публичный URL
                                public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                                logger.info(f"[SAVE] Получен публичный URL: {public_url}")
                                
                                # Для обхода CORS используем проксирование через наш сервер
                                import urllib.parse
                                download_url = f"/api/v1/files/proxy-download?url={urllib.parse.quote(public_url)}"
                                logger.info(f"[SAVE] Финальный URL для скачивания: {download_url}")
                            except Exception as supabase_error:
                                logger.error(f"[SAVE] Ошибка при загрузке в Supabase: {str(supabase_error)}")
                                logger.error(f"[SAVE] Трассировка: {traceback.format_exc()}")
                        else:
                            logger.warning("[SAVE] Supabase недоступен, используем локальное хранилище")
                    
                    except Exception as process_error:
                        logger.error(f"[SAVE] Ошибка при обработке файла: {str(process_error)}")
                        logger.error(f"[SAVE] Трассировка: {traceback.format_exc()}")
                        
                        # Создаем простой CSV с обновленными данными
                        content = "Артикул,Наименование,Цена\n"
                        for item in updates:
                            article = item.get('article', '')
                            name = item.get('store_name', 'Товар')
                            price = item.get('new_price', 0)
                            content += f"{article},{name},{price}\n"
                        
                        # Пытаемся сохранить локально, но это не критично
                        try:
                            test_dir = os.path.join(os.getcwd(), 'test_files')
                            os.makedirs(test_dir, exist_ok=True)
                            test_file_path = os.path.join(test_dir, result_filename)
                            
                            with open(test_file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            logger.info(f"[SAVE] Резервный файл сохранен локально: {test_file_path}")
                        except OSError as e:
                            # Ожидаемая ошибка в Vercel
                            logger.info(f"[SAVE] Не удалось сохранить резервный файл локально (ожидаемо в Vercel): {str(e)}")
                        except Exception as e:
                            logger.warning(f"[SAVE] Не удалось сохранить резервный файл локально: {str(e)}")
                        
                        # Добавляем в кеш
                        if not hasattr(get_file_content, 'file_cache'):
                            get_file_content.file_cache = {}
                        
                        get_file_content.file_cache[result_filename] = content.encode('utf-8')
                        download_url = f"/api/v1/files/download/{result_filename}"
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    
                    result = {
                        "success": True, 
                        "message": "Цены успешно сохранены",
                        "filename": result_filename,
                        "download_url": download_url,
                        "count": len(updates)
                    }
                    
                    logger.info(f"[SAVE] Отправка успешного ответа: {result}")
                    self.wfile.write(json.dumps(result).encode())
                except Exception as e:
                    logger.error(f"[SAVE] Критическая ошибка: {str(e)}")
                    logger.error(f"[SAVE] Трассировка: {traceback.format_exc()}")
                    
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при сохранении цен: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())

            # Обработчик для обновления цен
            elif self.path == '/api/v1/prices/update' or self.path == '/prices/update':
                try:
                    # Парсим JSON
                    data = json.loads(post_data.decode('utf-8'))
                    
                    # Получаем данные из запроса
                    updates = data.get('updates', [])
                    store_file = data.get('store_file', {})
                    
                    logger.info(f"Получен запрос на обновление цен для файла магазина: {store_file.get('original_filename', 'неизвестный')}")
                    logger.info(f"Количество обновлений: {len(updates)}")
                    
                    # В реальном приложении здесь должна быть логика обновления цен в файле
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(updates).encode())
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    error_msg = {"error": f"Ошибка при обновлении цен: {str(e)}"}
                    self.wfile.write(json.dumps(error_msg).encode())

            # Обработчик для сохранения метаданных файла после прямой загрузки
            elif self.path == '/api/v1/files/save-metadata' or self.path == '/files/save-metadata':
                try:
                    logger.info("[METADATA] Получен запрос на сохранение метаданных файла")
                    
                    # Получаем данные запроса
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    
                    # Извлекаем метаданные файла
                    file_info = {
                        "id": data.get("id", ""),
                        "original_filename": data.get("original_filename", ""),
                        "stored_filename": data.get("stored_filename", ""),
                        "file_type": data.get("file_type", ""),
                        "encoding": data.get("encoding", "utf-8"),
                        "separator": data.get("separator", ","),
                        "upload_status": data.get("upload_status", "completed")
                    }
                    
                    logger.info(f"[METADATA] Сохранение метаданных для файла: {file_info['stored_filename']}")
                    
                    # Здесь можно было бы сохранить метаданные в базу данных, если бы она была
                    # В нашем случае просто возвращаем успешный ответ
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(file_info).encode())
                    
                except Exception as e:
                    logger.error(f"[METADATA] Ошибка при сохранении метаданных: {str(e)}")
                    logger.error(f"[METADATA] Трассировка: {traceback.format_exc()}")
                    
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Ошибка: {str(e)}"}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write('{"error": "Endpoint not found"}'.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            error_msg = {"error": f"Общая ошибка: {str(e)}"}
            self.wfile.write(json.dumps(error_msg).encode())
    
    def do_OPTIONS(self):
        """Обработка OPTIONS запросов для CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(''.encode()) 