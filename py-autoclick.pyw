#!/usr/bin/env python3
"""Launcher shim — keeps the .desktop entry working without modification.

The actual code lives in the ``pyautoclick`` package next to this file.
For development install once: ``pip install --user -e .``
"""

import sys
from pathlib import Path

# Allow running directly without `pip install` (e.g. `python py-autoclick.pyw`)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyautoclick.__main__ import main

if __name__ == "__main__":
    main()
