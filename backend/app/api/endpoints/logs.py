from fastapi import APIRouter, Request, Body
from typing import Dict, Any, List
import logging
import uuid
from datetime import datetime
from pydantic import BaseModel
import json
import os

logger = logging.getLogger("app.user_actions")
frontend_logger = logging.getLogger("app.frontend")

router = APIRouter()

class UserAction(BaseModel):
    action_type: str
    component: str
    page: str
    details: Dict[str, Any] = {}
    timestamp: str = None

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    data: Dict[str, Any] = {}
    trace_id: str = None
    user_id: str = None

@router.post("/user-action")
async def log_user_action(
    request: Request,
    action: UserAction = Body(...)
):
    """
    Логирование действий пользователя (клики на кнопки, выборы в формах и т.д.)
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Добавляем timestamp, если его нет
    if not action.timestamp:
        action.timestamp = datetime.utcnow().isoformat()
    
    # Логируем действие пользователя
    logger.info(
        f"[{request_id}] Действие пользователя: {action.action_type} | "
        f"Компонент: {action.component} | Страница: {action.page} | "
        f"IP: {client_ip} | User-Agent: {user_agent} | "
        f"Детали: {action.details}"
    )
    
    return {"status": "success", "message": "Действие пользователя залогировано"}

@router.post("/user-actions/batch")
async def log_user_actions_batch(
    request: Request,
    actions: List[UserAction] = Body(...)
):
    """
    Пакетное логирование действий пользователя
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(f"[{request_id}] Получена пакетная запись действий пользователя, количество: {len(actions)}")
    
    # Логируем каждое действие пользователя
    for action in actions:
        # Добавляем timestamp, если его нет
        if not action.timestamp:
            action.timestamp = datetime.utcnow().isoformat()
        
        logger.info(
            f"[{request_id}] Действие пользователя: {action.action_type} | "
            f"Компонент: {action.component} | Страница: {action.page} | "
            f"IP: {client_ip} | Время: {action.timestamp} | "
            f"Детали: {action.details}"
        )
    
    return {"status": "success", "message": f"Залогировано {len(actions)} действий пользователя"}

@router.post("/frontend/batch")
async def save_frontend_logs_batch(
    request: Request,
    logs: List[LogEntry] = Body(...)
):
    """
    Сохранение пакета логов с фронтенда
    """
    try:
        # Получаем информацию о запросе
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Создаем директорию для логов если её нет
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Форматируем имя файла с текущей датой
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Группируем логи по уровню
        error_logs = []
        info_logs = []
        
        for log in logs:
            # Добавляем дополнительную информацию
            log_data = {
                "timestamp": log.timestamp,
                "level": log.level,
                "message": log.message,
                "data": log.data,
                "trace_id": log.trace_id,
                "user_id": log.user_id,
                "client_ip": client_ip,
                "user_agent": user_agent
            }
            
            # Распределяем логи по файлам в зависимости от уровня
            if log.level in ["ERROR", "UNCAUGHT", "UNHANDLED_PROMISE"]:
                error_logs.append(log_data)
            else:
                info_logs.append(log_data)
        
        # Записываем ошибки
        if error_logs:
            error_file = f"logs/frontend-error-{current_date}.log"
            with open(error_file, "a") as f:
                for log in error_logs:
                    # Форматируем лог для лучшей читаемости
                    formatted_log = f"[{log['timestamp']}] {log['level']} - {log['message']}"
                    if log.get('data'):
                        formatted_log += f" - Data: {json.dumps(log['data'], ensure_ascii=False)}"
                    if log.get('trace_id'):
                        formatted_log += f" - Trace: {log['trace_id']}"
                    if log.get('user_id'):
                        formatted_log += f" - User: {log['user_id']}"
                    f.write(formatted_log + "\n")
            
            # Также логируем в системный журнал
            for log in error_logs:
                frontend_logger.error(
                    f"Frontend error: {log['message']}", 
                    extra={
                        "trace_id": log["trace_id"],
                        "user_id": log["user_id"],
                        "data": log["data"]
                    }
                )
        
        # Записываем информационные логи
        if info_logs:
            info_file = f"logs/frontend-{current_date}.log"
            with open(info_file, "a") as f:
                for log in info_logs:
                    # Форматируем лог для лучшей читаемости
                    formatted_log = f"[{log['timestamp']}] {log['level']} - {log['message']}"
                    if log.get('data'):
                        formatted_log += f" - Data: {json.dumps(log['data'], ensure_ascii=False)}"
                    if log.get('trace_id'):
                        formatted_log += f" - Trace: {log['trace_id']}"
                    if log.get('user_id'):
                        formatted_log += f" - User: {log['user_id']}"
                    f.write(formatted_log + "\n")
            
            # Также логируем в системный журнал
            for log in info_logs:
                frontend_logger.info(
                    f"Frontend log: {log['message']}", 
                    extra={
                        "trace_id": log["trace_id"],
                        "user_id": log["user_id"],
                        "data": log["data"]
                    }
                )
        
        return {"status": "success", "processed": len(logs)}
        
    except Exception as e:
        frontend_logger.exception("Failed to save frontend logs batch")
        return {"status": "error", "message": str(e)}

@router.post("/frontend")
async def save_frontend_log(
    request: Request,
    log_entry: LogEntry = Body(...)
):
    """
    Сохранение одиночного лога с фронтенда
    """
    try:
        # Получаем информацию о запросе
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Создаем директорию для логов если её нет
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Форматируем имя файла с текущей датой
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Определяем файл лога в зависимости от уровня
        level = log_entry.level
        
        # Добавляем дополнительную информацию
        log_data = {
            "timestamp": log_entry.timestamp,
            "level": level,
            "message": log_entry.message,
            "data": log_entry.data,
            "trace_id": log_entry.trace_id,
            "user_id": log_entry.user_id,
            "client_ip": client_ip,
            "user_agent": user_agent
        }
        
        if level in ["ERROR", "UNCAUGHT", "UNHANDLED_PROMISE"]:
            log_file = f"logs/frontend-error-{current_date}.log"
            # Записываем лог в файл
            with open(log_file, "a") as f:
                # Форматируем лог для лучшей читаемости
                formatted_log = f"[{log_data['timestamp']}] {log_data['level']} - {log_data['message']}"
                if log_data.get('data'):
                    formatted_log += f" - Data: {json.dumps(log_data['data'], ensure_ascii=False)}"
                if log_data.get('trace_id'):
                    formatted_log += f" - Trace: {log_data['trace_id']}"
                if log_data.get('user_id'):
                    formatted_log += f" - User: {log_data['user_id']}"
                f.write(formatted_log + "\n")
            
            # Также логируем в системный журнал
            frontend_logger.error(
                f"Frontend error: {log_entry.message}", 
                extra={
                    "trace_id": log_entry.trace_id,
                    "user_id": log_entry.user_id,
                    "data": log_entry.data
                }
            )
        else:
            log_file = f"logs/frontend-{current_date}.log"
            # Записываем лог в файл
            with open(log_file, "a") as f:
                # Форматируем лог для лучшей читаемости
                formatted_log = f"[{log_data['timestamp']}] {log_data['level']} - {log_data['message']}"
                if log_data.get('data'):
                    formatted_log += f" - Data: {json.dumps(log_data['data'], ensure_ascii=False)}"
                if log_data.get('trace_id'):
                    formatted_log += f" - Trace: {log_data['trace_id']}"
                if log_data.get('user_id'):
                    formatted_log += f" - User: {log_data['user_id']}"
                f.write(formatted_log + "\n")
            
            # Также логируем в системный журнал
            frontend_logger.info(
                f"Frontend log: {log_entry.message}", 
                extra={
                    "trace_id": log_entry.trace_id,
                    "user_id": log_entry.user_id,
                    "data": log_entry.data
                }
            )
            
        return {"status": "success"}
        
    except Exception as e:
        frontend_logger.exception("Failed to save frontend log")
        return {"status": "error", "message": str(e)}

# Дублируем маршруты для совместимости с frontend
@router.post("/frontend/batch")
async def save_frontend_logs_batch_handler(
    request: Request,
    logs: List[LogEntry] = Body(...)
):
    """
    Сохранение пакета логов с фронтенда (основной маршрут)
    """
    return await save_frontend_logs_batch(request, logs)

@router.post("/user-actions/batch")
async def log_user_actions_batch_handler(
    request: Request,
    actions: List[UserAction] = Body(...)
):
    """
    Пакетное логирование действий пользователя (основной маршрут)
    """
    return await log_user_actions_batch(request, actions) 