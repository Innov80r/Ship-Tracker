"""
AIS NMEA decoder — wrapper for pyais library.
Used to decode raw NMEA sentences from Kystverket and other raw feeds.
"""

import logging
from typing import Optional

logger = logging.getLogger("ais_decoder")


def decode_nmea(sentence: str) -> Optional[dict]:
    """
    Decode a single NMEA AIS sentence using pyais.
    Returns a dict of decoded fields or None on failure.
    """
    try:
        from pyais import decode as pyais_decode
        decoded = pyais_decode(sentence)
        if decoded:
            msg = decoded.asdict() if hasattr(decoded, "asdict") else {}
            return msg
    except Exception as e:
        logger.debug(f"NMEA decode error: {e}")
    return None


def decode_nmea_batch(sentences: list[str]) -> list[dict]:
    """Decode a batch of NMEA sentences, skipping failures."""
    results = []
    for s in sentences:
        decoded = decode_nmea(s)
        if decoded:
            results.append(decoded)
    return results
