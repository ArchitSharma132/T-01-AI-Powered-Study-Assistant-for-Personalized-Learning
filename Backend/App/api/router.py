from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.quiz import router as quiz_router
from app.api.auth import router as auth_router
from app.api.reviews import router as reviews_router
from app.api.analytics import router as analytics_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(quiz_router)
api_router.include_router(reviews_router)
api_router.include_router(analytics_router)
