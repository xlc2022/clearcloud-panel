"""Reachability of the services shown in the sidebar footer."""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from .integrations import REGISTRY, TestResult
from .store import Store

log = logging.getLogger(__name__)

SERVICES = [
    ("home_assistant", "Home Assistant"),
    ("grafana", "Grafana"),
    ("mqtt", "MQTT"),
    ("tailscale", "Tailscale"),
]
INTERVAL_SECONDS = 60


class StatusMonitor:
    def __init__(self, store: Store):
        self.store = store
        self._latest: dict[str, dict[str, Any]] = {}
        self._task: asyncio.Task | None = None

    def note(self, kind: str, result: TestResult) -> None:
        self._latest[kind] = {
            "state": "ok" if result.ok else "error",
            "message": result.message,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    async def check(self, kind: str) -> None:
        integration_id = self.store.first_of_kind(kind)
        if integration_id is None or kind not in REGISTRY:
            self._latest.pop(kind, None)
            return
        _, config, secrets = self.store.resolved(integration_id)
        result = await REGISTRY[kind].test(config, secrets)
        self.store.record_test(integration_id, result)
        self.note(kind, result)

    async def check_all(self) -> None:
        await asyncio.gather(*(self.check(key) for key, _ in SERVICES), return_exceptions=True)

    def snapshot(self) -> list[dict[str, Any]]:
        out = []
        for key, label in SERVICES:
            entry = {
                "key": key,
                "label": label,
                "state": "unconfigured",
                "message": None,
                "checked_at": None,
            }
            if self.store.first_of_kind(key) is not None:
                entry.update(
                    self._latest.get(key) or {"state": "unknown", "message": "Not checked yet"}
                )
            elif key == "tailscale":
                entry["message"] = "Not set up yet"
            else:
                entry["message"] = "Add it on the Integrations page"
            out.append(entry)
        return out

    async def _run(self) -> None:
        while True:
            try:
                await self.check_all()
            except Exception:
                log.exception("Status check failed")
            await asyncio.sleep(INTERVAL_SECONDS)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
