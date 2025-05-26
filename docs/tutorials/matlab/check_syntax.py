#!/usr/bin/env python3
"""
Basic MATLAB syntax checker for tutorial files.
Checks for common syntax issues and structure.
"""

import re
import sys
from pathlib import Path

def check_matlab_syntax(file_path):
    """Basic syntax checking for MATLAB files."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Track open/close constructs
    if_count = 0
    for_count = 0
    while_count = 0
    function_count = 0
    try_count = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip comments
        if stripped.startswith('%'):
            continue
            
        # Check for if statements
        if re.match(r'\bif\b', stripped) and not re.match(r'\bend\b', stripped):
            if_count += 1
        if re.match(r'\bend\b', stripped):
            if_count -= 1
            
        # Check for for loops
        if re.match(r'\bfor\b', stripped):
            for_count += 1
        if re.match(r'\bend\b', stripped) and for_count > 0:
            for_count -= 1
            
        # Check for while loops
        if re.match(r'\bwhile\b', stripped):
            while_count += 1
        if re.match(r'\bend\b', stripped) and while_count > 0:
            while_count -= 1
            
        # Check for functions
        if re.match(r'\bfunction\b', stripped):
            function_count += 1
        if re.match(r'\bend\b', stripped) and function_count > 0:
            function_count -= 1
            
        # Check for try blocks
        if re.match(r'\btry\b', stripped):
            try_count += 1
        if re.match(r'\bend\b', stripped) and try_count > 0:
            try_count -= 1
            
        # Check for unclosed strings
        single_quotes = line.count("'") - line.count("''")
        if single_quotes % 2 != 0:
            issues.append(f"Line {i}: Possible unclosed string (odd number of quotes)")
            
        # Check for missing semicolons (basic check)
        if stripped and not any(stripped.endswith(x) for x in [';', ',', '...', '%', '{', '}']):
            if not any(keyword in stripped for keyword in ['if', 'else', 'elseif', 'for', 'while', 'end', 'function', 'try', 'catch']):
                # This might be intentional for display, so just note it
                pass
                
    # Check for unmatched blocks
    if if_count != 0:
        issues.append(f"Unmatched if/end blocks (count: {if_count})")
    if for_count != 0:
        issues.append(f"Unmatched for/end blocks (count: {for_count})")
    if while_count != 0:
        issues.append(f"Unmatched while/end blocks (count: {while_count})")
    if function_count != 0:
        issues.append(f"Unmatched function/end blocks (count: {function_count})")
    if try_count != 0:
        issues.append(f"Unmatched try/end blocks (count: {try_count})")
        
    return issues

def check_file_references(file_path):
    """Check for file path references in MATLAB code."""
    references = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Look for file operations
    patterns = [
        r"readtable\s*\(\s*['\"]([^'\"]+)['\"]",
        r"parquetread\s*\(\s*['\"]([^'\"]+)['\"]",
        r"csvread\s*\(\s*['\"]([^'\"]+)['\"]",
        r"load\s*\(\s*['\"]([^'\"]+)['\"]",
        r"addpath\s*\(\s*['\"]([^'\"]+)['\"]",
        r"exist\s*\(\s*['\"]([^'\"]+)['\"]",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            references.append(match)
            
    return references

# Check all MATLAB files
matlab_files = list(Path('.').glob('*.m'))

print("Checking MATLAB tutorial files...")
print("=" * 60)

for matlab_file in matlab_files:
    print(f"\nChecking: {matlab_file}")
    
    # Check syntax
    issues = check_matlab_syntax(matlab_file)
    if issues:
        print("  Syntax issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✓ No syntax issues detected")
    
    # Check file references
    refs = check_file_references(matlab_file)
    if refs:
        print("  File references:")
        for ref in refs:
            print(f"    - {ref}")
            # Check if file exists
            ref_path = Path(ref)
            if not ref_path.exists() and not ref.startswith('../'):
                print(f"      ⚠ File may not exist at this path")

print("\n" + "=" * 60)
print("MATLAB syntax check complete")