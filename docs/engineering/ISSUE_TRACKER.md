# Issue and PR tracker

Last checked: 2026-10-30 via connected GitHub issue search and issue/PR fetch. GitHub is authoritative. Search returned open issues #4–#43 (40 issues). The connector did not return issue timestamps/assignees/labels reliably for search results; no assignment or reproducibility is inferred. Bodies commonly label findings as proposed or requiring verification. Titles and issue links are indexed below; linked reports are not treated as confirmed bugs unless independently reproduced here.

## Open issues

| Issue | Title | Current local assessment |
|---|---|---|
| [#4](https://github.com/Abhishek764/devsweep/issues/4) | Skip cleanup targets when Git status cannot be verified | Confirmed gap; fixed locally: `unknown` always skipped, regression test added. |
| [#5](https://github.com/Abhishek764/devsweep/issues/5) | Detect the enclosing Git repository when scanning nested directories | Confirmed: checking only `<project>/.git` missed a parent repo; status now searches ancestors and uses Git from the nested project. Added dirty-parent-repository scan regression. |
| [#6](https://github.com/Abhishek764/devsweep/issues/6) | Make Git status checks read-only | Added `--no-optional-locks`; focused argument regression added. Full metadata-side-effect behavior not independently measured. |
| [#7](https://github.com/Abhishek764/devsweep/issues/7) | Do not ignore real source folders when calculating project activity | Confirmed gap; fixed to skip only marker-confirmed targets; regression added for `bin/cli.js`. |
| [#8](https://github.com/Abhishek764/devsweep/issues/8) | Narrow global cache targets and protect locally installed artifacts | Confirmed broad Windows JetBrains target removed; remaining cache policies require review. |
| [#9](https://github.com/Abhishek764/devsweep/issues/9) | Verify Windows extended-path handling for exclusions and root containment | PR #45 reports fix; PR now closed. Current issue search still lists issue open; remote CI not checked this turn. |
| [#10](https://github.com/Abhishek764/devsweep/issues/10) | Add an explicit protected-path policy for databases and persistent data | Not implemented/verified; high priority safety work. |
| [#11](https://github.com/Abhishek764/devsweep/issues/11) | Harden deletion against path replacement and symlink races | Cleaner revalidates but residual path race is documented; unresolved. |
| [#12](https://github.com/Abhishek764/devsweep/issues/12) | Require confirmation for destructive global cache operations | Not independently audited; high priority. |
| [#13](https://github.com/Abhishek764/devsweep/issues/13) | Add safe root, mount, and traversal limits | Not independently audited; high priority. |
| [#14](https://github.com/Abhishek764/devsweep/issues/14) | Load configuration values correctly and safely | Confirmed: omitted CLI options ignored config values; fixed precedence and empty XDG fallback locally with regressions. Remaining issue details (README type naming) still need review. |
| [#15](https://github.com/Abhishek764/devsweep/issues/15) | Implement correct Gitignore-style matching | Confirmed narrow edge: `**/dist` did not match root-level `dist`; fixed and tested root/nested patterns. Full Git-ignore semantics and nested ignore files remain outside current implementation. |
| [#16](https://github.com/Abhishek764/devsweep/issues/16) | Keep Python cache project detection scoped to the correct project | Reproduced and fixed locally: Python caches now keep the nearest Python marker as their project for age and display; repository status still searches enclosing Git repositories. Added sibling activity regression. |
| [#17](https://github.com/Abhishek764/devsweep/issues/17) | Handle read-only files and permission failures accurately on every OS | Not independently verified across OS. |
| [#18](https://github.com/Abhishek764/devsweep/issues/18) | Avoid reporting every internal symlink as a skipped target | Not independently reproduced this turn. |
| [#19](https://github.com/Abhishek764/devsweep/issues/19) | Validate CLI inputs and return useful exit codes | Not independently audited. |
| [#20](https://github.com/Abhishek764/devsweep/issues/20) | Number cleanup candidates in interactive selection | Not independently audited. |
| [#21](https://github.com/Abhishek764/devsweep/issues/21) | Report accurate reclaimed space after cleanup | Not independently audited; logical and physically freed bytes can differ. |
| [#22](https://github.com/Abhishek764/devsweep/issues/22) | Handle cache cleanup failures and unavailable tools consistently | Not independently audited. |
| [#23](https://github.com/Abhishek764/devsweep/issues/23) | Make Docker pruning consequences explicit | Not independently audited. |
| [#24](https://github.com/Abhishek764/devsweep/issues/24) | Cache Git status and project activity per project | Performance claim unmeasured; defer pending profile. |
| [#25](https://github.com/Abhishek764/devsweep/issues/25) | Apply target and metadata filters before expensive directory sizing | Inspect scan cost and type-filter semantics; no benchmark yet. |
| [#26](https://github.com/Abhishek764/devsweep/issues/26) | Add scan progress and cancellation for large workspaces | Determinate terminal progress bar added for candidate sizing; cancellation remains limited to existing interrupt handling and needs separate audit. |
| [#27](https://github.com/Abhishek764/devsweep/issues/27) | Resolve the PyPI distribution name and import-package collision | Confirmed blocker: PyPI JSON endpoint returns an existing `devsweep` 0.2.0 distribution with a different summary and no project URLs. Do not publish under this name; choose a non-colliding distribution/import name before release. |
| [#28](https://github.com/Abhishek764/devsweep/issues/28) | Modernize Python support and configuration compatibility | Metadata says Python ≥3.9; support changes require explicit compatibility audit. |
| [#29](https://github.com/Abhishek764/devsweep/issues/29) | Expand platform and Python-version coverage | Current CI: Ubuntu/Windows × 3.9/3.11/3.13; no macOS. |
| [#30](https://github.com/Abhishek764/devsweep/issues/30) | Harden GitHub Actions permissions and dependencies | CI now has workflow-level `contents: read`; release job keeps scoped `contents: write`. Action tags remain major-version references and are not SHA-pinned. |
| [#31](https://github.com/Abhishek764/devsweep/issues/31) | Use one source of truth for the version and update package metadata | Version is currently `pyproject.toml`; inspect duplication separately. |
| [#32](https://github.com/Abhishek764/devsweep/issues/32) | Make installation reliable on managed Python environments | Not verified. |
| [#33](https://github.com/Abhishek764/devsweep/issues/33) | Add macOS support with platform-specific cache rules | Explicitly unsupported/out of scope today. |
| [#34](https://github.com/Abhishek764/devsweep/issues/34) | Group Python cache targets by project | Feature request; defer until correctness baseline. |
| [#35](https://github.com/Abhishek764/devsweep/issues/35) | Add more ecosystem targets with strict marker evidence | Feature request; defer pending each target's safety evidence. |
| [#36](https://github.com/Abhishek764/devsweep/issues/36) | Add optional move-to-trash cleanup and recovery log | Feature request; platform/dependency trade-offs unassessed. |
| [#37](https://github.com/Abhishek764/devsweep/issues/37) | Add CI-friendly failure and machine-readable absolute paths | Feature request; JSON schema/exit contracts need design. |
| [#38](https://github.com/Abhishek764/devsweep/issues/38) | Correct size accounting for hard links and allocated disk blocks | Known limitation; defer until expected semantics are defined. |
| [#39](https://github.com/Abhishek764/devsweep/issues/39) | Add selective cache cleanup and active-process safeguards | Feature request; existing selection and race safety require audit. |
| [#40](https://github.com/Abhishek764/devsweep/issues/40) | Improve size and duration parsing | Feature request; inspect parser before scope. |
| [#41](https://github.com/Abhishek764/devsweep/issues/41) | Document safety guarantees, limitations, and risk tiers | Partly addressed in engineering records; user-facing README work remains. |
| [#42](https://github.com/Abhishek764/devsweep/issues/42) | Add a destructive-operation safety regression suite | Current suite has safety tests; requested matrix/property tests are not complete. |
| [#43](https://github.com/Abhishek764/devsweep/issues/43) | Add static typing and consistent error handling | No type checker configured; error taxonomy not complete. |

## Pull requests

| PR | Live state | Review/CI observation |
|---|---|---|
| [#45](https://github.com/Abhishek764/devsweep/pull/45) | Closed (GitHub fetched 2026-10-30) | No review submissions or inline review threads returned. PR body reports prior 45 passed/8 skipped and six CI jobs passed; current CI checks were not queried. Branch history contains the implementation commits. |
| [#44](https://github.com/Abhishek764/devsweep/pull/44) | Open | No review submissions or inline review threads returned. PR body requests CI review; current checks were not queried. Do not modify remotely without authorization. |

## Backlog order

1. P0: #10, #11, #12, #13 and remaining #8 cache-path audit.
2. P0: validate and confirm #4/#6/#7 local fix with cross-platform CI.
3. P1: #5 and verify already-implemented #9/#14 against remote status.
4. P1: audit #15–#23 and packaging/CI #27–#32 with focused reproductions.
5. P2: measure #24–#26; then triage #33–#43 features and quality work.
