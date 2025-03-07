import sys
import os

# Добавляем путь к директории backend в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Теперь можем импортировать app
from backend.app.main import app

# Специальный обработчик для Vercel Serverless Functions
from mangum import Mangum

# Создаем обработчик для AWS Lambda и Vercel
handler = Mangum(app)