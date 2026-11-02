from __future__ import annotations

import os
from pathlib import Path

import pytest
from conftest import try_create_symlink

from devsweep.platform_utils import error_text
from devsweep.sizes import allocated_size, directory_size, human_size, parse_size, path_size


def _try_create_hardlink(link: Path, target: Path) -> bool:
    """Create a hard link, returning False when the platform/filesystem does not support it."""
    try:
        os.link(target, link)
    except (NotImplementedError, OSError):
        return False
    return True


def test_directory_size_skips_symlinks(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "a.txt").write_bytes(b"abc")
    if not try_create_symlink(folder / "link", tmp_path, target_is_directory=True):
        pytest.skip("symlink creation is unavailable for this user or filesystem")
    errors: list[tuple[Path, str]] = []
    assert directory_size(folder, lambda path, reason: errors.append((path, reason))) == 3
    assert errors and errors[0][1] == "symlink skipped"
    assert path_size(folder / "missing", lambda path, reason: errors.append((path, reason))) == 0


def test_sizes_and_human_formatting(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_bytes(b"x" * 2048)
    assert path_size(path) == 2048
    assert human_size(0) == "0 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(1024**2) == "1.0 MB"
    assert human_size(1024**5) == "1024.0 TB"
    assert parse_size("100MB") == 100 * 1024**2
    assert parse_size("2.5 GB") == int(2.5 * 1024**3)
    assert parse_size("12") == 12
    assert parse_size("1.5B") == 1
    with pytest.raises(ValueError):
        parse_size("-1")
    with pytest.raises(ValueError):
        parse_size("nope")
    with pytest.raises(ValueError):
        parse_size("nopeMB")
    with pytest.raises(ValueError):
        parse_size("-1MB")
    assert error_text(PermissionError(13, "denied")) == "permission denied"


def test_path_size_handles_symlink_and_stat_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link"
    if not try_create_symlink(link, target):
        pytest.skip("symlink creation is unavailable for this user or filesystem")
    assert path_size(link) == 0

    class BrokenPath:
        def is_symlink(self):
            raise OSError("broken")

    errors: list[tuple[Path, str]] = []
    assert path_size(BrokenPath(), lambda path, reason: errors.append((path, reason))) == 0  # type: ignore[arg-type]


def test_directory_size_handles_entry_stat_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenEntry:
        path = os.fspath(tmp_path / "broken")

        def is_symlink(self):
            return False

        def is_dir(self, follow_symlinks=False):
            return False

        def is_file(self, follow_symlinks=False):
            return True

        def stat(self, follow_symlinks=False):
            raise PermissionError(13, "denied")

    class Entries:
        def __enter__(self):
            return iter((BrokenEntry(),))

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("devsweep.sizes.os.scandir", lambda path: Entries())
    errors: list[tuple[Path, str]] = []
    assert directory_size(tmp_path, lambda path, reason: errors.append((path, reason))) == 0
    assert errors


def test_directory_size_counts_hard_linked_inode_once(tmp_path: Path) -> None:
    """Hard-linked files sharing an inode are counted only once."""
    if not hasattr(os, "link"):
        pytest.skip("os.link is unavailable on this platform")
    folder = tmp_path / "folder"
    folder.mkdir()
    target = folder / "target.txt"
    target.write_bytes(b"x" * 1024)
    link = folder / "link.txt"
    if not _try_create_hardlink(link, target):
        pytest.skip("hard-link creation is unavailable for this user or filesystem")
    errors: list[tuple[Path, str]] = []
    # Same inode referenced by two directory entries: size counted once, not twice.
    assert directory_size(folder, lambda path, reason: errors.append((path, reason))) == 1024


def test_directory_size_counts_independent_files_separately(tmp_path: Path) -> None:
    """Non-hard-linked files are each counted individually."""
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "a.txt").write_bytes(b"a" * 512)
    (folder / "b.txt").write_bytes(b"b" * 512)
    errors: list[tuple[Path, str]] = []
    assert directory_size(folder, lambda path, reason: errors.append((path, reason))) == 1024


def test_allocated_size_returns_none_when_st_blocks_unavailable(tmp_path: Path) -> None:
    """allocated_size() returns None on platforms without st_blocks (e.g. Windows)."""
    path = tmp_path / "file"
    path.write_bytes(b"x" * 1024)
    if hasattr(os.stat(path), "st_blocks"):
        result = allocated_size(path)
        assert result is not None
        assert result >= 0
    else:
        assert allocated_size(path) is None


def test_allocated_size_none_for_missing_path(tmp_path: Path) -> None:
    """allocated_size() returns None for a path that does not exist."""
    assert allocated_size(tmp_path / "missing") is None
