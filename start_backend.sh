#!/bin/bash

# Выход при любой ошибке
set -e

echo "=== Подготовка к запуску PriceManager локально ==="

# Проверка наличия директории uploads
if [ ! -d "uploads" ]; then
  echo "Создание директории uploads..."
  mkdir -p uploads
fi

# Проверка файла .env
if [ ! -f ".env" ]; then
  echo "Создание файла .env из шаблона..."
  cp .env.example .env
fi

# Настройка бэкенда
echo "=== Настройка и запуск бэкенда ==="
cd backend

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

# Проверка наличия директории uploads в бэкенде
if [ ! -d "uploads" ]; then
  echo "Создание директории uploads в бэкенде..."
  mkdir -p uploads
fi

# Запуск бэкенда
echo "Запуск бэкенда на http://localhost:8000..."
echo "Для доступа к API документации перейдите на http://localhost:8000/docs"
echo "Нажмите Ctrl+C для остановки бэкенда"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 