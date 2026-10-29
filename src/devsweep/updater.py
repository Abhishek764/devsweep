"""Update the installed DevSweep command from the project source."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable

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


def update(*, run: Callable[..., subprocess.CompletedProcess] | None = None) -> str:
    """Update DevSweep and return the package manager used.

    Package-manager output is inherited so pipx, uv, and pip can display their
    native download progress. A failed manager is tried only as a fallback.
    """

    run = subprocess.run if run is None else run
    errors: list[str] = []
    for command in _commands():
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
