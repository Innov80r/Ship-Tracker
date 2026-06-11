"""Ports REST API router."""

from fastapi import APIRouter, Query
from services.port_service import PortService

router = APIRouter(prefix="/api/ports", tags=["ports"])


@router.get("")
async def get_ports(
    search: str | None = None,
    country: str | None = None,
    limit: int | None = Query(None, ge=1, le=10000),
):
    """Get cached ports, optionally filtered."""
    ps = PortService()
    ports = await ps.get_all_ports(search=search, country=country, limit=limit)
    return {"ports": ports, "total": len(ports)}


@router.get("/search")
async def search_ports(q: str = Query(..., min_length=1)):
    """Search ports by name."""
    ps = PortService()
    results = await ps.search_ports(q)
    return {"results": results}
