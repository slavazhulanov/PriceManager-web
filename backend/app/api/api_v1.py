from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.endpoints import files, comparison

api_router = APIRouter()

@api_router.get("/test", response_model=dict)
async def test_api():
    """
    Тестовый эндпоинт для проверки API
    """
    return {
        "status": "ok",
        "message": "API работает",
        "data": ["test1", "test2", "test3"],
        "complex_data": {
            "columns": ["col1", "col2", "col3"]
        }
    }

api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(comparison.router, prefix="/comparison", tags=["comparison"]) 