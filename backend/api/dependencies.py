"""
Dependency Injection
FastAPI dependencies for database, services, and configurations.
"""

import logging
from typing import Generator, Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status, Cookie

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings, APISettings
from .security import verify_token
from ..db.models import User
from ..ml.search import SearchService
from ..ml.retrieval import get_index_manager
from ..ml.caching import EmbeddingCache

logger = logging.getLogger(__name__)

# Database engine and session factory
_engine = None
_SessionLocal = None


def get_db_engine():
    """Get database engine (singleton)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
        )
        logger.info(f"Database engine created: {settings.database_url}")
    return _engine


def get_session_factory():
    """Get database session factory (singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_db_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database session factory created")
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Use as FastAPI dependency:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """
    Get search service instance.

    Use as FastAPI dependency:
        @app.post("/search")
        def search(service: SearchService = Depends(get_search_service)):
            ...
    """
    settings = get_settings()

    # Create session factory for the service
    SessionLocal = get_session_factory()

    service = SearchService(db_session_factory=SessionLocal)

    # Ensure FAISS index is loaded
    try:
        index_manager = get_index_manager()
        index_manager.ensure_index_loaded(session=db)
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        # Don't fail the request, but log the error

    return service


def get_embedding_cache() -> EmbeddingCache:
    """
    Get embedding cache instance.

    Use as FastAPI dependency:
        @app.get("/endpoint")
        def endpoint(cache: EmbeddingCache = Depends(get_embedding_cache)):
            ...
    """
    return EmbeddingCache()


def verify_api_key(
    settings: APISettings = Depends(get_settings), x_api_key: Optional[str] = Header(None)
) -> bool:
    """
    Verify API key if required.

    Use as FastAPI dependency:
        @app.get("/endpoint")
        def endpoint(authorized: bool = Depends(verify_api_key)):
            ...
    """
    if not settings.require_api_key:
        return True

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return True


def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[int]:
    """
    Get current user ID from header.

    Use as FastAPI dependency:
        @app.get("/endpoint")
        def endpoint(user_id: Optional[int] = Depends(get_current_user_id)):
            ...
    """
    if x_user_id is None:
        return None

    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )


def get_request_id(x_request_id: Optional[str] = Header(None)) -> str:
    """
    Get or generate request ID for tracing.

    Use as FastAPI dependency:
        @app.get("/endpoint")
        def endpoint(request_id: str = Depends(get_request_id)):
            ...
    """
    if x_request_id:
        return x_request_id

    # Generate UUID if not provided
    import uuid

    return str(uuid.uuid4())


def get_current_user(
    access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token in cookie.

    Use as FastAPI dependency to protect routes:
        @app.get("/endpoint")
        def endpoint(current_user: User = Depends(get_current_user)):
            ...

    Raises:
        HTTPException: 401 if not authenticated or token invalid
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify and decode token
    payload = verify_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def get_current_user_optional(
    access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user, but don't raise error if not authenticated.
    Returns None if no valid token.

    Use for endpoints that work for both authenticated and anonymous users.
    """
    if not access_token:
        return None

    try:
        payload = verify_token(access_token)
        if not payload:
            return None

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        user_id = UUID(user_id_str)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except Exception:
        return None
