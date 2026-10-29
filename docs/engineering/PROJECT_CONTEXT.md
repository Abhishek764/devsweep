# DevSweep — Project Context

> Living document describing the product vision, users, core behavior, and
> engineering constraints for DevSweep.

| Field       | Value                                |
|-------------|--------------------------------------|
| Product     | DevSweep                             |
| Version     | 0.1.0                                |
| Status      | Alpha — functional, narrowing scope  |
| License     | MIT                                  |
| Python      | ≥ 3.9                                |
| Platforms   | Linux, Windows                       |
| Last review | 2026-10-29                           |

---

## 1. Product Vision

**DevSweep is a safety-first developer disk cleanup CLI.**

Developers accumulate build artifacts, dependency caches, and toolchain
by-products across dozens of projects. DevSweep scans a directory tree,
identifies reclaimable disk space, and deletes it — but only when the evidence
is unambiguous and the operation is safe.

---

## 2. Target Users

| Persona | Description |
|---------|-------------|
| Individual developer | Runs `devsweep scan ~/projects` periodically to reclaim space on a laptop. |
| CI maintainer | Cleans build caches between pipeline runs. |
| DevOps engineer | Audits disk usage across shared build hosts. |

---

## 3. Core Behavior

1. **Scan** — Walk a directory tree, match projects against a registry of 25
   known target specifications, calculate reclaimable size.
2. **Clean** — Delete identified targets after a double safety re-check,
   respecting dry-run default.
3. **Caches** — Report global cache locations (pip, npm, cargo, etc.) per
   platform.
4. **Docker** — Report Docker disk usage via `docker system df`.

---

## 4. Non-Goals

- **macOS explicit support** — Not tested or targeted (may work incidentally).
- **GUI** — CLI only; rich TUI is out of scope.
- **Daemon / watch mode** — No background process; run on demand.
- **Cloud storage** — Local filesystems only.
- **Package manager integration** — DevSweep does not modify lock files or
  dependency manifests.

---

## 5. Safety Principles

DevSweep's safety model is the product's defining characteristic. All 13
principles are load-bearing:

| # | Principle | Description |
|---|-----------|-------------|
| 1 | Marker evidence mandatory | A target is only recognized when its marker file/directory is present. |
| 2 | Symlinks never followed | All symlink targets are skipped to prevent escaping the scan root. |
| 3 | Deletion contained below scan root | No path outside the scan root is ever deleted. |
| 4 | Dangerous roots refused | Scanning `/`, `C:\`, home directories, etc. is rejected outright. |
| 5 | Dirty Git projects skipped | Projects with uncommitted changes are not cleaned. |
| 6 | Staleness based on project activity | Only stale projects (no recent activity) are candidates. |
| 7 | Known marker rules conservative | The target registry errs on the side of not matching. |
| 8 | Targets atomic | Each target is a single unit — no double-counting across specs. |
| 9 | Ignore files respected | `.devsweepignore` and similar patterns are honored. |
| 10 | Failures isolated | One failed deletion does not abort the entire run. |
| 11 | Uncertainty means skip | If the tool cannot determine safety, the target is skipped. |
| 12 | Deletion explicit | Dry-run is the default; `--no-dry-run` required for actual deletion. |
| 13 | Interrupts clean | Ctrl-C leaves the filesystem in a consistent state. |

---

## 6. Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux    | Supported | Primary development platform. |
| Windows  | Supported | Long path support, reparse point handling, case-insensitive matching. |
| macOS    | Out of scope | No explicit support; may work but untested. |

---

## 7. Distribution

| Channel | Command |
|---------|---------|
| PyPI (pip) | `pip install devsweep` |
| uv | `uv pip install devsweep` |
| npm (optional launcher) | `npx devsweep` |

---

## 8. Module Overview

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `cli.py` | ~380 | Argparse CLI, subcommands (scan/clean/caches/docker), config merge |
| `scanner.py` | ~269 | Core scanning engine, target discovery, parallel sizing via `ThreadPoolExecutor` |
| `cleaner.py` | ~195 | Deletion with double safety re-check, TOCTOU mitigation |
| `targets.py` | ~150 | Data-driven registry of 25 `TargetSpec`s, marker matching |
| `caches.py` | ~150 | Global cache locations per platform |
| `platform_utils.py` | ~200 | Windows long paths, reparse points, dangerous roots, `safe_rmtree`, `error_text` |
| `output.py` | ~117 | ANSI colors, tables, progress, JSON output |
| `sizes.py` | ~86 | Size calculation, human formatting, parsing |
| `ignore.py` | ~92 | Conservative gitignore-style pattern matching |
| `git.py` | ~52 | Git status checking |
| `docker.py` | ~48 | Docker disk reporting |
| `config.py` | ~34 | Optional TOML config loading |

---

## 9. Engineering Priorities

1. **Safety** — Never delete something the user did not intend.
2. **Correctness** — Accurate size reporting and target identification.
3. **Cross-platform** — Linux and Windows parity.
4. **Performance** — Parallel sizing; single-pass scanning where possible.
5. **Simplicity** — Small codebase, minimal dependencies.

---

## 10. Open Questions / Unknowns

- **macOS support** — Community demand is unclear; no contributor has tested.
- **Plugin system** — Should third parties be able to register custom
  `TargetSpec`s? Deferred.
- **`git_available()` caching** — Called on every `repository_status()`; may be
  worth caching but no performance data yet.
- **FAT32/exFAT inode identity** — `st_ino == 0` makes the TOCTOU identity
  check a no-op on these filesystems.
