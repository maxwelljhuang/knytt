"""
Celery Application Configuration
"""

import os
from celery import Celery
from celery.schedules import crontab

# Get configuration from environment
# Use REDIS_URL if set, otherwise construct from CELERY_BROKER_URL or default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
app = Celery(
    "greenthumb",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.ingestion",
        "backend.tasks.embeddings",
    ],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configure periodic tasks with Celery Beat
app.conf.beat_schedule = {
    # Rebuild FAISS index weekly (every Sunday at 3 AM)
    "rebuild-faiss-index-weekly": {
        "task": "tasks.rebuild_faiss_index",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "kwargs": {"embedding_type": "text"},
    },
    # Generate embeddings for new products daily (2 AM)
    "generate-new-product-embeddings-daily": {
        "task": "tasks.generate_product_embeddings",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {
            "force_regenerate": False,
            "batch_size": 32,
        },
    },
    # Refresh user embeddings for active users (every 6 hours)
    "refresh-active-user-embeddings": {
        "task": "tasks.batch_refresh_user_embeddings",
        "schedule": crontab(minute=0, hour="*/6"),
        "kwargs": {"hours_active": 24},
    },
    # Clean up old sessions (daily at 4 AM)
    "cleanup-old-sessions": {
        "task": "tasks.cleanup_old_sessions",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"days_old": 7},
    },
}

if __name__ == "__main__":
    app.start()
