# API Documentation Template: Reality-Based Reference

**Use this template for all API documentation to ensure accuracy and verifiability**

## Function/Class Header Template

```markdown
# [Function/Class Name]

**Status**: ✅ Fully Implemented | 🚧 Partial Implementation | 📋 Planned | ⚠️ Known Issues

**Module**: `[actual.module.path]` (verified import path)
**Added**: Version [X.Y.Z]
**Last Verified**: YYYY-MM-DD

## Import Statement

**Verified working import** (tested YYYY-MM-DD):
```python
# Tested import - works in current codebase
from [actual.module.path] import [ClassName/function_name]

# Alternative import if needed
import sys
sys.path.append('[required/path]')  # Only if needed
from [module] import [item]
```

**Import verification test**:
```python
# Quick test to verify import works
try:
    from [module] import [item]
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```
```

## Function Signature Template

```markdown
## Function Signature

**Actual signature** (extracted from code YYYY-MM-DD):
```python
def function_name(
    param1: type_hint,
    param2: type_hint = default_value,
    *args,
    **kwargs
) -> return_type:
    """
    [Actual docstring from code]
    """
```

**Parameter verification**:
- **param1** (`type`): [Description] - ✅ Required | 🚧 Optional behavior
- **param2** (`type`, default=`value`): [Description] - ✅ Working default
- **Returns**: `return_type` - [Description of return value]

**Type validation test**:
```python
# Test parameter types and return type
result = function_name(param1="test_value", param2=123)
assert isinstance(result, expected_return_type)
print(f"✅ Function returns {type(result)}")
```
```

## Working Examples Template

```markdown
## Examples

### Basic Usage
**Tested example** (verified YYYY-MM-DD):
```python
# This exact code was tested and works
from [module] import [function]

# Basic usage
result = function(required_param="test_value")
print(f"Result: {result}")
```

**Expected output**:
```
Result: [actual output from testing]
```

**Verification**:
```python
# Verify the example works
assert result is not None
assert isinstance(result, expected_type)
print("✅ Basic usage verified")
```

### Advanced Usage
**Complex example** (tested YYYY-MM-DD):
```python
# Advanced usage with multiple parameters
result = function(
    param1="complex_value",
    param2=custom_object,
    optional_param=True
)

# Process result
processed = result.some_method()
print(f"Processed result: {processed}")
```

**Prerequisites for advanced example**:
```python
# Setup required for advanced example
custom_object = SomeClass(init_value="test")
# Verify setup
assert custom_object.is_valid()
```
```

## Error Handling Template

```markdown
## Error Handling

**Tested error cases** (verified YYYY-MM-DD):

### TypeError: Invalid Parameter Type
**Trigger condition**:
```python
# This will cause TypeError
function(param1=123)  # Wrong type - should be string
```

**Actual error message**:
```
TypeError: param1 must be string, got int
```

**Proper error handling**:
```python
try:
    result = function(param1=123)
except TypeError as e:
    print(f"Type error: {e}")
    # Correct usage
    result = function(param1="123")  # Convert to string
```

### ValueError: Invalid Parameter Value
**Trigger condition**:
```python
# This will cause ValueError
function(param1="invalid_value")
```

**Actual error**:
```
ValueError: param1 must be one of ['valid1', 'valid2'], got 'invalid_value'
```

**Solution**:
```python
# Valid values (from actual testing)
valid_values = ['valid1', 'valid2', 'valid3']
result = function(param1=valid_values[0])
```

### Common Edge Cases
**Empty input**:
```python
# Test with empty input
result = function(param1="")
# Result: [actual behavior - may be None, empty list, etc.]
```

**None input**:
```python
# Test with None
try:
    result = function(param1=None)
    print(f"None input result: {result}")
except Exception as e:
    print(f"None input error: {e}")
```
```

## Performance Information Template

```markdown
## Performance

**Measured performance** (tested YYYY-MM-DD on [environment]):

### Execution Time
```python
import time

# Performance test with typical input
start_time = time.time()
result = function(typical_input)
end_time = time.time()

print(f"Execution time: {end_time - start_time:.4f} seconds")
# Typical result: 0.0123 seconds
```

### Memory Usage
```python
import tracemalloc

# Memory test
tracemalloc.start()
result = function(large_input)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Memory usage: {current / 1024 / 1024:.2f} MB")
# Typical result: 1.23 MB
```

### Scalability
**Tested with different input sizes**:
- Small input (N=100): ~0.01s
- Medium input (N=1000): ~0.05s  
- Large input (N=10000): ~0.3s
- Performance pattern: O(N) linear scaling
```

## Known Issues Template

```markdown
## Known Issues

### Issue 1: [Specific Problem Description]
**Status**: 🚧 Workaround Available | ❌ No Solution | 📋 Fix Planned

**Problem description**:
```python
# This code demonstrates the issue
problematic_input = {"key": "special_value"}
result = function(problematic_input)
# Result is incorrect: gets [wrong_result] instead of [expected_result]
```

**Workaround** (tested working):
```python
# Working solution
fixed_input = preprocess_input(problematic_input)
result = function(fixed_input)
# Result is now correct: [correct_result]
```

**Root cause**: [Technical explanation of why issue occurs]
**Tracking**: [Link to issue tracker if available]

### Issue 2: Platform-Specific Behavior
**Affected platforms**: Windows 10/11
**Issue**: [Description of platform-specific issue]

**Platform-specific workaround**:
```python
import platform

if platform.system() == "Windows":
    # Windows-specific handling
    result = function_windows_version(param)
else:
    # Standard handling
    result = function(param)
```
```

## Dependencies Template

```markdown
## Dependencies

**Required dependencies** (verified YYYY-MM-DD):
```python
# Test dependency availability
import pandas  # Version 1.3+ required
import numpy   # Version 1.20+ required
import [other_dep]  # Version requirement

# Verify versions meet requirements
print(f"pandas: {pandas.__version__}")
print(f"numpy: {numpy.__version__}")
```

**Version compatibility matrix**:
| Dependency | Min Version | Max Version | Status |
|------------|-------------|-------------|---------|
| pandas     | 1.3.0      | 2.1.x      | ✅ Tested |
| numpy      | 1.20.0     | 1.24.x     | ✅ Tested |
| python     | 3.8.0      | 3.11.x     | ✅ Tested |

**Installation verification**:
```bash
# Verify all dependencies are installed correctly
pip install pandas>=1.3.0 numpy>=1.20.0
python3 -c "import pandas, numpy; print('✅ Dependencies verified')"
```
```

## Testing Template

```markdown
## Testing Information

**Test coverage** (as of YYYY-MM-DD):
- **Unit tests**: ✅ 95% coverage
- **Integration tests**: ✅ All major workflows
- **Edge case tests**: 🚧 Known edge cases covered
- **Performance tests**: ✅ Benchmarked regularly

**Run tests yourself**:
```bash
# Run specific tests for this function
python3 -m pytest tests/test_[function_name].py -v

# Expected output: all tests should pass
# ✅ test_basic_usage PASSED
# ✅ test_error_handling PASSED
# ✅ test_edge_cases PASSED
```

**Manual verification**:
```python
# Quick manual test
def verify_function():
    """Manual verification of function behavior"""
    # Test 1: Basic functionality
    result1 = function("test_input")
    assert result1 is not None
    
    # Test 2: Error handling
    try:
        function(invalid_input)
        assert False, "Should have raised error"
    except ValueError:
        pass  # Expected error
    
    # Test 3: Edge case
    result3 = function("")
    # result3 should be [expected_value]
    
    print("✅ All manual tests passed")

# Run verification
verify_function()
```
```

## Version History Template

```markdown
## Version History

### Version [X.Y.Z] (YYYY-MM-DD)
**Status**: Current version
**Changes**:
- Added feature X (✅ tested)
- Fixed bug Y (✅ verified)
- Improved performance by 20% (✅ benchmarked)

**Breaking changes**: None | [Description if any]
**Migration guide**: [Link if needed]

### Version [X.Y.Z-1] (YYYY-MM-DD)
**Status**: Previous version
**Changes**:
- Initial implementation
- Basic functionality

**Known issues in this version**:
- [Issue that was fixed in later version]
```

## Footer Template

```markdown
## API Reference Status

**Verification details**:
- **Last tested**: YYYY-MM-DD
- **Test environment**: [OS, Python version, dependency versions]
- **Code version**: [Git commit hash or version tag]
- **Tester**: [Name/team]

**Accuracy guarantee**:
- ✅ All code examples tested and working
- ✅ Error messages verified against actual code
- ✅ Performance data measured in real environment
- ✅ Dependencies verified and versions confirmed

**Update triggers**:
- Function signature changes
- Behavior modifications
- New error conditions
- Performance improvements
- User-reported issues

**Related documentation**:
- [Link to tutorial using this API]
- [Link to troubleshooting guide]
- [Link to source code]

---
**API Documentation Status**: ✅ Verified Accurate | Last Updated: YYYY-MM-DD
```

## Usage Instructions

1. **Copy this template** for each API function/class
2. **Extract actual signatures** from the source code
3. **Test all examples** in the documented environment
4. **Measure performance** on representative hardware
5. **Document real error messages** from actual testing
6. **Verify all imports** work as documented
7. **Update version information** when code changes
8. **Schedule regular re-verification** to maintain accuracy

This template ensures that API documentation provides developers with reliable, tested information about actual function behavior and capabilities.