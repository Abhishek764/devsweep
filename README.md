# devsweep

Safely find and remove reclaimable developer build artifacts, dependency folders, and caches.

`devsweep` is a conservative, dry-run-first CLI for Linux and Windows 10/11.
It only lists a directory when its ecosystem marker proves that the directory
is generated data. If safety cannot be established, it skips the path instead
of guessing.

## Demo

```text
$ devsweep scan . --older-than 30d
Reclaimable project folders
TYPE          SIZE    PROJECT       LAST ACTIVITY  PATH
------------  ------  ------------  -------------  ---------------------
node_modules  1.4 GB  example-app   47 days ago    packages/app/node_modules
venv          184 MB  tools         3 months ago   tools/.venv
Total reclaimable: 1.6 GB
Skipped: 1

$ devsweep clean . --older-than 30d
Would delete:
- packages/app/node_modules (1.4 GB)
- tools/.venv (184 MB)
Total space that would be freed: 1.6 GB
Skipped: 0; failures: 0
```

The first `clean` invocation is a preview. Nothing is removed unless you use
`--yes` or confirm an interactive selection.

## Installation

`devsweep` requires Python 3.9 or newer. Python 3.9 and 3.10 install the small
`tomli` compatibility dependency for TOML configuration; Python 3.11 and newer
use the standard library. The commands below install the current GitHub version.

### Linux and Windows

```bash
pipx install git+https://github.com/abhishek764/devsweep
uv tool install git+https://github.com/abhishek764/devsweep
uvx --from git+https://github.com/abhishek764/devsweep devsweep scan .
```

Use either `pipx` or `uv tool install` for a persistent installation. `uvx`
runs the command without installing it permanently.

### Linux installer

```bash
curl -fsSL https://raw.githubusercontent.com/abhishek764/devsweep/main/install.sh | sh
```

The installer checks Python, prefers `pipx`, then `uv`, and finally falls back
to `python3 -m pip install --user`. It warns if the user script directory is
not on `PATH`.

### Windows PowerShell installer

```powershell
irm https://raw.githubusercontent.com/abhishek764/devsweep/main/install.ps1 | iex
```

The PowerShell installer uses `pipx`, then `uv`, then `py -m pip install
--user`, and prints `PATH` advice when needed.

## Usage

Run `devsweep --help` or `devsweep COMMAND --help` for the live option list.

### Scan project folders

```bash
devsweep scan [PATH]
devsweep scan . --older-than 30d
devsweep scan ~/src --sort age --min-size 100MB
devsweep scan . --type node_modules --type venv --exclude 'vendor/private-*'
devsweep scan . --json
```

`PATH` defaults to the current directory. Results are sorted by size descending
by default. Use `--sort size`, `--sort age`, or `--sort path`. `--older-than`
accepts durations such as `7d`, `2w`, `3m`, and `1y`; the default is `30d`.
`--min-size` accepts bytes and binary units such as `100MB` or `2GB`.

The JSON form contains `items`, `total_bytes`, `skipped`, and `skipped_count`.
It is intended for scripts and does not contain ANSI color codes.

### Clean project folders

```bash
# Preview only; this is the default.
devsweep clean .

# Delete every item that passed the safety checks.
devsweep clean . --yes

# Select interactively when running in a terminal.
devsweep clean .
# Enter: all, 1, 1-3,5, or q

# Emit a machine-readable plan/result.
devsweep clean . --json
devsweep clean . --json --yes
```

Interactive clean accepts `all`, one-based item numbers, comma-separated
numbers, ranges such as `1-3,5`, or `q`. Invalid input is rejected and the
prompt remains open. Non-interactive execution without `--yes` remains a
dry-run.

`--force` allows scanning dirty Git projects. It does not disable marker,
symlink, path-containment, dangerous-root, or deletion revalidation checks.
`--i-know-what-i-am-doing` is required when cleaning `/`, a home directory, a
drive root, or protected system directories.

### Global caches

```bash
devsweep caches
devsweep caches --verbose
devsweep caches --yes
devsweep caches --include-maven --include-nuget --json
```

Only existing paths from the known-location table below are considered. Cache
cleanup is also dry-run by default. `--verbose` includes the command normally
used by the tool to clear each cache. Maven repositories and NuGet global
packages are excluded unless their explicit opt-in flags are present because
they are slow to rebuild.

### Docker

```bash
devsweep docker
devsweep docker --yes
devsweep docker --json
```

Without `--yes`, this reports `docker system df` only. With `--yes`, it runs
`docker image prune -f` and `docker builder prune -f`. It never prunes volumes
or containers. If Docker is missing or its daemon is stopped, the command
prints a friendly message and exits successfully.

### Output and common flags

These flags are available on the applicable commands:

| Flag | Meaning |
| --- | --- |
| `--json` | Machine-readable output |
| `--quiet` | Suppress normal human output |
| `--verbose` | Show skipped details or cache clear commands |
| `--older-than DURATION` | Require project inactivity for the duration |
| `--min-size SIZE` | Filter by minimum reclaimable size |
| `--type TYPE` | Repeatable target-type filter |
| `--exclude PATTERN` | Repeatable relative glob exclusion |
| `--force` | Override dirty-Git protection |
| `--yes` | Perform deletion without confirmation |
| `--no-color` | Disable ANSI colors |

Color is automatically disabled when output is not a TTY or `NO_COLOR` is
set. Windows virtual-terminal mode is enabled when supported. Consoles that
cannot encode Unicode receive ASCII fallbacks.

## How safety works

Safety is the primary feature. The following rules are enforced:

1. **Marker evidence is mandatory.** A directory name alone is never enough.
   `node_modules` requires `package.json`; build outputs require their
   ecosystem manifest; virtual environments require `pyvenv.cfg`; and
   Git-ignore requirements are enforced where specified.
2. **Symlinks are never followed.** Symlinked targets are skipped and reported.
   On Windows, directory junctions and reparse points are treated as
   symlinks using both link checks and the Windows reparse-point attribute.
3. **Deletion stays below the scan root.** Real paths are checked again before
   deletion and the target must be a strict descendant of the root. Windows
   comparisons normalize separators, drive letters, and case.
4. **Dangerous roots are refused.** Clean refuses `/`, the home directory,
   drive roots, `/usr`, `/etc`, `/bin`, `/var`, `C:\Windows`, `C:\Program
   Files`, and their protected descendants unless the explicit
   `--i-know-what-i-am-doing` override is supplied.
5. **Dirty Git projects are skipped.** `git status --porcelain` is checked in
   the project root. `--force` is required to override uncommitted changes.
   If Git is unavailable, the project is treated as unknown and only the
   age rule is applied.
6. **Staleness is based on project activity.** The newest mtime among project
   source files and `.git/HEAD` or `.git/index` is used. Detected target
   folders are excluded from that calculation. The default inactivity period
   is 30 days.
7. **Known marker rules are conservative.** `build`, `dist`, `bin`, `obj`,
   and `vendor` are never removed without their required manifest and, where
   required, a `.gitignore` entry.
8. **Detected targets are atomic.** The scanner never descends into a
   detected target, so nested `node_modules` and similar folders are not
   double-counted.
9. **Ignore files are respected.** `.devsweepignore` in the scan root uses
   simple gitignore-style globs. `--exclude` adds more patterns.
10. **Failures are isolated.** Permission errors, disappearing files,
    read-only files, long paths, locked files, and inaccessible directories
    are recorded and scanning continues. Windows deletion uses the `\\?\`
    long-path form and retries read-only entries. Linux paths without the
    execute bit are skipped safely.
11. **Uncertainty means skip.** An item is not listed or deleted if its safety
    cannot be established.
12. **Deletion is explicit.** Clean is dry-run by default and requires
    `--yes` or interactive confirmation. Freed bytes are measured after each
    successful deletion.
13. **Interrupts are clean.** Ctrl+C stops further deletion, reports what has
    already been removed, and exits with code 130.

Expected exit codes are `0` for success, `1` when a deletion fails, `2` for a
usage or invalid-root error, and `130` for Ctrl+C.

## Supported ecosystems

| Target | Required evidence |
| --- | --- |
| `node_modules` | `package.json` in the parent project |
| `.next`, `.nuxt`, `.svelte-kit` | `package.json` in the parent project |
| `dist` | `package.json` and `dist` listed in `.gitignore` |
| `venv`, `.venv`, `env` | `pyvenv.cfg` inside the directory |
| `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox` | Nearby `pyproject.toml`, `setup.py`, `requirements.txt`, or Python source |
| Rust `target` | `Cargo.toml` |
| Maven `target` | `pom.xml` |
| Gradle `build`, `.gradle` | `build.gradle`, `build.gradle.kts`, or `settings.gradle` |
| Composer `vendor` | `composer.json` and Git-ignore entry |
| Go `vendor` | `go.mod`, `vendor/modules.txt`, and Git-ignore entry |
| Terraform `.terraform` | Nearby `*.tf` file |
| .NET `bin`, `obj` | Nearby `*.csproj` or `*.sln`, plus Git-ignore entry |
| Dart `.dart_tool`, `build` | `pubspec.yaml` |

The registry is intentionally data-driven. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the five-line process for adding an
ecosystem.

## Global cache locations

Only paths that exist are shown. Environment variables are resolved at runtime;
usernames are never hardcoded.

### Linux

| Tool/cache | Location | Normal clear command |
| --- | --- | --- |
| npm | `~/.npm/_cacache` | `npm cache clean --force` |
| Yarn | `$XDG_CACHE_HOME/yarn` or `~/.cache/yarn` | `yarn cache clean` |
| pnpm | `$XDG_DATA_HOME/pnpm/store` or `~/.local/share/pnpm/store` | `pnpm store prune` |
| pip | `$XDG_CACHE_HOME/pip` or `~/.cache/pip` | `pip cache purge` |
| uv | `$XDG_CACHE_HOME/uv` or `~/.cache/uv` | `uv cache clean` |
| Cargo registry/git | `~/.cargo/registry/cache`, `~/.cargo/git` | `cargo cache --autoclean` |
| Gradle | `~/.gradle/caches` | `gradle --stop` then remove selected cache |
| Go build | `$XDG_CACHE_HOME/go-build` or `~/.cache/go-build` | `go clean -cache` |
| thumbnails | `~/.cache/thumbnails` | remove selected thumbnail cache |
| VS Code | `~/.config/Code/Cache` | remove selected VS Code cache |
| JetBrains | `~/.cache/JetBrains` | remove selected JetBrains cache |
| Maven, opt-in | `~/.m2/repository` | remove selected Maven repository |

`XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `XDG_CONFIG_HOME` are respected.

### Windows

| Tool/cache | Location | Normal clear command |
| --- | --- | --- |
| npm | `%LOCALAPPDATA%\npm-cache` | `npm cache clean --force` |
| Yarn | `%LOCALAPPDATA%\Yarn\Cache` | `yarn cache clean` |
| pnpm | `%LOCALAPPDATA%\pnpm\store` | `pnpm store prune` |
| pip | `%LOCALAPPDATA%\pip\Cache` | `pip cache purge` |
| uv | `%LOCALAPPDATA%\uv\cache` | `uv cache clean` |
| Cargo registry/git | `%USERPROFILE%\.cargo\registry\cache`, `%USERPROFILE%\.cargo\git` | `cargo cache --autoclean` |
| Gradle | `%USERPROFILE%\.gradle\caches` | `gradle --stop` then remove selected cache |
| Go build | `%LOCALAPPDATA%\go-build` | `go clean -cache` |
| VS Code | `%APPDATA%\Code\Cache`, `CachedData` | remove selected VS Code cache |
| JetBrains | `%LOCALAPPDATA%\JetBrains` | remove selected JetBrains cache |
| NuGet HTTP | `%LOCALAPPDATA%\NuGet\v3-cache` | `dotnet nuget locals http-cache --clear` |
| NuGet temp | `%TEMP%\NuGetScratch` | `dotnet nuget locals temp --clear` |
| NuGet packages, opt-in | `%NUGET_PACKAGES%` or `%USERPROFILE%\.nuget\packages` | `dotnet nuget locals global-packages --clear` |
| Maven, opt-in | `%USERPROFILE%\.m2\repository` | remove selected Maven repository |

Windows paths use `%LOCALAPPDATA%`, `%APPDATA%`, `%USERPROFILE%`, `%TEMP%`,
and `%NUGET_PACKAGES%` when set. The command never substitutes a fixed
username.

## Configuration

Configuration is optional. It is read from:

- Linux: `$XDG_CONFIG_HOME/devsweep/config.toml`, or `~/.config/devsweep/config.toml`
- Windows: `%APPDATA%\devsweep\config.toml`

Configuration is supported on every supported Python version. Python 3.9 and
3.10 use `tomli`; Python 3.11 and newer use the standard-library `tomllib`.
Missing or invalid files are ignored. CLI flags override config values.

Example:

```toml
older_than = "45d"
min_size = "50MB"
types = ["node_modules", "venv"]
exclude = ["archive/**"]
sort = "age"
force = false
no_color = false
```

The supported keys correspond to the common flags: `older_than`, `min_size`,
`types` (or `type`), `exclude`, `sort`, `force`, `no_color`, `quiet`,
`verbose`, `json`, and `yes`.

## `.devsweepignore`

Create `.devsweepignore` in the scan root to exclude trusted paths:

```gitignore
# Comments and blank lines are ignored.
legacy/**
vendor/private-*
```

Patterns are simple gitignore-style globs relative to the scan root. Add
one-off exclusions with `--exclude PATTERN`. An excluded directory is not
descended into and is reported in verbose/JSON skipped details.

## FAQ

### Does devsweep delete source files?

No. It only considers directories with an explicit generated-data marker, and
it performs a second safety validation immediately before deletion. When in
doubt, it skips the path.

### Why was a target skipped?

Use `--verbose` or `--json`. Common reasons are recent project activity,
uncommitted Git changes, a missing marker, an ignore pattern, a symlink or
junction, and a permission error.

### Why is `dist` not listed?

For JavaScript projects, `dist` must have `package.json` in its project and
must also be listed in `.gitignore`. This avoids deleting a deliberately
tracked distribution directory.

### Can I clean a home directory or drive root?

Not by accident. Clean refuses dangerous roots. If you have reviewed the
entire plan and intentionally need that scope, pass
`--i-know-what-i-am-doing`; ordinary marker and containment checks still apply.

### What happens if a file is locked on Windows?

The item is reported as in use or failed and the command continues. No other
target is sacrificed to make a locked deletion succeed.

### Does devsweep follow symlinks or junctions?

Never. This is not configurable. Symlinked targets, directory junctions, and
Windows reparse points are skipped.

### Does it support macOS?

macOS is out of scope for the supported target matrix. The implementation does
not add macOS-specific behavior and should fail conservatively rather than
assuming Linux or Windows paths.

### Does it work in WSL?

Running devsweep inside WSL on `/mnt/c` paths works, but can be slow because
the scan crosses the Windows/Linux filesystem boundary. For Windows folders,
the native Windows version is recommended.

### Does cache cleanup run the tool clear commands?

No. Cache cleanup deletes only the exact known cache directories listed in the
table. Verbose mode shows the conventional tool command for reference; it
does not execute arbitrary commands. Docker is the exception and has its own
strictly limited command set described above.

### How do I report a safety issue?

For a security vulnerability, report it through the repository's private
[security advisory form](https://github.com/Abhishek764/devsweep/security/advisories/new).
Do not publish exploit details, private paths, or credentials in a public issue.
For other safety regressions, open a bug report with the operating system,
Python version, exact command, and a synthetic reproduction. False-positive
deletion is a critical bug and should be labeled clearly.

## Development and contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, test and
lint commands, target-registry instructions, and pull-request expectations.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

Runtime code uses the standard library, with `tomli` installed only on Python
3.9 and 3.10. Changes that affect scanning or
deletion must include regression tests for both the safe positive case and the
nearby unsafe case.

## License

MIT. See [`LICENSE`](LICENSE).
