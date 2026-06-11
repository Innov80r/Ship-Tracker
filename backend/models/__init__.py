"""Models package — import all models so Base.metadata picks them up."""

from models.vessel import Vessel
from models.vessel_history import VesselHistory
from models.port import Port
from models.port_call import PortCall
from models.incident import Incident
from models.alert import Alert
from models.zone import Zone
from models.workspace import (
    Workspace,
    WatchlistEntry,
    SavedSearch,
    Fleet,
    FleetMember,
    WebhookEndpoint,
    WorkspaceVesselNote,
)
from models.intelligence import (
    NotificationDelivery,
    VesselProfile,
    ExternalIntelEvent,
)

__all__ = [
    "Vessel",
    "VesselHistory",
    "Port",
    "PortCall",
    "Incident",
    "Alert",
    "Zone",
    "Workspace",
    "WatchlistEntry",
    "SavedSearch",
    "Fleet",
    "FleetMember",
    "WebhookEndpoint",
    "WorkspaceVesselNote",
    "NotificationDelivery",
    "VesselProfile",
    "ExternalIntelEvent",
]
