# Known limitations

Last reviewed: 2026-10-30.

- **Deletion race:** Final path/identity validation and recursive deletion are separate operations. A concurrent adversary may replace a path in the gap. No atomic cross-platform guarantee is made.
- **Filesystem identity:** Target identity relies on filesystem `st_dev`/`st_ino`/`st_mode`; inode semantics can be weak or unavailable on some filesystems.
- **Platform coverage:** Current local validation was on Windows. Linux coverage is represented by the configured remote matrix but its current run was not independently checked in this session. macOS is out of scope and untested.
- **Symlink coverage:** Ten tests are skipped in the current Windows test run for platform/privilege-dependent symlink behavior; inspect `pytest -rs` output before treating them as equivalent to coverage.
- **Global caches:** Cache cleanup can remove expensive-to-regenerate or locally valuable data. Maven/NuGet global package paths are optional; the Windows JetBrains parent is now excluded. Other target policies still deserve review against current product data layouts.
- **Git behavior:** Git status is checked per candidate and not cached. Unknown state skips; callers should not interpret `--force` as bypassing this check.
- **Size estimates:** Logical bytes may double-count hard links and do not represent allocated blocks/reclaimed space exactly.
- **Distribution:** Metadata declares a Python package and console command, but this session did not build/install wheel and sdist, verify registry availability, or test uv. No npm launcher exists.
- **CI/release:** Workflow uses major-version action tags and was not hardened in this task. Release workflow creates a GitHub release on tags; PyPI publishing is disabled in the checked-in file.
- **Remote status:** Issues #4–#43 are reported open by GitHub search on 2026-10-30. PR #45 is closed; #44 remains open. Current CI checks could not be queried in this session.
