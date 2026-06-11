"""
Zone Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ZoneCreate(BaseModel):
    name: str
    zone_type: str = "monitoring"
    geometry: dict  # GeoJSON geometry object
    alert_on_entry: bool = True
    alert_on_exit: bool = False
    description: Optional[str] = None


class ZoneResponse(BaseModel):
    id: int
    name: str
    zone_type: str
    geometry: Optional[dict] = None
    alert_on_entry: bool = True
    alert_on_exit: bool = False
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_type: Optional[str] = None
    geometry: Optional[dict] = None
    alert_on_entry: Optional[bool] = None
    alert_on_exit: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
