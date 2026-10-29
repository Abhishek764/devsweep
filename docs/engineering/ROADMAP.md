# Roadmap

Updated 2026-10-30 from the current code review and live GitHub issue search. This is a local planning index; GitHub remains authoritative for issue state.

## P0 — data-loss and safety

1. **#8 — Narrow global cache targets.** Windows broad JetBrains path removed locally; review remaining cache paths and exact consequences before declaring resolved. Acceptance: fixture-proven paths, no parent/sibling deletion, platform review.
2. **#10 — Protected database/persistent data.** Add an explicit protection policy before cleanup plans can include recognized database/persistence fixtures. Dependency: define a conservative scope with maintainers.
3. **#11 — Replacement/symlink race.** Minimize race and add adversarial fixtures; document residual OS limitations.
4. **#12 — Global-cache confirmation.** Verify command confirmation semantics and risk messaging for each destructive cache.
5. **#13 — Root/mount/traversal limits.** Inspect mount boundary behavior and ensure dangerous roots stay refused.
6. **#4/#6/#7 — Git and activity.** Implemented locally with regression coverage; re-check issue status and remote CI before closure.

## P1 — correctness and compatibility

7. **#5 — Enclosing Git repository detection.** Confirm nested workspace/worktree behavior and add status caching only with tests.
8. **#9 — Windows extended paths.** PR #45 is closed; the audit reports fix and CI coverage, but issue remains open in current issue search. Reproduce/verify current tests and update issue externally only with authorization.
9. **#14 — configuration.** Core precedence and empty XDG fallback fixed locally; verify reported README type naming and remote status.
10. **#15 — ignore patterns.** Root-level `**/dist` and nested pattern regression fixed locally; full Git-ignore behavior remains unimplemented.
11. **#16–#19, #21–#23 — project association, CLI, cleanup, Docker.** Verify each report against implementation before changing behavior.
12. **#27 — package naming blocker.** PyPI currently has an unrelated `devsweep` 0.2.0 project. Choose a distinct distribution and import name before any registry install instructions or publication.
13. **#28–#32 — Python support, CI and install.** Reconcile compatibility claims, add local wheel/sdist/install validation (wheel install succeeded on Windows); CI workflow permissions are narrowed, but action SHA pinning remains.

## P2 — measured performance, usability, and features

14. **#24–#26 — repeated work, filter ordering, progress/cancel.** Profile representative synthetic trees before optimization.
15. **#33–#43 — macOS, UX, new targets, trash, JSON, sizing, typing.** Defer broad features until safety, compatibility, and packaging baseline are complete; keep each feature tied to evidence and regression fixtures.

## Release readiness

- Validate supported Python/platform matrix, build artifacts, install outside repository, verify `devsweep --help`, and check registry availability.
- npm remains exploratory; do not add a second cleanup implementation.
- Do not publish or create releases without explicit approval.
