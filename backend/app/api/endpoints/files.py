import os
import uuid
import logging
import pandas as pd
import chardet
import httpx
import traceback
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from app.models.file import FileInfo, FileType, ColumnMapping
from app.services.file_service import (
    detect_encoding, 
    detect_separator, 
    get_columns, 
    get_file_content,
    read_file,
    save_file,
    init_supabase_client,
)
from app.services.file_cache import cache_file_content
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger("app.api.files")

def get_supabase_client():
    """
    Возвращает инициализированный клиент Supabase или None
    """
    return init_supabase_client()

@router.post("/upload", response_model=FileInfo)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...)
):
    """
    Загрузка файла на сервер
    """
    try:
        # Чтение содержимого файла
        contents = await file.read()
        
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            logger.error(f"Размер файла превышает допустимый: {len(contents)} > {settings.MAX_UPLOAD_SIZE} байт")
            raise HTTPException(status_code=400, detail=f"Размер файла превышает {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f} МБ")
            
        # Логирование получения файла
        logger.info(f"Получен файл для загрузки: {file.filename}, тип: {file_type}, размер: {len(contents)} байт")
        
        # Генерация уникального имени файла для хранения
        timestamp = int(time.time())
        file_extension = os.path.splitext(file.filename)[1].lower()
        stored_filename = f"file_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        logger.info(f"Сгенерировано имя для сохранения: {stored_filename}")
        
        # Кешируем содержимое перед сохранением в Supabase
        cache_file_content(stored_filename, contents)
        logger.info(f"Содержимое файла закешировано: {stored_filename}")
        
        # Пробуем сохранить файл в Supabase
        try:
            file_url = save_file(stored_filename, contents)
            logger.info(f"Файл успешно сохранен в Supabase: {stored_filename}")
        except Exception as storage_error:
            logger.error(f"Ошибка при сохранении файла в Supabase: {str(storage_error)}")
            logger.error(traceback.format_exc())
            
            # Возвращаем ошибку клиенту
            raise HTTPException(
                status_code=500, 
                detail="Не удалось сохранить файл в облачном хранилище. Проверьте настройки Supabase и права доступа."
            )
        
        # Проверяем, что файл успешно сохранен
        try:
            check_content = get_file_content(stored_filename)
            if not check_content:
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Файл был сохранен, но не может быть прочитан: {stored_filename}")
                raise HTTPException(status_code=500, detail="Не удалось сохранить файл")
            
            logger.info(f"Файл успешно сохранен и доступен для чтения")
        except Exception as read_error:
            logger.error(f"Ошибка при проверке доступности файла: {str(read_error)}")
            logger.error(traceback.format_exc())
            
            # Используем кешированное содержимое
            logger.info(f"Используем файл из кеша: {stored_filename}")
        
        # Определение кодировки и разделителя
        encoding = detect_encoding(contents)
        separator = detect_separator(contents, encoding)
        
        logger.info(f"Определена кодировка: {encoding}, разделитель: {separator}")
        
        # Создание объекта FileInfo с информацией о файле
        file_info = FileInfo(
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_url=file_url,
            file_type=file_type,
            file_size=len(contents),
            encoding=encoding,
            separator=separator
        )
        
        logger.info(f"Создан объект FileInfo: {file_info.model_dump_json()}")
        
        return file_info
    except HTTPException as he:
        # Пробрасываем HTTP-исключения
        raise he
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}", exc_info=True)
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

@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Скачивание файла по имени.
    
    В режиме Vercel (продакшн) - проксирует из Supabase
    В режиме локальной разработки - из локального хранилища или Supabase
    
    Args:
        filename: Имя файла для скачивания
        
    Returns:
        Файл для скачивания
    """
    logger.info(f"Запрос на скачивание файла: {filename}")
    
    # Проверка на специальное имя для сэмпла
    if filename == "sample":
        return await download_sample_file()
    
    # Получаем содержимое файла с универсальной функцией
    content = get_file_content(filename)
    
    if content:
        # Определяем content-type на основе расширения файла
        extension = os.path.splitext(filename)[1].lower()
        content_type = "application/octet-stream"
        
        if extension == ".csv":
            content_type = "text/csv"
        elif extension == ".xlsx" or extension == ".xls":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Определяем имя файла для скачивания, удаляя префиксы
        display_name = filename
        if filename.startswith("updated_"):
            display_name = filename.replace("updated_", "")
        
        # Возвращаем файл для скачивания
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{display_name}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    
    # Если файл не найден ни локально, ни в Supabase, предлагаем скачать прокси или сэмпл
    if settings.USE_CLOUD_STORAGE:
        # Пробуем через прокси
        client = get_supabase_client()
        if client:
            try:
                # Формируем URL для Supabase Storage
                file_path = f"{settings.SUPABASE_FOLDER}/{filename}"
                url = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
                logger.info(f"Пытаемся проксировать файл через URL: {url}")
                return await proxy_download(url=url)
            except Exception as e:
                logger.error(f"Ошибка при проксировании файла из Supabase: {str(e)}")
                # Возвращаем сэмпл, если не удалось
                return await download_sample_file()
    
    # Если файл не найден и не удалось проксировать, возвращаем сэмпл
    logger.warning(f"Файл {filename} не найден, возвращаем сэмпл")
    return await download_sample_file()

@router.get("/download/sample")
async def download_sample_file():
    """
    Возвращает сэмпл-файл для демонстрации.
    
    Returns:
        Файл сэмпла для скачивания
    """
    logger.info("Запрос на скачивание сэмпл-файла")
    
    # Генерируем содержимое сэмпл-файла
    csv_content = """Артикул,Наименование товара,Цена магазина
A001,Товар 1,100.00
A002,Товар 2,200.00
A003,Товар 3,300.00
A004,Товар 4,400.00
A005,Товар 5,500.00
"""
    
    # Возвращаем CSV-файл
    return Response(
        content=csv_content.encode('utf-8-sig'),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="sample_file.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/proxy-download")
async def proxy_download(url: str):
    """
    Проксирует скачивание файла по URL.
    
    Используется для скачивания файлов из Supabase Storage.
    
    Args:
        url: URL файла для скачивания
        
    Returns:
        Проксированный файл
    """
    logger.info(f"Запрос на проксирование файла: {url}")
    
    try:
        # Проверяем, является ли URL Supabase URL
        is_supabase_url = settings.SUPABASE_URL and settings.SUPABASE_URL in url
        
        if not is_supabase_url and not url.startswith(('http://', 'https://')):
            logger.warning(f"Недопустимый URL для проксирования: {url}")
            raise HTTPException(status_code=400, detail="Недопустимый URL для проксирования")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code != 200:
                logger.error(f"Ошибка при проксировании файла, статус: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка при проксировании файла: {response.text}"
                )
            
            # Получаем имя файла из URL или заголовка Content-Disposition
            filename = url.split("/")[-1]
            content_disposition = response.headers.get("Content-Disposition", "")
            
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            
            # Определяем content-type из ответа или по расширению
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проксировании файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при проксировании файла: {str(e)}") 

@router.get("/supabase-diagnostics")
async def check_supabase_connection():
    """
    Диагностика подключения к Supabase
    """
    try:
        client = init_supabase_client()
        if not client:
            return {
                "status": "error",
                "message": "Не удалось инициализировать Supabase клиент",
                "details": {
                    "url": settings.SUPABASE_URL,
                    "key_preview": f"{settings.SUPABASE_KEY[:5]}...{settings.SUPABASE_KEY[-5:]}",
                    "bucket": settings.SUPABASE_BUCKET,
                    "folder": settings.SUPABASE_FOLDER
                }
            }
        
        # Проверка списка бакетов
        buckets = client.storage.list_buckets()
        bucket_names = [b['name'] for b in buckets]
        
        # Проверка доступа к бакету price-manager
        bucket_status = "not_found"
        folder_status = "not_checked"
        files_list = []
        
        if settings.SUPABASE_BUCKET in bucket_names:
            bucket_status = "found"
            
            # Проверка доступа к папке
            try:
                files = client.storage.from_(settings.SUPABASE_BUCKET).list(settings.SUPABASE_FOLDER)
                folder_status = "accessible"
                files_list = files
                
                # Пробуем создать тестовый файл
                test_file_name = f"{settings.SUPABASE_FOLDER}/test-{uuid.uuid4()}.txt"
                try:
                    client.storage.from_(settings.SUPABASE_BUCKET).upload(
                        test_file_name,
                        b"This is a test file to check write access to Supabase storage",
                        {"content-type": "text/plain"}
                    )
                    
                    # Пробуем получить URL к файлу
                    file_url = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(test_file_name)
                    
                    return {
                        "status": "success",
                        "message": "Диагностика успешно завершена",
                        "details": {
                            "buckets": bucket_names,
                            "target_bucket": settings.SUPABASE_BUCKET,
                            "bucket_status": bucket_status,
                            "folder_status": folder_status,
                            "files": files_list,
                            "test_file": {
                                "name": test_file_name,
                                "url": file_url
                            }
                        }
                    }
                except Exception as upload_err:
                    return {
                        "status": "partial_success",
                        "message": "Бакет доступен, но не удалось загрузить тестовый файл",
                        "details": {
                            "buckets": bucket_names,
                            "target_bucket": settings.SUPABASE_BUCKET,
                            "bucket_status": bucket_status,
                            "folder_status": folder_status,
                            "files": files_list,
                            "upload_error": str(upload_err)
                        }
                    }
            except Exception as folder_err:
                return {
                    "status": "partial_success",
                    "message": "Бакет найден, но не удалось получить доступ к папке",
                    "details": {
                        "buckets": bucket_names,
                        "target_bucket": settings.SUPABASE_BUCKET,
                        "bucket_status": bucket_status,
                        "folder_status": "error",
                        "folder_error": str(folder_err)
                    }
                }
        
        # Если не нашли бакет
        return {
            "status": "error",
            "message": f"Бакет '{settings.SUPABASE_BUCKET}' не найден",
            "details": {
                "buckets": bucket_names,
                "target_bucket": settings.SUPABASE_BUCKET,
                "bucket_status": bucket_status
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка при выполнении диагностики: {str(e)}",
            "traceback": traceback.format_exc()
        } 