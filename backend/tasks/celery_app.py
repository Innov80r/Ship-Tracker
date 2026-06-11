"""
Celery application configuration.
Uses Redis as broker. Solo pool for Windows compatibility.
"""

import sys
from pathlib import Path

from celery import Celery
from celery.schedules import crontab

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "sea_tracker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.weather_tasks",
        "tasks.port_tasks",
        "tasks.analytics_tasks",
        "tasks.cleanup_tasks",
        "tasks.cable_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_pool="solo",  # Required for Windows
    beat_schedule={
        "fetch-weather-grid": {
            "task": "tasks.weather_tasks.fetch_weather_grid",
            "schedule": 900.0,  # Every 15 minutes
        },
        "fetch-tides": {
            "task": "tasks.weather_tasks.fetch_tides",
            "schedule": 1800.0,  # Every 30 minutes
        },
        "refresh-ports": {
            "task": "tasks.port_tasks.refresh_ports",
            "schedule": crontab(day_of_week="sunday", hour=3, minute=0),  # Weekly
        },
        "aggregate-analytics": {
            "task": "tasks.analytics_tasks.aggregate_analytics",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-history": {
            "task": "tasks.cleanup_tasks.cleanup_old_history",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "mark-inactive-vessels": {
            "task": "tasks.cleanup_tasks.mark_inactive_vessels",
            "schedule": 60.0,  # Every minute
        },
    },
)
