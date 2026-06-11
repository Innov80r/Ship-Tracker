"""
Vessel Pydantic schemas for API request/response.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VesselBase(BaseModel):
    mmsi: int
    imo: Optional[int] = None
    name: Optional[str] = None
    call_sign: Optional[str] = None
    vessel_type: Optional[int] = None
    vessel_type_name: Optional[str] = None
    flag_country: Optional[str] = None
    flag_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    course: Optional[float] = None
    rot: Optional[float] = None
    nav_status: Optional[int] = None
    nav_status_text: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draught: Optional[float] = None
    gross_tonnage: Optional[float] = None
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    transponder_class: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None
    is_active: Optional[bool] = True


class VesselResponse(VesselBase):
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VesselUpdate(BaseModel):
    """Partial update from an AIS source."""
    mmsi: int
    imo: Optional[int] = None
    name: Optional[str] = None
    call_sign: Optional[str] = None
    vessel_type: Optional[int] = None
    vessel_type_name: Optional[str] = None
    flag_country: Optional[str] = None
    flag_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    course: Optional[float] = None
    rot: Optional[float] = None
    nav_status: Optional[int] = None
    nav_status_text: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draught: Optional[float] = None
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    transponder_class: Optional[str] = None
    data_source: Optional[str] = None


class VesselHistoryPoint(BaseModel):
    mmsi: int
    latitude: float
    longitude: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    course: Optional[float] = None
    nav_status: Optional[int] = None
    data_source: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class VesselSearchResult(BaseModel):
    mmsi: int
    name: Optional[str] = None
    vessel_type_name: Optional[str] = None
    flag_country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    is_active: Optional[bool] = True

    model_config = {"from_attributes": True}
