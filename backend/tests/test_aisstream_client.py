"""Unit tests for AISStream client helpers."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.sources.aisstream import AISStreamClient


async def _noop(_: dict) -> None:
    return None


class AISStreamClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_probe_connection_returns_true_when_pong_arrives(self):
        client = AISStreamClient(_noop)

        class _HealthyWebSocket:
            @staticmethod
            async def ping():
                async def _pong():
                    return None

                return _pong()

        self.assertTrue(await client._probe_connection(_HealthyWebSocket()))

    async def test_probe_connection_returns_false_when_ping_fails(self):
        client = AISStreamClient(_noop)

        class _BrokenWebSocket:
            @staticmethod
            async def ping():
                raise RuntimeError("socket closed")

        self.assertFalse(await client._probe_connection(_BrokenWebSocket()))


if __name__ == "__main__":
    unittest.main()
