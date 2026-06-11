"""
Workspace persistence models for operator intelligence state.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Aegis Maritime Command")
    shared_workspace_notes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Shared workspace is local-first in this build. Export the workspace profile to pass it between operators.",
    )
    browser_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    watchlist_entries: Mapped[list["WatchlistEntry"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    saved_searches: Mapped[list["SavedSearch"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    fleets: Mapped[list["Fleet"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    webhook_endpoints: Mapped[list["WebhookEndpoint"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    vessel_notes: Mapped[list["WorkspaceVesselNote"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("workspace_id", "mmsi", name="uq_watchlist_workspace_mmsi"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    mmsi: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="watchlist_entries")


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="saved_searches")


class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="fleets")
    members: Mapped[list["FleetMember"]] = relationship(back_populates="fleet", cascade="all, delete-orphan")


class FleetMember(Base):
    __tablename__ = "fleet_members"
    __table_args__ = (UniqueConstraint("fleet_id", "mmsi", name="uq_fleet_member_mmsi"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fleet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True)
    mmsi: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    fleet: Mapped[Fleet] = relationship(back_populates="members")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False, default="webhook")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signing_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="webhook_endpoints")


class WorkspaceVesselNote(Base):
    __tablename__ = "workspace_vessel_notes"
    __table_args__ = (UniqueConstraint("workspace_id", "mmsi", name="uq_workspace_note_mmsi"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    mmsi: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="vessel_notes")
