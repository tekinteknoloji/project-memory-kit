#!/usr/bin/env python3
"""Compatibility entry point for the shared skill installer."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'plugins/project-memory/skills/project-memory/scripts'))
from skill_install import *

if __name__ == '__main__':
    raise SystemExit(main())
