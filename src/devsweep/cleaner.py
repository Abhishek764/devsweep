"""Deletion with a second, independent safety check."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .platform_utils import (
    is_dangerous_root,
    is_strict_descendant,
    is_symlink_or_reparse,
    safe_rmtree,
    to_extended_path,
)
from .scanner import Target
from .sizes import path_size
from .targets import marker_matches, specs_for_directory


class CleanSafetyError(ValueError):
    """Raised when clean cannot establish a safe deletion boundary."""


@dataclass(frozen=True)
class CleanFailure:
    path: Path
    reason: str


@dataclass(frozen=True)
class Cleaned:
    path: Path
    requested_bytes: int
    freed_bytes: int


@dataclass
class CleanResult:
    planned: list[Target] = field(default_factory=list)
    deleted: list[Cleaned] = field(default_factory=list)
    skipped: list[CleanFailure] = field(default_factory=list)
    failures: list[CleanFailure] = field(default_factory=list)

    @property
    def freed_bytes(self) -> int:
        return sum(item.freed_bytes for item in self.deleted)


def parse_selection(value: str, count: int) -> list[int]:
    """Parse ``all``, one-based numbers, comma lists, ranges, or ``q``."""

    raw = value.strip().lower()
    if raw == "q":
        return []
    if raw == "all":
        return list(range(count))
    if not raw:
        raise ValueError("enter all, item numbers, ranges such as 1-3, or q")
    selected: set[int] = set()
    try:
        for part in raw.split(","):
            token = part.strip()
            if "-" in token:
                left, right = token.split("-", 1)
                start, end = int(left), int(right)
                if start > end:
                    raise ValueError
                values = range(start, end + 1)
            else:
                values = (int(token),)
            for number in values:
                if number < 1 or number > count:
                    raise ValueError
                selected.add(number - 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid selection; use all, numbers, ranges such as 1-3, or q") from exc
    return sorted(selected)


def _is_current_target(item: Target) -> bool:
    """Re-check the marker after scan, before deleting a possibly changed path."""

    try:
        if is_symlink_or_reparse(item.path) or not item.path.is_dir():
            return False
        if not is_strict_descendant(item.project, item.path):
            return False
        specs = specs_for_directory(item.path.name)
        return any(marker_matches(spec, item.path, item.project) and spec.type == item.type for spec in specs)
    except OSError:
        return False


def _safe_target(root: Path, item: Target) -> tuple[bool, str]:
    try:
        if not os.path.lexists(item.path):
            return False, "target disappeared"
        if is_symlink_or_reparse(item.path):
            return False, "symlink or junction appeared after scan"
        if is_symlink_or_reparse(item.project):
            return False, "project root is a symlink or junction"
        if item.project != root and not is_strict_descendant(root, item.project):
            return False, "project root is outside the scan root"
        if not _is_current_target(item):
            return False, "target marker changed or target disappeared"
        if not is_strict_descendant(root, item.path):
            return False, "target is outside the scan root"
    except OSError as exc:
        return False, str(exc) or exc.__class__.__name__
    return True, ""


def clean(
    root: Path | str,
    items: Iterable[Target],
    *,
    yes: bool = False,
    selection: str | Iterable[int] | None = None,
    allow_dangerous: bool = False,
) -> CleanResult:
    """Plan or delete scanned items.

    With neither ``yes`` nor ``selection``, this is a dry-run.  A caller that
    wants an interactive prompt parses the answer and passes its indexes back
    here, keeping the deletion primitive independent of terminal UX.
    """

    scan_root = Path(root).expanduser()
    if not allow_dangerous and is_dangerous_root(scan_root):
        raise CleanSafetyError("refusing to clean a system, drive-root, or home directory; use --i-know-what-i-am-doing")
    try:
        if is_symlink_or_reparse(scan_root) or not scan_root.is_dir():
            raise CleanSafetyError("scan root must be an existing directory and not a symlink or junction")
        scan_root = Path(os.path.abspath(os.fspath(scan_root)))
    except OSError as exc:
        raise CleanSafetyError(str(exc) or "unable to inspect scan root") from exc

    all_items = list(items)
    result = CleanResult()
    if yes:
        selected = set(range(len(all_items)))
    elif selection is None:
        result.planned.extend(all_items)
        return result
    elif isinstance(selection, str):
        selected = set(parse_selection(selection, len(all_items)))
    else:
        selected = set(selection)

    for index, item in enumerate(all_items):
        if index not in selected:
            result.planned.append(item)
            continue
        safe, reason = _safe_target(scan_root, item)
        if not safe:
            if "disappeared" in reason:
                result.skipped.append(CleanFailure(item.path, "already gone, skipped"))
            else:
                result.skipped.append(CleanFailure(item.path, reason))
            continue
        before = path_size(item.path)
        try:
            identity = item.path.lstat()
        except OSError:
            result.skipped.append(CleanFailure(item.path, "already gone, skipped"))
            continue
        safe, reason = _safe_target(scan_root, item)
        try:
            current_identity = item.path.lstat() if safe else None
        except OSError:
            current_identity = None
            safe, reason = False, "target disappeared"
        if safe and (
            current_identity is None
            or (identity.st_dev, identity.st_ino, identity.st_mode)
            != (current_identity.st_dev, current_identity.st_ino, current_identity.st_mode)
        ):
            safe, reason = False, "target changed after validation"
        if not safe:
            result.skipped.append(CleanFailure(item.path, "already gone, skipped" if "disappeared" in reason else reason))
            continue
        try:
            safe_rmtree(to_extended_path(item.path))
        except KeyboardInterrupt:
            raise
        except (OSError, PermissionError) as exc:
            message = "in use, skipped" if isinstance(exc, PermissionError) else (str(exc) or exc.__class__.__name__)
            result.failures.append(CleanFailure(item.path, message))
            continue
        after = path_size(item.path) if item.path.exists() else 0
        freed = max(0, before - after)
        result.deleted.append(Cleaned(item.path, before, freed))
    return result
