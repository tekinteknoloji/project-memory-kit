# Security Policy

## Supported version

Security fixes are applied to the latest released version.

## Reporting a vulnerability

Do not open a public issue containing credentials, private project memory, or exploit details. Contact the repository owner privately through the security-reporting method configured on the GitHub repository.

The PowerShell installer writes only to the current user's `.codex` directory. Forced updates create a timestamped backup before replacing an existing `project-memory` skill.
The shared `install_skill.py` installer targets `.codex` or `.claude` beneath the OS user's home (or an explicitly supplied `--user-home`). It never modifies global instruction files. Updates and uninstall retain backups outside the skills discovery directory. Python 3.10+ is required; linked installation paths are rejected. Run installers as the normal user, without administrator/root elevation.

The existing-project updater is separate. Its plans/backups must be outside Git working trees; backups contain private project memory and custom tools. It never rewrites live memory or project instructions. Customized managed tools block automatic updates. Use the package updater's `recover` for `memory/.transaction/project-update.json`; do not use the ordinary memory-close recovery command for that journal. Tool-directory swaps require the same filesystem and are not a power-loss atomicity guarantee.

The Git-address manager accepts HTTPS repository URLs without embedded credentials and selects stable version tags with an exact declarative `release.json`. Its trusted local procedure does not execute downloaded installers/checkers. The user-selected repository remains a trust boundary: hashes verify content consistency, not publisher identity or future behavior. Private manager runs retain full project trial copies, Git snapshots, provenance and backups outside Git working trees. Same-version mutations, downgrades, unknown origins and local customizations stop automatic installation. A hard interruption can require receipt/lock inspection and explicit tools recovery; skill+project updates are not a single atomic transaction.


Secret detection is heuristic, not a guarantee or a publishing gate. Review files before sharing. Local bundles contain committed Git history (including any previously committed secrets), exclude ignored/uncommitted files, and do not replace offsite backups. Windows launchers bypass execution policy for the invoked process; use only a reviewed package.
