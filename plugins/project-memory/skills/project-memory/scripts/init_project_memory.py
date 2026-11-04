#!/usr/bin/env python3
"""Package entry point; implementation is shared with the portable initializer."""
from pathlib import Path
import sys

ASSETS=Path(__file__).resolve().parents[1]/'assets/project-memory'
sys.path.insert(0,str(ASSETS/'tools'))
from memory_init import main

if __name__=='__main__':
    sys.exit(main(ASSETS,ASSETS/'tools'))
