from __future__ import annotations

import errno
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def try_create_symlink(link: Path, target: Path, *, target_is_directory: bool = False) -> bool:
    """Create a test symlink, returning false only for known unsupported environments."""

    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except NotImplementedError:
        return False
    except OSError as exc:
        if os.name == "nt":
            unavailable = getattr(exc, "winerror", None) == 1314
        else:
            unavailable = exc.errno in {
                errno.EACCES,
                errno.EPERM,
                getattr(errno, "ENOSYS", -1),
                getattr(errno, "ENOTSUP", -1),
                getattr(errno, "EOPNOTSUPP", -1),
            }
        if not unavailable:
            raise
        return False
    return True
