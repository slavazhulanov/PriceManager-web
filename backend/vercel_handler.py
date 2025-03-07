from app.main import app

# Специальный обработчик для Vercel Serverless Functions
from mangum import Mangum

# Создаем обработчик для AWS Lambda и Vercel
handler = Mangum(app) 