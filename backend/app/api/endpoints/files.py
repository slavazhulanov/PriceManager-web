import os
import uuid
import pandas as pd
import chardet
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models.file import FileInfo, FileType, ColumnMapping
from app.services.file_service import (
    detect_encoding, 
    detect_separator, 
    get_columns, 
    save_file,
    get_file_content
)
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
    # Проверка размера файла
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой")
    
    # Создаем уникальное имя для файла
    file_extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Сохраняем файл
    save_file(stored_filename, contents)
    
    # Определяем кодировку и разделитель
    encoding = detect_encoding(contents)
    separator = detect_separator(contents, encoding)
    
    # Создаем информацию о файле
    file_info = FileInfo(
        id=str(uuid.uuid4()),
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_type=file_type,
        encoding=encoding,
        separator=separator
    )
    
    return file_info

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