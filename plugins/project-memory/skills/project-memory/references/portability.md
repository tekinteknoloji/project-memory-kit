# Portability acceptance

Use disposable project roots and isolated profiles. Never run an initializer over an existing project to upgrade its tools. Installing an updated skill does not upgrade already initialized projects. Compare project-specific customizations and tool hashes before a separately authorized migration.

Run `python -m unittest discover -s tests -p "test_*.py"` on each target OS. On Windows run `tests/test_one_click.ps1` and `tests/test_safety.ps1` with Windows PowerShell and PowerShell 7 when available. They use temporary profiles rather than the real global skill directory.

The portability tests cover UTF-8/Turkish and space-containing paths, zip transport with the source directory removed, exact preservation of decision bytes and session-history prefixes, initialization from transported neutral templates without the skill, and recovery of a pending transaction after a directory move. A zip copied from trusted project files is not proof of safe extraction for arbitrary untrusted archives.

For an actual second machine/user, record OS, Python/Git availability, user identity, write permissions, package SHA-256 and test output. Copy the candidate source package, extract it into a normal writable user directory, then run the tests above. A temporary USERPROFILE on one Windows account does not test another account's ACLs, and WSL is not a second physical Windows machine. Do not install dependencies, change system ACLs or switch real global configurations merely to produce a green receipt.

Release manifest version, source commit and actual installed file hashes are separate identifiers. An old plugin version on an unreleased branch must not imply that installed project tools are up to date. Keep a verified before-copy, test failed activation rollback, and verify that updating or uninstalling a skill leaves existing project records unchanged. Finalize release numbering only after acceptance; do not publish private memory or test artifacts.
