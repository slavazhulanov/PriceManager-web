from http.server import BaseHTTPRequestHandler
import json
import os
import pandas as pd
import io
from supabase import create_client

# Инициализация Supabase
def get_supabase_client():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return None
    return create_client(supabase_url, supabase_key)

# Функция для получения содержимого файла из Supabase
def get_file_content(stored_filename):
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        bucket_name = os.environ.get("SUPABASE_BUCKET", "price-manager")
        folder = os.environ.get("SUPABASE_FOLDER", "uploads")
        
        # Получаем файл из Supabase Storage
        file_path = f"{folder}/{stored_filename}" if folder else stored_filename
        response = supabase.storage.from_(bucket_name).download(file_path)
        
        return response
    except Exception as e:
        print(f"Ошибка при получении файла из Supabase: {str(e)}")
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
        print(f"Ошибка при чтении файла: {str(e)}")
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
                price_diff = store_price - supplier_price
                price_diff_percent = (price_diff / supplier_price) * 100 if supplier_price > 0 else 0
                
                # Получаем названия товаров если они есть
                supplier_name = supplier_df.loc[supplier_df[supplier_article_col] == article, supplier_name_col].iloc[0] if supplier_name_col else None
                store_name = store_df.loc[store_df[store_article_col] == article, store_name_col].iloc[0] if store_name_col else None
                
                matches.append({
                    "article": article,
                    "supplier_price": float(supplier_price),
                    "store_price": float(store_price),
                    "price_diff": float(price_diff),
                    "price_diff_percent": float(price_diff_percent),
                    "supplier_name": supplier_name if supplier_name_col else None,
                    "store_name": store_name if store_name_col else None
                })
            else:
                # Товар есть у поставщика, но нет в магазине
                supplier_name = supplier_df.loc[supplier_df[supplier_article_col] == article, supplier_name_col].iloc[0] if supplier_name_col else None
                missing_in_store.append({
                    "article": article,
                    "supplier_price": float(supplier_price),
                    "supplier_name": supplier_name if supplier_name_col else None
                })
        
        # Товары, которые есть в магазине, но нет у поставщика
        for article, store_price in store_dict.items():
            if article not in supplier_dict:
                store_name = store_df.loc[store_df[store_article_col] == article, store_name_col].iloc[0] if store_name_col else None
                missing_in_supplier.append({
                    "article": article,
                    "store_price": float(store_price),
                    "store_name": store_name if store_name_col else None
                })
        
        return {
            "matches": matches,
            "missing_in_store": missing_in_store,
            "missing_in_supplier": missing_in_supplier
        }
    except Exception as e:
        print(f"Ошибка при сравнении файлов: {str(e)}")
        return {"error": f"Ошибка при сравнении файлов: {str(e)}"}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write('{"message": "PriceManager API работает"}'.encode())
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
            
            # Для сравнения прайс-листов
            if self.path == '/api/v1/comparison/compare':
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