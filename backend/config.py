"""
Sea Tracker — Central Configuration
Loads all settings from environment variables via pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:yourpassword@localhost:5432/seatracker"
    DATABASE_SYNC_URL: str = "postgresql://postgres:yourpassword@localhost:5432/seatracker"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── AIS Data Sources ──────────────────────────────────────
    AISSTREAM_API_KEY: str = ""
    AISSTREAM_IDLE_RESTART_SECONDS: int = 90
    AISSTREAM_PROBE_TIMEOUT_SECONDS: int = 15
    AISSTREAM_MAX_RECONNECT_SECONDS: int = 120
    GFW_API_KEY: str = ""
    CMEMS_USERNAME: str = ""
    CMEMS_PASSWORD: str = ""

    # ── Vessel Tracking ───────────────────────────────────────
    VESSEL_TIMEOUT_MINUTES: int = 30
    LIVE_FEED_WINDOW_MINUTES: float = 5.0
    SOURCE_STALE_SECONDS: int = 180
    HISTORY_RETENTION_DAYS: int = 30
    COLLISION_ALERT_DISTANCE_NM: float = 2.0

    # ── Alerts ────────────────────────────────────────────────
    ALERT_SOUND_ENABLED: bool = True
    VESSEL_DARK_MINUTES: int = 5

    # ── Notifications ─────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    # ── Polling Intervals (seconds) ──────────────────────────
    NOAA_POLL_INTERVAL: int = 60
    GFW_POLL_INTERVAL: int = 300
    WEATHER_POLL_INTERVAL: int = 900
    OCEAN_POLL_INTERVAL: int = 3600
    TIDE_POLL_INTERVAL: int = 1800
    PORT_REFRESH_INTERVAL: int = 604800  # 1 week

    # ── Server ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = {
        "env_file": BASE_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
