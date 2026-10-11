"""Encryption of stored secrets with a key generated on first run."""

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet


def load_or_create_key(path: Path) -> bytes:
    if path.exists():
        return path.read_bytes().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


class SecretBox:
    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def seal(self, secrets: dict[str, str]) -> bytes:
        return self._fernet.encrypt(json.dumps(secrets).encode())

    def open(self, blob: bytes | None) -> dict[str, str]:
        if not blob:
            return {}
        return json.loads(self._fernet.decrypt(blob))
