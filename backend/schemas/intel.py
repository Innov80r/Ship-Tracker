"""
Schemas for notification and intelligence APIs.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class VesselProfilePayload(BaseModel):
    owner_name: Optional[str] = None
    operator_name: Optional[str] = None
    manager_name: Optional[str] = None
    country_of_control: Optional[str] = None
    sanctions_status: Optional[str] = None
    vessel_classification: Optional[str] = None
    profile_source: Optional[str] = None
    risk_flags: list[str] = Field(default_factory=list)
    intelligence_notes: Optional[str] = None
    known_aliases: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    last_enriched_at: Optional[datetime | str] = None


class ExternalIntelEventPayload(BaseModel):
    event_type: str
    severity: str = "info"
    title: str
    summary: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    region: Optional[str] = None
    related_mmsi: Optional[int] = None
    related_flag: Optional[str] = None
    related_owner: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    occurred_at: Optional[datetime | str] = None


class NotificationTestPayload(BaseModel):
    channel: str = "webhook"
    target: str
    event_type: str = "test"
    title: str = "Sea Tracker test"
    message: str = "Test notification from Sea Tracker."
    severity: str = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)
