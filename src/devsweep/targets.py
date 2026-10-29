"""Data-driven registry of project-generated directories.

The registry deliberately describes *evidence* required before a directory is
considered reclaimable.  A new ecosystem should normally be one
``TargetSpec`` row plus an existing marker kind, rather than a new scanner
branch.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .platform_utils import is_symlink_or_reparse


@dataclass(frozen=True)
class TargetSpec:
    """A directory name and the marker evidence required for it."""

    type: str
    directory: str
    marker: str
    description: str


# Keep this table ordered from specific ecosystems to generic names.  The
# scanner never descends into a detected target, so a nested target cannot
# replace its already-detected parent.
TARGET_REGISTRY: tuple[TargetSpec, ...] = (
    TargetSpec("node_modules", "node_modules", "package_json_parent", "Node dependencies"),
    TargetSpec("next", ".next", "package_json_parent", "Next.js build output"),
    TargetSpec("nuxt", ".nuxt", "package_json_parent", "Nuxt build output"),
    TargetSpec("svelte-kit", ".svelte-kit", "package_json_parent", "SvelteKit build output"),
    TargetSpec("dist", "dist", "package_json_gitignored", "JavaScript distribution output"),
    TargetSpec("venv", "venv", "pyvenv_cfg", "Python virtual environment"),
    TargetSpec("venv", ".venv", "pyvenv_cfg", "Python virtual environment"),
    TargetSpec("venv", "env", "pyvenv_cfg", "Python virtual environment"),
    TargetSpec("python-cache", "__pycache__", "python_project", "Python bytecode cache"),
    TargetSpec("python-cache", ".pytest_cache", "python_project", "pytest cache"),
    TargetSpec("python-cache", ".mypy_cache", "python_project", "mypy cache"),
    TargetSpec("python-cache", ".ruff_cache", "python_project", "Ruff cache"),
    TargetSpec("python-cache", ".tox", "python_project", "tox environment"),
    TargetSpec("cargo-target", "target", "cargo_manifest", "Cargo build output"),
    TargetSpec("maven-target", "target", "maven_manifest", "Maven build output"),
    TargetSpec("gradle-build", "build", "gradle_manifest", "Gradle build output"),
    TargetSpec("gradle-cache", ".gradle", "gradle_manifest", "Project Gradle cache"),
    TargetSpec("composer-vendor", "vendor", "composer_gitignored", "Composer dependencies"),
    TargetSpec("go-vendor", "vendor", "go_vendor_gitignored", "Go vendored dependencies"),
    TargetSpec("terraform", ".terraform", "terraform_files", "Terraform working data"),
    TargetSpec("dotnet-bin", "bin", "dotnet_gitignored", ".NET build output"),
    TargetSpec("dotnet-obj", "obj", "dotnet_gitignored", ".NET intermediate output"),
    TargetSpec("dart-tool", ".dart_tool", "dart_manifest", "Dart tool data"),
    TargetSpec("dart-build", "build", "dart_manifest", "Dart build output"),
)


def specs_for_directory(name: str) -> tuple[TargetSpec, ...]:
    """Return registry entries that can apply to *name*.

    Uses case-insensitive comparison on Windows to match the scanner's
    ``_name_equal`` behavior.
    """
    if os.name == "nt":
        folded = name.casefold()
        return tuple(spec for spec in TARGET_REGISTRY if spec.directory.casefold() == folded)
    return tuple(spec for spec in TARGET_REGISTRY if spec.directory == name)


def _has_any(path: Path, names: Iterable[str]) -> bool:
    return any(_is_regular_file(path / name) for name in names)


def _nearby_python_marker(project: Path) -> bool:
    current = project
    for _ in range(4):
        if _has_any(current, ("pyproject.toml", "setup.py", "requirements.txt")):
            return True
        try:
            if any(
                _is_regular_file(entry) and entry.suffix.lower() == ".py"
                for entry in current.iterdir()
            ):
                return True
        except (OSError, PermissionError):
            return False
        if current.parent == current:
            break
        current = current.parent
    return False


def marker_matches(spec: TargetSpec, target: Path, project: Path) -> bool:
    """Check the conservative marker rule for one registry entry."""

    marker = spec.marker
    if marker == "package_json_parent":
        return _is_regular_file(project / "package.json")
    if marker == "package_json_gitignored":
        return _is_regular_file(project / "package.json") and _gitignored(project, target)
    if marker == "pyvenv_cfg":
        return _is_regular_file(target / "pyvenv.cfg")
    if marker == "python_project":
        return _nearby_python_marker(project)
    if marker == "cargo_manifest":
        return _is_regular_file(project / "Cargo.toml")
    if marker == "maven_manifest":
        return _is_regular_file(project / "pom.xml")
    if marker == "gradle_manifest":
        return _has_any(project, ("build.gradle", "build.gradle.kts", "settings.gradle"))
    if marker == "composer_gitignored":
        return _is_regular_file(project / "composer.json") and _gitignored(project, target)
    if marker == "go_vendor_gitignored":
        return _is_regular_file(project / "go.mod") and _is_regular_file(target / "modules.txt") and _gitignored(project, target)
    if marker == "terraform_files":
        return _has_extension(project, ".tf")
    if marker == "dotnet_gitignored":
        return _has_extension(project, ".csproj", ".sln") and _gitignored(project, target)
    if marker == "dart_manifest":
        return _is_regular_file(project / "pubspec.yaml")
    return False


def _has_extension(project: Path, *suffixes: str) -> bool:
    try:
        return any(_is_regular_file(entry) and entry.suffix.lower() in suffixes for entry in project.iterdir())
    except (OSError, PermissionError):
        return False


def _is_regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not is_symlink_or_reparse(path)
    except OSError:
        return False


def _gitignored(project: Path, target: Path) -> bool:
    # Imported lazily to keep the registry usable by itself and to avoid an
    # import cycle when ignore.py uses the registry's directory names.
    try:
        from .ignore import is_ignored

        return is_ignored(target, project)
    except (OSError, PermissionError):
        return False
