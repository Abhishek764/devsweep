"""Terminal output helpers with non-TTY and non-UTF-8 fallbacks."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from .platform_utils import enable_virtual_terminal_processing
from .sizes import human_size


class Colors:
    def __init__(self, stream: TextIO = sys.stdout, disabled: bool = False) -> None:
        self.enabled = bool(
            not disabled and not os.environ.get("NO_COLOR") and getattr(stream, "isatty", lambda: False)()
        )
        if self.enabled:
            enable_virtual_terminal_processing()

    def wrap(self, value: str, code: str) -> str:
        return f"\033[{code}m{value}\033[0m" if self.enabled else value

    def heading(self, value: str) -> str:
        return self.wrap(value, "1;36")

    def muted(self, value: str) -> str:
        return self.wrap(value, "2")

    def warning(self, value: str) -> str:
        return self.wrap(value, "33")

    def danger(self, value: str) -> str:
        return self.wrap(value, "31")

    def success(self, value: str) -> str:
        return self.wrap(value, "32")


def write_line(stream: TextIO, text: str = "") -> None:
    try:
        stream.write(text + "\n")
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        data = (text + "\n").encode(encoding, errors="replace")
        buffer = getattr(stream, "buffer", None)
        if buffer is not None:
            buffer.write(data)
        else:
            stream.write(data.decode(encoding, errors="replace"))


def relative_age(timestamp: float, now: float | None = None) -> str:
    if not timestamp:
        return "unknown"
    seconds = max(0, (time.time() if now is None else now) - timestamp)
    units = ((365 * 86400, "year"), (30 * 86400, "month"), (7 * 86400, "week"), (86400, "day"), (3600, "hour"), (60, "minute"))
    for size, name in units:
        if seconds >= size:
            count = int(seconds // size)
            return f"{count} {name}{'' if count == 1 else 's'} ago"
    return "just now"


def display_path(path: Path, root: Path | None = None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix() or "."
        except (OSError, ValueError):
            pass
    return os.fspath(path)


def render_table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    header_values = list(headers)
    row_values = [list(row) for row in rows]
    widths = [len(value) for value in header_values]
    for row in row_values:
        if len(row) > len(widths):
            widths.extend([0] * (len(row) - len(widths)))
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    output = ["  ".join(value.ljust(widths[index]) for index, value in enumerate(header_values))]
    output.append("  ".join("-" * width for width in widths[: len(header_values)]))
    output.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in row_values)
    return "\n".join(output)


def progress_line(stream: TextIO, count: int, total: int, unicode_ok: bool) -> None:
    total = max(1, total)
    completed = min(total, max(0, count))
    width = 24
    filled = int(width * completed / total)
    full, empty = ("█", "░") if unicode_ok else ("#", "-")
    bar = full * filled + empty * (width - filled)
    try:
        stream.write(f"\rScanning [{bar}] {completed}/{total} targets")
        stream.flush()
    except UnicodeEncodeError:
        fallback = "#" * filled + "-" * (width - filled)
        stream.write(f"\rScanning [{fallback}] {completed}/{total} targets")
        stream.flush()


def clear_progress(stream: TextIO) -> None:
    try:
        stream.write("\r\033[2K")
        stream.flush()
    except OSError:
        pass


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def format_bytes(value: int) -> str:
    return human_size(value)
