"""
Analytics Pydantic schemas for dashboard/statistics responses.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VesselTypeCount(BaseModel):
    vessel_type_name: str
    count: int


class FlagCount(BaseModel):
    flag_country: str
    count: int


class NavStatusCount(BaseModel):
    nav_status_text: str
    count: int


class PortTrafficEntry(BaseModel):
    port_name: str
    arrivals: int = 0
    departures: int = 0
    vessel_count: int = 0


class DataSourceCount(BaseModel):
    data_source: str
    count: int


class DashboardStats(BaseModel):
    total_vessels: int = 0
    active_vessels: int = 0
    vessels_underway: int = 0
    vessels_anchored: int = 0
    vessels_moored: int = 0
    vessels_in_distress: int = 0
    active_incidents: int = 0
    unread_alerts: int = 0
    type_breakdown: list[VesselTypeCount] = []
    flag_breakdown: list[FlagCount] = []
    status_breakdown: list[NavStatusCount] = []
    source_breakdown: list[DataSourceCount] = []


class PortDashboard(BaseModel):
    port_name: str
    vessel_count: int = 0
    arrivals_24h: int = 0
    departures_24h: int = 0
    avg_dwell_hours: Optional[float] = None
    congestion_level: str = "low"  # low, medium, high, critical
    type_breakdown: list[VesselTypeCount] = []
