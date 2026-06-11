"""
PortCall model — records vessel arrivals and departures at ports.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PortCall(Base):
    __tablename__ = "port_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mmsi: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    vessel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    port_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    arrival_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    departure_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrival_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PortCall mmsi={self.mmsi} port={self.port_name}>"
