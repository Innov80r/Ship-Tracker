"""Workspace persistence API for operator intelligence state."""

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import delete, select

from database import async_session_factory
from models.workspace import (
    Fleet,
    FleetMember,
    SavedSearch,
    WatchlistEntry,
    WebhookEndpoint,
    Workspace,
    WorkspaceVesselNote,
)
from schemas.workspace import WorkspaceSnapshotPayload

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

DEFAULT_WORKSPACE_SLUG = "default"
DEFAULT_WORKSPACE_NAME = "Aegis Maritime Command"
DEFAULT_WORKSPACE_NOTES = (
    "Shared workspace is local-first in this build. Export the workspace profile to pass it between operators."
)
DEFAULT_NOTIFICATION_RULES = [
    {
        "id": "rule-distress",
        "name": "Distress escalation",
        "event": "distress",
        "channel": "browser",
        "severity": "critical",
        "enabled": True,
    },
    {
        "id": "rule-military",
        "name": "Military motion",
        "event": "military",
        "channel": "browser",
        "severity": "warning",
        "enabled": True,
    },
    {
        "id": "rule-dark",
        "name": "AIS silence",
        "event": "dark-vessel",
        "channel": "browser",
        "severity": "warning",
        "enabled": False,
    },
]


async def _get_or_create_workspace(session) -> Workspace:
    result = await session.execute(
        select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG)
    )
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace

    workspace = Workspace(
        slug=DEFAULT_WORKSPACE_SLUG,
        name=DEFAULT_WORKSPACE_NAME,
        shared_workspace_notes=DEFAULT_WORKSPACE_NOTES,
        browser_notifications_enabled=False,
        notification_rules=DEFAULT_NOTIFICATION_RULES,
    )
    session.add(workspace)
    await session.flush()
    return workspace


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


async def _build_snapshot(session, workspace: Workspace) -> dict:
    watchlist_result = await session.execute(
        select(WatchlistEntry).where(WatchlistEntry.workspace_id == workspace.id)
        .order_by(WatchlistEntry.created_at.desc())
    )
    saved_search_result = await session.execute(
        select(SavedSearch).where(SavedSearch.workspace_id == workspace.id)
        .order_by(SavedSearch.created_at.desc())
    )
    fleet_result = await session.execute(
        select(Fleet).where(Fleet.workspace_id == workspace.id)
        .order_by(Fleet.created_at.asc())
    )
    webhook_result = await session.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace.id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    note_result = await session.execute(
        select(WorkspaceVesselNote).where(WorkspaceVesselNote.workspace_id == workspace.id)
    )

    watchlist_entries = watchlist_result.scalars().all()
    saved_searches = saved_search_result.scalars().all()
    fleets = fleet_result.scalars().all()
    webhooks = webhook_result.scalars().all()
    notes = note_result.scalars().all()

    fleet_ids = [fleet.id for fleet in fleets]
    fleet_members_map: dict[int, list[dict]] = {fleet_id: [] for fleet_id in fleet_ids}
    if fleet_ids:
        member_result = await session.execute(
            select(FleetMember)
            .where(FleetMember.fleet_id.in_(fleet_ids))
            .order_by(FleetMember.created_at.asc())
        )
        for member in member_result.scalars().all():
            fleet_members_map.setdefault(member.fleet_id, []).append(
                {
                    "id": member.id,
                    "mmsi": member.mmsi,
                    "note": member.note,
                    "created_at": member.created_at,
                }
            )

    return {
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "workspace_name": workspace.name,
        "shared_workspace_notes": workspace.shared_workspace_notes,
        "browser_notifications_enabled": workspace.browser_notifications_enabled,
        "notification_rules": workspace.notification_rules or [],
        "watchlist_mmsis": [entry.mmsi for entry in watchlist_entries],
        "saved_searches": [
            {
                "id": entry.id,
                "name": entry.name,
                "filters": entry.filters or {},
                "created_at": entry.created_at,
            }
            for entry in saved_searches
        ],
        "fleets": [
            {
                "id": fleet.id,
                "name": fleet.name,
                "description": fleet.description,
                "members": fleet_members_map.get(fleet.id, []),
                "created_at": fleet.created_at,
            }
            for fleet in fleets
        ],
        "analyst_notes": {
            str(note.mmsi): note.note
            for note in notes
            if note.note
        },
        "webhook_endpoints": [
            {
                "id": entry.id,
                "name": entry.name,
                "url": entry.url,
                "channel": entry.channel,
                "enabled": entry.enabled,
                "signing_secret": entry.signing_secret,
                "created_at": entry.created_at,
            }
            for entry in webhooks
        ],
        "created_at": workspace.created_at,
        "updated_at": workspace.updated_at,
    }


async def _replace_snapshot(session, workspace: Workspace, payload: WorkspaceSnapshotPayload):
    workspace.name = payload.workspace_name or DEFAULT_WORKSPACE_NAME
    workspace.shared_workspace_notes = payload.shared_workspace_notes or DEFAULT_WORKSPACE_NOTES
    workspace.browser_notifications_enabled = payload.browser_notifications_enabled
    workspace.notification_rules = [rule.model_dump() for rule in payload.notification_rules]

    await session.execute(
        delete(WatchlistEntry).where(WatchlistEntry.workspace_id == workspace.id)
    )
    await session.execute(
        delete(SavedSearch).where(SavedSearch.workspace_id == workspace.id)
    )
    await session.execute(
        delete(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace.id)
    )
    await session.execute(
        delete(WorkspaceVesselNote).where(WorkspaceVesselNote.workspace_id == workspace.id)
    )

    fleet_result = await session.execute(
        select(Fleet.id).where(Fleet.workspace_id == workspace.id)
    )
    fleet_ids = fleet_result.scalars().all()
    if fleet_ids:
        await session.execute(
            delete(FleetMember).where(FleetMember.fleet_id.in_(fleet_ids))
        )
    await session.execute(
        delete(Fleet).where(Fleet.workspace_id == workspace.id)
    )

    await session.flush()

    watchlist_values = sorted({mmsi for mmsi in payload.watchlist_mmsis if mmsi})
    for mmsi in watchlist_values:
        session.add(WatchlistEntry(workspace_id=workspace.id, mmsi=mmsi))

    for search in payload.saved_searches:
        session.add(
            SavedSearch(
                workspace_id=workspace.id,
                name=search.name,
                filters=search.filters or {},
                created_at=_parse_datetime(search.created_at) or datetime.utcnow(),
            )
        )

    for endpoint in payload.webhook_endpoints:
        session.add(
            WebhookEndpoint(
                workspace_id=workspace.id,
                name=endpoint.name,
                url=endpoint.url,
                channel=endpoint.channel,
                enabled=endpoint.enabled,
                signing_secret=endpoint.signing_secret,
                created_at=_parse_datetime(endpoint.created_at) or datetime.utcnow(),
            )
        )

    for mmsi, note in payload.analyst_notes.items():
        if not note:
            continue
        try:
            note_mmsi = int(mmsi)
        except (TypeError, ValueError):
            continue
        session.add(
            WorkspaceVesselNote(
                workspace_id=workspace.id,
                mmsi=note_mmsi,
                note=note,
            )
        )

    for fleet in payload.fleets:
        fleet_row = Fleet(
            workspace_id=workspace.id,
            name=fleet.name,
            description=fleet.description,
            created_at=_parse_datetime(fleet.created_at) or datetime.utcnow(),
        )
        session.add(fleet_row)
        await session.flush()

        seen_members = set()
        for member in fleet.members:
            if member.mmsi in seen_members:
                continue
            seen_members.add(member.mmsi)
            session.add(
                FleetMember(
                    fleet_id=fleet_row.id,
                    mmsi=member.mmsi,
                    note=member.note,
                    created_at=_parse_datetime(member.created_at) or datetime.utcnow(),
                )
            )

    workspace.updated_at = datetime.utcnow()
    await session.flush()


@router.get("")
async def get_workspace_snapshot():
    """Return the persisted default workspace snapshot."""
    try:
        async with async_session_factory() as session:
            workspace = await _get_or_create_workspace(session)
            await session.commit()
            return await _build_snapshot(session, workspace)
    except Exception as exc:
        return {"error": str(exc)}


@router.put("")
async def save_workspace_snapshot(payload: WorkspaceSnapshotPayload):
    """Replace the persisted default workspace snapshot."""
    try:
        async with async_session_factory() as session:
            workspace = await _get_or_create_workspace(session)
            await _replace_snapshot(session, workspace, payload)
            await session.commit()
            return await _build_snapshot(session, workspace)
    except Exception as exc:
        return {"error": str(exc)}
