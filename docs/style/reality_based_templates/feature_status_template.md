# Feature Status Documentation Template

**Use this template to accurately communicate feature implementation status**

## Feature Status Header Template

```markdown
# [Feature Name]

**Implementation Status**: [Status Badge]
**Last Verified**: YYYY-MM-DD
**Test Coverage**: [X]% verified working
**User Impact**: [High/Medium/Low]

## Status Legend
- ✅ **Fully Available**: Feature is complete, tested, and working
- 🚧 **Partially Available**: Core functionality works but has limitations
- 🔄 **In Development**: Feature is being actively implemented
- 📋 **Planned**: Feature is designed but not yet started
- ⚠️ **Has Issues**: Feature exists but has known problems
- ❌ **Not Available**: Feature is not implemented
- 🚫 **Deprecated**: Feature is being removed or replaced
```

## Implementation Details Template

```markdown
## Implementation Status

### ✅ Working Components
**[Component Name]** - Last tested: YYYY-MM-DD
```python
# Verified working example
from module import working_component
result = working_component.function()
print(f"✅ Works: {result}")
```
**What works**:
- [Specific functionality 1]
- [Specific functionality 2]
- [Specific functionality 3]

**Limitations**: None known

### 🚧 Partial Components
**[Component Name]** - Last tested: YYYY-MM-DD
```python
# Partially working example
from module import partial_component
result = partial_component.basic_function()  # Works
# result = partial_component.advanced_function()  # Fails - not implemented
```
**What works**:
- ✅ Basic functionality
- ✅ Simple use cases
- ✅ Standard input types

**What doesn't work**:
- ❌ Advanced features
- ❌ Complex input types
- ❌ Error recovery

**Workarounds**:
```python
# Use basic functionality only
result = basic_approach(input_data)
# Or use alternative method
result = alternative_component.function(input_data)
```

### 📋 Planned Components
**[Component Name]** - Target: Q[X] 20YY
**Design Status**: [Complete/In Progress/Not Started]
**Dependencies**: [List any blocking dependencies]

**Planned functionality**:
- [Feature 1] - [Target date]
- [Feature 2] - [Target date]
- [Feature 3] - [Target date]

**Current alternatives**:
```python
# Temporary workaround until feature is available
manual_result = manual_process(input_data)
```

### ⚠️ Problematic Components
**[Component Name]** - Issues identified: YYYY-MM-DD
**Problem severity**: [High/Medium/Low]

**Known issues**:
```python
# This code demonstrates the problem
try:
    result = problematic_function(input_data)
except Exception as e:
    print(f"❌ Known issue: {e}")
```

**Root cause**: [Technical explanation]
**Impact**: [Who is affected and how]
**Workaround**: 
```python
# Working alternative approach
result = alternative_approach(input_data)
```

**Fix status**: [Planned/In Progress/Blocked]
**Tracking**: [Link to issue/ticket]
```

## User Capability Matrix Template

```markdown
## User Capability Matrix

| Use Case | Status | Verification | Notes |
|----------|--------|--------------|-------|
| [Basic Use Case 1] | ✅ Available | Tested YYYY-MM-DD | Fully working |
| [Basic Use Case 2] | ✅ Available | Tested YYYY-MM-DD | Fully working |
| [Advanced Use Case 1] | 🚧 Partial | Tested YYYY-MM-DD | Requires workaround |
| [Advanced Use Case 2] | 📋 Planned | Target Q[X] 20YY | Not yet started |
| [Complex Use Case] | ⚠️ Issues | Tested YYYY-MM-DD | Known limitations |
| [Edge Case] | ❌ Not Available | N/A | No implementation |

### Use Case Details

#### ✅ [Basic Use Case 1]
**What you can do**:
```python
# Verified working example
result = feature.basic_operation(standard_input)
assert result.success == True
```

**Requirements**: [List prerequisites]
**Performance**: [Measured performance data]
**Limitations**: None known

#### 🚧 [Advanced Use Case 1]
**What works**:
```python
# This part works
basic_result = feature.advanced_operation(simple_input)
```

**What doesn't work**:
```python
# This fails
# complex_result = feature.advanced_operation(complex_input)
# Error: NotImplementedError
```

**Workaround**:
```python
# Use this approach instead
workaround_result = feature.basic_operation(preprocessed_input)
```

**When full implementation expected**: [Target date]

#### ⚠️ [Complex Use Case]
**Known issues**:
- Issue 1: [Description and impact]
- Issue 2: [Description and impact]

**Workaround**:
```python
# Reliable alternative approach
alternative_result = alternative_feature.operation(input)
```

**Risk assessment**: [High/Medium/Low] - [Explanation]
```

## Integration Status Template

```markdown
## Integration Status

### System Integration
| Component | Status | Last Tested | Issues |
|-----------|--------|-------------|---------|
| Database Layer | ✅ Working | YYYY-MM-DD | None |
| API Layer | 🚧 Partial | YYYY-MM-DD | Auth issues |
| UI Layer | 📋 Planned | N/A | Not started |
| External APIs | ⚠️ Issues | YYYY-MM-DD | Rate limiting |

### Integration Testing Results
**End-to-end workflow test** (YYYY-MM-DD):
```python
# Complete workflow test
def test_complete_workflow():
    # Step 1 - Database (✅ Working)
    data = database.fetch_data()
    assert data is not None
    
    # Step 2 - Processing (✅ Working)
    processed = feature.process(data)
    assert processed.is_valid()
    
    # Step 3 - API (🚧 Partial - manual auth needed)
    # api_result = api.submit(processed)  # Fails - auth issue
    api_result = manual_api_submit(processed)  # Workaround
    
    # Step 4 - UI (📋 Planned - not implemented)
    # ui.display(api_result)  # Not available
    print(f"Result: {api_result}")  # Temporary

test_complete_workflow()
```

**Integration success rate**: [X]% (based on actual testing)
**Blocking issues**: [List critical blockers]
```

## Performance Status Template

```markdown
## Performance Status

### Benchmarked Performance
**Test environment**: [Hardware/OS specifications]
**Last benchmarked**: YYYY-MM-DD

| Operation | Target | Actual | Status |
|-----------|--------|--------|---------|
| [Operation 1] | <100ms | 45ms | ✅ Meets target |
| [Operation 2] | <500ms | 1.2s | ⚠️ Slower than target |
| [Operation 3] | <1s | N/A | 📋 Not implemented |

### Performance Test Results
```python
# Actual performance measurements
import time

# Test 1: Basic operation
start = time.time()
result = feature.basic_operation(test_data)
duration = time.time() - start
print(f"Basic operation: {duration:.3f}s")
# Result: 0.045s (✅ Meets <100ms target)

# Test 2: Complex operation  
start = time.time()
result = feature.complex_operation(large_data)
duration = time.time() - start
print(f"Complex operation: {duration:.3f}s")
# Result: 1.234s (⚠️ Exceeds 500ms target)
```

**Performance issues**:
- **Complex operations**: 2.4x slower than target
  - **Cause**: [Technical reason]
  - **Fix planned**: [Timeline]
  - **Workaround**: Use smaller batch sizes
```

## Compatibility Status Template

```markdown
## Compatibility Status

### Platform Compatibility
| Platform | Status | Last Tested | Notes |
|----------|--------|-------------|-------|
| Windows 10/11 | ✅ Supported | YYYY-MM-DD | Full functionality |
| Ubuntu 20.04+ | ✅ Supported | YYYY-MM-DD | Full functionality |
| macOS 12+ | 🚧 Partial | YYYY-MM-DD | Some features limited |
| CentOS 7 | ❌ Not Supported | N/A | Python version too old |

### Dependency Compatibility
```python
# Verified compatible versions
compatible_versions = {
    'python': '3.8-3.11',      # ✅ Tested
    'pandas': '1.3-2.1',       # ✅ Tested  
    'numpy': '1.20-1.24',      # ✅ Tested
    'matplotlib': '3.5+',      # 🚧 Partial (some features require 3.6+)
}

# Test compatibility
def test_compatibility():
    import sys
    import pandas as pd
    import numpy as np
    
    print(f"Python: {sys.version}")
    print(f"Pandas: {pd.__version__}")
    print(f"NumPy: {np.__version__}")
    
    # Test basic functionality
    result = feature.test_function()
    print(f"✅ Basic compatibility verified: {result}")

test_compatibility()
```

### Version Migration Status
**Current version**: [X.Y.Z]
**Migration status from previous versions**:
- From v[X.Y.Z-1]: ✅ Automatic migration
- From v[X.Y.Z-2]: 🚧 Manual steps required
- From v[X.Y.Z-3]: ❌ Not supported

**Migration guide**: [Link to migration documentation]
```

## Documentation Status Template

```markdown
## Documentation Status

### Documentation Completeness
| Document Type | Status | Last Updated | Accuracy |
|---------------|--------|--------------|----------|
| API Reference | ✅ Complete | YYYY-MM-DD | ✅ Verified |
| User Guide | 🚧 Partial | YYYY-MM-DD | ✅ Verified |
| Tutorials | 📋 Planned | N/A | N/A |
| Troubleshooting | ⚠️ Outdated | YYYY-MM-DD | 🚧 Needs update |

### Documentation Accuracy
**Verification process**:
```python
# All documented examples are tested
def verify_documentation():
    # Test API examples
    api_examples_pass = test_api_examples()
    
    # Test user guide examples
    guide_examples_pass = test_guide_examples()
    
    # Test troubleshooting solutions
    troubleshooting_pass = test_troubleshooting()
    
    return {
        'api_examples': api_examples_pass,      # ✅ 100% verified
        'guide_examples': guide_examples_pass,  # 🚧 80% verified
        'troubleshooting': troubleshooting_pass # ⚠️ 60% verified
    }
```

**Documentation issues**:
- **User Guide**: Missing examples for advanced features
- **Troubleshooting**: Some solutions outdated for current version
- **API Reference**: All examples tested and working

**Update priority**: [High/Medium/Low]
```

## Communication Template

```markdown
## Status Communication

### For End Users
**What you can do right now**:
- ✅ [List of fully available features]
- ✅ [List of working capabilities]

**What needs workarounds**:
- 🚧 [Feature with limitation]: Use [workaround approach]
- 🚧 [Feature with issues]: Alternative method: [description]

**What's coming soon**:
- 📋 [Planned feature]: Expected [timeframe]
- 📋 [Planned improvement]: Target [date]

### For Developers
**Implementation status**:
- **Core functionality**: ✅ Complete and tested
- **Advanced features**: 🚧 70% complete
- **Edge cases**: ⚠️ Known issues in [specific areas]
- **Performance**: 🚧 Meets targets except [specific operations]

**Development blockers**:
- [Blocker 1]: [Description and impact]
- [Blocker 2]: [Description and resolution plan]

### For Project Managers
**Delivery status**:
- **Milestone 1**: ✅ Complete (YYYY-MM-DD)
- **Milestone 2**: 🚧 80% complete (target: YYYY-MM-DD)
- **Milestone 3**: 📋 Not started (target: YYYY-MM-DD)

**Risk assessment**:
- **High risk**: [Issue that could impact timeline]
- **Medium risk**: [Issue with workaround available]
- **Low risk**: [Minor issues that don't affect delivery]

**Resource needs**:
- [Specific resource requirements]
- [Blocking dependencies]
```

## Update Schedule Template

```markdown
## Status Update Schedule

**Regular updates**:
- **Weekly**: Development team status review
- **Bi-weekly**: User-facing status page updates
- **Monthly**: Comprehensive feature status audit
- **Quarterly**: Status communication to stakeholders

**Trigger-based updates**:
- **Immediate**: Critical issues or security problems
- **24-48 hours**: Significant feature completions
- **1 week**: Minor bug fixes or improvements

**Update responsibilities**:
- **Developer**: Update technical status after changes
- **QA**: Verify and update test status
- **Documentation**: Update user-facing status
- **PM**: Communicate status to stakeholders

**Status verification**:
- All status claims must be verified before publication
- Include verification date and responsible person
- Link to supporting evidence (test results, benchmarks)
- Regular audit of status accuracy

---
**Feature Status Documentation**: ✅ Template Verified | Last Updated: YYYY-MM-DD
```

## Usage Instructions

1. **Copy appropriate sections** for your feature
2. **Test all claimed functionality** before documenting status
3. **Use specific status indicators** consistently
4. **Include verification dates** and testing details
5. **Document workarounds** for partial implementations
6. **Update regularly** as implementation progresses
7. **Verify accuracy** before publishing status updates

This template ensures that feature status communication is honest, accurate, and helpful for users making decisions based on current capabilities.