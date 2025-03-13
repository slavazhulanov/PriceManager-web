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
from pydantic import BaseModel

# Импорт функции регистрации для сравнения файлов
# Импортируем здесь для предотвращения циклических импортов
from app.api.endpoints.comparison import register_file, file_registry

router = APIRouter()
logger = logging.getLogger("app.api.files")

# Определяем модель для запроса upload_url
class UploadUrlRequest(BaseModel):
    fileName: str
    fileType: FileType

def get_supabase_client():
    """
    Возвращает инициализированный клиент Supabase или None
    """
    return init_supabase_client()

@router.post("/upload_url")
async def get_upload_url(request: UploadUrlRequest):
    """
    Получение URL для прямой загрузки в Supabase
    """
    try:
        file_extension = os.path.splitext(request.fileName)[1].lower()
        timestamp = int(time.time())
        stored_filename = f"file_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        # Получаем клиент Supabase
        client = get_supabase_client()
        
        if client:
            # Получаем URL для загрузки напрямую в Supabase
            upload_path = f"uploads/{stored_filename}"
            upload_url = client.storage.from_(settings.SUPABASE_BUCKET).create_signed_upload_url(upload_path)
            
            # Выводим структуру объекта в логи для диагностики
            logger.info(f"Получен ответ от Supabase: {upload_url}")
            
            # Создаем объект с информацией о файле 
            file_info = {
                "original_filename": request.fileName,
                "stored_filename": stored_filename,
                "file_type": request.fileType,
                "upload_path": upload_path
            }
            
            # Проверяем наличие ключа signedURL
            if 'signedURL' in upload_url:
                signed_url = upload_url['signedURL']
            elif 'signed_url' in upload_url:
                signed_url = upload_url['signed_url']
            elif 'url' in upload_url:
                signed_url = upload_url['url']
            else:
                # Если не находим ожидаемых ключей, создаем заглушку
                logger.warning(f"Не удалось найти URL в ответе Supabase, используя прямой доступ через API")
                bucket_url = client.storage.from_(settings.SUPABASE_BUCKET)._get_url()
                object_url = f"{bucket_url}/object/{settings.SUPABASE_BUCKET}/{upload_path}"
                signed_url = f"{object_url}?token={uuid.uuid4()}"
            
            return {
                "uploadUrl": signed_url,
                "fileInfo": file_info
            }
        else:
            # Если Supabase недоступен, возвращаем заглушку
            logger.warning("Supabase недоступен, используем заглушку для upload_url")
            return {
                "uploadUrl": f"/api/v1/files/mock-upload/{stored_filename}",
                "fileInfo": {
                    "original_filename": request.fileName,
                    "stored_filename": stored_filename,
                    "file_type": request.fileType,
                    "upload_path": f"uploads/{stored_filename}"
                }
            }
    except Exception as e:
        logger.error(f"Ошибка при создании URL для загрузки: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось создать URL для загрузки: {str(e)}")

class RegisterFileRequest(BaseModel):
    fileInfo: Dict[str, Any]

@router.post("/register", response_model=FileInfo)
async def register_uploaded_file(request: RegisterFileRequest):
    """
    Регистрация файла после прямой загрузки в Supabase
    """
    try:
        file_info = request.fileInfo
        
        # Получаем содержимое файла
        client = get_supabase_client()
        file_path = file_info.get("upload_path")
        stored_filename = file_info.get("stored_filename")
        
        if not client:
            logger.warning("Supabase недоступен, используем заглушечные данные")
            # Если Supabase недоступен, создаем объект FileInfo с заглушечными данными
            registered_file = FileInfo(
                id=str(uuid.uuid4()),
                original_filename=file_info.get("original_filename", "sample.csv"),
                stored_filename=stored_filename,
                file_url=f"/api/v1/files/download/{stored_filename}",
                file_type=file_info.get("file_type", FileType.SUPPLIER),
                file_size=1000,
                encoding="utf-8",
                separator=","
            )
            
            # Регистрируем файл в реестре для сравнения
            register_file(registered_file)
            
            return registered_file
        
        # Получаем файл из Supabase
        try:
            # Попытка получить файл из Supabase
            file_content = client.storage.from_(settings.SUPABASE_BUCKET).download(file_path)
            
            # Определяем кодировку и разделитель
            encoding = detect_encoding(file_content)
            separator = detect_separator(file_content, encoding)
            
            # Создаем публичную ссылку для доступа к файлу
            file_url = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
            
            # Создаем объект FileInfo
            registered_file = FileInfo(
                id=str(uuid.uuid4()),
                original_filename=file_info.get("original_filename"),
                stored_filename=stored_filename,
                file_url=file_url,
                file_type=file_info.get("file_type"),
                file_size=len(file_content),
                encoding=encoding,
                separator=separator
            )
            
            # Регистрируем файл в реестре для сравнения
            register_file(registered_file)
            
            return registered_file
        except Exception as e:
            logger.error(f"Ошибка при получении файла из Supabase: {str(e)}", exc_info=True)
            # В случае ошибки возвращаем объект с базовой информацией
            return FileInfo(
                id=str(uuid.uuid4()),
                original_filename=file_info.get("original_filename", "unknown"),
                stored_filename=stored_filename,
                file_url=f"/api/v1/files/download/{stored_filename}",
                file_type=file_info.get("file_type", FileType.SUPPLIER),
                file_size=0,
                encoding="utf-8",
                separator=","
            )
    except Exception as e:
        logger.error(f"Ошибка при регистрации файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось зарегистрировать файл: {str(e)}")

@router.post("/upload", response_model=FileInfo)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...)
):
    """
    Загрузка файла прайс-листа
    """
    try:
        # Проверка типа файла
        if file_type not in [FileType.SUPPLIER, FileType.STORE]:
            logger.error(f"Неверный тип файла: {file_type}")
            raise HTTPException(status_code=400, detail=f"Неверный тип файла: {file_type}. Допустимые типы: supplier, store")
        
        # Проверка расширения файла
        allowed_extensions = ['.csv', '.xlsx', '.xls', '.txt']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            logger.error(f"Неподдерживаемый формат файла: {file_extension}")
            raise HTTPException(
                status_code=400, 
                detail=f"Неподдерживаемый формат файла: {file_extension}. Поддерживаемые форматы: {', '.join(allowed_extensions)}"
            )
        
        # Чтение содержимого файла
        contents = await file.read()
        
        # Проверка размера файла
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ
        if len(contents) > MAX_FILE_SIZE:
            logger.error(f"Размер файла превышает допустимый: {len(contents)} > {MAX_FILE_SIZE} байт")
            raise HTTPException(
                status_code=400, 
                detail=f"Размер файла превышает допустимый: {len(contents) / (1024 * 1024):.2f} МБ (макс. 10 МБ)"
            )
            
        # Сброс позиции файла после чтения
        await file.seek(0)
        
        # Логирование получения файла
        logger.info(f"Получен файл для загрузки: {file.filename}, тип: {file_type}, размер: {len(contents)} байт")
        
        # Генерация уникального имени файла для хранения
        timestamp = int(time.time())
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
    logger.info(f"Запрос колонок для файла: {filename}, кодировка: {encoding}, разделитель: {separator}")
    
    try:
        # Получаем содержимое файла
        logger.debug(f"Получаем содержимое файла {filename}")
        file_content = get_file_content(filename)
        
        if not file_content:
            logger.error(f"Файл не найден: {filename}")
            raise HTTPException(status_code=404, detail=f"Файл не найден: {filename}")
        
        logger.debug(f"Получено содержимое файла {filename}, размер: {len(file_content)} байт")
        
        # Получаем расширение файла
        extension = os.path.splitext(filename)[1]
        logger.debug(f"Расширение файла: {extension}")
        
        # Получаем колонки
        logger.debug(f"Извлекаем колонки из файла {filename}")
        columns = get_columns(file_content, extension, encoding, separator)
        
        logger.info(f"Успешно получены колонки для файла {filename}: {columns}")
        return columns
    except ValueError as e:
        logger.error(f"Ошибка при получении колонок файла {filename}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении колонок файла {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка при получении колонок: {str(e)}")

@router.post("/mapping", response_model=FileInfo)
async def save_column_mapping(file_info: FileInfo):
    """
    Сохранение сопоставления колонок для файла
    """
    # В реальном приложении здесь будет сохранение в базу данных
    
    # Обновляем информацию о файле в реестре для сравнения
    if file_info.id:
        if file_info.id in file_registry:
            # Обновляем существующий файл в реестре
            existing_file = file_registry[file_info.id]
            # Обновляем маппинг колонок
            existing_file.column_mapping = file_info.column_mapping
            logger.info(f"Обновлен маппинг колонок для файла в реестре: id={file_info.id}")
        else:
            # Если файл ещё не в реестре, добавляем его
            register_file(file_info)
            logger.info(f"Файл добавлен в реестр с маппингом колонок: id={file_info.id}")
    
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

@router.get("/mock-test", response_model=Dict[str, Any])
async def test_mock_files():
    """
    Тестовый маршрут для проверки работы с mock-файлами
    """
    raise HTTPException(status_code=404, detail="Endpoint removed")

@router.get("/create-mock-files", response_model=Dict[str, Any])
async def create_mock_files():
    """
    Создает мок-файлы для тестирования сравнения
    """
    raise HTTPException(status_code=404, detail="Endpoint removed")

@router.get("/prepare-mock-test", response_model=Dict[str, Any])
async def prepare_mock_test():
    """
    Подготовительный маршрут для создания и проверки конкретных мок-файлов
    """
    raise HTTPException(status_code=404, detail="Endpoint removed")

@router.get("/create-mock-cache")
async def create_mock_cache():
    """
    Создает кешированные версии мок-файлов без сохранения в Supabase
    """
    raise HTTPException(status_code=404, detail="Endpoint removed") 