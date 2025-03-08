#!/bin/bash

# Выход при любой ошибке
set -e

echo "=== Подготовка к запуску PriceManager локально ==="

# Проверка файла .env в корне проекта
if [ ! -f ".env" ]; then
  echo "Проверка файла .env в корне проекта..."
  if [ -f "backend/.env" ]; then
    echo "Найден файл backend/.env, копирование в корень проекта не требуется"
  else
    echo "ВНИМАНИЕ: Файл .env отсутствует. Создайте файл .env в директории backend"
    exit 1
  fi
fi

# Настройка бэкенда
echo "=== Настройка и запуск бэкенда ==="
cd backend

# Проверка файла .env в директории backend
if [ ! -f ".env" ]; then
  echo "ВНИМАНИЕ: Файл .env отсутствует в директории backend"
  echo "Пожалуйста, создайте файл .env в директории backend с необходимыми настройками"
  exit 1
fi

# Проверка и создание виртуального окружения
if [ ! -d "venv" ]; then
  echo "Создание виртуального окружения Python..."
  python -m venv venv
fi

# Активация виртуального окружения и установка зависимостей
echo "Активация виртуального окружения и установка зависимостей..."
source venv/bin/activate
pip install -r requirements.txt
pip install pydantic-settings

# Запуск бэкенда
echo "Запуск бэкенда на http://localhost:8000..."
echo "Для доступа к API документации перейдите на http://localhost:8000/docs"
echo "Нажмите Ctrl+C для остановки бэкенда"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 