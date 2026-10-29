"""Small platform-specific helpers used by the safety boundary."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    from ctypes import wintypes

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def to_extended_path(path: Path | str) -> str:
    """Return a Windows long-path spelling, or the normal spelling elsewhere."""

    value = os.fspath(path)
    if os.name != "nt":
        return value
    if value.startswith("\\\\?\\"):
        return value
    absolute = os.path.abspath(value)
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def to_public_path(path: Path | str) -> Path:
    """Strip Windows long-path prefixes from paths exposed by filesystem APIs."""

    value = os.fspath(path)
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def is_reparse_point(path: Path) -> bool:
    """Detect Windows junctions/reparse points without traversing them."""

    if os.name != "nt":
        return False
    return _windows_is_reparse_point(path)


def _windows_is_reparse_point(path: Path) -> bool:
    """Read Windows attributes; split out so Win32 behavior can be unit tested elsewhere."""

    try:
        get_attributes = ctypes.windll.kernel32.GetFileAttributesW
        get_attributes.argtypes = [wintypes.LPCWSTR]
        get_attributes.restype = wintypes.DWORD
        attributes = get_attributes(to_extended_path(path))
        if attributes == 0xFFFFFFFF:
            try:
                return os.path.lexists(os.fspath(path))
            except OSError:
                return True
        return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return False
    except OSError:
        # An inability to identify a Windows directory is handled by callers
        # as an unsafe/skip condition rather than risking a deletion.
        return True


def is_symlink_or_reparse(path: Path) -> bool:
    try:
        return path.is_symlink() or is_reparse_point(path)
    except OSError:
        return True


def path_key(path: Path | str) -> str:
    """Normalize a path for containment comparisons (case-insensitive on Windows)."""

    value = os.path.abspath(os.fspath(to_public_path(path)))
    return os.path.normcase(os.path.normpath(value))


def resolved_key(path: Path | str) -> str:
    """Normalize a real path, resolving existing links for safety checks."""

    return path_key(Path(os.path.realpath(os.fspath(to_public_path(path)))))


def is_strict_descendant(root: Path, target: Path) -> bool:
    """Return true only when target is below root, never when it equals root."""

    root_key = resolved_key(root)
    target_key = resolved_key(target)
    if root_key == target_key:
        return False
    try:
        return os.path.commonpath((root_key, target_key)) == root_key
    except ValueError:
        # Different Windows drives cannot be descendants.
        return False


def is_dangerous_root(root: Path) -> bool:
    """Identify roots where an accidental clean would be disproportionately risky."""

    try:
        absolute = Path(os.path.abspath(os.fspath(root)))
        key = path_key(absolute)
        home = path_key(Path.home())
        if key == home:
            return True
        if os.name == "nt":
            drive, _ = os.path.splitdrive(str(absolute))
            drive_root = path_key(Path(drive + os.sep)) if drive else ""
            if drive_root and key == drive_root:
                return True
            forbidden = (
                Path(os.environ.get("WINDIR", r"C:\Windows")),
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            )
        else:
            if key == path_key(Path(os.sep)):
                return True
            forbidden = (Path("/usr"), Path("/etc"), Path("/bin"), Path("/var"))
        for item in forbidden:
            forbidden_key = path_key(item)
            try:
                if key == forbidden_key or os.path.commonpath((forbidden_key, key)) == forbidden_key:
                    return True
            except ValueError:
                continue
        return False
    except (OSError, ValueError):
        return True


def enable_virtual_terminal_processing() -> bool:
    """Enable ANSI processing on Windows consoles when possible."""

    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError, ValueError):
        return False


def supports_unicode(stream: object) -> bool:
    encoding = getattr(stream, "encoding", None) or ""
    return "utf" in encoding.lower()


# ---------------------------------------------------------------------------
# Shared helpers: rmtree with read-only retry, error text formatting
# ---------------------------------------------------------------------------


def _read_only_retry_onexc(func, path: str, exc: BaseException) -> None:
    """``onexc`` handler for Python >= 3.12."""
    if os.name != "nt":
        raise exc
    try:
        os.chmod(path, 0o700)
        func(path)
    except OSError as new_exc:
        raise new_exc from exc


def _read_only_retry_onerror(func, path: str, exc_info) -> None:
    """``onerror`` handler for Python < 3.12."""
    if os.name != "nt":
        raise exc_info[1]
    try:
        os.chmod(path, 0o700)
        func(path)
    except OSError as exc:
        raise exc from exc_info[1]


def safe_rmtree(path: Path | str) -> None:
    """Remove a directory tree, retrying read-only files on Windows.

    Uses ``onexc`` on Python >= 3.12 and ``onerror`` on older versions to
    avoid the deprecation warning introduced in 3.12 and the removal in 3.14.
    """
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_read_only_retry_onexc)
    else:
        shutil.rmtree(path, onerror=_read_only_retry_onerror)


def error_text(exc: BaseException) -> str:
    """Return a human-readable one-line description of a filesystem error."""
    if isinstance(exc, PermissionError):
        return "permission denied"
    return str(exc) or exc.__class__.__name__
