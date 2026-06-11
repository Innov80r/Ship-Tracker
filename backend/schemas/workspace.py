"""
Workspace schemas for persisted operator intelligence state.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SavedSearchPayload(BaseModel):
    id: Optional[int | str] = None
    name: str
    filters: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime | str] = None


class FleetMemberPayload(BaseModel):
    id: Optional[int | str] = None
    mmsi: int
    note: Optional[str] = None
    created_at: Optional[datetime | str] = None


class FleetPayload(BaseModel):
    id: Optional[int | str] = None
    name: str
    description: Optional[str] = None
    members: list[FleetMemberPayload] = Field(default_factory=list)
    created_at: Optional[datetime | str] = None


class WebhookEndpointPayload(BaseModel):
    id: Optional[int | str] = None
    name: str
    url: str
    channel: str = "webhook"
    enabled: bool = True
    signing_secret: Optional[str] = None
    created_at: Optional[datetime | str] = None


class NotificationRulePayload(BaseModel):
    id: str
    name: str
    event: str
    channel: str
    severity: Optional[str] = None
    enabled: bool = True


class WorkspaceSnapshotPayload(BaseModel):
    workspace_name: str = "Aegis Maritime Command"
    shared_workspace_notes: str = ""
    browser_notifications_enabled: bool = False
    watchlist_mmsis: list[int] = Field(default_factory=list)
    saved_searches: list[SavedSearchPayload] = Field(default_factory=list)
    fleets: list[FleetPayload] = Field(default_factory=list)
    analyst_notes: dict[str, str] = Field(default_factory=dict)
    notification_rules: list[NotificationRulePayload] = Field(default_factory=list)
    webhook_endpoints: list[WebhookEndpointPayload] = Field(default_factory=list)


class WorkspaceSnapshotResponse(WorkspaceSnapshotPayload):
    workspace_id: int
    workspace_slug: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
