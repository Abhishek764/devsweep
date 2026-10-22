"""Safe discovery of reclaimable project directories."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Callable

from .git import git_activity_paths, repository_status
from .ignore import load_devsweep_patterns, matches
from .platform_utils import (
    is_reparse_point,
    is_symlink_or_reparse,
    to_extended_path,
    to_public_path,
)
from .sizes import path_size
from .targets import TARGET_REGISTRY, TargetSpec, marker_matches


@dataclass(frozen=True)
class Skipped:
    path: Path
    reason: str


@dataclass(frozen=True)
class Target:
    type: str
    path: Path
    project: Path
    project_name: str
    size: int
    activity: float

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.activity) if self.activity else float("inf")


@dataclass
class ScanResult:
    items: list[Target] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


def _duration_seconds(value: float | int | timedelta) -> float:
    if isinstance(value, timedelta):
        return max(0.0, value.total_seconds())
    return max(0.0, float(value))


def _name_equal(left: str, right: str) -> bool:
    return left.casefold() == right.casefold() if os.name == "nt" else left == right


def _candidate_spec(path: Path, project: Path) -> TargetSpec | None:
    for spec in TARGET_REGISTRY:
        if _name_equal(path.name, spec.directory) and marker_matches(spec, path, project):
            return spec
    return None


def _project_root(target: Path, project: Path, scan_root: Path, spec: TargetSpec) -> Path:
    """Use the repository root when available, otherwise the nearest marker."""

    current = project
    marker_project = project
    while True:
        try:
            if (current / ".git").exists():
                return current
            if spec.marker == "python_project" and marker_matches(spec, target, current):
                marker_project = current
        except OSError:
            break
        if current == scan_root or current.parent == current:
            break
        current = current.parent
    return marker_project


def _safe_mtime(path: Path) -> float | None:
    try:
        if is_symlink_or_reparse(path):
            return None
        return os.stat(os.fspath(path), follow_symlinks=False).st_mtime
    except OSError:
        return None


def project_activity(project: Path) -> float:
    """Find newest project activity without entering generated targets."""

    newest = 0.0
    for path in git_activity_paths(project):
        value = _safe_mtime(path)
        if value is not None:
            newest = max(newest, value)

    stack = [project]
    generated_names = {spec.directory.casefold() if os.name == "nt" else spec.directory for spec in TARGET_REGISTRY}
    while stack:
        current = stack.pop()
        try:
            with os.scandir(to_extended_path(current)) as entries:
                for entry in entries:
                    child = to_public_path(entry.path)
                    name = entry.name.casefold() if os.name == "nt" else entry.name
                    try:
                        if name == ".git":
                            continue
                        if name in generated_names:
                            continue
                        if entry.is_symlink() or is_reparse_point(child):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(child)
                        elif entry.is_file(follow_symlinks=False):
                            value = _safe_mtime(child)
                            if value is not None:
                                newest = max(newest, value)
                    except OSError:
                        continue
        except OSError:
            continue
    return newest


def _walk_candidates(
    root: Path, patterns: tuple[str, ...], result: ScanResult
) -> list[tuple[TargetSpec, Path, Path]]:
    candidates: list[tuple[TargetSpec, Path, Path]] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(to_extended_path(current)) as entries:
                for entry in entries:
                    child = to_public_path(entry.path)
                    try:
                        if matches(child, root, patterns):
                            result.skipped.append(Skipped(child, "ignored by pattern"))
                            continue
                        if entry.is_symlink() or is_reparse_point(child):
                            result.skipped.append(Skipped(child, "symlink or junction skipped"))
                            continue
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                        if entry.name == ".git":
                            continue
                        spec = _candidate_spec(child, current)
                        if spec is not None:
                            candidates.append((spec, child, _project_root(child, current, root, spec)))
                            # A detected target is an atomic unit.  Never scan
                            # inside it, even when a type filter excludes it.
                            continue
                        stack.append(child)
                    except OSError as exc:
                        result.skipped.append(Skipped(child, _error_text(exc)))
        except OSError as exc:
            result.skipped.append(Skipped(current, _error_text(exc)))
    return candidates


def _error_text(exc: OSError) -> str:
    if getattr(exc, "errno", None) == 13:
        return "permission denied"
    return str(exc) or exc.__class__.__name__


def scan(
    root: Path | str,
    *,
    older_than: float | int | timedelta = 30 * 86400,
    min_size: int = 0,
    types: Iterable[str] = (),
    excludes: Iterable[str] = (),
    force: bool = False,
    sort: str = "size",
    now: float | None = None,
    progress: Callable[[int], None] | None = None,
) -> ScanResult:
    """Scan *root* while applying all conservative detection rules."""

    scan_root = Path(root).expanduser()
    result = ScanResult()
    try:
        if is_symlink_or_reparse(scan_root):
            result.skipped.append(Skipped(scan_root, "scan root is a symlink or junction"))
            return result
        if not scan_root.exists():
            result.skipped.append(Skipped(scan_root, "path does not exist"))
            return result
        if not scan_root.is_dir():
            result.skipped.append(Skipped(scan_root, "scan root is not a directory"))
            return result
        scan_root = Path(os.path.abspath(os.fspath(scan_root)))
    except OSError as exc:
        result.skipped.append(Skipped(scan_root, _error_text(exc)))
        return result

    patterns = load_devsweep_patterns(scan_root, excludes)
    candidates = _walk_candidates(scan_root, patterns, result)
    selected_types = set(types)
    threshold = _duration_seconds(older_than)
    current_time = time.time() if now is None else now
    lock = threading.Lock()

    def size_one(candidate: tuple[TargetSpec, Path, Path]) -> tuple[tuple[TargetSpec, Path, Path], int]:
        _, target_path, _ = candidate

        def record_error(path: Path, reason: str) -> None:
            with lock:
                result.skipped.append(Skipped(path, reason))

        return candidate, path_size(target_path, on_error=record_error)

    workers = min(32, max(1, len(candidates)))
    sized: list[tuple[tuple[TargetSpec, Path, Path], int]] = []
    if candidates:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="devsweep-size") as pool:
            for value in pool.map(size_one, candidates):
                sized.append(value)
                if progress:
                    progress(len(sized))

    for (spec, target_path, project), size in sized:
        if selected_types and spec.type not in selected_types:
            continue
        if size < min_size:
            continue
        status = repository_status(project)
        if status == "dirty" and not force:
            result.skipped.append(Skipped(target_path, "git project has uncommitted changes"))
            continue
        if status == "unavailable" and not force:
            result.skipped.append(Skipped(target_path, "git status could not be verified"))
            continue
        activity = project_activity(project)
        age = current_time - activity if activity else float("inf")
        if age < threshold:
            result.skipped.append(Skipped(target_path, "project activity is more recent than --older-than"))
            continue
        result.items.append(
            Target(
                type=spec.type,
                path=target_path,
                project=project,
                project_name=project.name or os.fspath(project),
                size=size,
                activity=activity,
            )
        )

    def path_order(item: Target) -> tuple[str, str]:
        value = os.fspath(item.path)
        return value.casefold(), value

    if sort == "size":
        result.items.sort(key=lambda item: (-item.size, *path_order(item)))
    elif sort == "age":
        result.items.sort(key=lambda item: (-item.age_seconds, *path_order(item)))
    elif sort == "path":
        result.items.sort(key=path_order)
    else:
        raise ValueError("sort must be size, age, or path")
    return result
