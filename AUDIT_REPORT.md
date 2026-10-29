# DevSweep stability audit report

- **Date:** 2026-10-22
- **Branch:** `fix/windows-stability-cross-platform`
- **Pull request:** [#45](https://github.com/Abhishek764/devsweep/pull/45)
- **Base:** `main`

## Summary

The audit reproduced 11 failing tests on Windows with Python 3.11.9. The failures shared Windows path and reparse-point handling defects, alongside failures in cleanup validation and the configuration test. These issues are fixed on the implementation branch. The separate repository setup PR, [#44](https://github.com/Abhishek764/devsweep/pull/44), remains open and unchanged.

## Confirmed causes and fixes

- **TOML on Python 3.9 and 3.10:** `load_config()` returned `{}` before trying to parse configuration. It now falls back to `tomli`, declared only for Python versions below 3.11. Missing and invalid files remain optional.
- **Win32 attributes:** `GetFileAttributesW` had no ctypes argument or return types. Its invalid-attributes value could be treated as a reparse-point bitmask. The call now uses `LPCWSTR` and `DWORD`, with tests for ordinary, reparse, and invalid attributes.
- **Extended Windows paths:** `scandir()` entries created from `\\?\` paths leaked into public `Path` objects. This broke equality, ignore-pattern matching, scan-root containment, and cleanup. Prefixes are now removed at the filesystem result boundary while extended paths remain available for I/O.
- **Cleaner validation:** Missing paths were classified as newly appeared links. Cleanup now distinguishes disappeared targets, checks project and target containment and marker evidence, and revalidates the target identity immediately before removal. A regression test also covers forged results tied to an unrelated project root.
- **Deterministic output:** Sort ties now use the original path as a secondary key. A CLI test confirms JSON output remains parseable when progress diagnostics are written to stderr.
- **Contributor setup:** The issue and PR templates are populated, security vulnerability guidance points to private advisories, and the PowerShell installer checks native command exit codes before reporting success.

## Files changed

- `src/devsweep/platform_utils.py`, `scanner.py`, and `sizes.py`: Win32 attributes and path normalization.
- `src/devsweep/cleaner.py`: containment, marker, missing-target, and identity revalidation.
- `src/devsweep/config.py`, `pyproject.toml`, and `README.md`: Python 3.9/3.10 TOML support and corrected documentation.
- `tests/conftest.py` and scanner, cleaner, safety, config, sizes, and CLI tests: regressions and narrowly handled symlink availability.
- `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/config.yml`, and `.github/pull_request_template.md`: contributor forms.
- `install.ps1`: installer exit-code handling.

## Verification results

### Baseline

- Environment: Windows, Python 3.11.9.
- `.venv\Scripts\python.exe -m pytest -q`: **11 failed, 29 passed, 6 skipped**.
- `.venv\Scripts\python.exe -m ruff check .`: passed.

### Final local checks

- `.venv\Scripts\python.exe -m pip install -e ".[dev]"`: passed.
- `.venv\Scripts\python.exe -m ruff check .`: passed.
- `.venv\Scripts\python.exe -m pytest -q -rs`: **45 passed, 8 skipped, 0 failed**.
- `.venv\Scripts\python.exe -m pytest --cov=devsweep.scanner --cov=devsweep.cleaner --cov=devsweep.ignore --cov=devsweep.sizes --cov-report=term-missing`: **45 passed, 8 skipped; 88% coverage** across the four configured modules.
- `.venv\Scripts\python.exe -m pip check`: passed.
- TOML parsing with `tomllib`, YAML parsing of both workflows and both issue templates, `bash -n install.sh`, PowerShell parser validation of `install.ps1`, and `git diff --check`: passed.

Seven local skips are symlink-dependent tests skipped because Windows returned privilege error 1314. The remaining skip is a case-sensitive sort test, which is inapplicable on Windows. The symlink test helper raises for unexpected filesystem errors instead of broadly skipping them.

### Remote CI

The repository workflow targets Ubuntu and Windows with Python 3.9, 3.11, and 3.13. All six jobs passed on the final PR run. An earlier run failed because the Win32 unit test changed the process-wide `os.name`; the test now calls the isolated Windows attribute helper directly, and the rerun passed.

## Environment coverage and limitations

- Local verification was performed only on Windows with Python 3.11.9. Python 3.9, 3.13, and Ubuntu were verified by the remote CI matrix.
- Local symlink creation requiring elevated Windows privilege was unavailable; those cases were skipped locally. The CI matrix passed.
- Cleaner validation is repeated immediately before deletion and compares the target identity. The final validation and path-based `shutil.rmtree()` call are still separate filesystem operations, so the implementation cannot make a concurrent hostile replacement race fully atomic on every supported platform.
- `install.sh` was syntax-checked; its implementation was not changed. `install.ps1` was syntax-checked, but the installer was not run end-to-end.

## Git and PR state

- Commits: `296c924` (implementation) and `ff604ef` (CI test isolation fix).
- PR #45 is open against `main`; all six latest CI jobs passed.
- PR #44 remains open as the separate setup PR.
- No PR was merged.
