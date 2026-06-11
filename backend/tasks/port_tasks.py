"""Port refresh periodic tasks."""

import asyncio
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.port_tasks.refresh_ports")
def refresh_ports():
    """Refresh port data from Overpass API."""
    from services.port_service import PortService

    async def _run():
        ps = PortService()
        await ps.fetch_ports(rebuild=True)
        await ps.backfill_port_countries()

    asyncio.run(_run())
