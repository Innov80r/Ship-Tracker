"""
Port Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PortResponse(BaseModel):
    id: int
    name: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    port_type: Optional[str] = None
    un_locode: Optional[str] = None
    geofence_radius_nm: Optional[float] = 2.0
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class PortCallResponse(BaseModel):
    id: int
    mmsi: int
    vessel_name: Optional[str] = None
    port_id: Optional[int] = None
    port_name: Optional[str] = None
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    arrival_speed: Optional[float] = None

    model_config = {"from_attributes": True}
