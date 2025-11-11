"""
Celery Tasks Module
Background task processing for GreenThumb
"""

from .celery_app import app as celery_app

__all__ = ["celery_app"]
