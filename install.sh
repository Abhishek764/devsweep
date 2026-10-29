#!/usr/bin/env sh
set -eu

REPOSITORY="git+https://github.com/abhishek764/devsweep"

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "devsweep requires Python 3.9 or newer. Install python3 first." >&2
    exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
    printf '%s\n' "devsweep requires Python 3.9 or newer." >&2
    exit 1
fi

printf '%s\n' "Downloading and installing DevSweep; the installer will show transfer progress when available."

if command -v pipx >/dev/null 2>&1; then
    PIP_PROGRESS_BAR=on pipx install "$REPOSITORY"
elif command -v uv >/dev/null 2>&1; then
    uv tool install "$REPOSITORY"
else
    PIP_PROGRESS_BAR=on python3 -m pip install --user "$REPOSITORY"
fi

case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ;;
    *)
        printf '%s\n' "Warning: ${HOME}/.local/bin is not on PATH; add it to run devsweep." >&2
        ;;
esac
printf '%s\n' "Installed devsweep. Try: devsweep scan ."
printf '%s\n' "To update later: devsweep update"
