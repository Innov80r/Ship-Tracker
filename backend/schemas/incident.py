"""
Incident Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IncidentCreate(BaseModel):
    mmsi: int
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    incident_type: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed_at_incident: Optional[float] = None
    heading_at_incident: Optional[float] = None


class IncidentResponse(BaseModel):
    id: int
    mmsi: int
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    incident_type: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed_at_incident: Optional[float] = None
    heading_at_incident: Optional[float] = None
    is_active: bool = True
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    detected_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentResolve(BaseModel):
    is_resolved: bool = True
