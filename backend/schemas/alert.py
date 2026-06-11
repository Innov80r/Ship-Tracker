"""
Alert Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertCreate(BaseModel):
    alert_type: str
    severity: str = "info"
    mmsi: Optional[int] = None
    vessel_name: Optional[str] = None
    title: str
    message: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[int] = None


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    mmsi: Optional[int] = None
    vessel_name: Optional[str] = None
    title: str
    message: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_read: bool = False
    zone_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertMarkRead(BaseModel):
    is_read: bool = True
