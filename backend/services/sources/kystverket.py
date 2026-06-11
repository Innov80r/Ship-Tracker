"""
Kystverket AIS TCP client — Norway / North Sea real-time AIS.
Connects to the open AIS data feed at 153.44.253.27:5631 (IEC 62320-1 NMEA format).
Falls back to BarentsWatch open AIS REST API if TCP fails.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable

from utils.ais_codes import get_vessel_type_name, get_nav_status_text
from utils.flag_utils import get_flag_from_mmsi

logger = logging.getLogger("kystverket")
VesselUpdate = dict[str, Any]


class KystverketClient:
    """
    TCP client for Norwegian Coastal Administration open AIS data.
    Free, no API key, receives raw NMEA AIS sentences.
    Falls back to BarentsWatch REST if TCP is unavailable.
    """

    TCP_HOST = "153.44.253.27"
    TCP_PORT = 5631
    BARENTSWATCH_URL = "https://live.ais.barentswatch.no/v1/latest/combined"

    def __init__(self, on_message: Callable[[VesselUpdate], Awaitable[None]]):
        self.on_message = on_message
        self._running = False
        self._reconnect_delay = 1

    async def start(self):
        """Start AIS listener with auto-reconnection."""
        self._running = True
        while self._running:
            try:
                await self._connect_tcp()
            except Exception as e:
                logger.error("Kystverket TCP error: %s", e)
            if self._running:
                # Try REST fallback
                try:
                    await self._poll_rest()
                except Exception as e:
                    logger.debug("Kystverket REST fallback error: %s", e)

                delay = min(self._reconnect_delay, 120)
                logger.info("Kystverket reconnecting in %ss...", delay)
                await asyncio.sleep(delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 120)

    async def _connect_tcp(self):
        """Connect to Kystverket's raw TCP AIS feed."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.TCP_HOST, self.TCP_PORT),
            timeout=15,
        )
        self._reconnect_delay = 1
        logger.info("Kystverket TCP connected to %s:%s", self.TCP_HOST, self.TCP_PORT)

        try:
            while self._running:
                line = await asyncio.wait_for(reader.readline(), timeout=60)
                if not line:
                    break
                try:
                    raw = line.decode("ascii", errors="ignore").strip()
                    if raw.startswith("!"):
                        vessel = self._parse_nmea(raw)
                        if vessel:
                            await self.on_message(vessel)
                except Exception as e:
                    logger.debug("Kystverket parse error: %s", e)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def _parse_nmea(self, raw: str) -> VesselUpdate | None:
        """
        Parse NMEA AIS sentence. Uses pyais if available, otherwise
        extracts basic data from common sentence types.
        """
        try:
            from pyais import decode as pyais_decode

            decoded = pyais_decode(raw.encode()).asdict()

            mmsi = decoded.get("mmsi")
            if not mmsi:
                return None

            vessel: VesselUpdate = {
                "mmsi": int(mmsi),
                "data_source": "kystverket",
            }

            lat = self._as_float(decoded.get("lat"))
            if lat is not None and lat != 91.0:
                vessel["latitude"] = lat
            lon = self._as_float(decoded.get("lon"))
            if lon is not None and lon != 181.0:
                vessel["longitude"] = lon
            speed = self._as_float(decoded.get("speed"))
            if speed is not None:
                vessel["speed"] = speed
            heading = self._as_int(decoded.get("heading"))
            if heading is not None and heading != 511:
                vessel["heading"] = float(heading)
            course = self._as_float(decoded.get("course"))
            if course is not None:
                vessel["course"] = course
            turn = self._as_float(decoded.get("turn"))
            if turn is not None:
                vessel["rot"] = turn
            status = self._as_int(decoded.get("status"))
            if status is not None:
                ns = status
                vessel["nav_status"] = ns
                vessel["nav_status_text"] = get_nav_status_text(ns)
            ship_name = self._as_text(decoded.get("shipname"))
            if ship_name:
                vessel["name"] = ship_name
            imo = self._as_int(decoded.get("imo"))
            if imo:
                vessel["imo"] = imo
            call_sign = self._as_text(decoded.get("callsign"))
            if call_sign:
                vessel["call_sign"] = call_sign
            ship_type = self._as_int(decoded.get("shiptype"))
            if ship_type is not None:
                vtype = ship_type
                vessel["vessel_type"] = vtype
                vessel["vessel_type_name"] = get_vessel_type_name(vtype)
            destination = self._as_text(decoded.get("destination"))
            if destination:
                vessel["destination"] = destination

            # Dimensions
            to_bow = self._as_float(decoded.get("to_bow")) or 0.0
            to_stern = self._as_float(decoded.get("to_stern")) or 0.0
            to_port = self._as_float(decoded.get("to_port")) or 0.0
            to_starboard = self._as_float(decoded.get("to_starboard")) or 0.0
            if to_bow + to_stern > 0:
                vessel["length"] = float(to_bow + to_stern)
            if to_port + to_starboard > 0:
                vessel["width"] = float(to_port + to_starboard)
            draught = self._as_float(decoded.get("draught"))
            if draught is not None:
                vessel["draught"] = draught / 10.0

            # Flag from MMSI
            country, iso = get_flag_from_mmsi(vessel["mmsi"])
            vessel["flag_country"] = country
            vessel["flag_code"] = iso

            if "latitude" in vessel and "longitude" in vessel:
                return vessel
            return None

        except ImportError:
            # pyais not installed — skip NMEA decoding
            logger.debug("pyais not installed, skipping NMEA decode")
            return None
        except Exception:
            return None

    async def _poll_rest(self):
        """Fallback: poll BarentsWatch open AIS REST endpoint."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(self.BARENTSWATCH_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    vessels: list[dict[str, Any]] = data if isinstance(data, list) else data.get("data", [])
                    count: int = 0
                    for v in vessels[:200]:  # Limit batch size
                        vessel = self._parse_barentswatch(v)
                        if vessel:
                            await self.on_message(vessel)
                            count += 1
                    if count > 0:
                        logger.info("Kystverket REST: processed %s vessels", count)
                else:
                    logger.debug("BarentsWatch HTTP %s", resp.status_code)
        except Exception as e:
            logger.debug("BarentsWatch poll error: %s", e)

    def _parse_barentswatch(self, v: dict[str, Any]) -> VesselUpdate | None:
        """Parse a BarentsWatch vessel entry."""
        mmsi = self._as_int(v.get("mmsi"))
        if not mmsi:
            return None

        vessel: VesselUpdate = {
            "mmsi": mmsi,
            "data_source": "kystverket",
        }

        latitude = self._as_float(v.get("latitude"))
        if latitude is not None:
            vessel["latitude"] = latitude
        longitude = self._as_float(v.get("longitude"))
        if longitude is not None:
            vessel["longitude"] = longitude
        speed = self._as_float(v.get("speedOverGround"))
        if speed is not None:
            vessel["speed"] = speed
        course = self._as_float(v.get("courseOverGround"))
        if course is not None:
            vessel["course"] = course
        heading = self._as_int(v.get("trueHeading"))
        if heading is not None and heading != 511:
            vessel["heading"] = float(heading)
        nav_status = self._as_int(v.get("navigationalStatus"))
        if nav_status is not None:
            ns = nav_status
            vessel["nav_status"] = ns
            vessel["nav_status_text"] = get_nav_status_text(ns)
        name = self._as_text(v.get("name"))
        if name:
            vessel["name"] = name
        ship_type = self._as_int(v.get("shipType"))
        if ship_type is not None:
            vtype = ship_type
            vessel["vessel_type"] = vtype
            vessel["vessel_type_name"] = get_vessel_type_name(vtype)

        country, iso = get_flag_from_mmsi(vessel["mmsi"])
        vessel["flag_country"] = country
        vessel["flag_code"] = iso

        if "latitude" in vessel and "longitude" in vessel:
            return vessel
        return None

    async def stop(self):
        """Stop the client."""
        self._running = False
        logger.info("Kystverket AIS disconnected")

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        return text or None
