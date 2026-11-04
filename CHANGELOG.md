# Changelog

All notable changes to this project are documented here.

## Unreleased

- Define a portable record lifecycle and scoped recall contract; separate proposals, approval and verified implementation without rewriting legacy memory.
- Align protocol lock guidance with explicit owner-verified recovery.

- Share one initializer across package and portable entry points, with full preflight and exclusive destination creation.
- Generate portable neutral templates from one canonical source tree; retain multi-generation privacy and preservation checks.
- Prune dependency/cache directories before traversal and cache text reads per audit; expose scan scope in JSON.
- Extend advisory credential-assignment detection with placeholder filtering and value-free reports.
- Require the shared initialization helper in the 21-file health check.

- Fix closing a clean Git repository: date the recorded pre-close Git observation while reporting current Git state independently.
- Preserve detection of real Git changes and unexpected post-write warnings; distinguish Git access failure from a missing repository.

- Add a shared journaled storage module with verified before/after snapshots.
- Block new closes and health-check success while a transaction is pending.
- Add explicit recovery for interrupted closes; preserve external changes and corrupt journals for review.
- Reclaim only demonstrably exited process locks during explicit recovery; preserve live, legacy and uncertain owners.
- Test process termination, partial writes, rollback failures, concurrent edits, snapshot corruption and Windows junctions.

- Preserve existing Markdown documents and history during initialization and session close.
- Bundle neutral portable templates without copying private project records.
- Validate session saves before and after writing; roll back caught failures and preserve last durable-write timestamps.
- Honor uninstall WhatIf for global rules; preserve UTF-8 user rules.
- Stage updates before backing up the installed skill and restore it after failed activation.
- Add preservation, rollback, lock, backup and Windows safety regression tests.

## 1.1.0 — 2026-08-21

- Added one-click Windows install, update, and uninstall launchers.
- Added safe backup behavior before forced updates.
- Added optional, marker-delimited global project-memory rules.
- Added Git-aware initialization status and 19-file health verification.
- Added cross-platform package tests and Windows end-to-end CI coverage.

## 1.0.0 — 2026-08-21

- Initial portable Markdown project-memory skill and Codex plugin package.
