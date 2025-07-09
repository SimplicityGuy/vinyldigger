from fastapi import APIRouter

from src.api.v1.endpoints import auth, collections, config, searches

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(config.router, prefix="/config", tags=["configuration"])
api_router.include_router(searches.router, prefix="/searches", tags=["searches"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
