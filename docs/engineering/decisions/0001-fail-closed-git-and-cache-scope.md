# 0001: Fail-closed Git status and narrow cache scope

- **Date:** 2026-10-30
- **Status:** accepted
- **Related:** GitHub issues [#4](https://github.com/Abhishek764/devsweep/issues/4), [#5](https://github.com/Abhishek764/devsweep/issues/5), [#6](https://github.com/Abhishek764/devsweep/issues/6), [#7](https://github.com/Abhishek764/devsweep/issues/7), [#8](https://github.com/Abhishek764/devsweep/issues/8)

## Context

Review of the current scanner found that `unknown` Git status was not skipped when `--force` was set, nested scans did not notice enclosing repositories, generic names from the cleanup registry were omitted from project activity even when the directory was not a cleanup target, and the Windows JetBrains cache spec named the full `%LOCALAPPDATA%/JetBrains` tree. Git status also lacked `--no-optional-locks`. These findings are directly visible in the checked-out code; live issue reports corroborate the areas but do not establish every reproduction detail.

## Requirements and options

Preserve non-Git workspace scanning, treat unverifiable Git repositories conservatively, avoid hiding edits in ordinary source folders, and never treat a broad product-data directory as disposable cache. Considered making every non-clean status an unconditional skip, changing only `--force`, or distinguishing a normal non-repository directory from an uninspectable repository. Chose the distinction: `not-repository` may scan; `unknown` always skips; `unavailable` may be overridden by the existing explicit force policy. `--no-optional-locks` makes Git status less likely to update repository metadata.

## Decision and evidence

`repository_status()` searches the project and ancestor directories for `.git`, so nested scans observe the enclosing repository. It returns `not-repository` only when metadata is absent and `unknown` when repository metadata exists but its state cannot be verified. The scanner always skips `unknown`, including with force. Activity traversal skips a directory only when the registered marker rule actually recognizes it as a generated target. The broad Windows JetBrains path was removed; a narrower product-specific target is deferred until its contents and policy are verified.

Regression evidence: tests assert unknown status remains skipped under force, normal source in `bin/` contributes activity, Git receives `--no-optional-locks`, and the Windows cache list omits JetBrains.

## Trade-offs and implications

Some legitimate stale targets in repositories with broken Git state remain unavailable even under force. Removing the JetBrains entry reduces coverage but avoids deleting settings, installed tools, history, or other data under a broad parent. Path-based deletion still has a TOCTOU window. Linux/macOS cache rules are not changed by this decision.

## Revisit when

A platform-specific, documented JetBrains cache child path has a clear safety policy and fixture coverage; or Git's state model changes with evidence that another status category can be handled safely.
