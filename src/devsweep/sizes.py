"""Size and age calculations that never follow links."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .platform_utils import error_text, is_symlink_or_reparse, to_extended_path, to_public_path


def directory_size(path: Path, on_error: Callable[[Path, str], None] | None = None) -> int:
    """Return bytes below *path*, ignoring symlinks and recording bad entries."""

    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(to_extended_path(current)) as entries:
                for entry in entries:
                    child = to_public_path(entry.path)
                    try:
                        if entry.is_symlink() or is_symlink_or_reparse(child):
                            if on_error:
                                on_error(child, "symlink skipped")
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(child)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError as exc:
                        if on_error:
                            on_error(child, error_text(exc))
        except OSError as exc:
            if on_error:
                on_error(current, error_text(exc))
    return total


def path_size(path: Path, on_error: Callable[[Path, str], None] | None = None) -> int:
    try:
        if is_symlink_or_reparse(path):
            return 0
        if path.is_file():
            return path.stat().st_size
        return directory_size(path, on_error=on_error)
    except OSError as exc:
        if on_error:
            on_error(path, error_text(exc))
        return 0


def human_size(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    number = float(value)
    for unit in ("KB", "MB", "GB", "TB"):
        number /= 1024
        if number < 1024 or unit == "TB":
            return f"{number:.1f} {unit}"
    return f"{value} B"


def parse_size(value: str) -> int:
    """Parse bytes or binary units such as ``100MB``."""

    raw = value.strip().upper().replace(" ", "")
    units = {"B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2, "G": 1024**3, "GB": 1024**3}
    for suffix in sorted(units, key=len, reverse=True):
        if raw.endswith(suffix):
            number = raw[: -len(suffix)]
            try:
                parsed = float(number) * units[suffix]
            except ValueError as exc:
                raise ValueError(f"invalid size: {value}") from exc
            if parsed < 0:
                raise ValueError(f"invalid size: {value}")
            return int(parsed)
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid size: {value}") from exc
    if parsed < 0:
        raise ValueError(f"invalid size: {value}")
    return parsed
