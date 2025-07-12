from fastapi import APIRouter

from src.api.v1.endpoints import admin, auth, collections, config, docs, ebay_oauth_redirect, oauth, searches

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(ebay_oauth_redirect.router, tags=["oauth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(config.router, prefix="/config", tags=["configuration"])
api_router.include_router(searches.router, prefix="/searches", tags=["searches"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(docs.router, prefix="/docs", tags=["documentation"])
