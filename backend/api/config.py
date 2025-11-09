"""
API Configuration
Settings and configuration for FastAPI application.
"""

import os
import json
from typing import List, Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class APISettings(BaseSettings):
    """
    API configuration settings.

    Load from environment variables with API_ prefix.
    """

    # API Info
    app_name: str = "GreenThumb ML API"
    version: str = "0.1.0"
    description: str = "ML-powered product search and recommendations"

    # Server settings
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    reload: bool = Field(default=False, alias="API_RELOAD")
    workers: int = Field(default=4, alias="API_WORKERS")

    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        alias="API_CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database settings
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/greenthumb",
        alias="DATABASE_URL"
    )
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Redis settings
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=1, alias="REDIS_DB")

    # Performance settings
    enable_cache: bool = Field(default=True, alias="API_ENABLE_CACHE")
    cache_ttl_search: int = Field(default=300, alias="API_CACHE_TTL_SEARCH")  # 5 min
    cache_ttl_recommend: int = Field(default=120, alias="API_CACHE_TTL_RECOMMEND")  # 2 min
    cache_ttl_product: int = Field(default=3600, alias="API_CACHE_TTL_PRODUCT")  # 1 hour

    # Rate limiting
    enable_rate_limit: bool = Field(default=True, alias="API_ENABLE_RATE_LIMIT")
    rate_limit_requests: int = Field(default=100, alias="API_RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="API_RATE_LIMIT_WINDOW")  # seconds

    # Logging
    log_level: str = Field(default="INFO", alias="API_LOG_LEVEL")
    log_format: str = "json"  # json or text

    # Security
    api_key_header: str = "X-API-Key"
    require_api_key: bool = Field(default=False, alias="API_REQUIRE_KEY")
    api_keys: List[str] = Field(default=[], alias="API_KEYS")

    # Performance targets
    target_p95_latency_ms: int = 150

    # ML settings
    ml_model_version: str = Field(default="v1.0-clip-vit-b32", alias="ML_MODEL_VERSION")
    faiss_index_path: str = Field(
        default="models/cache/faiss_index",
        alias="FAISS_INDEX_PATH"
    )

    # Feature flags
    enable_text_search: bool = Field(default=True, alias="API_ENABLE_TEXT_SEARCH")
    enable_personalization: bool = Field(default=True, alias="API_ENABLE_PERSONALIZATION")
    enable_feedback: bool = Field(default=True, alias="API_ENABLE_FEEDBACK")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated list
                return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env file
        env_prefix="",  # No prefix for environment variables
        validate_default=True,
        populate_by_name=True  # Allow using both field name and alias for env vars
    )


# Global settings instance
_settings: Optional[APISettings] = None


def get_settings() -> APISettings:
    """Get global API settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
