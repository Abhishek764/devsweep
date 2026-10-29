# DevSweep project context

Last reviewed: 2026-10-30. Treat GitHub for live issue/PR state and `pyproject.toml` for package metadata.

## Product and users

DevSweep is an alpha Python CLI that discovers explicitly recognized developer-generated directories and offers a dry-run-first cleanup workflow. Its users are individual developers and build/CI maintainers who need to understand what will be removed and why. It is not a generic recursive “delete cache/build/temp” tool.

## Current behavior

- `scan` traverses a supplied root, applies ignore/exclude rules, identifies targets from the registry in `src/devsweep/targets.py`, calculates logical sizes, checks project activity and Git status, and emits text or JSON.
- `clean` consumes recognized targets and is non-destructive by default; deletion requires explicit selection/confirmation. It validates containment, markers, symlink/reparse status and target identity again.
- `caches` reports a fixed list of global cache paths, with some high-risk locations opt-in. Treat cache deletion separately from project target cleanup.
- `docker` reports Docker disk usage through the Docker CLI.

## Safety rules

1. A directory name alone never authorizes project cleanup; registry marker rules must match.
2. Do not follow symlinks or Windows reparse points during discovery or deletion.
3. Keep cleanup strictly inside the requested scan root and reject dangerous roots.
4. Skip dirty projects by default and fail closed when Git status is unknown. `--force` does not bypass unknown status or path/marker checks.
5. Use dry-run by default; require explicit user selection for destructive actions.
6. Keep failure reasons visible and do not overstate reclaimed bytes or atomic race protection.

## Support and distribution

`pyproject.toml` declares Python ≥3.9, Linux and Windows, a setuptools `src` layout, and the `devsweep` console entry point. CI is configured for Ubuntu and Windows on Python 3.9, 3.11, and 3.13. macOS is not currently an explicit support target. Pip/uv installation is intended but registry availability and clean-environment installs have not been verified in this review. There is no npm launcher.

## Architecture and priorities

See [ARCHITECTURE.md](ARCHITECTURE.md). Current module boundaries are small and task-focused; avoid a plugin framework or second cleanup implementation without a concrete need.

Priority order: (1) safety issues and global cache scope, (2) verified functional bugs, (3) cross-platform and packaging validation, (4) coverage and contributor/docs gaps, (5) measured performance, then justified features. The live issue index is [ISSUE_TRACKER.md](ISSUE_TRACKER.md); open issues do not automatically mean their reported behavior is currently reproducible.

## Known unknowns

- Path-based recursive deletion still has a TOCTOU race after the final validation.
- Filesystem logical sizes can overcount hard links and do not equal allocated/reclaimed blocks.
- Current task's tests ran only on Windows; no current remote CI result was queried.
- macOS semantics remain untested and unsupported.
- Current pip/uv registry availability, wheel/sdist cleanliness, and installation behavior remain unverified.
- Historical rationale for existing implementation choices is unknown unless recorded in an ADR.
