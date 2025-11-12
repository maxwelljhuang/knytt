"""
API Routers
FastAPI route handlers for different endpoints.
"""

from .admin import router as admin_router
from .auth import router as auth_router
from .discover import router as discover_router
from .feedback import router as feedback_router
from .health import router as health_router
from .onboarding import router as onboarding_router
from .recommend import router as recommend_router
from .search import router as search_router
from .users import router as users_router

__all__ = [
    "health_router",
    "auth_router",
    "search_router",
    "discover_router",
    "recommend_router",
    "feedback_router",
    "admin_router",
    "users_router",
    "onboarding_router",
]
