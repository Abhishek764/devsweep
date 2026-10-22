# Contributing to devsweep

Thanks for helping make disk cleanup safer. Safety regressions are critical:
changes must preserve the no-follow, strict-root-boundary, marker, dirty-Git,
and dry-run guarantees.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest --cov=devsweep.scanner --cov=devsweep.cleaner --cov=devsweep.ignore --cov=devsweep.sizes
.venv/bin/ruff check .
```

On Windows, use `.venv\Scripts\python.exe` and
`.venv\Scripts\ruff.exe` instead. Runtime code must remain standard-library
only.

## Adding an ecosystem target

Add one `TargetSpec` row to `src/devsweep/targets.py` and use an existing
marker kind whenever possible. A normal addition is five lines: the registry
row, a test project, the expected scan assertion, and any documentation table
entry. If a new kind of evidence is genuinely required, add one conservative
branch to `marker_matches`, then add tests for both positive and negative
cases. Never make a directory name alone sufficient evidence.

Every target must have a marker file, must not follow links, and must be
covered by scanner and cleaner safety tests before review.

## Pull requests

Use a conventional commit prefix (`feat:`, `fix:`, `test:`, `docs:`, or
`chore:`), include the actual commands you ran, and explain any platform
specific behavior. Do not include credentials, private paths, or real user
data in tests or examples.
