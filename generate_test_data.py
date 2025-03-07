import pandas as pd
import random
import uuid

# Настройки
num_records = 100  # Количество записей
supplier_file = 'supplier_data.csv'
store_file = 'store_data.csv'

# Генерация тестовых данных для поставщика
supplier_data = {
    'Артикул': [str(uuid.uuid4())[:8] for _ in range(num_records)],
    'Наименование товара': [f'Товар {i}' for i in range(num_records)],
    'Цена поставщика': [round(random.uniform(1000, 50000), 2) for _ in range(num_records)],
}

supplier_df = pd.DataFrame(supplier_data)
supplier_df.to_csv(supplier_file, index=False, encoding='utf-8-sig')

# Генерация тестовых данных для магазина
store_data = {
    'Артикул': supplier_data['Артикул'],  # Используем те же артикулы
    'Наименование товара': [f'Товар {i} (магазин)' for i in range(num_records)],
    'Цена магазина': [round(random.uniform(1000, 50000), 2) for _ in range(num_records)],
}

store_df = pd.DataFrame(store_data)
store_df.to_csv(store_file, index=False, encoding='utf-8-sig')

print(f'Тестовые данные успешно сгенерированы и сохранены в файлы: {supplier_file}, {store_file}')
