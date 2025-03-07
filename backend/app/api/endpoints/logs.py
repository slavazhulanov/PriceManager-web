from fastapi import APIRouter, Request, Body
from typing import Dict, Any, List
import logging
import uuid
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger("app.user_actions")

router = APIRouter()

class UserAction(BaseModel):
    action_type: str
    component: str
    page: str
    details: Dict[str, Any] = {}
    timestamp: str = None

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