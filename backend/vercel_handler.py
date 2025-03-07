import sys
import os

# Получаем текущую директорию, где находится vercel_handler.py
current_dir = os.path.dirname(os.path.abspath(__file__))

# Добавляем директорию backend в путь поиска модулей
sys.path.append(current_dir)

# Важно: создаем символическую ссылку для импортов из app.*
# Проверяем, существует ли уже app в sys.modules
if 'app' not in sys.modules:
    # Импортируем необходимые модули
    from backend.app import main, api, core, models, services, utils
    from backend.app.api import endpoints
    
    # Добавляем их в sys.modules под нужными именами
    sys.modules['app'] = sys.modules['backend.app']
    sys.modules['app.api'] = sys.modules['backend.app.api']
    sys.modules['app.core'] = sys.modules['backend.app.core']
    sys.modules['app.models'] = sys.modules['backend.app.models']
    sys.modules['app.services'] = sys.modules['backend.app.services']
    sys.modules['app.utils'] = sys.modules['backend.app.utils']
    sys.modules['app.api.endpoints'] = sys.modules['backend.app.api.endpoints']

# Импортируем app после настройки путей
from backend.app.main import app

# Специальный обработчик для Vercel Serverless Functions
from mangum import Mangum

# Создаем обработчик для AWS Lambda и Vercel
handler = Mangum(app)