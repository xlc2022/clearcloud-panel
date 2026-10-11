"""Settings and integrations persisted in SQLite, secrets encrypted."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from .crypto import SecretBox
from .integrations import REGISTRY, TestResult


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class Invalid(Exception):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, db: sqlite3.Connection, box: SecretBox):
        self.db = db
        self.box = box

    # settings ---------------------------------------------------------------

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    @property
    def setup_complete(self) -> bool:
        return self.get_setting("setup_complete") == "1"

    # users ------------------------------------------------------------------

    def password_hash(self, username: str) -> str | None:
        row = self.db.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        return row["password_hash"] if row else None

    def create_user(self, username: str, password_hash: str) -> None:
        try:
            self.db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, now()),
            )
        except sqlite3.IntegrityError as exc:
            raise Conflict("User already exists") from exc

    # integrations -----------------------------------------------------------

    def _public(self, row: sqlite3.Row) -> dict[str, Any]:
        t = REGISTRY.get(row["kind"])
        stored = self.box.open(row["secrets"])
        secret_keys = t.secret_keys if t else set(stored)
        return {
            "id": row["id"],
            "kind": row["kind"],
            "name": row["name"],
            "enabled": bool(row["enabled"]),
            "config": json.loads(row["config"]),
            "secrets_set": {k: bool(stored.get(k)) for k in secret_keys},
            "last_test": json.loads(row["last_test"]) if row["last_test"] else None,
        }

    def _row(self, integration_id: int) -> sqlite3.Row:
        row = self.db.execute(
            "SELECT * FROM integrations WHERE id = ?", (integration_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"No integration {integration_id}")
        return row

    def list_integrations(self) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT * FROM integrations ORDER BY kind, name, id").fetchall()
        return [self._public(r) for r in rows]

    def get_integration(self, integration_id: int) -> dict[str, Any]:
        return self._public(self._row(integration_id))

    def resolved(self, integration_id: int) -> tuple[str, dict[str, Any], dict[str, str]]:
        """Kind, config, and decrypted secrets, for tests and collectors."""
        row = self._row(integration_id)
        return row["kind"], json.loads(row["config"]), self.box.open(row["secrets"])

    def first_of_kind(self, kind: str) -> int | None:
        row = self.db.execute(
            "SELECT id FROM integrations WHERE kind = ? AND enabled = 1 ORDER BY id LIMIT 1",
            (kind,),
        ).fetchone()
        return row["id"] if row else None

    def merge_secrets(
        self, kind: str, incoming: dict[str, Any] | None, existing: dict[str, str]
    ) -> dict[str, str]:
        t = REGISTRY[kind]
        merged = dict(existing)
        for key, value in (incoming or {}).items():
            if key in t.secret_keys and value not in (None, ""):
                merged[key] = str(value)
        return merged

    def _clean_config(self, kind: str, config: dict[str, Any] | None) -> dict[str, Any]:
        t = REGISTRY[kind]
        allowed = {f.key: f for f in t.fields if f.type != "secret"}
        cleaned = t.defaults()
        cleaned = {k: v for k, v in cleaned.items() if k in allowed}
        for key, value in (config or {}).items():
            if key in allowed:
                cleaned[key] = value
        return cleaned

    def _check_required(self, kind: str, config: dict[str, Any], secrets: dict[str, str]) -> None:
        missing = [
            f.label
            for f in REGISTRY[kind].fields
            if f.required
            and (secrets.get(f.key) if f.type == "secret" else config.get(f.key)) in (None, "")
        ]
        if missing:
            raise Invalid("Missing: " + ", ".join(missing))

    def create_integration(
        self,
        kind: str,
        name: str | None,
        config: dict[str, Any] | None,
        secrets: dict[str, Any] | None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        t = REGISTRY.get(kind)
        if t is None:
            raise Invalid(f"Unknown integration type {kind!r}")
        if (
            not t.multiple
            and self.db.execute("SELECT 1 FROM integrations WHERE kind = ?", (kind,)).fetchone()
        ):
            raise Conflict(f"{t.label} is already set up. Edit the existing one instead.")
        cfg = self._clean_config(kind, config)
        sec = self.merge_secrets(kind, secrets, {})
        self._check_required(kind, cfg, sec)
        ts = now()
        cur = self.db.execute(
            "INSERT INTO integrations "
            "(kind, name, enabled, config, secrets, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                kind,
                (name or "").strip() or t.label,
                int(enabled),
                json.dumps(cfg),
                self.box.seal(sec),
                ts,
                ts,
            ),
        )
        return self.get_integration(cur.lastrowid)

    def update_integration(
        self,
        integration_id: int,
        name: str | None,
        config: dict[str, Any] | None,
        secrets: dict[str, Any] | None,
        enabled: bool | None,
    ) -> dict[str, Any]:
        row = self._row(integration_id)
        kind = row["kind"]
        cfg = self._clean_config(kind, config) if config is not None else json.loads(row["config"])
        sec = self.merge_secrets(kind, secrets, self.box.open(row["secrets"]))
        self._check_required(kind, cfg, sec)
        self.db.execute(
            "UPDATE integrations SET name = ?, enabled = ?, config = ?, secrets = ?, "
            "updated_at = ? WHERE id = ?",
            (
                (name or "").strip() or row["name"],
                int(row["enabled"] if enabled is None else enabled),
                json.dumps(cfg),
                self.box.seal(sec),
                now(),
                integration_id,
            ),
        )
        return self.get_integration(integration_id)

    def delete_integration(self, integration_id: int) -> None:
        self._row(integration_id)
        self.db.execute("DELETE FROM integrations WHERE id = ?", (integration_id,))

    def record_test(self, integration_id: int, result: TestResult) -> None:
        payload = {**result.model_dump(), "at": now()}
        self.db.execute(
            "UPDATE integrations SET last_test = ? WHERE id = ?",
            (json.dumps(payload), integration_id),
        )

    def seed_defaults(self) -> None:
        """Integrations that live inside the stack need no input, so they exist from the start."""
        if self.get_setting("seeded_mqtt") == "1":
            return
        if self.first_of_kind("mqtt") is None:
            self.create_integration("mqtt", None, None, None)
        self.set_setting("seeded_mqtt", "1")
