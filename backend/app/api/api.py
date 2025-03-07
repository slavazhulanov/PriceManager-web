from fastapi import APIRouter
from app.api.endpoints import files, comparison, prices

api_router = APIRouter()
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(comparison.router, prefix="/comparison", tags=["comparison"])
api_router.include_router(prices.router, prefix="/prices", tags=["prices"]) 