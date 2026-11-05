#!/usr/bin/env python3
"""Git-address entry point; installed skills carry the same manager."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "plugins/project-memory/skills/project-memory/scripts"))
from install_from_git import main

if __name__ == "__main__":
    raise SystemExit(main())
