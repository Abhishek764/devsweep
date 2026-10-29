# Architecture

Last reviewed: 2026-10-30. This describes the checked-out source, not a target architecture.

## Runtime flow

`cli.py` parses arguments and configuration, calls a focused operation, and renders through `output.py`. A project scan in `scanner.py` normalizes/validates the root, loads ignore rules (`ignore.py`), traverses directories without following symlinks/reparse points, identifies directories through `targets.py`, sizes candidates (`sizes.py`), checks Git state/activity (`git.py` and scanner activity walk), and returns `ScanResult`/`Target` records. `cleaner.py` accepts those records, validates root containment, target markers, link state, and target identity again, then calls `platform_utils.safe_rmtree`. Cache reporting/cleaning is separate in `caches.py`; Docker reporting is isolated in `docker.py`.

## Responsibilities and interfaces

| Module | Responsibility / principal interface |
|---|---|
| `cli.py` | `main()` and subcommand orchestration |
| `config.py` | Optional TOML configuration |
| `targets.py` | Immutable `TargetSpec` registry and marker validation |
| `scanner.py` | `scan(...) -> ScanResult`; traversal and candidate policy |
| `git.py` | Git availability, repository status, activity paths |
| `ignore.py` | Ignore-file and explicit exclusion matching |
| `sizes.py` | Directory size and byte formatting/parsing |
| `cleaner.py` | `clean(...) -> CleanResult`; repeated safety validation and deletion |
| `caches.py` | Explicit global cache locations and opt-in cleanup |
| `platform_utils.py` | Path normalization, Windows reparse checks and safe tree removal |
| `output.py` | Human and JSON presentation, progress |
| `docker.py` | Docker CLI reporting |

The scan-to-clean boundary is a `Target` dataclass containing type, path, project, estimated bytes, and activity. This object is untrusted when passed to cleanup: cleanup reconstructs the registry evidence and checks containment rather than trusting scan results. Python caches use their nearest Python marker as the project for activity and display; Git status independently checks enclosing repositories. `--force` affects the dirty repository/activity policy; unknown Git status still skips. `--yes` authorizes deletion of selected recognized targets; default operation is non-destructive.

## Safety boundaries and known limits

- Registry marker evidence authorizes candidate discovery; names by themselves do not.
- Scanner traversal uses `os.scandir` and does not descend into symlink/reparse entries or a recognized target.
- Cleanup rejects paths outside the scan root, links/reparse points, missing/changed targets, and targets whose marker no longer matches.
- The last validation and `shutil.rmtree` are separate path-based operations. A concurrent hostile replacement can still race this boundary; the implementation does not claim atomic race prevention.
- Git status is read-only with optional locks disabled. Unknown status is fail-closed. A non-repository directory is distinct from a repository whose status cannot be established.
- Global caches are a separate feature and may contain expensive-to-regenerate or user-valued data. Maven/NuGet global packages are opt-in; the broad Windows JetBrains path is removed pending a narrower verified target.
- Filesystem size reports count logical file sizes and may double-count hard links or differ from allocated blocks.

## Packaging

`pyproject.toml` is the metadata source. Setuptools discovers `src/devsweep`; `devsweep.cli:main` is the console entry point. Python 3.9+ is declared and `tomli` is conditional for Python <3.11. The source tree includes no npm launcher. Local build artifacts exist in `dist/`, but their provenance/freshness was not established during this review.

## Constraints

Linux and Windows are declared/supported in metadata and CI. macOS is not explicitly supported. CI currently covers Ubuntu and Windows with Python 3.9, 3.11, and 3.13, running Ruff and pytest with workflow `contents: read` permissions. No type checker, package artifact validation, installed-wheel smoke test, action SHA pinning, or npm job was found in the workflow.
