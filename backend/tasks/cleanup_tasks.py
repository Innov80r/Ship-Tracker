"""Cleanup periodic tasks — history purge and inactive vessel marking."""

import asyncio
from datetime import datetime, timezone, timedelta
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.cleanup_tasks.cleanup_old_history")
def cleanup_old_history():
    """Delete position history older than retention period."""
    from database import async_session_factory
    from models.vessel_history import VesselHistory
    from config import get_settings
    from sqlalchemy import delete

    settings = get_settings()

    async def _run():
        cutoff = datetime.utcnow() - timedelta(days=settings.HISTORY_RETENTION_DAYS)
        async with async_session_factory() as session:
            result = await session.execute(
                delete(VesselHistory).where(VesselHistory.timestamp < cutoff)
            )
            await session.commit()

    asyncio.run(_run())


@celery_app.task(name="tasks.cleanup_tasks.mark_inactive_vessels")
def mark_inactive_vessels():
    """Mark vessels inactive if no update within timeout."""
    from database import async_session_factory
    from models.vessel import Vessel
    from config import get_settings
    from sqlalchemy import update

    settings = get_settings()

    async def _run():
        cutoff = datetime.utcnow() - timedelta(minutes=settings.VESSEL_TIMEOUT_MINUTES)
        async with async_session_factory() as session:
            await session.execute(
                update(Vessel).where(
                    Vessel.is_active == True,
                    Vessel.last_updated < cutoff,
                ).values(is_active=False)
            )
            await session.commit()

    asyncio.run(_run())
