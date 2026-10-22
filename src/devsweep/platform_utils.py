"""Small platform-specific helpers used by the safety boundary."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

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


def is_reparse_point(path: Path) -> bool:
    """Detect Windows junctions/reparse points without traversing them."""

    if os.name != "nt":
        return False
    try:
        attributes = ctypes.windll.kernel32.GetFileAttributesW(ctypes.c_wchar_p(to_extended_path(path)))
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

    value = os.path.abspath(os.fspath(path))
    return os.path.normcase(os.path.normpath(value))


def resolved_key(path: Path | str) -> str:
    """Normalize a real path, resolving existing links for safety checks."""

    return path_key(Path(os.path.realpath(os.fspath(path))))


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


def running_on_windows() -> bool:
    return sys.platform == "win32"
