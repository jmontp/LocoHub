#!/usr/bin/env python3
"""Compatibility wrapper for create_clean_dataset.

This script forwards to create_clean_dataset.py while printing a short
migration note. Remove once external tooling switches to the new name.
"""

from pathlib import Path
import runpy
import sys

SCRIPT_DIR = Path(__file__).parent
TARGET = SCRIPT_DIR / "create_clean_dataset.py"

print("⚠️  'create_filtered_dataset.py' is deprecated. Use 'create_clean_dataset.py' instead.")

if not TARGET.exists():
    print("❌  Expected create_clean_dataset.py next to this wrapper but it was not found.")
    sys.exit(1)

# Preserve CLI behaviour by re-executing the clean script in the same process
runpy.run_path(str(TARGET), run_name="__main__")
