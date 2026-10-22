from __future__ import annotations

import os
from pathlib import Path

import pytest
from conftest import try_create_symlink

from devsweep.platform_utils import (
    is_reparse_point,
    is_symlink_or_reparse,
    path_key,
    to_public_path,
)
from devsweep.scanner import scan


def test_path_key_is_normalized_and_case_insensitive_on_windows() -> None:
    value = path_key(Path("/tmp/a/../b"))
    assert value.endswith(os.path.normcase(os.path.join("tmp", "b")))


def test_extended_windows_paths_are_normalized_for_public_paths() -> None:
    assert str(to_public_path(r"\\?\C:\work\target")) == r"C:\work\target"
    assert str(to_public_path(r"\\?\UNC\server\share\target")) == r"\\server\share\target"
    assert path_key(r"\\?\C:\work\target") == path_key(r"C:\work\target")


@pytest.mark.parametrize(
    ("attributes", "expected"),
    ((0x10, False), (0x0400, True), (0xFFFFFFFF, False)),
)
def test_windows_attributes_classify_reparse_points_correctly(
    monkeypatch: pytest.MonkeyPatch, attributes: int, expected: bool
) -> None:
    import devsweep.platform_utils as platform_utils

    class FakeFunction:
        argtypes = None
        restype = None

        def __call__(self, _path: str) -> int:
            return attributes

    fake_function = FakeFunction()

    class FakeKernel:
        GetFileAttributesW = fake_function

    class FakeWindll:
        kernel32 = FakeKernel()

    monkeypatch.setattr(platform_utils.os, "name", "nt")
    monkeypatch.setattr(platform_utils.ctypes, "windll", FakeWindll(), raising=False)
    monkeypatch.setattr(platform_utils, "to_extended_path", lambda path: str(path))
    monkeypatch.setattr(platform_utils.os.path, "lexists", lambda _path: False)

    assert platform_utils.is_reparse_point(Path("C:/candidate")) is expected
    assert fake_function.argtypes
    assert fake_function.restype is not None


def test_symlink_outside_root_is_skipped(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-project"
    outside.mkdir()
    (outside / "package.json").write_text("{}", encoding="utf-8")
    if not try_create_symlink(tmp_path / "node_modules", outside, target_is_directory=True):
        pytest.skip("symlink creation is unavailable for this user or filesystem")
    result = scan(tmp_path, older_than=0)
    assert not result.items
    assert result.skipped


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point behavior")
def test_windows_reparse_point_helpers_exist() -> None:
    path = Path("C:/Windows")
    assert isinstance(is_reparse_point(path), bool)
    assert isinstance(is_symlink_or_reparse(path), bool)
