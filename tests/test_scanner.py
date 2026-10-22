from __future__ import annotations

import os
import subprocess
import time
from datetime import timedelta
from pathlib import Path

import pytest

from devsweep.scanner import (
    ScanResult,
    _duration_seconds,
    _safe_mtime,
    project_activity,
    scan,
)


def write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_old(path: Path, days: int = 60) -> None:
    stamp = time.time() - days * 86400
    os.utime(path, (stamp, stamp))


def scanned(root: Path, **kwargs):
    result = scan(root, **kwargs)
    assert isinstance(result, ScanResult)
    return result.items


def test_detects_marked_targets_and_not_unmarked_build_or_dist(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    (tmp_path / "node_modules" / "dep").mkdir(parents=True)
    write(tmp_path / "node_modules" / "dep" / "index.js", "dependency")
    (tmp_path / "dist").mkdir()
    (tmp_path / "build").mkdir()
    write(tmp_path / ".gitignore", "dist/\n")
    write(tmp_path / "source.py", "print('ok')")
    for path in (tmp_path / "package.json", tmp_path / ".gitignore", tmp_path / "source.py"):
        make_old(path)

    items = scanned(tmp_path, older_than=1)
    assert {(item.type, item.path.name) for item in items} == {
        ("node_modules", "node_modules"),
        ("dist", "dist"),
    }


def test_nested_targets_are_not_double_counted(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    outer = tmp_path / "node_modules"
    write(outer / "package.json", "{}")
    write(outer / "nested" / "package.json", "{}")
    (outer / "nested" / "node_modules").mkdir(parents=True)
    make_old(tmp_path / "package.json")

    items = scanned(tmp_path, older_than=1)
    assert len(items) == 1
    assert items[0].path == outer


def test_virtual_environment_requires_pyvenv_cfg(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "pytest")
    (tmp_path / ".venv").mkdir()
    assert scanned(tmp_path, older_than=0) == []
    write(tmp_path / ".venv" / "pyvenv.cfg", "home = python")
    make_old(tmp_path / "requirements.txt")
    assert [item.type for item in scanned(tmp_path, older_than=1)] == ["venv"]


def test_symlinked_target_is_skipped_and_never_followed(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    outside = tmp_path.parent / "outside-node-modules"
    outside.mkdir()
    write(outside / "secret.txt", "do not touch")
    link = tmp_path / "node_modules"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    result = scan(tmp_path, older_than=0)
    assert result.items == []
    assert any(entry.path == link and "symlink" in entry.reason for entry in result.skipped)
    assert (outside / "secret.txt").exists()


def test_ignore_file_and_cli_excludes_apply(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    for name in ("node_modules", "ignored_modules"):
        (tmp_path / name).mkdir()
    write(tmp_path / ".devsweepignore", "node_modules\n")
    result = scan(tmp_path, older_than=0, excludes=("ignored_modules",))
    assert not result.items
    assert len(result.skipped) >= 2


def test_project_activity_excludes_target_and_recent_project_is_skipped(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    (tmp_path / "node_modules").mkdir()
    result = scan(tmp_path, older_than=30 * 86400)
    assert result.items == []
    assert any("recent" in entry.reason for entry in result.skipped)


def test_size_and_type_filters(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    target = tmp_path / "node_modules"
    target.mkdir()
    write(target / "large.bin", "a" * 128)
    make_old(tmp_path / "package.json")
    items = scanned(tmp_path, older_than=1, min_size=100, types=("node_modules",))
    assert len(items) == 1
    assert items[0].size >= 128
    assert scanned(tmp_path, older_than=1, min_size=1000) == []


def test_detects_ecosystem_markers_conservatively(tmp_path: Path) -> None:
    rust = tmp_path / "rust"
    rust.mkdir()
    write(rust / "Cargo.toml", "[package]")
    (rust / "target").mkdir()
    maven = tmp_path / "maven"
    maven.mkdir()
    write(maven / "pom.xml", "<project/>")
    (maven / "target").mkdir()
    gradle = tmp_path / "gradle"
    gradle.mkdir()
    write(gradle / "build.gradle", "plugins {}")
    (gradle / "build").mkdir()
    dart = tmp_path / "dart"
    dart.mkdir()
    write(dart / "pubspec.yaml", "name: app")
    (dart / "build").mkdir()
    terraform = tmp_path / "terraform"
    terraform.mkdir()
    write(terraform / "main.tf", "resource {}")
    (terraform / ".terraform").mkdir()
    dotnet = tmp_path / "dotnet"
    dotnet.mkdir()
    write(dotnet / "app.csproj", "<Project/>")
    write(dotnet / ".gitignore", "bin/\nobj/\n")
    (dotnet / "bin").mkdir()
    (dotnet / "obj").mkdir()
    for project in (rust, maven, gradle, dart, terraform, dotnet):
        for marker in project.iterdir():
            if marker.is_file():
                make_old(marker)

    types = {item.type for item in scanned(tmp_path, older_than=1)}
    assert {"cargo-target", "maven-target", "gradle-build", "dart-build", "terraform", "dotnet-bin", "dotnet-obj"} <= types


def test_vendor_requires_marker_and_gitignore(tmp_path: Path) -> None:
    project = tmp_path / "go"
    project.mkdir()
    write(project / "go.mod", "module example")
    vendor = project / "vendor"
    write(vendor / "modules.txt", "# example")
    assert not scanned(tmp_path, older_than=0)
    write(project / ".gitignore", "vendor/\n")
    make_old(project / "go.mod")
    make_old(project / ".gitignore")
    assert [item.type for item in scanned(tmp_path, older_than=1)] == ["go-vendor"]


def test_dirty_git_project_is_skipped_unless_forced(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    (tmp_path / "node_modules").mkdir()
    make_old(tmp_path / "package.json")
    subprocess.run(["git", "init", "-q", os.fspath(tmp_path)], check=True)
    make_old(tmp_path / ".git" / "HEAD")
    skipped = scan(tmp_path, older_than=1)
    assert skipped.items == []
    assert any("uncommitted" in item.reason for item in skipped.skipped)
    forced = scan(tmp_path, older_than=1, force=True)
    assert len(forced.items) == 1


def test_empty_unicode_and_space_named_targets_and_sorting(tmp_path: Path) -> None:
    first = tmp_path / "space project"
    first.mkdir()
    write(first / "package.json", "{}")
    (first / "node_modules").mkdir()
    second = tmp_path / "unicode-π"
    second.mkdir()
    write(second / "package.json", "{}")
    (second / "node_modules").mkdir()
    write(second / "node_modules" / "one", "123")
    for marker in (first / "package.json", second / "package.json"):
        make_old(marker)
    items = scanned(tmp_path, older_than=1, sort="path")
    assert [item.project_name for item in items] == ["space project", "unicode-π"]
    assert items[0].size == 0
    assert scanned(tmp_path, older_than=1, sort="age")


def test_nested_python_cache_uses_project_marker_ancestor(tmp_path: Path) -> None:
    write(tmp_path / "pyproject.toml", "[project]\nname='x'")
    cache = tmp_path / "src" / "module" / "__pycache__"
    cache.mkdir(parents=True)
    make_old(tmp_path / "pyproject.toml")
    items = scanned(tmp_path, older_than=1)
    assert len(items) == 1
    assert items[0].project == tmp_path


def test_missing_or_file_root_is_reported_without_crashing(tmp_path: Path) -> None:
    missing = scan(tmp_path / "missing")
    assert missing.items == []
    assert missing.skipped
    file_root = tmp_path / "file.txt"
    file_root.write_text("x", encoding="utf-8")
    result = scan(file_root)
    assert result.items == []
    assert result.skipped


def test_invalid_sort_is_reported() -> None:
    with pytest.raises(ValueError):
        scan(Path.cwd(), older_than=0, sort="invalid")


def test_scanner_helpers_cover_git_activity_progress_and_missing_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _duration_seconds(timedelta(days=2)) == 2 * 86400
    assert _duration_seconds(-1) == 0
    assert project_activity(tmp_path / "missing") == 0
    git = tmp_path / ".git"
    git.mkdir()
    write(git / "HEAD", "ref")
    assert project_activity(tmp_path) > 0
    assert _safe_mtime(tmp_path / "missing") is None
    link = tmp_path / "link"
    try:
        link.symlink_to(git, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert _safe_mtime(link) is None
    write(tmp_path / "package.json", "{}")
    (tmp_path / "node_modules").mkdir()
    make_old(tmp_path / "package.json")
    counts: list[int] = []
    result = scan(tmp_path, older_than=0, progress=counts.append, types=("not-a-type",))
    assert result.items == []
    assert counts == [1]


def test_scan_root_symlink_and_scandir_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        link = tmp_path / "root-link"
        link.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        link = None
    if link is not None:
        assert scan(link).skipped
    real_scandir = os.scandir

    def broken(path):
        if Path(path) == tmp_path:
            raise PermissionError(13, "denied")
        return real_scandir(path)

    monkeypatch.setattr("devsweep.scanner.os.scandir", broken)
    result = scan(tmp_path)
    assert any("permission denied" in entry.reason for entry in result.skipped)


def test_project_activity_skips_target_symlink_and_size_records_inner_symlink(tmp_path: Path) -> None:
    write(tmp_path / "package.json", "{}")
    target = tmp_path / "node_modules"
    target.mkdir()
    outside = tmp_path.parent / "size-outside"
    outside.mkdir(exist_ok=True)
    try:
        (target / "link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    make_old(tmp_path / "package.json")
    result = scan(tmp_path, older_than=1)
    assert result.items
    assert any(entry.path == target / "link" for entry in result.skipped)
