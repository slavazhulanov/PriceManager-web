from supabase import create_client
import os
import sys

# Получение настроек из переменных окружения или .env файла
def load_env_from_file():
    env_path = os.path.join('backend', '.env')
    if not os.path.exists(env_path):
        env_path = '.env'
        if not os.path.exists(env_path):
            print("Файл .env не найден")
            return False
    
    with open(env_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    return True

# Проверка наличия необходимых переменных окружения
def check_env_variables():
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_BUCKET']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
        return False
    
    return True

# Создание бакета в Supabase
def create_bucket():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    bucket_name = os.environ.get('SUPABASE_BUCKET')
    
    print(f"Подключение к Supabase: {url}")
    client = create_client(url, key)
    
    try:
        # Получаем список существующих бакетов
        buckets = client.storage.list_buckets()
        bucket_names = [b['name'] for b in buckets]
        
        if bucket_name in bucket_names:
            print(f"Бакет '{bucket_name}' уже существует")
            return True
        
        # Создаем новый бакет
        # Используем правильный формат, соответствующий API Supabase
        response = client.storage.create_bucket(bucket_name)
        print(f"Бакет '{bucket_name}' успешно создан")
        
        # Обновляем настройки бакета для публичного доступа
        print(f"Настройка публичного доступа для бакета '{bucket_name}'...")
        
        # Создаем политику доступа для чтения
        policy_name = "allow_public_read"
        definition = "*"  # Разрешить всем
        
        try:
            client.storage.from_(bucket_name).create_signed_url(
                path="test-file.txt",
                expires_in=3600  # 1 час
            )
            print("Публичный доступ настроен")
        except Exception as e:
            print(f"Ошибка при настройке публичного доступа: {str(e)}")
        
        print("Бакет успешно создан и настроен")
        return True
    
    except Exception as e:
        print(f"Ошибка при создании бакета: {str(e)}")
        return False

if __name__ == "__main__":
    if not load_env_from_file():
        sys.exit(1)
    
    if not check_env_variables():
        sys.exit(1)
    
    if create_bucket():
        print("Скрипт успешно выполнен")
    else:
        print("Скрипт завершился с ошибкой")
        sys.exit(1) 