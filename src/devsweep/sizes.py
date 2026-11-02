"""Size and age calculations that never follow links."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .platform_utils import error_text, is_symlink_or_reparse, to_extended_path, to_public_path


def directory_size(
    path: Path,
    on_error: Callable[[Path, str], None] | None = None,
    *,
    dedup_inodes: bool = True,
) -> int:
    """Return bytes below *path*, ignoring symlinks and recording bad entries.

    When *dedup_inodes* is true (default), each unique inode identified by
    ``(st_dev, st_ino)`` is counted only once, so hard-linked files are not
    double-counted.  On platforms where ``st_dev``/``st_ino`` are unavailable,
    every entry is counted as before.
    """

    total = 0
    seen_inodes: set[tuple[int, int]] = set()
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
                            try:
                                st = os.stat(child, follow_symlinks=False)
                            except OSError as exc:
                                if on_error:
                                    on_error(child, error_text(exc))
                                continue
                            if dedup_inodes:
                                try:
                                    inode_key = (st.st_dev, st.st_ino)
                                except AttributeError:
                                    # st_dev/st_ino unavailable; count every entry.
                                    total += st.st_size
                                    continue
                                try:
                                    nlink = st.st_nlink
                                except AttributeError:
                                    # st_nlink unavailable; cannot confirm hard links, count every entry.
                                    total += st.st_size
                                    continue
                                if nlink <= 1:
                                    # Regular file with a single directory entry: always count,
                                    # even if its inode happens to collide with another file's.
                                    total += st.st_size
                                    continue
                                if inode_key in seen_inodes:
                                    continue
                                seen_inodes.add(inode_key)
                            total += st.st_size
                    except OSError as exc:
                        if on_error:
                            on_error(child, error_text(exc))
        except OSError as exc:
            if on_error:
                on_error(current, error_text(exc))
    return total


def path_size(
    path: Path,
    on_error: Callable[[Path, str], None] | None = None,
    *,
    dedup_inodes: bool = True,
) -> int:
    try:
        if is_symlink_or_reparse(path):
            return 0
        if path.is_file():
            return path.stat().st_size
        return directory_size(path, on_error=on_error, dedup_inodes=dedup_inodes)
    except OSError as exc:
        if on_error:
            on_error(path, error_text(exc))
        return 0


def allocated_size(path: Path) -> int | None:
    """Return allocated disk bytes for *path*, or ``None`` when unavailable.

    Uses ``st_blocks * st_blksize`` when the platform supports it (POSIX).
    Returns ``None`` on platforms without ``st_blocks`` (e.g. Windows) or when
    the path cannot be stat'd.
    """

    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    try:
        blocks = st.st_blocks
        blksize = st.st_blksize
    except AttributeError:
        # st_blocks/st_blksize unavailable (e.g. Windows).
        return None
    if blocks is None or blksize is None:
        return None
    return int(blocks) * int(blksize)


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
