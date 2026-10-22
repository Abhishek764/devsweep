from __future__ import annotations

import os
from pathlib import Path

import pytest

from devsweep.platform_utils import is_reparse_point, is_symlink_or_reparse, path_key
from devsweep.scanner import scan


def test_path_key_is_normalized_and_case_insensitive_on_windows() -> None:
    value = path_key(Path("/tmp/a/../b"))
    assert value.endswith(os.path.normcase(os.path.join("tmp", "b")))


def test_symlink_outside_root_is_skipped(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-project"
    outside.mkdir()
    (outside / "package.json").write_text("{}", encoding="utf-8")
    try:
        (tmp_path / "node_modules").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    result = scan(tmp_path, older_than=0)
    assert not result.items
    assert result.skipped


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point behavior")
def test_windows_reparse_point_helpers_exist() -> None:
    path = Path("C:/Windows")
    assert isinstance(is_reparse_point(path), bool)
    assert isinstance(is_symlink_or_reparse(path), bool)
