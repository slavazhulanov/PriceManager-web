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

## Подготовка к размещению в продакшн

Перед развертыванием в продакшн среде необходимо выполнить следующие шаги:

1. **Настройки безопасности**
   - Сгенерировать надежный секретный ключ для `SECRET_KEY` (длиной не менее 32 символов)
   - Обновить `CORS_ORIGINS` - указать только доверенные домены для обращения к API
   - Убедиться, что в продакшн используется HTTPS для всех доменов

2. **Настройка Supabase**
   - Настроить правильные политики доступа в Supabase для защиты данных
   - Установить ограничения на размер и типы файлов
   - Настроить автоматическую очистку хранилища для удаления старых файлов

3. **Логирование и мониторинг**
   - Настроить централизованное логирование (например, через Datadog, New Relic или ELK Stack)
   - Установить соответствующий уровень логирования (`LOG_LEVEL=WARNING` или `LOG_LEVEL=ERROR`)
   - Настроить алерты для критических ошибок

4. **Производительность**
   - Настроить кеширование для оптимизации работы с файлами
   - Установить ограничения на размер загружаемых файлов
   - Оптимизировать план тарифа Supabase в зависимости от ожидаемой нагрузки

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

## Настройка хранилища Supabase

Для корректной работы приложения необходимо настроить облачное хранилище в Supabase:

1. Создайте аккаунт на [Supabase](https://supabase.com/) (если у вас его еще нет)
2. Создайте новый проект в Supabase
3. Перейдите в раздел "Storage" в панели управления проектом
4. Создайте новый бакет с именем `price-manager` (или другим, указанным в вашем `.env` файле)
5. Настройте политики доступа для бакета:
   - Перейдите на вкладку "Policies"
   - Создайте политику "Public READ access" для всех файлов
   - При необходимости настройте политики для операций INSERT, UPDATE, DELETE

## Настройка переменных окружения

Создайте файл `.env` в директории `backend` со следующими параметрами:

```
# Настройки безопасности
SECRET_KEY=<ваш-секретный-ключ>

# Настройки Supabase
SUPABASE_URL=<url-вашего-проекта-supabase>
SUPABASE_KEY=<ваш-публичный-ключ-api>
SUPABASE_BUCKET=price-manager
SUPABASE_FOLDER=uploads

# Настройки сервера
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Настройки логирования
LOG_LEVEL=INFO
TIMEZONE=Europe/Moscow

# Настройки CORS
CORS_ORIGINS=["https://your-domain.com", "https://app.your-domain.com"]
```

## Запуск в продакшн

Для запуска в продакшн среде рекомендуется использовать:

```bash
cd backend
python run.py
```

Для запуска с использованием промышленного WSGI сервера (например, Gunicorn):

```bash
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## Важные замечания по безопасности

1. **Секретные ключи**: Никогда не храните секретные ключи в коде или репозитории. Используйте переменные окружения или секреты Vercel.

2. **CORS настройки**: В продакшн среде ограничьте CORS только доверенными доменами и всегда используйте HTTPS.

3. **Управление доступом**: Настройте политики в Supabase для ограничения доступа к файлам только авторизованным пользователям.

4. **Ограничение размера файлов**: Установите разумные ограничения на размер загружаемых файлов для предотвращения DoS атак.

5. **Регулярное обновление зависимостей**: Периодически обновляйте зависимости для устранения уязвимостей безопасности.

## Запуск приложения

Для запуска бэкенда:

```bash
./start_backend.sh
```

## Важные замечания

- Для создания бакета в Supabase вам потребуются административные права доступа. Это нельзя сделать через обычный API с анонимным ключом.
- Убедитесь, что в вашем проекте Supabase настроены правильные политики доступа для бакета.
- При развертывании на Vercel убедитесь, что переменные окружения корректно настроены в разделе "Environment Variables" проекта Vercel.

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
   # Базовый URL API (относительный путь для работы в локальном и продакшен окружении)
   REACT_APP_API_URL=/api/v1
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
│   ├── logs/               # Логи приложения
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

## Тестовый коммит 
Тестовый коммит для проверки процесса сборки. Временная метка: [2025-03-13T09:43:10Z] 