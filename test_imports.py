#!/usr/bin/env python3
"""
Test script to verify all import paths work correctly
"""

import sys
from pathlib import Path

print("Testing import paths...")

# Test 1: README suggested import path (BROKEN)
print("\n1. Testing README suggested import path:")
try:
    sys.path.append('source/lib/python')
    from locomotion_analysis import LocomotionData
    print("✅ SUCCESS: source/lib/python import works")
except (ImportError, ModuleNotFoundError) as e:
    print(f"❌ FAILED: source/lib/python import - {e}")

# Test 2: Actual correct import path
print("\n2. Testing actual correct import path:")
try:
    sys.path.insert(0, str(Path(__file__).parent / "lib" / "core"))
    from locomotion_analysis import LocomotionData
    print("✅ SUCCESS: lib/core import works")
except (ImportError, ModuleNotFoundError) as e:
    print(f"❌ FAILED: lib/core import - {e}")

# Test 3: CLI tool import paths
print("\n3. Testing CLI tool import pattern:")
try:
    project_root = Path(__file__).parent
    sys.path.append(str(project_root))
    from lib.validation.release_manager import ReleaseManager
    print("✅ SUCCESS: CLI tool imports work")
except (ImportError, ModuleNotFoundError) as e:
    print(f"❌ FAILED: CLI tool imports - {e}")

# Test 4: Tutorial import suggestions
print("\n4. Testing tutorial import suggestions:")
try:
    # This should work if running from project root
    import pandas as pd
    print("✅ SUCCESS: pandas import works")
except ImportError as e:
    print(f"❌ FAILED: pandas import - {e}")

print("\nTest completed.")