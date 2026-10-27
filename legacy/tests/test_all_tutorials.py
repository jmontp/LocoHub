#!/usr/bin/env python3
"""
Test All Tutorials - Master Test Runner

Created: 2025-08-07
Purpose: Run all tutorial tests and generate a comprehensive report

This script runs all tutorial tests in sequence and provides a summary
of the results.
"""

import sys
import subprocess
from pathlib import Path
import time


def run_test(test_file):
    """
    Run a single test file and return results.
    
    Returns:
        tuple: (success: bool, duration: float, output: str)
    """
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        duration = time.time() - start_time
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        
        return success, duration, output
        
    except subprocess.TimeoutExpired:
        return False, 30.0, "Test timed out after 30 seconds"
    except Exception as e:
        return False, 0.0, f"Error running test: {e}"


def main():
    """Run all tutorial tests."""
    print("="*70)
    print("RUNNING ALL TUTORIAL TESTS")
    print("="*70)
    
    # Find all tutorial test files
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob('test_tutorial_*.py'))
    
    if not test_files:
        print("ERROR: No tutorial test files found!")
        return 1
    
    print(f"\nFound {len(test_files)} tutorial tests to run\n")
    
    # Check mock dataset exists
    mock_dataset = test_dir / 'mock_data' / 'mock_dataset_phase.parquet'
    if not mock_dataset.exists():
        print("ERROR: Mock dataset not found!")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    # Run each test
    results = []
    total_duration = 0
    
    for i, test_file in enumerate(test_files, 1):
        test_name = test_file.stem.replace('test_tutorial_', 'Tutorial ')
        print(f"[{i}/{len(test_files)}] Running {test_name}...", end=' ', flush=True)
        
        success, duration, output = run_test(test_file)
        total_duration += duration
        
        if success:
            print(f"✓ PASSED ({duration:.2f}s)")
            # Show key results from output
            for line in output.split('\n'):
                if 'Testing' in line and '...' in line:
                    print(f"    - {line.strip()}")
        else:
            print(f"✗ FAILED ({duration:.2f}s)")
            # Show error details
            error_lines = [l for l in output.split('\n') if 'Error' in l or 'Failed' in l]
            if error_lines:
                print(f"    Error: {error_lines[0]}")
        
        results.append({
            'name': test_name,
            'file': test_file.name,
            'success': success,
            'duration': duration,
            'output': output
        })
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"\nTotal tests run: {len(results)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print(f"Total time: {total_duration:.2f} seconds")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in results:
            if not r['success']:
                print(f"  - {r['name']} ({r['file']})")
                # Show first error line
                for line in r['output'].split('\n'):
                    if 'TEST FAILED' in line or 'Error' in line:
                        print(f"    {line.strip()}")
                        break
    
    # Detailed results table
    print("\n" + "-"*70)
    print(f"{'Test':<25} {'Status':<10} {'Time (s)':<10}")
    print("-"*70)
    
    for r in results:
        status = "✓ PASS" if r['success'] else "✗ FAIL"
        print(f"{r['name']:<25} {status:<10} {r['duration']:<10.2f}")
    
    print("-"*70)
    
    # Generate report file
    report_path = test_dir / 'tutorial_test_report.txt'
    with open(report_path, 'w') as f:
        f.write("TUTORIAL TEST REPORT\n")
        f.write("="*70 + "\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total tests: {len(results)}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Total duration: {total_duration:.2f} seconds\n\n")
        
        for r in results:
            f.write("-"*70 + "\n")
            f.write(f"Test: {r['name']}\n")
            f.write(f"File: {r['file']}\n")
            f.write(f"Status: {'PASSED' if r['success'] else 'FAILED'}\n")
            f.write(f"Duration: {r['duration']:.2f} seconds\n")
            if not r['success']:
                f.write("\nError Output:\n")
                f.write(r['output'][-1000:])  # Last 1000 chars of error
            f.write("\n")
    
    print(f"\nDetailed report saved to: {report_path.name}")
    
    # Final result
    if failed == 0:
        print("\n" + "="*70)
        print("🎉 ALL TUTORIAL TESTS PASSED! 🎉")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print(f"⚠️  {failed} TUTORIAL TEST(S) FAILED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())