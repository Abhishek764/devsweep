"""Optional TOML configuration (available on Python 3.11 and newer)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def config_path(env: dict[str, str] | None = None, platform: str | None = None) -> Path:
    values = os.environ if env is None else env
    system = sys.platform if platform is None else platform
    if system == "win32":
        base = Path(values.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(values.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "devsweep" / "config.toml"


def load_config(env: dict[str, str] | None = None, platform: str | None = None) -> dict[str, Any]:
    if sys.version_info < (3, 11):
        return {}
    try:
        import tomllib
    except ImportError:  # pragma: no cover - only Python 3.10 and older
        return {}
    path = config_path(env, platform)
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return {}
