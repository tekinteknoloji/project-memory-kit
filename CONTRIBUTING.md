# Contributing

Contributions are welcome when they preserve portability, selective context loading, and safe installation.

## Development checks

Run the cross-platform tests:

```text
python tests/test_package.py
```

On Windows, also run:

```powershell
.\tests\test_one_click.ps1
```

Do not commit project-specific memory, credentials, absolute user paths, generated backups, or build artifacts. Update `CHANGELOG.md` when behavior visible to users changes.
