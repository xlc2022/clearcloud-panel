"""Process-level settings.

Only values a person never edits live here. Every address and credential is
configured in the GUI and stored in the database (see ``store``).
"""

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    static_dir: Path
    port: int

    @property
    def db_path(self) -> Path:
        return self.data_dir / "panel.db"

    @property
    def key_path(self) -> Path:
        return self.data_dir / "panel.key"


def load_settings() -> Settings:
    return Settings(
        data_dir=Path(os.environ.get("PANEL_DATA_DIR", "./data")).resolve(),
        static_dir=Path(os.environ.get("PANEL_STATIC_DIR", PACKAGE_DIR / "static")).resolve(),
        port=int(os.environ.get("PANEL_PORT", "8080")),
    )
