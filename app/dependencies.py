"""Shared FastAPI dependencies."""
from functools import lru_cache
from src.config.settings import get_settings


@lru_cache()
def get_app_settings():
    """Return cached settings instance for FastAPI dependency injection."""
    return get_settings()
