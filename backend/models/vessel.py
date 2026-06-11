"""
Vessel model — current state of a tracked vessel.
Positions stored as PostGIS Point geometry for spatial queries.
"""

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Vessel(Base):
    """
    SQLAlchemy ORM model representing a vessel and its current state.
    """

    __tablename__ = "vessels"

    mmsi: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    imo: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    call_sign: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vessel_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vessel_type_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flag_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flag_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[Any | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    course: Mapped[float | None] = mapped_column(Float, nullable=True)
    rot: Mapped[float | None] = mapped_column(Float, nullable=True)
    nav_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nav_status_text: Mapped[str | None] = mapped_column(String(100), nullable=True)

    length: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    draught: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_tonnage: Mapped[float | None] = mapped_column(Float, nullable=True)

    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transponder_class: Mapped[str | None] = mapped_column(String(5), nullable=True)

    data_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_vessel_position", "position", postgresql_using="gist"),
        Index("idx_vessel_type", "vessel_type"),
        Index("idx_vessel_active", "is_active"),
        Index("idx_vessel_last_updated", "last_updated"),
    )

    def __repr__(self):
        return f"<Vessel mmsi={self.mmsi} name={self.name}>"
