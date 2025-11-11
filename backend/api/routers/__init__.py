"""
API Routers
FastAPI route handlers for different endpoints.
"""

from .health import router as health_router
from .auth import router as auth_router
from .search import router as search_router
from .recommend import router as recommend_router
from .feedback import router as feedback_router
from .admin import router as admin_router
from .users import router as users_router
from .onboarding import router as onboarding_router

__all__ = [
    "health_router",
    "auth_router",
    "search_router",
    "recommend_router",
    "feedback_router",
    "admin_router",
    "users_router",
    "onboarding_router",
]
