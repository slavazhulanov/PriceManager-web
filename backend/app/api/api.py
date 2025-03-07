from fastapi import APIRouter
from app.api.endpoints import files, comparison, prices, logs

api_router = APIRouter()
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(comparison.router, prefix="/comparison", tags=["comparison"])
api_router.include_router(prices.router, prefix="/prices", tags=["prices"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"]) 