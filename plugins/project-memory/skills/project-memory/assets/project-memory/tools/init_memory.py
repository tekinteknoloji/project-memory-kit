#!/usr/bin/env python3
"""Portable entry point. Only bundled neutral templates seed new projects."""
from pathlib import Path
import sys
from memory_init import main

ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    sys.exit(main(ROOT/'tools/project_memory_template',ROOT/'tools'))
