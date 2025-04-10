from http.server import BaseHTTPRequestHandler
import json
import os
import uuid
import time
import re
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Проверяем, является ли это запросом на получение колонок файла
        columns_pattern = re.compile(r'/api/v1/files/columns/(.+)')
        columns_match = columns_pattern.match(self.path)
        
        if columns_match:
            # Это запрос на получение колонок
            filename = columns_match.group(1)
            # Обрезаем параметры запроса, если они есть
            if '?' in filename:
                filename = filename.split('?')[0]
            
            print(f"Запрос колонок для файла: {filename}")
            
            # Возвращаем тестовый набор колонок в зависимости от типа файла
            if 'supplier' in filename.lower():
                columns = ["Артикул", "Наименование", "Цена", "Остаток", "Код производителя"]
                print(f"Возвращаем колонки для файла поставщика: {columns}")
            else:
                columns = ["Артикул", "Наименование", "Цена", "Количество"]
                print(f"Возвращаем колонки для файла магазина: {columns}")
            
            # Возвращаем колонки в формате, который ожидает фронтенд
            self.wfile.write(json.dumps(columns, ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/api/v1/files/') and '/columns/' not in self.path:
            # Другие запросы к файлам, но не для получения колонок
            file_id = self.path.split('/')[-1]
            
            response_data = {
                "id": file_id,
                "original_filename": f"file_{file_id}.csv",
                "stored_filename": f"file_{file_id}.csv",
                "file_url": f"/api/v1/files/download/{file_id}",
                "file_type": "supplier" if "supplier" in self.path else "store",
                "file_size": 1000,
                "encoding": "utf-8",
                "separator": ",",
                "upload_date": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            # Общий ответ API для других запросов
            response_data = {
                "status": "ok",
                "message": "API работает",
                "timestamp": datetime.now().isoformat(),
                "path": self.path
            }
            
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        return
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            post_data_json = json.loads(post_data.decode('utf-8'))
            path = self.path
            
            # Обрабатываем запрос URL для загрузки
            if path == '/api/v1/files/upload_url':
                file_name = post_data_json.get('fileName', '')
                file_type = post_data_json.get('fileType', '')
                
                # Генерируем временный идентификатор для файла
                timestamp = int(time.time())
                file_ext = os.path.splitext(file_name)[1]
                stored_filename = f"file_{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
                
                # Создаем заглушку для загрузки
                response_data = {
                    "uploadUrl": f"/api/v1/files/mock-upload/{stored_filename}",
                    "fileInfo": {
                        "id": f"mock-{uuid.uuid4()}",
                        "original_filename": file_name,
                        "stored_filename": stored_filename,
                        "file_type": file_type,
                        "upload_path": f"uploads/{stored_filename}"
                    }
                }
            elif path == '/api/v1/files/register':
                # Обработка регистрации загруженного файла
                file_info = post_data_json.get('fileInfo', {})
                
                # Возвращаем информацию о файле в формате, ожидаемом клиентом
                response_data = {
                    "id": file_info.get('id', str(uuid.uuid4())),
                    "original_filename": file_info.get('original_filename', 'unknown.csv'),
                    "stored_filename": file_info.get('stored_filename', ''),
                    "file_url": f"/api/v1/files/download/{file_info.get('stored_filename', '')}",
                    "file_type": file_info.get('file_type', 'supplier'),
                    "file_size": 1000,
                    "encoding": "utf-8",
                    "separator": ",",
                    "upload_date": datetime.now().isoformat()
                }
            elif path == '/api/v1/comparison/compare':
                # Обработка запроса на сравнение файлов
                supplier_file = post_data_json.get('supplier_file', {})
                store_file = post_data_json.get('store_file', {})
                
                # Создаем тестовый результат сравнения
                response_data = {
                    "matches": [
                        {
                            "article": "TEST001",
                            "supplier_price": 1000,
                            "store_price": 1200,
                            "price_diff": -200,
                            "price_diff_percent": -16.67,
                            "supplier_name": "Тестовый товар 1",
                            "store_name": "Тестовый товар 1"
                        },
                        {
                            "article": "TEST002",
                            "supplier_price": 2000,
                            "store_price": 2500,
                            "price_diff": -500,
                            "price_diff_percent": -20.0,
                            "supplier_name": "Тестовый товар 2",
                            "store_name": "Тестовый товар 2"
                        }
                    ],
                    "missing_in_store": [],
                    "missing_in_supplier": [],
                    "matches_data": [
                        {
                            "article": "TEST001",
                            "supplier_price": 1000,
                            "store_price": 1200,
                            "price_diff": -200,
                            "price_diff_percent": -16.67,
                            "supplier_name": "Тестовый товар 1",
                            "store_name": "Тестовый товар 1"
                        },
                        {
                            "article": "TEST002",
                            "supplier_price": 2000,
                            "store_price": 2500,
                            "price_diff": -500,
                            "price_diff_percent": -20.0,
                            "supplier_name": "Тестовый товар 2",
                            "store_name": "Тестовый товар 2"
                        }
                    ],
                    "total_items": 2,
                    "items_only_in_file1": 0,
                    "items_only_in_file2": 0,
                    "mismatches": 0,
                    "preview_data": [],
                    "column_mapping": {"identifier": "article", "value": "price"}
                }
            else:
                # Для других запросов возвращаем стандартный ответ
                response_data = {
                    "status": "ok",
                    "message": "Данные получены",
                    "timestamp": datetime.now().isoformat(),
                    "path": self.path,
                    "received_data": post_data_json
                }
            
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            return
        except Exception as e:
            error_response = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "path": self.path
            }
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
            return
    
    def do_PUT(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Простая обработка загрузки файла
        content_length = int(self.headers.get('Content-Length', 0))
        self.rfile.read(content_length)  # Читаем данные, но не используем их
        
        response_data = {
            "status": "ok",
            "message": "Файл успешно загружен"
        }
        
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        return
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return 