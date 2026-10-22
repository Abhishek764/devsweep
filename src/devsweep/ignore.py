"""Conservative, small gitignore-style pattern matching."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import Path

from .platform_utils import is_symlink_or_reparse


def read_patterns(path: Path) -> tuple[str, ...]:
    try:
        if is_symlink_or_reparse(path):
            return ()
    except OSError:
        return ()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, UnicodeError):
        return ()
    patterns: list[str] = []
    for line in lines:
        value = line.strip()
        if value and not value.startswith("#"):
            patterns.append(value)
    return tuple(patterns)


def load_devsweep_patterns(root: Path, extra: Iterable[str] = ()) -> tuple[str, ...]:
    return read_patterns(root / ".devsweepignore") + tuple(extra)


def _relative(path: Path, root: Path) -> str | None:
    try:
        value = path.absolute().relative_to(root.absolute())
    except (OSError, ValueError):
        return None
    relative = value.as_posix().strip("/")
    return None if relative in ("", ".") else relative


def _matches_one(relative: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/").strip()
    if not pattern:
        return False
    if pattern.startswith("!"):
        pattern = pattern[1:]
    anchored = pattern.startswith("/")
    pattern = pattern.lstrip("/")
    directory_pattern = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    if not pattern:
        return False

    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        if relative == prefix or relative.startswith(prefix + "/"):
            return True
    if "/" not in pattern:
        parts = relative.split("/")
        if any(fnmatch.fnmatchcase(part, pattern) for part in parts):
            return True
    if fnmatch.fnmatchcase(relative, pattern):
        return True
    if not anchored and fnmatch.fnmatchcase(relative, "*/" + pattern):
        return True
    if directory_pattern and relative.startswith(pattern + "/"):
        return True
    return False


def matches(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    relative = _relative(path, root)
    if relative is None or not relative:
        return False
    ignored = False
    for raw in patterns:
        pattern = raw.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        if _matches_one(relative, pattern):
            ignored = not negated
    return ignored


def is_ignored(path: Path, root: Path, patterns: Iterable[str] | None = None) -> bool:
    if patterns is None:
        patterns = read_patterns(root / ".gitignore")
    return matches(path, root, patterns)
