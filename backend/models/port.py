"""
Port model — world port/terminal data fetched from Overpass API.
"""

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[Any | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    port_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    un_locode: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    osm_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    geofence_radius_nm: Mapped[float] = mapped_column(Float, default=2.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_refreshed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Port name={self.name} country={self.country}>"
