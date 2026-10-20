"""Asynchroner Telnet-Client für die Hargassner-Steuerung."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from .parser import Telegram, parse_line

_LOGGER = logging.getLogger(__name__)

READ_TIMEOUT = 30  # Sekunden ohne Daten -> Neuverbindung
CONNECT_TIMEOUT = 10
MAX_BACKOFF = 60


async def probe(host: str, port: int, timeout: float = 15) -> Telegram:
    """Verbindet einmalig und wartet auf eine gültige pm-Zeile (für den Config-Flow)."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port), CONNECT_TIMEOUT
    )
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = await asyncio.wait_for(
                reader.readline(), max(0.1, deadline - time.monotonic())
            )
            if not raw:
                raise ConnectionError("Verbindung vom Kessel geschlossen")
            telegram = parse_line(raw.decode("latin-1", errors="replace"))
            if telegram:
                return telegram
        raise TimeoutError("Keine pm-Zeile empfangen")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


class HargassnerClient:
    """Hält eine dauerhafte Verbindung und verteilt gedrosselt neue Telegramme."""

    def __init__(self, host: str, port: int, update_interval: float) -> None:
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.latest: Telegram | None = None
        self.connected = False
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None
        self._last_push = 0.0

    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return remove

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    def start(self, create_task: Callable[..., asyncio.Task]) -> None:
        self._task = create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _set_connected(self, value: bool) -> None:
        if self.connected != value:
            self.connected = value
            self._notify()

    async def _run(self) -> None:
        backoff = 1
        while True:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), CONNECT_TIMEOUT
                )
                _LOGGER.info("Verbunden mit Hargassner %s:%s", self.host, self.port)
                backoff = 1
                while True:
                    raw = await asyncio.wait_for(reader.readline(), READ_TIMEOUT)
                    if not raw:
                        raise ConnectionError("Verbindung geschlossen")
                    telegram = parse_line(raw.decode("latin-1", errors="replace"))
                    if not telegram:
                        continue
                    self.latest = telegram
                    first = not self.connected
                    self.connected = True
                    now = time.monotonic()
                    if first or now - self._last_push >= self.update_interval:
                        self._last_push = now
                        self._notify()
            except asyncio.CancelledError:
                raise
            except (OSError, asyncio.TimeoutError, ConnectionError) as err:
                _LOGGER.warning(
                    "Hargassner %s: %s, neuer Versuch in %ss", self.host, err, backoff
                )
            finally:
                if writer:
                    writer.close()
            self._set_connected(False)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)
