# Changelog

All notable changes to this project are documented here.

## Unreleased

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
