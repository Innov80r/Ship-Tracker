"""Intelligence API routes."""

from fastapi import APIRouter, Query

from schemas.intel import ExternalIntelEventPayload, VesselProfilePayload
from services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/api/intel", tags=["intel"])


@router.get("/vessels")
async def filter_vessels(
    search: str | None = None,
    vessel_type: int | None = None,
    flag: str | None = None,
    category: str | None = None,
    source: str | None = None,
    speed_min: float | None = None,
    speed_max: float | None = None,
    risk_min: float | None = None,
    dark_only: bool = False,
    destination_required: bool = False,
    last_seen_minutes: float | None = None,
    limit: int = Query(100, ge=1, le=5000),
):
    """Filter vessels with server-side intelligence-aware constraints."""
    try:
        service = IntelligenceService()
        vessels = await service.filter_vessels(
            search=search,
            vessel_type=vessel_type,
            flag=flag,
            category=category,
            source=source,
            speed_min=speed_min,
            speed_max=speed_max,
            risk_min=risk_min,
            dark_only=dark_only,
            destination_required=destination_required,
            last_seen_minutes=last_seen_minutes,
            limit=limit,
        )
        return {"vessels": vessels, "total": len(vessels)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/risk")
async def risk_leaderboard(limit: int = Query(25, ge=1, le=200)):
    """Return highest-risk active vessels."""
    try:
        return {"vessels": await IntelligenceService().get_risk_leaderboard(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/dark-vessels")
async def dark_vessels(
    threshold_minutes: float = Query(60.0, ge=1.0, le=1440.0),
    limit: int = Query(25, ge=1, le=500),
):
    """Return vessels with significant AIS gaps."""
    try:
        return {
            "vessels": await IntelligenceService().get_dark_vessels(
                threshold_minutes=threshold_minutes,
                limit=limit,
            )
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/ports/congestion")
async def port_congestion(limit: int = Query(20, ge=1, le=200)):
    """Return congestion leaderboard for known ports."""
    try:
        return {"ports": await IntelligenceService().get_port_congestion(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/corridors")
async def corridors(limit: int = Query(20, ge=1, le=200)):
    """Return coarse traffic corridors derived from active traffic."""
    try:
        return {"corridors": await IntelligenceService().get_corridors(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/weather-impact")
async def weather_impact(limit: int = Query(25, ge=1, le=200)):
    """Return vessels most affected by current cached weather conditions."""
    try:
        return {"vessels": await IntelligenceService().get_weather_impact_leaderboard(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/route/{mmsi}")
async def route_prediction(mmsi: int):
    """Return projected route and ETA estimate for a vessel."""
    try:
        return await IntelligenceService().get_route_prediction(mmsi)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/profiles/{mmsi}")
async def get_vessel_profile(mmsi: int, include_related: bool = True):
    """Return ownership and risk profile for a vessel."""
    try:
        return await IntelligenceService().get_vessel_profile(mmsi, include_related=include_related)
    except Exception as exc:
        return {"error": str(exc)}


@router.put("/profiles/{mmsi}")
async def update_vessel_profile(mmsi: int, payload: VesselProfilePayload):
    """Create or update a vessel profile."""
    try:
        return {"profile": await IntelligenceService().upsert_vessel_profile(mmsi, payload.model_dump())}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/military")
async def military_board(limit: int = Query(25, ge=1, le=200)):
    """Return military or naval vessels detected from current vessel metadata."""
    try:
        return {"vessels": await IntelligenceService().get_military_board(limit=limit)}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/external-events")
async def external_events(
    event_type: str | None = None,
    active_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
):
    """Return external intelligence events."""
    try:
        return {
            "events": await IntelligenceService().list_external_events(
                event_type=event_type,
                active_only=active_only,
                limit=limit,
            )
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/external-events")
async def create_external_event(payload: ExternalIntelEventPayload):
    """Create an external intelligence event record."""
    try:
        return {"event": await IntelligenceService().create_external_event(payload.model_dump())}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/external-events/seed-demo")
async def seed_demo_external_events():
    """Seed demo external events so the new intelligence views are populated."""
    try:
        return {"events": await IntelligenceService().seed_demo_external_events()}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/external-events/correlations")
async def external_correlations(
    radius_nm: float = Query(80.0, ge=1.0, le=1000.0),
    hours: int = Query(168, ge=1, le=720),
):
    """Return vessels correlated with nearby external events."""
    try:
        return {
            "correlations": await IntelligenceService().get_external_correlations(
                radius_nm=radius_nm,
                hours=hours,
            )
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/reports/briefing")
async def intelligence_briefing():
    """Return a compact maritime operations briefing."""
    try:
        return await IntelligenceService().get_report()
    except Exception as exc:
        return {"error": str(exc)}
