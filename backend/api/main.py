"""
FastAPI Main Application
Entry point for the GreenThumb ML API.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import get_settings
from .errors import setup_error_handlers
from .middleware import RequestLoggingMiddleware, RequestTimingMiddleware
from .routers import (
    health_router,
    search_router,
    recommend_router,
    feedback_router,
    admin_router,
    auth_router,
    users_router,
    onboarding_router,
)
from ..ml.retrieval import get_index_manager
from ..db.session import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs on startup and shutdown to initialize/cleanup resources.
    """
    # Startup
    logger.info("Starting GreenThumb ML API...")

    settings = get_settings()

    # Load FAISS index in background (non-blocking)
    # This allows the app to start quickly and pass health checks
    import threading

    def load_index_background():
        try:
            logger.info("Loading FAISS index in background...")
            index_manager = get_index_manager(db_session_factory=SessionLocal)
            index_manager.ensure_index_loaded()

            stats = index_manager.get_stats()
            logger.info(
                f"FAISS index loaded successfully: {stats.get('num_vectors', 0)} vectors, "
                f"type={stats.get('index_type', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            logger.warning("Search functionality may be limited until index is loaded")

    # Start index loading in background thread
    index_thread = threading.Thread(target=load_index_background, daemon=True)
    index_thread.start()

    logger.info("GreenThumb ML API started successfully (FAISS index loading in background)")

    yield

    # Shutdown
    logger.info("Shutting down GreenThumb ML API...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add custom middleware
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Set up error handlers
    setup_error_handlers(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(auth_router)  # Auth router (for /api/v1/auth endpoints)
    app.include_router(users_router)  # User endpoints (favorites, history, stats)
    app.include_router(onboarding_router)  # Onboarding flow
    app.include_router(search_router)
    app.include_router(recommend_router)
    app.include_router(feedback_router)
    app.include_router(admin_router)

    return app


# Create app instance
app = create_app()


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        API information
    """
    settings = get_settings()

    return {
        "name": settings.app_name,
        "version": settings.version,
        "description": settings.description,
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "metrics": "/metrics",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
