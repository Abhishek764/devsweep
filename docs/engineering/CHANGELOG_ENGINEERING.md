# Engineering changelog

## 2026-10-30 - Make Windows self-update reliable

- **Problem:** A running uv-managed `devsweep.exe` cannot replace its own tool environment because Windows locks the active `Scripts` directory. The old updater then fell back to an environment without pip.
- **Changes:** uv updates launched from a uv-managed Windows installation are deferred to a detached retry that runs after DevSweep exits; the command reports the scheduled state clearly.
- **Regression coverage:** Added an updater test proving the uv process is not run synchronously when deferral is selected.

## 2026-10-30 - Add an in-place update command

- **Request:** Installed users had no documented way to fetch newer DevSweep releases.
- **Changes:** Added `devsweep update`, which refreshes the GitHub installation through pipx, uv, or the active Python environment and preserves native package-manager download progress. Installers and README now show the command.
- **Verification:** `devsweep update --help`, Ruff, Python compilation, and `git diff --check` passed. No live update was run.

## 2026-10-30 - Scope Python cache activity to the nearest project

- **Problem:** GitHub issue #16 reproduced: when Python projects are nested under a workspace with its own Python marker, the outer marker replaced the nearest project and sibling activity could make a stale cache appear recent.
- **Changes:** Python cache project resolution now retains the nearest Python marker for labels and activity; Git status continues to inspect enclosing repositories.
- **Regression coverage:** Added two sibling Python projects, with recent activity in one and an old cache in the other; the cache remains associated with the stale project.
- **Verification:** Scanner tests: 19 passed, 4 skipped. Ruff and `git diff --check` passed on Windows.

## 2026-10-30 — Git and target-safety corrections

- **Problem:** Open reports #4, #6, #7, and #8 concern Git verification, incidental repository writes, activity detection, and an overly broad Windows JetBrains path. The current source confirmed those gaps.
- **Changes:** `git.py` distinguishes absent Git metadata from unknown status and runs status with optional locks disabled. `scanner.py` fails closed for unknown status (even with force) and only excludes directories positively recognized by a target marker. `caches.py` no longer offers the broad Windows JetBrains directory for deletion.
- **Regression tests:** Added scanner cases for source files under `bin`, unknown Git status under force, and the Git command flags; added Windows cache-target exclusion assertion.
- **Verification:** `.venv\\Scripts\\python.exe -m pytest -q -rs` — 57 passed, 10 skipped. `.venv\\Scripts\\python.exe -m ruff check .` and `python -m pip check` — passed. `python -m build` produced wheel and sdist; a fresh temporary venv installed the wheel and `devsweep --help` succeeded. `twine check` was unavailable because Twine is not installed. `git diff --check` passed with Git line-ending conversion warnings.
- **Distribution finding:** PyPI currently serves a different `devsweep` 0.2.0 project at the requested distribution name. Local metadata remains 0.1.0; publication under this name is blocked pending a naming decision.
- **Limitations:** Tests and wheel install ran on Windows only. The race between final path validation and recursive deletion remains. The remote issue and PR state is recorded in `ISSUE_TRACKER.md`.

## 2026-10-30 — Honor optional configuration values

- **Problem:** GitHub issue #14 reports that settings from the TOML file do not take effect when corresponding CLI options are omitted. `_config_value()` returned the hard-coded default for `None` instead of consulting the config.
- **Changes:** Omitted and false boolean CLI values now fall back to configuration; explicit non-default CLI values retain precedence. Empty `XDG_CONFIG_HOME`/`APPDATA` values fall back to the home-based default instead of creating a relative config path.
- **Regression tests:** Added tests for config-only older-than, minimum size, sort, force, target and exclusion settings; CLI precedence; and empty XDG config home.
- **Verification:** `.venv\\Scripts\\python.exe -m pytest -q -rs` — 60 passed, 10 skipped. Ruff, pip check, and `git diff --check` passed.
- **Limitations:** The issue remains open remotely; other reported config/documentation mismatches have not all been addressed.

## 2026-10-30 — Nested Git state, ignore glob and workflow permissions

- **Problems:** Nested scans missed enclosing Git repositories (#5); `**/dist` failed to match a root-level target (#15); CI did not declare minimal workflow permissions (#30).
- **Changes:** Git status searches `.git` metadata from the project through its ancestors; the ignore matcher handles zero-directory `**/` prefixes; CI now declares `contents: read`.
- **Regression tests:** A scan below a dirty parent repo is skipped; root and nested `**/dist` patterns match; existing wildcard tests remain.
- **Verification:** `.venv\\Scripts\\python.exe -m pytest -q -rs` — 61 passed, 10 skipped. Ruff, pip check, and `git diff --check` passed.
- **Remaining:** Git worktree coverage and full ignore semantics are not implemented. Workflow action references still use major tags instead of immutable commit SHAs. GitHub issue states were not updated.

## 2026-10-30 — Graffiti branding and progress feedback

- **Request:** Add DevSweep graffiti branding on the GitHub landing page, a scan progress bar, and download progress during installation.
- **Changes:** Added `assets/devsweep-graffiti.svg` and placed it at the top of the README. Replaced the CLI's count-only scan indicator with a determinate terminal bar written to stderr; JSON stdout stays clean and non-TTY/quiet runs remain silent. Install scripts label the download/install step and enable pip's native transfer bar; uv/pipx output is passed through.
- **Regression coverage:** Existing TTY JSON scan test now checks that the progress bar reports completion without corrupting JSON. Scanner test verifies total candidate count is supplied to the progress callback.
- **Verification:** Full pytest suite, Ruff, SVG XML parsing, PowerShell parser validation, Bash syntax validation, and `git diff --check` passed on Windows/WSL.
- **Limitations:** Installer transfer bars are provided by pipx/uv/pip and only appear when those tools detect a capable terminal. The installer was syntax-checked, not run against GitHub or a package registry.
