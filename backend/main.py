"""
Sea Tracker — FastAPI Application Entry Point.
Real-time global maritime tracking system.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import init_db, close_db
from services.redis_broker import RedisBroker
from services.vessel_tracker import VesselTracker
from services.ais_aggregator import AISAggregator
from services.incident_detector import IncidentDetector
from services.alert_engine import AlertEngine
from services.collision_detector import CollisionDetector
from services.zone_monitor import ZoneMonitor
from services.cable_service import CableService
from services.notification_service import NotificationService
from services.port_service import PortService
from websocket.vessel_ws import vessel_ws_endpoint, start_vessel_broadcaster
from websocket.alert_ws import alert_ws_endpoint, start_alert_broadcaster
from websocket.incident_ws import incident_ws_endpoint, start_incident_broadcaster
from routers import (
    vessels, history, incidents, alerts,
    ports, zones, analytics, weather, layers, workspace, intel, notifications,
)

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-15s | %(levelname)-7s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("sea_tracker")

settings = get_settings()

# ── Global service instances ──────────────────────────────────
redis_broker = RedisBroker()
vessel_tracker = VesselTracker(redis_broker)
notification_service = NotificationService()
alert_engine = AlertEngine(redis_broker, notification_service=notification_service)
incident_detector = IncidentDetector(redis_broker)
collision_detector = CollisionDetector(alert_engine)
zone_monitor = ZoneMonitor(alert_engine)
aggregator = AISAggregator(redis_broker, vessel_tracker)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚢 Sea Tracker starting up...")

    # 1. Init database tables
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("⚠️ Database init failed: %s", exc)
        logger.error(
            "   Make sure PostgreSQL is running and "
            "the database 'seatracker' exists."
        )

    # 2. Connect Redis
    try:
        await redis_broker.connect()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("⚠️ Redis connection failed: %s", exc)
        logger.error("   Make sure Redis is running on localhost:6379")

    # 3. Load zones for monitoring
    try:
        await zone_monitor.load_zones()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Zone load skipped: %s", exc)

    # 4. Fetch static data (cables, ports) in background
    asyncio.create_task(_init_static_data())

    # 5. Start notification retry loop
    notification_service.start_retry_loop()
    logger.info("✅ Notification retry loop started")

    # 6. Start AIS data sources
    asyncio.create_task(aggregator.start())
    logger.info("✅ AIS Aggregator started")

    # 7. Start WebSocket broadcasters
    asyncio.create_task(start_vessel_broadcaster(redis_broker))
    asyncio.create_task(start_alert_broadcaster(redis_broker))
    asyncio.create_task(start_incident_broadcaster(redis_broker))
    logger.info("✅ WebSocket broadcasters started")

    logger.info("🌊 Sea Tracker is live at http://localhost:8000")

    yield

    # Shutdown
    logger.info("🛑 Sea Tracker shutting down...")
    try:
        await aggregator.stop()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    try:
        await notification_service.stop_retry_loop()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    try:
        await redis_broker.close()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    try:
        await close_db()
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    logger.info("👋 Sea Tracker stopped")


async def _init_static_data():
    """Load static datasets on first startup."""
    try:
        # Fetch submarine cables if not cached
        if not os.path.exists("static/cables.geojson"):
            os.makedirs("static", exist_ok=True)
            cable_service = CableService()
            await cable_service.fetch_cables()

        # Ensure the world ports catalog is complete and country metadata is normalized
        port_service = PortService()
        summary = await port_service.ensure_port_catalog()
        logger.info(
            "Port catalog ready: %s ports cached, %s refreshed, %s normalized",
            summary["count"],
            summary["refreshed"],
            summary["normalized"],
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Static data init error: %s", exc)


# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(
    title="Sea Tracker",
    description="Real-time global maritime traffic tracking system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── REST API Routers ──────────────────────────────────────────
app.include_router(vessels.router)
app.include_router(history.router)
app.include_router(incidents.router)
app.include_router(alerts.router)
app.include_router(ports.router)
app.include_router(zones.router)
app.include_router(analytics.router)
app.include_router(weather.router)
app.include_router(layers.router)
app.include_router(workspace.router)
app.include_router(intel.router)
app.include_router(notifications.router)


# ── WebSocket Endpoints ──────────────────────────────────────
@app.websocket("/ws/vessels")
async def ws_vessels(websocket: WebSocket):
    """WebSocket endpoint for vessel updates."""
    await vessel_ws_endpoint(websocket)


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """WebSocket endpoint for alert updates."""
    await alert_ws_endpoint(websocket)


@app.websocket("/ws/incidents")
async def ws_incidents(websocket: WebSocket):
    """WebSocket endpoint for incident updates."""
    await incident_ws_endpoint(websocket)


# ── Health Check ──────────────────────────────────────────────
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "redis_connected": redis_broker.connected,
        "active_sources": aggregator.active_sources,
        "message_count": aggregator.message_count,
        "ws_clients": {
            "vessels": vessel_tracker.update_count,
        },
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"app": "Sea Tracker", "version": "1.0.0", "docs": "/docs"}
