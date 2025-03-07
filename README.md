# PriceManager Web

Веб-приложение для управления ценами между прайс-листами поставщиков и интернет-магазинов.

## Описание

PriceManager Web - это веб-версия приложения для сравнения и обновления цен между прайс-листами поставщиков и интернет-магазинов. Приложение позволяет:

- Загружать прайс-листы в форматах Excel и CSV
- Сопоставлять колонки с артикулами, ценами и названиями товаров
- Сравнивать цены между прайс-листами
- Выявлять отсутствующие товары
- Обновлять цены в прайс-листе магазина на основе цен поставщика
- Скачивать обновленный прайс-лист в исходном формате (сохраняя кодировку и разделители)

## Технологии

### Бэкенд
- Python 3.10+
- FastAPI
- Pandas для обработки данных
- SQLite для хранения данных
- Supabase для хранения файлов

### Фронтенд
- React
- TypeScript
- Material UI
- AG Grid для таблиц

### Инфраструктура
- Vercel для хостинга
- Supabase для хранения файлов

## Подготовка к публикации в GitHub

1. Убедитесь, что все секретные данные вынесены в `.env` файлы и добавлены в `.gitignore`
2. Проверьте качество кода и отсутствие закомментированного неиспользуемого кода
3. Запустите проект локально для проверки всех функций
4. Создайте репозиторий на GitHub и загрузите код:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/PriceManager-web.git
git push -u origin main
```

## Настройка Supabase

1. Создайте аккаунт на [Supabase](https://supabase.io)
2. Создайте новый проект
3. В разделе Storage создайте новый бакет с именем `price-manager`
4. Настройте правила доступа к бакету:
   - Для аутентифицированных пользователей: полный доступ
   - Для публичного доступа: только чтение
5. Получите URL проекта и API ключ из настроек проекта (Settings > API)
6. Внесите эти данные в файл `.env`

## Настройка Vercel

1. Создайте аккаунт на [Vercel](https://vercel.com)
2. Установите CLI Vercel (опционально):
   ```bash
   npm i -g vercel
   ```

3. Войдите в свой аккаунт Vercel:
   ```bash
   vercel login
   ```

4. Выполните первичное развертывание:
   ```bash
   vercel
   ```

5. В настройках проекта на Vercel добавьте переменные окружения:
   - `USE_CLOUD_STORAGE=true`
   - `SUPABASE_URL=ваш_url_supabase`
   - `SUPABASE_KEY=ваш_api_ключ_supabase`
   - `SUPABASE_BUCKET=price-manager`
   - `SUPABASE_FOLDER=uploads`
   - `SECRET_KEY=ваш_секретный_ключ` (для JWT-токенов)

6. Настройте интеграцию с GitHub для автоматических деплоев:
   - Перейдите на [Vercel](https://vercel.com)
   - Выберите свой проект
   - Перейдите в Settings > Git
   - Подключите репозиторий GitHub
   - Настройте автоматические деплои при пуше в main ветку

## Локальный запуск для разработки

### Настройка переменных окружения

1. Скопируйте файл `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Создайте файл `.env` в директории `frontend/`:
   ```
   REACT_APP_USE_REAL_API=false  # установите true для использования реального API
   ```

### Запуск бэкенда

1. Перейдите в директорию бэкенда:
   ```bash
   cd backend
   ```

2. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/Mac
   venv\Scripts\activate     # для Windows
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Запустите сервер:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Запуск фронтенда

1. Перейдите в директорию фронтенда:
   ```bash
   cd frontend
   ```

2. Установите зависимости:
   ```bash
   npm install
   ```

3. Запустите сервер разработки:
   ```bash
   npm start
   ```

4. Откройте приложение в браузере: http://localhost:3000

### Использование скриптов запуска

Для удобства в корне проекта есть скрипты запуска:

- `start_backend.sh` - запускает бэкенд
- `start_frontend.sh` - запускает фронтенд

Для запуска скриптов выполните:
```bash
chmod +x start_backend.sh start_frontend.sh
./start_backend.sh
./start_frontend.sh
```

## Использование приложения

1. На главной странице выберите "Загрузить файлы"
2. Загрузите прайс-лист поставщика и прайс-лист магазина
3. Настройте сопоставление колонок для обоих файлов
4. Перейдите к сравнению цен
5. Все товары будут автоматически выбраны для обновления
6. Нажмите "Обновить цены"
7. Скачайте обновленный прайс-лист

## Важные особенности

1. **Сохранение формата файлов** - приложение сохраняет исходный формат, кодировку и разделители файлов
2. **Обработка ошибок** - все запросы к API включают обработку ошибок и пользовательские сообщения
3. **Поддержка разных сред** - код учитывает работу в различных окружениях (разработка и продакшн)

## Структура проекта

```
PriceManager-web/
├── backend/                # Бэкенд на FastAPI
│   ├── app/                # Код приложения
│   │   ├── api/            # API эндпоинты
│   │   ├── core/           # Ядро приложения
│   │   ├── models/         # Модели данных
│   │   ├── services/       # Бизнес-логика
│   │   └── utils/          # Утилиты
│   ├── requirements.txt    # Зависимости
│   └── vercel_handler.py   # Обработчик для Vercel
├── frontend/               # Фронтенд на React
│   ├── .env                # Переменные окружения для фронтенда
│   ├── public/             # Статические файлы
│   ├── src/                # Исходный код
│   │   ├── components/     # Компоненты
│   │   ├── pages/          # Страницы
│   │   ├── services/       # Сервисы для API
│   │   └── types/          # TypeScript типы
│   └── package.json        # Зависимости
├── uploads/                # Директория для локального хранения файлов
├── .env                    # Глобальные переменные окружения
├── .env.example            # Пример файла конфигурации
├── vercel.json             # Конфигурация Vercel
├── start_backend.sh        # Скрипт запуска бэкенда
├── start_frontend.sh       # Скрипт запуска фронтенда
└── README.md               # Документация проекта
```

## Лицензия

MIT 