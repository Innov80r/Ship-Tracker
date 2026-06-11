"""Cable data fetch task."""

import asyncio
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.cable_tasks.fetch_cables")
def fetch_cables():
    """Download submarine cable GeoJSON."""
    from services.cable_service import CableService

    async def _run():
        cs = CableService()
        await cs.fetch_cables()

    asyncio.run(_run())
