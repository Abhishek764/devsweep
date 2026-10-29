"""Known, explicit global developer cache locations."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .platform_utils import is_symlink_or_reparse, safe_rmtree, to_extended_path
from .sizes import path_size


@dataclass(frozen=True)
class CacheSpec:
    tool: str
    path: Path
    clear_command: str
    optional: bool = False


@dataclass(frozen=True)
class CacheEntry:
    spec: CacheSpec
    size: int


@dataclass(frozen=True)
class CacheFailure:
    path: Path
    reason: str


@dataclass
class CacheCleanResult:
    deleted: list[CacheEntry]
    failures: list[CacheFailure]

    @property
    def freed_bytes(self) -> int:
        return sum(entry.size for entry in self.deleted)


def _home(env: dict[str, str]) -> Path:
    return Path(env.get("USERPROFILE") or env.get("HOME") or str(Path.home()))


def cache_specs(
    *,
    env: dict[str, str] | None = None,
    platform: str | None = None,
    include_maven: bool = False,
    include_nuget: bool = False,
) -> tuple[CacheSpec, ...]:
    values = dict(os.environ if env is None else env)
    system = os.name if platform is None else ("nt" if platform in ("nt", "win32") else "posix")
    home = _home(values)
    specs: list[CacheSpec] = []
    if system == "nt":
        local = Path(values.get("LOCALAPPDATA") or home / "AppData" / "Local")
        roaming = Path(values.get("APPDATA") or home / "AppData" / "Roaming")
        specs.extend(
            (
                CacheSpec("npm", local / "npm-cache", "npm cache clean --force"),
                CacheSpec("yarn", local / "Yarn" / "Cache", "yarn cache clean"),
                CacheSpec("pnpm", local / "pnpm" / "store", "pnpm store prune"),
                CacheSpec("pip", local / "pip" / "Cache", "pip cache purge"),
                CacheSpec("uv", local / "uv" / "cache", "uv cache clean"),
                CacheSpec("cargo registry", home / ".cargo" / "registry" / "cache", "cargo cache --autoclean"),
                CacheSpec("cargo git", home / ".cargo" / "git", "cargo cache --autoclean"),
                CacheSpec("Gradle", home / ".gradle" / "caches", "gradle --stop"),
                CacheSpec("Go", local / "go-build", "go clean -cache"),
                CacheSpec("VS Code", roaming / "Code" / "Cache", "code --clear-cache"),
                CacheSpec("VS Code", roaming / "Code" / "CachedData", "code --clear-cache"),
                CacheSpec("NuGet HTTP", local / "NuGet" / "v3-cache", "dotnet nuget locals http-cache --clear"),
                CacheSpec(
                    "NuGet temp",
                    Path(values.get("TEMP") or values.get("TMP") or tempfile.gettempdir()) / "NuGetScratch",
                    "dotnet nuget locals temp --clear",
                ),
            )
        )
        if include_nuget:
            specs.append(
                CacheSpec(
                    "NuGet global packages",
                    Path(values.get("NUGET_PACKAGES") or home / ".nuget" / "packages"),
                    "dotnet nuget locals global-packages --clear",
                    optional=True,
                )
            )
        if include_maven:
            specs.append(CacheSpec("Maven", home / ".m2" / "repository", "# remove selected Maven repository", optional=True))
    else:
        cache_home = Path(values.get("XDG_CACHE_HOME") or home / ".cache")
        data_home = Path(values.get("XDG_DATA_HOME") or home / ".local" / "share")
        specs.extend(
            (
                CacheSpec("npm", home / ".npm" / "_cacache", "npm cache clean --force"),
                CacheSpec("yarn", cache_home / "yarn", "yarn cache clean"),
                CacheSpec("pnpm", data_home / "pnpm" / "store", "pnpm store prune"),
                CacheSpec("pip", cache_home / "pip", "pip cache purge"),
                CacheSpec("uv", cache_home / "uv", "uv cache clean"),
                CacheSpec("cargo registry", home / ".cargo" / "registry" / "cache", "cargo cache --autoclean"),
                CacheSpec("cargo git", home / ".cargo" / "git", "cargo cache --autoclean"),
                CacheSpec("Gradle", home / ".gradle" / "caches", "gradle --stop"),
                CacheSpec("Go", cache_home / "go-build", "go clean -cache"),
                CacheSpec("thumbnails", cache_home / "thumbnails", "# remove selected thumbnail cache"),
                CacheSpec("VS Code", home / ".config" / "Code" / "Cache", "# remove selected VS Code cache"),
                CacheSpec("JetBrains", cache_home / "JetBrains", "# remove selected JetBrains cache"),
            )
        )
        if include_maven:
            specs.append(CacheSpec("Maven", home / ".m2" / "repository", "# remove selected Maven repository", optional=True))
    return tuple(specs)


def existing_caches(**kwargs) -> tuple[CacheEntry, ...]:
    entries: list[CacheEntry] = []
    for spec in cache_specs(**kwargs):
        try:
            if spec.path.exists() and not is_symlink_or_reparse(spec.path):
                entries.append(CacheEntry(spec, path_size(spec.path)))
        except OSError:
            continue
    return tuple(entries)


def clean_caches(entries: Iterable[CacheEntry], *, yes: bool = False) -> CacheCleanResult:
    deleted: list[CacheEntry] = []
    failures: list[CacheFailure] = []
    if not yes:
        return CacheCleanResult([], [])
    for entry in entries:
        path = entry.spec.path
        try:
            if not path.exists():
                continue
            if is_symlink_or_reparse(path):
                failures.append(CacheFailure(path, "symlink or junction skipped"))
                continue
            before = path_size(path)
            safe_rmtree(to_extended_path(path))
            after = path_size(path) if path.exists() else 0
            deleted.append(CacheEntry(entry.spec, max(0, before - after)))
        except (OSError, PermissionError) as exc:
            failures.append(CacheFailure(path, str(exc) or exc.__class__.__name__))
    return CacheCleanResult(deleted, failures)
