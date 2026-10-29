"""Update the installed DevSweep command from the project source."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPOSITORY = "git+https://github.com/abhishek764/devsweep"


class UpdateError(RuntimeError):
    """Raised when no supported package manager can update DevSweep."""


def _commands(which: Callable[[str], str | None] | None = None) -> list[list[str]]:
    which = shutil.which if which is None else which
    commands: list[list[str]] = []
    if which("pipx"):
        commands.append(["pipx", "install", "--force", REPOSITORY])
    if which("uv"):
        commands.append(["uv", "tool", "install", "--force", "--upgrade", REPOSITORY])
    commands.append([sys.executable, "-m", "pip", "install", "--user", "--upgrade", REPOSITORY])
    return commands


def _running_from_uv_tool() -> bool:
    """Return whether this process is running from uv's managed tool env."""

    parts = {part.casefold() for part in Path(sys.executable).parts}
    return "uv" in parts and "tools" in parts


def _schedule_uv_update(command: list[str]) -> bool:
    """Retry a uv update after this Windows process releases its executable."""

    if sys.platform != "win32" or not _running_from_uv_tool():
        return False
    try:
        uv_command = subprocess.list2cmdline(command)
        script = f"timeout /t 2 /nobreak >nul & {uv_command}"
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", script],
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def update(*, run: Callable[..., subprocess.CompletedProcess] | None = None) -> str:
    """Update DevSweep and return the package manager used.

    Package-manager output is inherited so pipx, uv, and pip can display their
    native download progress. A failed manager is tried only as a fallback.
    """

    run = subprocess.run if run is None else run
    errors: list[str] = []
    for command in _commands():
        if command[0] == "uv" and _schedule_uv_update(command):
            return "uv (scheduled after exit)"
        try:
            completed = run(command, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{' '.join(command[:2])}: {exc}")
            continue
        if completed.returncode == 0:
            return command[0]
        errors.append(f"{' '.join(command[:2])}: exited with {completed.returncode}")
    raise UpdateError("DevSweep update failed; " + "; ".join(errors))


__all__ = ("REPOSITORY", "UpdateError", "update")
