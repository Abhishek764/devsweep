from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from conftest import try_create_symlink

from devsweep.cleaner import CleanSafetyError, _read_only_retry, clean, parse_selection
from devsweep.scanner import Target, scan


def setup_target(root: Path) -> Path:
    (root / "package.json").write_text("{}", encoding="utf-8")
    target = root / "node_modules"
    target.mkdir()
    (target / "file.bin").write_bytes(b"junk")
    old = 1_000_000
    os.utime(root / "package.json", (old, old))
    return target


def test_parse_selection_supports_all_ranges_and_quit() -> None:
    assert parse_selection("all", 3) == [0, 1, 2]
    assert parse_selection("1-3, 5", 5) == [0, 1, 2, 4]
    assert parse_selection("q", 3) == []
    with pytest.raises(ValueError):
        parse_selection("0", 3)
    with pytest.raises(ValueError):
        parse_selection("3-1", 3)
    with pytest.raises(ValueError):
        parse_selection("", 3)


def test_clean_is_dry_run_by_default(tmp_path: Path) -> None:
    setup_target(tmp_path)
    result = scan(tmp_path, older_than=1)
    assert len(result.items) == 1
    clean_result = clean(tmp_path, result.items)
    assert clean_result.planned == result.items
    assert (tmp_path / "node_modules").exists()


def test_clean_yes_deletes_only_target_and_reports_freed_bytes(tmp_path: Path) -> None:
    target = setup_target(tmp_path)
    result = scan(tmp_path, older_than=1)
    clean_result = clean(tmp_path, result.items, yes=True)
    assert clean_result.failures == []
    assert clean_result.deleted[0].path == target
    assert clean_result.freed_bytes >= 4
    assert not target.exists()
    assert (tmp_path / "package.json").exists()


def test_clean_selection_deletes_selected_items_only(tmp_path: Path) -> None:
    setup_target(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "package.json").write_text("{}", encoding="utf-8")
    (other / "node_modules").mkdir()
    os.utime(other / "package.json", (1_000_000, 1_000_000))
    result = scan(tmp_path, older_than=1, sort="path")
    assert len(result.items) == 2
    clean(tmp_path, result.items, selection="1")
    assert not result.items[0].path.exists()
    assert result.items[1].path.exists()


def test_clean_refuses_dangerous_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devsweep.cleaner.is_dangerous_root", lambda path: True)
    with pytest.raises(CleanSafetyError):
        clean(tmp_path, [])


def test_clean_skips_changed_or_outside_target(tmp_path: Path) -> None:
    setup_target(tmp_path)
    result = scan(tmp_path, older_than=1)
    target = result.items[0]
    outside = tmp_path.parent / "outside-target"
    outside.mkdir()
    replacement = target.path
    replacement.rename(tmp_path / "old-node-modules")
    if not try_create_symlink(replacement, outside, target_is_directory=True):
        pytest.skip("symlink creation is unavailable for this user or filesystem")
    clean_result = clean(tmp_path, [target], yes=True)
    assert clean_result.deleted == []
    assert clean_result.skipped
    assert outside.exists()


def test_clean_handles_marker_change_and_missing_target(tmp_path: Path) -> None:
    setup_target(tmp_path)
    result = scan(tmp_path, older_than=1)
    item = result.items[0]
    (tmp_path / "package.json").unlink()
    changed = clean(tmp_path, [item], yes=True)
    assert changed.skipped
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    shutil.rmtree(item.path)
    gone = clean(tmp_path, [item], yes=True)
    assert gone.skipped[0].reason == "already gone, skipped"


def test_clean_handles_invalid_roots_and_delete_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = setup_target(tmp_path)
    item = scan(tmp_path, older_than=1).items[0]
    with pytest.raises(CleanSafetyError):
        clean(tmp_path / "missing", [item])
    monkeypatch.setattr("devsweep.cleaner.shutil.rmtree", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("locked")))
    result = clean(tmp_path, [item], yes=True)
    assert result.failures[0].reason == "in use, skipped"
    assert target.exists()


def test_clean_accepts_explicit_index_iterable_and_reports_outside(tmp_path: Path) -> None:
    setup_target(tmp_path)
    item = scan(tmp_path, older_than=1).items[0]
    outside_project = tmp_path.parent / "other-project"
    outside_project.mkdir()
    (outside_project / "package.json").write_text("{}", encoding="utf-8")
    outside_target = outside_project / "node_modules"
    outside_target.mkdir()
    outside = Target("node_modules", outside_target, outside_project, "other-project", 0, 1_000_000)
    result = clean(tmp_path, [item, outside], selection=[1])
    assert result.skipped and "outside" in result.skipped[0].reason
    assert item in result.planned


def test_clean_rejects_target_authorized_by_external_project_marker(tmp_path: Path) -> None:
    target = setup_target(tmp_path)
    item = scan(tmp_path, older_than=1).items[0]
    external_project = tmp_path.parent / "external-project"
    external_project.mkdir()
    (external_project / "package.json").write_text("{}", encoding="utf-8")
    forged = Target(item.type, item.path, external_project, item.project_name, item.size, item.activity)

    result = clean(tmp_path, [forged], yes=True)

    assert result.deleted == []
    assert result.skipped
    assert "project root is outside" in result.skipped[0].reason
    assert target.exists()


def test_read_only_retry_is_conservative_on_linux() -> None:
    with pytest.raises(OSError):
        _read_only_retry(lambda _: None, "missing", (None, OSError("no"), None))
