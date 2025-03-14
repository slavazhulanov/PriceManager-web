#!/usr/bin/env python
"""
Скрипт для быстрой диагностики API endpoints
"""

import requests
import json
import sys
import os
from urllib.parse import urlparse

# Функция для проверки API
def test_api(base_url):
    print(f"\n🔍 Тестирование API по адресу: {base_url}")
    
    # Проверка базового API
    try:
        response = requests.get(f"{base_url}/api/v1/test")
        print(f"Базовый тест API: {response.status_code}")
        if response.status_code == 200:
            print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при проверке базового API: {str(e)}")
    
    # Проверка API колонок для файла поставщика
    try:
        response = requests.get(f"{base_url}/api/v1/files/columns/supplier_test.csv")
        print(f"\nКолонки для файла поставщика: {response.status_code}")
        if response.status_code == 200:
            print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при получении колонок поставщика: {str(e)}")
    
    # Проверка API колонок для файла магазина
    try:
        response = requests.get(f"{base_url}/api/v1/files/columns/store_test.csv")
        print(f"\nКолонки для файла магазина: {response.status_code}")
        if response.status_code == 200:
            print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при получении колонок магазина: {str(e)}")
    
    # Проверка API загрузки URL
    try:
        payload = {
            "fileName": "test.csv", 
            "fileType": "supplier"
        }
        response = requests.post(
            f"{base_url}/api/v1/files/upload_url",
            json=payload
        )
        print(f"\nЗапрос URL для загрузки: {response.status_code}")
        if response.status_code == 200:
            print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при запросе URL для загрузки: {str(e)}")
    
    print("\n✅ Тестирование API завершено")

# Главная функция
def main():
    # Получение аргументов командной строки
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        print("Используется локальный URL по умолчанию")
        base_url = "http://localhost:3000"
    
    # Проверка URL
    try:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            print(f"❌ Неверный формат URL: {base_url}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при разборе URL: {str(e)}")
        sys.exit(1)
    
    # Запуск тестирования
    test_api(base_url)

if __name__ == "__main__":
    main() 