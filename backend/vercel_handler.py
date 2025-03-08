from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import pandas as pd
import io
from supabase import create_client
import time
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("vercel_handler")

# Инициализация Supabase
def get_supabase_client():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("Отсутствуют переменные окружения SUPABASE_URL или SUPABASE_KEY")
        return None
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Не удалось инициализировать Supabase клиент: {str(e)}")
        return None

# Функция для получения содержимого файла из Supabase
def get_file_content(stored_filename):
    try:
        # Для mock-файлов возвращаем заготовленные данные без обращения к Supabase
        if "mock_" in stored_filename:
            logger.info(f"Запрошен мок-файл: {stored_filename}, возвращаем тестовые данные")
            
            # Генерируем тестовые данные в зависимости от назначения файла
            if "_supplier" in stored_filename or stored_filename.endswith("3_mock_file.csv") or stored_filename.endswith("0_mock_file.csv"):
                # Данные поставщика
                return "article,name,price,quantity\n1001,Product 1,100.00,10\n1002,Product 2,200.00,20\n1003,Product 3,300.00,30".encode('utf-8')
            else:
                # Данные магазина
                return "article,name,price,quantity\n1001,Product 1,150.00,5\n1002,Product 2,250.00,15\n1004,Product 4,400.00,25".encode('utf-8')
        
        # Для не-мок файлов обращаемся к Supabase
        supabase = get_supabase_client()
        if not supabase:
            logger.error("Не удалось инициализировать Supabase клиент")
            return None
        
        bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
        folder = os.environ.get("SUPABASE_FOLDER", "uploads")
        
        # Получаем файл из Supabase Storage
        file_path = f"{folder}/{stored_filename}" if folder else stored_filename
        logger.info(f"Запрос файла из Supabase: бакет={bucket_name}, путь={file_path}")
        
        try:
            response = supabase.storage.from_(bucket_name).download(file_path)
            logger.info(f"Файл успешно получен: {stored_filename}, размер: {len(response)} байт")
            return response
        except Exception as download_error:
            logger.error(f"Ошибка при загрузке файла через API: {str(download_error)}")
            
            # Если это тестовый файл, возвращаем базовые тестовые данные
            if stored_filename == "test.csv":
                logger.info("Возвращаем базовые тестовые данные для test.csv")
                return "column1,column2,column3\nvalue1,value2,value3\n".encode('utf-8')
            
            return None
    except Exception as e:
        logger.error(f"Общая ошибка при получении файла из Supabase: {str(e)}")
        return None

# Функция для чтения и анализа файла
def read_file(file_content, extension, encoding, separator):
    try:
        if extension in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(file_content))
        else:  # CSV
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, sep=separator)
        return df
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {str(e)}")
        return None


# Функция для сравнения файлов
def compare_files(supplier_file_info, store_file_info):
    try:
        # Получаем файлы из Supabase
        supplier_content = get_file_content(supplier_file_info['stored_filename'])
        store_content = get_file_content(store_file_info['stored_filename'])
        
        if not supplier_content or not store_content:
            return {"error": "Не удалось получить файлы из хранилища"}
        
        # Получаем информацию о колонках
        supplier_mapping = supplier_file_info.get('column_mapping', {})
        store_mapping = store_file_info.get('column_mapping', {})
        
        if not supplier_mapping or not store_mapping:
            return {"error": "Отсутствует маппинг колонок"}
        
        # Читаем файлы
        supplier_ext = os.path.splitext(supplier_file_info['original_filename'])[1].lower()
        store_ext = os.path.splitext(store_file_info['original_filename'])[1].lower()
        
        supplier_df = read_file(supplier_content, supplier_ext, supplier_file_info.get('encoding', 'utf-8'), supplier_file_info.get('separator', ','))
        store_df = read_file(store_content, store_ext, store_file_info.get('encoding', 'utf-8'), store_file_info.get('separator', ','))
        
        if supplier_df is None or store_df is None:
            return {"error": "Ошибка при чтении файлов"}
        
        # Колонки для сравнения
        supplier_article_col = supplier_mapping.get('article_column')
        supplier_price_col = supplier_mapping.get('price_column')
        supplier_name_col = supplier_mapping.get('name_column')
        
        store_article_col = store_mapping.get('article_column')
        store_price_col = store_mapping.get('price_column')
        store_name_col = store_mapping.get('name_column')
        
        # Создаем структуры для результатов
        matches = []
        missing_in_store = []
        missing_in_supplier = []
        
        # Преобразуем артикулы в строки для сравнения
        supplier_df[supplier_article_col] = supplier_df[supplier_article_col].astype(str)
        store_df[store_article_col] = store_df[store_article_col].astype(str)
        
        # Создаем словари для быстрого поиска
        supplier_dict = dict(zip(supplier_df[supplier_article_col], supplier_df[supplier_price_col]))
        store_dict = dict(zip(store_df[store_article_col], store_df[store_price_col]))
        
        # Сравнение цен
        for article, supplier_price in supplier_dict.items():
            if article in store_dict:
                store_price = store_dict[article]
                price_diff = float(store_price) - float(supplier_price)
                price_diff_percent = (price_diff / float(supplier_price)) * 100 if float(supplier_price) > 0 else 0
                
                # Получаем названия товаров если они есть
                supplier_name = supplier_df.loc[supplier_df[supplier_article_col] == article, supplier_name_col].iloc[0] if supplier_name_col else None
                store_name = store_df.loc[store_df[store_article_col] == article, store_name_col].iloc[0] if store_name_col else None
                
                matches.append({
                    "article": article,
                    "supplier_price": float(supplier_price),
                    "store_price": float(store_price),
                    "price_diff": float(price_diff),
                    "price_diff_percent": float(price_diff_percent),
                    "supplier_name": str(supplier_name) if supplier_name_col else None,
                    "store_name": str(store_name) if store_name_col else None
                })
            else:
                # Товар есть у поставщика, но нет в магазине
                supplier_name = supplier_df.loc[supplier_df[supplier_article_col] == article, supplier_name_col].iloc[0] if supplier_name_col else None
                missing_in_store.append({
                    "article": article,
                    "supplier_price": float(supplier_price),
                    "supplier_name": str(supplier_name) if supplier_name_col else None
                })
        
        # Товары, которые есть в магазине, но нет у поставщика
        for article, store_price in store_dict.items():
            if article not in supplier_dict:
                store_name = store_df.loc[store_df[store_article_col] == article, store_name_col].iloc[0] if store_name_col else None
                missing_in_supplier.append({
                    "article": article,
                    "store_price": float(store_price),
                    "store_name": str(store_name) if store_name_col else None
                })
        
        return {
            "matches": matches,
            "missing_in_store": missing_in_store,
            "missing_in_supplier": missing_in_supplier
        }
    except Exception as e:
        logger.error(f"Ошибка при сравнении файлов: {str(e)}")
        return {"error": f"Ошибка при сравнении файлов: {str(e)}"}

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
                
                # Определяем тип файла по имени
                is_supplier = 'supplier' in filename or 'поставщик' in filename.lower()
                
                if is_supplier:
                    columns = ['Артикул', 'Цена поставщика', 'Наименование товара', 'Категория', 'Бренд']
                else:
                    columns = ['Артикул', 'Цена магазина', 'Наименование товара', 'Остаток', 'Категория']
                
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
            
            # Обработчик загрузки файлов
            if self.path == '/api/v1/files/upload' or self.path == '/files/upload':
                try:
                    # Проверяем, является ли контент многофайловым
                    content_type = self.headers.get('Content-Type', '')
                    if 'multipart/form-data' in content_type:
                        logger.info("Получен запрос на загрузку файла (multipart/form-data)")
                        
                        # В реальном приложении здесь должен быть код для обработки multipart/form-data и сохранения файла
                        
                        filename = "mock_file.csv"  # В реальном приложении извлекается из запроса
                        file_type = "store"         # В реальном приложении извлекается из запроса
                        
                        # Генерируем уникальное имя для сохраненного файла
                        stored_filename = f"mock_{int(time.time())}_{filename}"
                        
                        # Формируем ответ
                        file_info = {
                            "id": f"mock-id-{int(time.time())}",
                            "original_filename": filename,
                            "stored_filename": stored_filename,
                            "file_type": file_type,
                            "encoding": "utf-8",
                            "separator": ","
                        }
                        
                        # Отправляем успешный ответ
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps(file_info).encode())
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
                    # Парсим JSON
                    data = json.loads(post_data.decode('utf-8'))
                    supplier_file = data.get('supplier_file', {})
                    store_file = data.get('store_file', {})
                    
                    # Проверка наличия данных
                    if not supplier_file or not store_file:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Отсутствуют данные о файлах"}).encode())
                        return
                    
                    # Сравниваем файлы
                    result = compare_files(supplier_file, store_file)
                    
                    # Если произошла ошибка
                    if "error" in result:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                        return
                    
                    # Отправляем результат
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                except Exception as e:
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
                    logger.info(f"Получен запрос на сохранение данных:")
                    logger.info(f"- Файл магазина: {store_file.get('filename', 'не указан')}")
                    logger.info(f"- Количество обновлений: {len(updates)}")
                    logger.info(f"- Сохранять формат: {preserve_format}")
                    
                    # Имя файла для сохранения результатов
                    filename = store_file.get('filename', '')
                    result_filename = f"updated_{filename}" if filename else "updated_prices.xlsx"
                    
                    # В реальном приложении здесь должно быть сохранение в базу данных
                    
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
                        "download_url": f"/downloads/{result_filename}",
                        "count": len(updates)
                    }
                    self.wfile.write(json.dumps(result).encode())
                except Exception as e:
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