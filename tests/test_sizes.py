from __future__ import annotations

import os
from pathlib import Path

import pytest

from devsweep.sizes import _error_text, directory_size, human_size, parse_size, path_size


def test_directory_size_skips_symlinks(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "a.txt").write_bytes(b"abc")
    try:
        (folder / "link").symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
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
    assert _error_text(PermissionError(13, "denied")) == "permission denied"


def test_path_size_handles_symlink_and_stat_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
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
