#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для проверки совместимости приложения с платформой Vercel
"""

import sys
import json
import importlib.util
import inspect
import os
import traceback
from typing import Dict, Any, List, Tuple, Optional

# Цвета для вывода в терминал
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
ENDC = '\033[0m'
BOLD = '\033[1m'

def success(message: str) -> None:
    """Вывод сообщения об успехе"""
    print(f"{GREEN}✓ {message}{ENDC}")

def warning(message: str) -> None:
    """Вывод предупреждения"""
    print(f"{YELLOW}! {message}{ENDC}")

def error(message: str) -> None:
    """Вывод сообщения об ошибке"""
    print(f"{RED}✗ {message}{ENDC}")

def info(message: str) -> None:
    """Вывод информационного сообщения"""
    print(f"{BLUE}i {message}{ENDC}")

def header(message: str) -> None:
    """Вывод заголовка"""
    print(f"\n{BOLD}{message}{ENDC}")

def create_test_event(method: str = 'GET', path: str = '/api/test') -> Dict[str, Any]:
    """Создание тестового события в формате AWS API Gateway"""
    return {
        'method': method,
        'path': path,
        'headers': {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
            'Host': 'example.vercel.app'
        },
        'body': json.dumps({'test': 'data'}) if method == 'POST' else '',
        'isBase64Encoded': False
    }

def load_handler_module() -> Tuple[Optional[Any], Optional[str]]:
    """Загрузка модуля handler.py"""
    try:
        handler_path = 'vercel_handler.py'
        
        if not os.path.exists(handler_path):
            error(f"Файл {handler_path} не найден")
            return None, f"Файл {handler_path} не найден"
            
        spec = importlib.util.spec_from_file_location("vercel_handler", handler_path)
        if not spec or not spec.loader:
            error(f"Не удалось загрузить спецификацию модуля из {handler_path}")
            return None, f"Не удалось загрузить спецификацию модуля из {handler_path}"
            
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        if not hasattr(handler_module, 'handler'):
            error("Функция 'handler' не найдена в модуле")
            return None, "Функция 'handler' не найдена в модуле"
            
        return handler_module, None
    except Exception as e:
        error(f"Ошибка при загрузке модуля: {str(e)}")
        error(traceback.format_exc())
        return None, str(e)

def test_handler_format(handler_module: Any) -> bool:
    """Проверка формата функции handler"""
    try:
        handler_func = handler_module.handler
        
        # Проверяем сигнатуру функции
        sig = inspect.signature(handler_func)
        if len(sig.parameters) != 2:
            error(f"Функция handler должна принимать 2 параметра (event, context), но принимает {len(sig.parameters)}")
            return False
            
        param_names = list(sig.parameters.keys())
        if param_names[0] != 'event' or param_names[1] != 'context':
            warning(f"Имена параметров функции handler должны быть (event, context), но они {param_names}")
        
        success("Формат функции handler соответствует требованиям Vercel")
        return True
    except Exception as e:
        error(f"Ошибка при проверке формата handler: {str(e)}")
        return False

def test_http_methods(handler_module: Any) -> bool:
    """Тестирование обработки различных HTTP методов"""
    handler_func = handler_module.handler
    
    methods = ['GET', 'POST', 'OPTIONS']
    all_successful = True
    
    for method in methods:
        try:
            event = create_test_event(method=method)
            response = handler_func(event, {})
            
            status_code = response.get('statusCode')
            if not status_code or status_code >= 400:
                error(f"Метод {method} вернул код состояния {status_code}")
                all_successful = False
                continue
                
            success(f"Метод {method} успешно обработан (код {status_code})")
        except Exception as e:
            error(f"Ошибка при тестировании метода {method}: {str(e)}")
            all_successful = False
    
    return all_successful

def test_dependencies() -> bool:
    """Проверка зависимостей"""
    requirements_path = 'vercel_requirements.txt'
    
    if not os.path.exists(requirements_path):
        warning(f"Файл {requirements_path} не найден")
        return False
        
    try:
        with open(requirements_path, 'r') as f:
            requirements = [line.strip() for line in f if line.strip()]
            
        if 'pandas' in requirements:
            warning("Библиотека pandas может вызвать проблемы с размером Lambda функции или совместимостью")
            
        if 'numpy' in requirements:
            warning("Библиотека numpy может вызвать проблемы с размером Lambda функции или совместимостью")
            
        success(f"Файл {requirements_path} проверен, найдено {len(requirements)} зависимостей")
        return True
    except Exception as e:
        error(f"Ошибка при проверке зависимостей: {str(e)}")
        return False

def test_vercel_config() -> bool:
    """Проверка конфигурации Vercel"""
    config_path = '../vercel.json'
    
    if not os.path.exists(config_path):
        warning(f"Файл {config_path} не найден")
        return False
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Проверка builds
        builds = config.get('builds', [])
        python_build = next((b for b in builds if b.get('use') == '@vercel/python'), None)
        
        if not python_build:
            error("Не найдена конфигурация для Python в секции builds")
            return False
            
        # Проверка routes
        routes = config.get('routes', [])
        api_route = next((r for r in routes if r.get('src', '').startswith('/api')), None)
        
        if not api_route:
            warning("Не найдено правило маршрутизации для API (/api)")
            
        success("Конфигурация Vercel проверена")
        return True
    except Exception as e:
        error(f"Ошибка при проверке конфигурации Vercel: {str(e)}")
        return False

def main() -> None:
    """Основная функция для запуска всех тестов"""
    header("Тест совместимости с Vercel")
    
    handler_module, load_error = load_handler_module()
    if not handler_module:
        error(f"Тесты не могут быть выполнены из-за ошибки загрузки модуля: {load_error}")
        sys.exit(1)
        
    # Запуск тестов
    tests = [
        ("Проверка формата handler", lambda: test_handler_format(handler_module)),
        ("Тестирование HTTP методов", lambda: test_http_methods(handler_module)),
        ("Проверка зависимостей", test_dependencies),
        ("Проверка конфигурации Vercel", test_vercel_config)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        header(test_name)
        if not test_func():
            all_passed = False
    
    # Вывод итогового результата
    header("Результаты тестирования")
    if all_passed:
        success("Все тесты пройдены успешно")
        info("Ваше приложение должно быть совместимо с Vercel")
    else:
        warning("Есть проблемы, требующие внимания")
        info("Рекомендации:")
        info("1. Исправьте ошибки, указанные выше")
        info("2. Минимизируйте размер и зависимости функции handler")
        info("3. Убедитесь, что код совместим со средой выполнения Vercel")

if __name__ == "__main__":
    main() 