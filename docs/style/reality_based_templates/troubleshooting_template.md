# Troubleshooting Documentation Template

**Use this template to document real issues and verified solutions**

## Issue Documentation Header Template

```markdown
# [Issue Category/Component] Troubleshooting

**Last Updated**: YYYY-MM-DD
**Solution Success Rate**: [X]% (based on user reports)
**Most Common Issues**: [List top 3 issues]

## Quick Diagnosis

**Before diving into detailed troubleshooting:**
```bash
# Quick diagnostic commands
python3 --version  # Check Python version
pip list | grep [package_name]  # Check package installation
[other_diagnostic_command]  # Check specific requirements
```

**Expected output**:
```
Python 3.9.16
[package_name] 1.2.3
[expected_output]
```

**If any diagnostic fails**: Jump to [relevant section](#section-name)
```

## Individual Issue Template

```markdown
## Issue: [Specific Error Description]

**Frequency**: [Common/Occasional/Rare] (based on user reports)
**Impact**: [High/Medium/Low]
**Platforms affected**: [Windows/Linux/macOS/All]
**First reported**: YYYY-MM-DD
**Last updated**: YYYY-MM-DD

### Problem Description
**User experience**:
[Describe what the user sees/experiences]

**Typical error message**:
```
[Exact error message from real testing]
```

**Error context**:
```python
# Code that triggers the error
[specific code that causes the issue]
```

### Root Cause Analysis
**Technical cause**: [What actually causes this issue]
**Why it happens**: [Underlying reason - missing dependencies, path issues, etc.]
**Conditions that trigger it**: 
- [Condition 1]
- [Condition 2]
- [Condition 3]

### Solution

#### ✅ Verified Working Solution
**Tested solution** (verified YYYY-MM-DD):
```bash
# Step-by-step solution that was tested
step_1_command
step_2_command
step_3_command
```

**Expected output after fix**:
```
[What user should see when solution works]
```

**Verification test**:
```python
# Quick test to confirm fix worked
[test_code_to_verify_solution]
# Expected result: [description]
```

**Solution success rate**: [X]% (based on follow-up reports)

#### 🚧 Alternative Workaround (if main solution fails)
**Workaround approach**:
```python
# Alternative method if main solution doesn't work
[workaround_code]
```

**Limitations of workaround**:
- [Limitation 1]
- [Limitation 2]

**When to use workaround**: [Specific circumstances]

### Prevention
**How to avoid this issue**:
1. [Preventive step 1]
2. [Preventive step 2]
3. [Preventive step 3]

**Early warning signs**:
- [Warning sign 1]
- [Warning sign 2]

### Related Issues
**Similar problems**:
- [Link to related issue 1]
- [Link to related issue 2]

**If this solution doesn't work**: [Link to escalation path]
```

## Environment-Specific Issues Template

```markdown
## Platform-Specific Issues

### Windows Issues

#### Issue: [Windows-specific problem]
**Affects**: Windows 10/11
**Typical error**:
```
[Windows-specific error message]
```

**Windows solution** (tested on Windows 11):
```powershell
# Windows-specific commands
windows_command_1
windows_command_2
```

**Alternative for older Windows**:
```cmd
# For Windows 10 compatibility
cmd_command_1
cmd_command_2
```

### Linux Issues

#### Issue: [Linux-specific problem]
**Affects**: Ubuntu 20.04+, CentOS 8+
**Typical error**:
```
[Linux-specific error message]
```

**Linux solution** (tested on Ubuntu 22.04):
```bash
# Linux-specific commands
sudo apt update
sudo apt install [required_package]
[additional_commands]
```

**Distribution-specific notes**:
- **Ubuntu/Debian**: Use `apt` commands above
- **CentOS/RHEL**: Replace `apt` with `yum` or `dnf`
- **Arch**: Use `pacman -S [package_name]`

### macOS Issues

#### Issue: [macOS-specific problem]
**Affects**: macOS 12+
**Typical error**:
```
[macOS-specific error message]
```

**macOS solution** (tested on macOS 13):
```bash
# macOS-specific commands
brew install [required_package]
[other_macos_commands]
```

**Homebrew troubleshooting**:
```bash
# If brew commands fail
brew doctor
brew update
# Then retry installation
```
```

## Installation Issues Template

```markdown
## Installation Troubleshooting

### Package Installation Issues

#### Issue: pip install fails
**Common error patterns**:
```
ERROR: Could not find a version that satisfies the requirement [package]
ERROR: No matching distribution found for [package]
ERROR: Failed building wheel for [package]
```

**Solution by error type**:

**Version not found**:
```bash
# Check available versions
pip index versions [package_name]
# Install specific compatible version
pip install [package_name]==X.Y.Z
```

**Build failures**:
```bash
# Install build dependencies
pip install --upgrade pip setuptools wheel
# Try installation with verbose output
pip install [package_name] -v
```

**Verification after installation**:
```python
# Test that package installed correctly
try:
    import [package_name]
    print(f"✅ {package_name} version: {package_name.__version__}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

### Virtual Environment Issues

#### Issue: Virtual environment activation fails
**Common symptoms**:
- Command not found errors
- Wrong Python version
- Package import failures

**Solution** (tested working):
```bash
# Create fresh virtual environment
python3 -m venv fresh_env
source fresh_env/bin/activate  # Linux/macOS
# OR
fresh_env\Scripts\activate  # Windows

# Verify activation
which python  # Should show venv path
python --version  # Should show expected version
```

**Verification**:
```bash
# Confirm virtual environment is working
pip list  # Should show minimal packages
pip install [test_package]
python -c "import [test_package]; print('✅ Virtual env working')"
```
```

## Import and Module Issues Template

```markdown
## Import/Module Issues

### Module Not Found Errors

#### Issue: ModuleNotFoundError
**Error pattern**:
```
ModuleNotFoundError: No module named '[module_name]'
```

**Diagnostic steps**:
```python
# Check Python path
import sys
print("Python path:")
for path in sys.path:
    print(f"  {path}")

# Check if module exists
import os
module_locations = [
    'lib/[module_name]',
    'source/lib/[module_name]', 
    'src/[module_name]'
]
for location in module_locations:
    if os.path.exists(location):
        print(f"✅ Found module at: {location}")
    else:
        print(f"❌ Not found: {location}")
```

**Solution 1: Fix Python path**:
```python
# Add correct path to sys.path
import sys
sys.path.append('lib')  # Adjust path as needed
import [module_name]
```

**Solution 2: Use relative imports**:
```python
# If running from project directory
from lib.[module_name] import [component]
```

**Solution 3: Install in development mode**:
```bash
# Install package in development mode
pip install -e .
```

**Verification**:
```python
# Test that import now works
try:
    from [module_name] import [component]
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Still failing: {e}")
```

### Path and Structure Issues

#### Issue: Incorrect import paths
**Common in projects with complex structure**

**Diagnostic approach**:
```bash
# Show actual project structure
find . -name "*.py" -type f | head -20
# Show where files actually are vs. where docs claim they are
```

**Solution template**:
```python
# Determine correct import path
import os
print("Current working directory:", os.getcwd())
print("Project structure:")
for root, dirs, files in os.walk('.'):
    level = root.replace('.', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        if file.endswith('.py'):
            print(f"{subindent}{file}")
```
```

## Performance Issues Template

```markdown
## Performance Troubleshooting

### Slow Execution Issues

#### Issue: Operations taking too long
**Symptoms**:
- Functions taking >10x expected time
- Memory usage growing continuously
- System becoming unresponsive

**Diagnostic tools** (install if needed):
```bash
pip install memory-profiler line-profiler
```

**Performance diagnosis**:
```python
# Memory profiling
from memory_profiler import profile

@profile
def diagnose_memory():
    # Your problematic code here
    [problematic_function_call]

# Time profiling
import time
start_time = time.time()
result = [slow_function]()
execution_time = time.time() - start_time
print(f"Execution time: {execution_time:.2f} seconds")

# Expected times for comparison:
# Small dataset (N<1000): <1 second
# Medium dataset (N<10000): <10 seconds  
# Large dataset (N>10000): Review algorithm
```

**Common solutions**:

**Large dataset optimization**:
```python
# Instead of loading all data at once
# data = load_entire_dataset()  # Slow for large files

# Use chunked processing
def process_in_chunks(data_source, chunk_size=1000):
    for chunk in data_source.read_chunks(chunk_size):
        processed_chunk = process_data(chunk)
        yield processed_chunk
```

**Memory optimization**:
```python
# Free memory explicitly
import gc
del large_data_structure
gc.collect()

# Use generators instead of lists
def data_generator():
    for item in data_source:
        yield process_item(item)
# Instead of: processed_list = [process_item(x) for x in data_source]
```

**Verification of improvements**:
```python
# Measure improvement
import time
import psutil

# Before optimization
start_memory = psutil.Process().memory_info().rss
start_time = time.time()
result_old = old_slow_function()
old_time = time.time() - start_time
old_memory = psutil.Process().memory_info().rss - start_memory

# After optimization  
start_memory = psutil.Process().memory_info().rss
start_time = time.time()
result_new = new_fast_function()
new_time = time.time() - start_time
new_memory = psutil.Process().memory_info().rss - start_memory

print(f"Speed improvement: {old_time/new_time:.1f}x faster")
print(f"Memory improvement: {old_memory/new_memory:.1f}x less memory")
```
```

## Data Issues Template

```markdown
## Data-Related Issues

### File Format Issues

#### Issue: Cannot read data files
**Common error patterns**:
```
ParserError: Error tokenizing data
UnicodeDecodeError: 'utf-8' codec can't decode
FileNotFoundError: No such file or directory
```

**Diagnostic approach**:
```python
# Check file existence and basic properties
import os
file_path = '[your_file_path]'
if os.path.exists(file_path):
    file_size = os.path.getsize(file_path)
    print(f"✅ File exists, size: {file_size} bytes")
    
    # Check file encoding
    with open(file_path, 'rb') as f:
        raw_bytes = f.read(100)
        print(f"First 100 bytes: {raw_bytes}")
else:
    print(f"❌ File not found: {file_path}")
    # List files in directory
    dir_path = os.path.dirname(file_path)
    print(f"Files in {dir_path}:")
    for f in os.listdir(dir_path):
        print(f"  {f}")
```

**Solutions by error type**:

**Encoding issues**:
```python
# Try different encodings
encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
for encoding in encodings:
    try:
        import pandas as pd
        data = pd.read_csv(file_path, encoding=encoding)
        print(f"✅ Successfully read with encoding: {encoding}")
        break
    except UnicodeDecodeError:
        print(f"❌ Failed with encoding: {encoding}")
```

**Parser issues**:
```python
# Robust CSV reading
import pandas as pd
try:
    # Try with error handling
    data = pd.read_csv(
        file_path, 
        on_bad_lines='warn',  # Don't fail on bad lines
        encoding_errors='ignore',  # Skip encoding errors
        low_memory=False  # Avoid mixed type warnings
    )
    print(f"✅ Read {len(data)} rows with warnings handled")
except Exception as e:
    print(f"❌ Still failing: {e}")
    # Try manual inspection
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            if i < 5:  # Show first 5 lines
                print(f"Line {i}: {repr(line)}")
```

### Data Validation Issues

#### Issue: Data validation failures
**Common validation errors**:
- Missing required columns
- Incorrect data types
- Values outside expected ranges
- Inconsistent data format

**Validation diagnostic**:
```python
import pandas as pd

def diagnose_data_issues(df):
    """Comprehensive data diagnosis"""
    print("=== Data Diagnosis Report ===")
    
    # Basic info
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Missing data
    missing = df.isnull().sum()
    if missing.any():
        print("\n❌ Missing data found:")
        for col, count in missing[missing > 0].items():
            print(f"  {col}: {count} missing values")
    else:
        print("\n✅ No missing data")
    
    # Data types
    print(f"\nData types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")
    
    # Value ranges
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        print(f"\nNumeric ranges:")
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            print(f"  {col}: {min_val} to {max_val}")
    
    return df

# Use diagnostic function
diagnosed_data = diagnose_data_issues(your_dataframe)
```

**Common fixes**:
```python
# Fix missing data
df['column_name'].fillna(default_value, inplace=True)

# Fix data types
df['numeric_column'] = pd.to_numeric(df['numeric_column'], errors='coerce')
df['date_column'] = pd.to_datetime(df['date_column'], errors='coerce')

# Fix value ranges
df.loc[df['value'] < min_threshold, 'value'] = min_threshold
df.loc[df['value'] > max_threshold, 'value'] = max_threshold

# Verification after fixes
print("After fixes:")
diagnose_data_issues(df)
```
```

## Getting Help Template

```markdown
## When These Solutions Don't Work

### Information to Gather Before Asking for Help

**System information**:
```bash
# Gather system details
python3 --version
pip --version
pip list > installed_packages.txt
# Include OS and version
```

**Error information**:
```python
# Capture full error traceback
try:
    [problematic_code]
except Exception as e:
    import traceback
    print("Full error traceback:")
    traceback.print_exc()
```

**Reproduction case**:
```python
# Create minimal example that demonstrates the problem
def minimal_reproduction():
    """
    Minimal code that reproduces the issue
    """
    # Include only essential code
    [minimal_example]
    
# Test that reproduction case actually fails
try:
    minimal_reproduction()
except Exception as e:
    print(f"Error reproduced: {e}")
```

### Where to Get Help

**Community resources**:
- [Link to project discussions/forum]
- [Link to issue tracker]
- [Link to community chat/discord]

**Professional support**:
- [Link to paid support options if available]
- [Contact information for enterprise support]

**Contributing fixes**:
- [Link to contribution guidelines]
- [Process for submitting bug fixes]

### Help Request Template

```markdown
**Issue Description**: [Brief description]

**Environment**:
- OS: [Operating system and version]
- Python: [Version]
- Package versions: [Relevant package versions]

**Error Message**:
```
[Full error message/traceback]
```

**Reproduction Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior**: [What should happen]
**Actual Behavior**: [What actually happens]

**Solutions Tried**:
- [X] Tried solution 1 from docs - [result]
- [X] Tried solution 2 from docs - [result]
- [ ] Haven't tried solution 3 yet

**Additional Context**: [Any other relevant information]
```

---
**Troubleshooting Guide Status**: ✅ Solutions Verified | Last Updated: YYYY-MM-DD
```

## Usage Instructions

1. **Document real issues** encountered by actual users
2. **Test all solutions** in the documented environment
3. **Include exact error messages** from real testing
4. **Provide step-by-step solutions** that have been verified to work
5. **Add verification steps** so users can confirm fixes worked
6. **Update regularly** as new issues are discovered
7. **Track solution success rates** based on user feedback

This template ensures troubleshooting documentation provides users with reliable solutions to real problems they're likely to encounter.