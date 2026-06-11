"""
AISStream.io WebSocket client — primary real-time global AIS source.
Connects to wss://stream.aisstream.io/v0/stream and decodes position reports.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from config import get_settings
from utils.ais_codes import get_vessel_type_name, get_nav_status_text
from utils.flag_utils import get_flag_from_mmsi

logger = logging.getLogger("aisstream")
settings = get_settings()


class AISStreamClient:
    """
    WebSocket client for aisstream.io — global real-time AIS.
    Subscribes with a world-wide bounding box and streams vessel updates.
    """

    WS_URL = "wss://stream.aisstream.io/v0/stream"

    def __init__(self, on_message: Callable[[dict[str, Any]], Awaitable[None]]):
        self.on_message = on_message  # async callback(vessel_dict)
        self._running = False
        self._ws = None
        self._reconnect_delay = 1  # exponential backoff start
        self._last_message_at: datetime | None = None

    async def start(self):
        """Start the WebSocket listener with auto-reconnection."""
        if not settings.AISSTREAM_API_KEY:
            logger.warning("AISSTREAM_API_KEY not set — skipping AISStream source")
            return
        self._running = True
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"AISStream connection error: {e}")
            if self._running:
                delay = min(self._reconnect_delay, settings.AISSTREAM_MAX_RECONNECT_SECONDS)
                logger.info(f"AISStream reconnecting in {delay}s...")
                await asyncio.sleep(delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, settings.AISSTREAM_MAX_RECONNECT_SECONDS)

    async def _connect(self):
        """Establish connection and process messages."""
        subscription = {
            "APIKey": settings.AISSTREAM_API_KEY,
            "BoundingBoxes": [[[-90, -180], [90, 180]]],
            "FilterMessageTypes": [
                "PositionReport",
                "ShipStaticData",
                "StandardSearchAndRescueAircraftReport",
            ],
        }

        async with websockets.connect(
            self.WS_URL,
            ping_interval=None,
            close_timeout=10,
            open_timeout=30,
            max_size=2**20,
        ) as ws:
            self._ws = ws
            self._reconnect_delay = 1  # reset on successful connect
            self._last_message_at = datetime.now(timezone.utc)
            logger.info("AISStream connected — sending subscription")
            await ws.send(json.dumps(subscription))

            while self._running:
                try:
                    raw = await asyncio.wait_for(
                        ws.recv(),
                        timeout=settings.AISSTREAM_IDLE_RESTART_SECONDS,
                    )
                except asyncio.TimeoutError as exc:
                    idle_for = settings.AISSTREAM_IDLE_RESTART_SECONDS
                    if self._last_message_at is not None:
                        idle_for = int((datetime.now(timezone.utc) - self._last_message_at).total_seconds())
                    if not await self._probe_connection(ws):
                        raise RuntimeError(
                            f"AISStream idle for {idle_for}s and connection probe failed"
                        ) from exc
                    logger.warning(
                        "AISStream idle for %ss; connection probe succeeded, waiting for new data",
                        idle_for,
                    )
                    continue
                except ConnectionClosed:
                    raise

                if not self._running:
                    break

                self._last_message_at = datetime.now(timezone.utc)
                try:
                    msg = json.loads(raw)
                    vessel = self._parse_message(msg)
                    if vessel:
                        await self.on_message(vessel)
                except json.JSONDecodeError:
                    logger.debug("AISStream: non-JSON message skipped")
                except Exception as e:
                    logger.error(f"AISStream parse error: {e}")

    async def _probe_connection(self, ws) -> bool:
        """Ping the server when the stream goes idle before forcing a reconnect."""
        try:
            pong_waiter = await ws.ping()
            await asyncio.wait_for(
                pong_waiter,
                timeout=settings.AISSTREAM_PROBE_TIMEOUT_SECONDS,
            )
            return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("AISStream connection probe failed: %s", exc)
            return False

    def _parse_message(self, msg: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Parse an AISStream JSON message into a normalized vessel dict."""
        msg_type = msg.get("MessageType", "")
        meta = msg.get("MetaData", {})
        mmsi = meta.get("MMSI")
        if not mmsi:
            return None

        vessel: dict[str, Any] = {
            "mmsi": int(mmsi),
            "data_source": "aisstream",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        # Metadata fields
        if meta.get("ShipName"):
            vessel["name"] = meta["ShipName"].strip()
        if meta.get("latitude") is not None:
            vessel["latitude"] = float(meta["latitude"])
        if meta.get("longitude") is not None:
            vessel["longitude"] = float(meta["longitude"])

        # Flag from MMSI
        country, iso = get_flag_from_mmsi(vessel["mmsi"])
        vessel["flag_country"] = country
        vessel["flag_code"] = iso

        # Parse based on message type
        if msg_type == "PositionReport":
            report = msg.get("Message", {}).get("PositionReport", {})
            if report:
                vessel.update(self._parse_position_report(report))
        elif msg_type == "ShipStaticData":
            static = msg.get("Message", {}).get("ShipStaticData", {})
            if static:
                vessel.update(self._parse_static_data(static))
        elif msg_type == "StandardSearchAndRescueAircraftReport":
            sar = msg.get("Message", {}).get("StandardSearchAndRescueAircraftReport", {})
            if sar:
                vessel.update(self._parse_sar(sar))

        return vessel

    def _parse_position_report(self, report: dict[str, Any]) -> dict[str, Any]:
        """Extract fields from a PositionReport."""
        data: dict[str, Any] = {}
        if "Latitude" in report:
            data["latitude"] = float(report["Latitude"])
        if "Longitude" in report:
            data["longitude"] = float(report["Longitude"])
        if "Sog" in report:
            data["speed"] = float(report["Sog"])
        if "TrueHeading" in report:
            hdg = int(report["TrueHeading"])
            if hdg != 511:  # 511 = not available
                data["heading"] = float(hdg)
        if "Cog" in report:
            data["course"] = float(report["Cog"])
        if "RateOfTurn" in report:
            data["rot"] = float(report["RateOfTurn"])
        if "NavigationalStatus" in report:
            ns = int(report["NavigationalStatus"])
            data["nav_status"] = ns
            data["nav_status_text"] = get_nav_status_text(ns)
        return data

    def _parse_static_data(self, static: dict[str, Any]) -> dict[str, Any]:
        """Extract fields from ShipStaticData (message type 5)."""
        data: dict[str, Any] = {}
        if "ImoNumber" in static:
            imo = int(static["ImoNumber"])
            if imo > 0:
                data["imo"] = imo
        if "CallSign" in static:
            data["call_sign"] = static["CallSign"].strip()
        if "Name" in static:
            data["name"] = static["Name"].strip()
        if "Type" in static:
            vtype = int(static["Type"])
            data["vessel_type"] = vtype
            data["vessel_type_name"] = get_vessel_type_name(vtype)
        if "Dimension" in static:
            dim = static["Dimension"]
            a = dim.get("A", 0)
            b = dim.get("B", 0)
            c = dim.get("C", 0)
            d = dim.get("D", 0)
            if a + b > 0:
                data["length"] = float(a + b)
            if c + d > 0:
                data["width"] = float(c + d)
        if "MaximumStaticDraught" in static:
            data["draught"] = float(static["MaximumStaticDraught"]) / 10.0
        if "Destination" in static:
            data["destination"] = static["Destination"].strip()
        if "Eta" in static:
            eta = static["Eta"]
            if isinstance(eta, dict):
                from utils.time_utils import parse_ais_eta
                parsed = parse_ais_eta(
                    eta.get("Month", 0), eta.get("Day", 0),
                    eta.get("Hour", 0), eta.get("Minute", 0),
                )
                if parsed:
                    data["eta"] = parsed.isoformat()
        return data

    def _parse_sar(self, sar: dict[str, Any]) -> dict[str, Any]:
        """Parse SAR aircraft report."""
        data: dict[str, Any] = {"vessel_type_name": "SAR Aircraft"}
        if "Latitude" in sar:
            data["latitude"] = float(sar["Latitude"])
        if "Longitude" in sar:
            data["longitude"] = float(sar["Longitude"])
        if "Sog" in sar:
            data["speed"] = float(sar["Sog"])
        if "Cog" in sar:
            data["course"] = float(sar["Cog"])
        return data

    async def stop(self):
        """Stop the WebSocket client."""
        self._running = False
        if self._ws:
            await self._ws.close()
            logger.info("AISStream disconnected")
