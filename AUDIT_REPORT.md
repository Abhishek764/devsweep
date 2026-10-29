# DevSweep repository audit and implementation report

- **Verified:** 2026-10-30
- **Branch:** `fix/windows-stability-cross-platform`
- **Base:** local `origin/fix/windows-stability-cross-platform`; no commit, push, merge, issue edit, or release was performed.
- **Repository:** [Abhishek764/devsweep](https://github.com/Abhishek764/devsweep)

## Repository and GitHub state

The checkout was clean at the start of this work. The branch points at `26d1789` (`feat: add core devsweep implementation and tests`) and tracks the same-named origin branch. The local worktree is now modified; see the session handoff below.

GitHub issue search returned **40 open issues, #4–#43**, last checked 2026-10-30. Their titles, reported priority, local confirmation/fix state, and follow-up status are indexed in [docs/engineering/ISSUE_TRACKER.md](docs/engineering/ISSUE_TRACKER.md). Search results did not reliably return assignees, labels, timestamps, or issue state fields, so none are inferred. Issue descriptions often explicitly call findings proposed or request platform verification.

- **PR #45:** GitHub fetch reports closed. Its PR body records historical fixes for Python 3.9 TOML, Windows path handling, cleaner validation, determinism, templates and installer behavior. No review submissions or inline threads were returned in the current connector query. The PR body reports 45 passed/8 skipped and six CI jobs passed at that time; current CI checks were not queried.
- **PR #44:** GitHub fetch reports open. No review submissions or inline threads were returned. Its body asks reviewers to check installer changes and CI; current checks were not queried.

## Confirmed local findings and changes

The current code confirmed four gaps relevant to open P0 issues:

1. `repository_status()` returned `unknown` when Git metadata was missing and scan only rejected `dirty` and `unavailable`. This allowed an unverifiable state through with `--force`. It now distinguishes `not-repository` from `unknown`; unknown always skips, even with force. Regression added. **Issue #4: locally addressed; remote issue remains open.**
2. Git status did not pass `--no-optional-locks`. It now does; a focused command-argument regression was added. This mitigates incidental index updates but the test does not measure all Git metadata side effects. **Issue #6: locally addressed; remote issue remains open.**
3. Project activity ignored every directory whose name appeared in the cleanup registry, even if it was ordinary source. Activity traversal now excludes only directories whose target marker matches. A `bin/cli.js` regression was added. **Issue #7: locally addressed; remote issue remains open.**
4. Windows cache discovery exposed all of `%LOCALAPPDATA%/JetBrains` as removable. That broad parent is removed from the cache registry pending a narrow, verified cache path. A regression asserts it is absent. **Issue #8: broad Windows path addressed; remaining cache policies still need review.**
5. `_config_value()` selected hard-coded defaults when CLI options were omitted, ignoring configured values. It now falls back to the TOML setting while explicit CLI values retain precedence; empty XDG/APPDATA settings use home-based defaults. Regression coverage was added. **Issue #14: core precedence bug addressed locally; documentation/type-name aspects remain.**
6. Git status looked only for `.git` directly under the inferred project path, missing a parent repository when scanning a nested directory. Repository status now checks ancestor metadata and runs Git from the nested project. A dirty-parent scan regression was added. **Issue #5: nested parent repository case addressed locally; worktree coverage remains.**
7. Ignore matching treated `**/dist` as requiring at least one directory, so root-level `dist` did not match. The zero-directory case is now handled with root and nested regressions. **Issue #15: this glob defect is addressed; full Git-ignore semantics remain open.**
8. The CI workflow had no workflow permissions declaration. It now requests only `contents: read`; the release workflow's `contents: write` remains job-scoped. Action refs still use major tags. **Issue #30: permissions narrowed; action pinning remains.**

Additional known safety limitations: cleanup's path validation and recursive removal are separate operations, so a residual TOCTOU race exists; size calculation counts logical file sizes and may overcount hard links; broader protected database/persistent-data policy (#10) and mount/traversal limits (#13) remain open.

## Prioritized remaining backlog

1. **P0 safety:** #10 protected database/persistent data; #11 path replacement and symlink race; #12 global cache confirmation; #13 root/mount/traversal limits; review all remaining global cache paths (#8).
2. **P0 verification:** run cross-platform CI for the local #4/#6/#7/#8 changes; issue state is not modified remotely.
3. **P1 correctness:** verify #5 enclosing Git repository/worktree handling; recheck #9/#14 fixes claimed by the closed PR; reproduce #15–#23 config, ignore, CLI, cache, Docker and cleanup findings.
4. **P1 packaging/security:** resolve #27 name collision; address #28–#32 compatibility, installer, CI permissions, version metadata and coverage.
5. **P2 measured/features:** profile before #24–#26 performance work; defer #33–#43 feature requests until safety and distribution are settled.

## Distribution audit

- Local metadata declares distribution `devsweep` version `0.1.0`, Python ≥3.9, setuptools, and console entry point `devsweep.cli:main`.
- `python -m build` succeeded and produced a wheel and source archive.
- A fresh temporary Windows virtual environment installed the wheel with `pip install --no-deps`; its installed `devsweep --help` succeeded.
- `python -m pip check` passed in the project environment. `uv 0.13.0` is installed, but a uv tool install was not run. `twine check` could not run because Twine is not installed.
- **Release blocker:** PyPI JSON lookup for `devsweep` returned an existing, different `devsweep` 0.2.0 project with a different summary and no project URLs. Do not publish this project's 0.1.0 under that name; choose a distinct distribution and import-package name first. No package was published.
- No npm launcher exists, and no npm package-name check was performed because Python remains the authoritative implementation and npm is optional.

## Verification performed

On Windows with the repository Python 3.11 environment:

- `.venv\\Scripts\\python.exe -m pytest -q -rs` — **61 passed, 10 skipped, 0 failed**.
- `.venv\\Scripts\\python.exe -m ruff check .` — passed.
- `.venv\\Scripts\\python.exe -m pip check` — passed.
- `.venv\\Scripts\\python.exe -m build` — wheel and sdist built successfully.
- Fresh temporary venv: wheel installation and installed `devsweep --help` — passed.
- `git diff --check` — passed; Git printed expected LF-to-CRLF conversion warnings for edited files.

Skips: symlink creation is unavailable due Windows privilege/filesystem limits; POSIX-only error-handler tests are not applicable on Windows; case-sensitive path ordering is not applicable on Windows. Linux, macOS and other Python versions were not tested locally in this session. Current remote CI was not queried.

## Engineering context and decisions

- Architecture and data flow: [docs/engineering/ARCHITECTURE.md](docs/engineering/ARCHITECTURE.md)
- Issue and PR index: [docs/engineering/ISSUE_TRACKER.md](docs/engineering/ISSUE_TRACKER.md)
- Priorities: [docs/engineering/ROADMAP.md](docs/engineering/ROADMAP.md)
- Limitations: [docs/engineering/KNOWN_LIMITATIONS.md](docs/engineering/KNOWN_LIMITATIONS.md)
- Decision: [0001 — Fail-closed Git status and narrow cache scope](docs/engineering/decisions/0001-fail-closed-git-and-cache-scope.md)
- Engineering changes: [docs/engineering/CHANGELOG_ENGINEERING.md](docs/engineering/CHANGELOG_ENGINEERING.md)

## Session handoff

- **Branch:** `fix/windows-stability-cross-platform`
- **Working tree:** modified locally; no commit/push.
- **Changed code:** `src/devsweep/git.py`, `scanner.py`, `caches.py`, `cli.py`, `config.py`, and `ignore.py`; CI in `.github/workflows/ci.yml`; tests in `test_scanner.py`, `test_caches.py`, `test_cli.py`, `test_ignore.py`, and `test_output_config_docker.py`.
- **Changed records:** this audit report and engineering context, architecture, issue tracker, roadmap, limitations, decision log, ADR, and engineering changelog.
- **Next recommended work:** resolve package/import naming before any registry release; then implement the P0 protected-path/global-cache/root-scope safeguards and validate with the Ubuntu/Windows CI matrix.
- **Pending external action:** maintainer decision on a unique package/import name; verify remote CI before considering issues fixed. No publication, PR change, or issue update was authorized or performed.
