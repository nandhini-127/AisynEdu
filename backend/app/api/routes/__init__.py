from fastapi import APIRouter
from app.api.routes import admin, analytics, auth, chat, documents, health, multimodal

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(multimodal.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
