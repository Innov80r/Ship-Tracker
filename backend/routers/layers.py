"""Layers REST API router — serves GeoJSON data for map overlays."""

import json
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from services.cable_service import CableService
from services.shipping_lane_service import ShippingLaneService
from utils.country_utils import list_country_catalog

router = APIRouter(prefix="/api/layers", tags=["layers"])


@router.get("/cables")
async def get_cables():
    """Get submarine cable GeoJSON."""
    cs = CableService()
    data = await cs.get_cables()
    if data:
        return JSONResponse(content=data)
    return {"error": "Cable data not available. Run fetch first."}


@router.get("/eez")
async def get_eez():
    """Get EEZ boundary GeoJSON."""
    try:
        with open("static/eez_boundaries.geojson", "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except FileNotFoundError:
        return {"type": "FeatureCollection", "features": []}


@router.get("/countries")
async def get_countries():
    """Get the normalized country catalog for search and fallback matching."""
    return {"countries": list_country_catalog()}


@router.get("/shipping-lanes")
async def get_shipping_lanes():
    """Get cached or freshly fetched shipping lane GeoJSON."""
    service = ShippingLaneService()
    data = await service.get_shipping_lanes()
    if data:
        return JSONResponse(content=data)
    return {"type": "FeatureCollection", "features": []}
