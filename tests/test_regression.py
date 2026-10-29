"""Regression tests for issues discovered during the 2026-10-29 audit.

Each test targets a specific confirmed bug.  The test should fail on the
unfixed code and pass after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from devsweep.platform_utils import (
    _read_only_retry_onerror,
    _read_only_retry_onexc,
    error_text,
    safe_rmtree,
)
from devsweep.targets import specs_for_directory

# ---------------------------------------------------------------------------
# A1: ctypes.wintypes must not crash on non-Windows platforms
# ---------------------------------------------------------------------------

def test_platform_utils_importable_on_all_platforms() -> None:
    """Regression: ``from ctypes import wintypes`` at module level crashed
    on Linux/macOS because ``ctypes.wintypes`` is a Windows-only module.

    The fix makes the import conditional on ``sys.platform == 'win32'``.
    This test verifies the module loads without ImportError on any platform.
    """
    import importlib
    mod = importlib.import_module("devsweep.platform_utils")
    # Verify the key public symbols exist regardless of platform.
    assert callable(mod.safe_rmtree)
    assert callable(mod.error_text)
    assert callable(mod.is_symlink_or_reparse)
    assert callable(mod.is_dangerous_root)


# ---------------------------------------------------------------------------
# A2/D1: shutil.rmtree onerror → onexc migration (Python 3.12+/3.14)
# ---------------------------------------------------------------------------

def test_safe_rmtree_deletes_directory_tree(tmp_path: Path) -> None:
    """safe_rmtree must remove a directory tree using the correct
    shutil.rmtree handler for the running Python version."""
    folder = tmp_path / "deleteme"
    folder.mkdir()
    (folder / "a.txt").write_text("hello")
    sub = folder / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("world")
    safe_rmtree(folder)
    assert not folder.exists()


def test_safe_rmtree_handles_read_only_on_windows(tmp_path: Path) -> None:
    """On Windows, safe_rmtree should retry after clearing read-only bits."""
    folder = tmp_path / "readonly"
    folder.mkdir()
    readonly_file = folder / "locked.txt"
    readonly_file.write_text("locked")
    if os.name == "nt":
        os.chmod(str(readonly_file), 0o444)
    safe_rmtree(folder)
    assert not folder.exists()


def test_read_only_retry_onerror_raises_on_non_windows() -> None:
    """The onerror handler must re-raise on non-Windows platforms."""
    if os.name == "nt":
        pytest.skip("This test validates non-Windows behavior")
    with pytest.raises(OSError, match="test error"):
        _read_only_retry_onerror(lambda _: None, "path", (None, OSError("test error"), None))


def test_read_only_retry_onexc_raises_on_non_windows() -> None:
    """The onexc handler must re-raise on non-Windows platforms."""
    if os.name == "nt":
        pytest.skip("This test validates non-Windows behavior")
    with pytest.raises(OSError, match="test error"):
        _read_only_retry_onexc(lambda _: None, "path", OSError("test error"))


# ---------------------------------------------------------------------------
# A3: specs_for_directory case-sensitivity mismatch on Windows
# ---------------------------------------------------------------------------

def test_specs_for_directory_case_insensitive_on_windows() -> None:
    """Regression: ``specs_for_directory`` used exact string comparison,
    while the scanner uses ``casefold()`` on Windows.  This meant the
    cleaner's re-validation in ``_is_current_target`` could fail on Windows
    for mixed-case directory names.

    The fix makes ``specs_for_directory`` case-insensitive on Windows.
    """
    # Regardless of platform, test both cases.
    lower = specs_for_directory("node_modules")
    assert len(lower) >= 1
    assert all(s.type == "node_modules" for s in lower)

    if os.name == "nt":
        # On Windows, mixed case must match.
        upper = specs_for_directory("Node_Modules")
        assert len(upper) == len(lower)
        assert all(s.type == "node_modules" for s in upper)

        mixed = specs_for_directory("NODE_MODULES")
        assert len(mixed) == len(lower)
    else:
        # On non-Windows, exact match only.
        upper = specs_for_directory("Node_Modules")
        assert len(upper) == 0


# ---------------------------------------------------------------------------
# F1: _read_only_retry deduplication
# ---------------------------------------------------------------------------

def test_read_only_retry_not_in_cleaner_or_caches() -> None:
    """Regression: ``_read_only_retry`` was duplicated in cleaner.py and
    caches.py.  The fix moves it to platform_utils.py.

    Verify neither cleaner nor caches has its own copy.
    """
    import devsweep.caches as caches_mod
    import devsweep.cleaner as cleaner_mod
    assert not hasattr(cleaner_mod, "_read_only_retry")
    assert not hasattr(caches_mod, "_read_only_retry")


# ---------------------------------------------------------------------------
# F2: error_text deduplication
# ---------------------------------------------------------------------------

def test_error_text_handles_permission_and_generic_errors() -> None:
    """The shared error_text function must handle PermissionError and
    generic OSError consistently."""
    assert error_text(PermissionError(13, "denied")) == "permission denied"
    assert error_text(OSError("disk full")) == "disk full"
    assert error_text(OSError()) == "OSError"


def test_error_text_not_in_scanner_or_sizes() -> None:
    """Regression: ``_error_text`` was duplicated in scanner.py and sizes.py.
    The fix moves it to platform_utils.py.

    Verify neither scanner nor sizes has its own copy.
    """
    import devsweep.scanner as scanner_mod
    import devsweep.sizes as sizes_mod
    assert not hasattr(scanner_mod, "_error_text")
    assert not hasattr(sizes_mod, "_error_text")


# ---------------------------------------------------------------------------
# F3: running_on_windows() removed
# ---------------------------------------------------------------------------

def test_running_on_windows_removed() -> None:
    """Regression: ``running_on_windows()`` was defined but never used.
    The fix removes it."""
    import devsweep.platform_utils as pu
    assert not hasattr(pu, "running_on_windows")


# ---------------------------------------------------------------------------
# E1/E2: pyproject.toml metadata completeness
# ---------------------------------------------------------------------------

def test_pyproject_has_urls_and_classifiers() -> None:
    """pyproject.toml must contain project.urls and all supported Python
    version classifiers."""
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    toml_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    project = data["project"]

    # URLs must be present
    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Source" in urls
    assert "Issues" in urls

    # All supported Python versions in classifiers
    classifiers = project.get("classifiers", [])
    for version in ("3.9", "3.10", "3.11", "3.12", "3.13"):
        expected = f"Programming Language :: Python :: {version}"
        assert expected in classifiers, f"Missing classifier: {expected}"
