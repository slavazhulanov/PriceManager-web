import os
import uuid
import pandas as pd
import chardet
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from app.models.file import FileInfo, FileType, ColumnMapping
from app.services.file_service import (
    detect_encoding, 
    detect_separator, 
    get_columns, 
    save_file,
    get_file_content
)
from app.services.file_cache import cache_file_content
from app.core.config import settings

router = APIRouter()

@router.post("/upload", response_model=FileInfo)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...)
):
    """
    Загрузка файла прайс-листа (поставщика или магазина)
    """
    try:
        # Проверка размера файла
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Файл слишком большой")
        
        print(f"Получен файл для загрузки: {file.filename}, тип: {file_type}, размер: {len(contents)} байт")
        
        # Создаем уникальное имя для файла
        file_extension = os.path.splitext(file.filename)[1]
        stored_filename = f"{uuid.uuid4()}{file_extension}"
        
        print(f"Сгенерировано имя для сохранения: {stored_filename}")
        
        # Создаем директорию, если она не существует
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Сохраняем файл и явно кешируем его содержимое
        file_path = save_file(stored_filename, contents)
        cache_file_content(stored_filename, contents)
        
        # Проверяем, что файл доступен для чтения
        cached_content = get_file_content(stored_filename)
        if not cached_content:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл был сохранен, но не может быть прочитан: {stored_filename}")
            raise HTTPException(status_code=500, detail="Ошибка при сохранении файла, невозможно прочитать сохраненный файл")
        
        print(f"Файл успешно сохранен и доступен для чтения")
        
        # Определяем кодировку и разделитель
        encoding = detect_encoding(contents)
        separator = detect_separator(contents, encoding)
        
        print(f"Определена кодировка: {encoding}, разделитель: {separator}")
        
        # Создаем информацию о файле
        file_info = FileInfo(
            id=str(uuid.uuid4()),
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_type=file_type,
            encoding=encoding,
            separator=separator
        )
        
        print(f"Создан объект FileInfo: {file_info}")
        
        return file_info
    except Exception as e:
        print(f"Ошибка при загрузке файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")

@router.get("/columns/{filename}", response_model=List[str])
async def get_file_columns(filename: str, encoding: str = "utf-8", separator: str = ","):
    """
    Получение списка колонок из файла
    """
    # Получаем содержимое файла
    file_content = get_file_content(filename)
    if not file_content:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Получаем расширение файла
    extension = os.path.splitext(filename)[1]
    
    # Получаем колонки
    columns = get_columns(file_content, extension, encoding, separator)
    return columns

@router.post("/mapping", response_model=FileInfo)
async def save_column_mapping(file_info: FileInfo):
    """
    Сохранение сопоставления колонок для файла
    """
    # В реальном приложении здесь будет сохранение в базу данных
    
    return file_info 