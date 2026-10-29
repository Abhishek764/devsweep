"""Git status and project activity helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .platform_utils import is_symlink_or_reparse


def git_available() -> bool:
    return shutil.which("git") is not None


def repository_status(project: Path) -> str:
    """Return ``clean``, ``dirty``, ``unknown``, ``unavailable`` or ``not-repository``."""

    has_repository_metadata = False
    for directory in (project, *project.parents):
        git_dir = directory / ".git"
        try:
            if is_symlink_or_reparse(git_dir):
                return "unknown"
            if git_dir.exists():
                has_repository_metadata = True
                break
        except OSError:
            return "unknown"
    if not has_repository_metadata:
        return "not-repository"
    if not git_available():
        return "unknown"
    try:
        result = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-C",
                os.fspath(project),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    return "dirty" if result.stdout.strip() else "clean"


def git_activity_paths(project: Path) -> tuple[Path, ...]:
    git_dir = project / ".git"
    if is_symlink_or_reparse(git_dir):
        return ()
    if git_dir.is_dir():
        return tuple(path for path in (git_dir / "HEAD", git_dir / "index") if path.exists())
    if git_dir.is_file():
        return (git_dir,)
    return ()
