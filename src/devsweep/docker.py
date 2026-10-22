"""Restricted Docker disk reporting and pruning."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class DockerResult:
    status: str
    report: str = ""
    actions: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def docker_cleanup(*, yes: bool = False) -> DockerResult:
    docker = shutil.which("docker")
    if not docker:
        return DockerResult("missing", "Docker is not installed; nothing to clean.")
    try:
        report = subprocess.run(
            [docker, "system", "df"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return DockerResult("unavailable", "Docker is installed, but the daemon is not running or is unavailable.")
    if report.returncode != 0:
        return DockerResult("unavailable", "Docker is installed, but the daemon is not running or is unavailable.")
    result = DockerResult("ok", report.stdout.strip())
    if not yes:
        return result
    for command in ((docker, "image", "prune", "-f"), (docker, "builder", "prune", "-f")):
        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            result.failures.append(str(exc) or exc.__class__.__name__)
            continue
        if completed.returncode == 0:
            result.actions.append(" ".join(command))
        else:
            result.failures.append(completed.stderr.strip() or "Docker prune command failed")
    return result
