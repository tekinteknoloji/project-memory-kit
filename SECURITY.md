# Security Policy

## Supported version

Security fixes are applied to the latest released version.

## Reporting a vulnerability

Do not open a public issue containing credentials, private project memory, or exploit details. Contact the repository owner privately through the security-reporting method configured on the GitHub repository.

The installer writes only to the current user's `.codex` directory. Forced updates create a timestamped backup before replacing an existing `project-memory` skill.


Secret detection is heuristic, not a guarantee or a publishing gate. Review files before sharing. Local bundles contain committed Git history (including any previously committed secrets), exclude ignored/uncommitted files, and do not replace offsite backups. Windows launchers bypass execution policy for the invoked process; use only a reviewed package.
