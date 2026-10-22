"""Optional TOML configuration on all supported Python versions."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10
    import tomli as tomllib


def config_path(env: dict[str, str] | None = None, platform: str | None = None) -> Path:
    values = os.environ if env is None else env
    system = sys.platform if platform is None else platform
    if system == "win32":
        base = Path(values.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(values.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "devsweep" / "config.toml"


def load_config(env: dict[str, str] | None = None, platform: str | None = None) -> dict[str, Any]:
    path = config_path(env, platform)
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return {}
