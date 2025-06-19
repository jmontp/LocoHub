# Truth-First Writing Style Guide

**Single Source of Truth for Accurate Technical Documentation**

Created: 2025-06-19 with user permission
Purpose: Ensure all documentation claims are verifiable against actual code

Intent: Eliminate documentation drift by embedding fact-checking directly into the writing process. Every technical claim must be tested before publication.

## Core Writing Principles

### 1. Verifiable First
**Every technical claim must be testable against the actual codebase.**

**Required Actions:**
- Test every code example before documenting it
- Verify every file path and import statement 
- Run every command and procedure before writing about it
- Validate every feature claim against actual implementation

**Language Templates:**
```markdown
✅ GOOD: "Run `python3 lib/validation/dataset_validator_phase.py --help` (tested 2025-06-19)"
❌ BAD: "Run the validation tool to check your dataset"

✅ GOOD: "Import the library: `from lib.core.locomotion_analysis import LocomotionData` (verified working)"
❌ BAD: "Import the library from the source directory"
```

### 2. Status Transparent 
**Clearly distinguish between available, partial, and planned features.**

**Status Indicators:**
- **✅ Available**: Feature is fully implemented and tested
- **🚧 Partial**: Feature is implemented but has known limitations
- **📋 Planned**: Feature is designed but not yet implemented
- **⚠️ Issues**: Feature exists but has known problems

**Language Templates:**
```markdown
✅ GOOD: "**✅ Available**: Load data with `LocomotionData.from_parquet()`"
✅ GOOD: "**🚧 Partial**: MATLAB integration works for data loading but plotting has import issues"
✅ GOOD: "**📋 Planned**: Automated ML benchmark generation (target: Q3 2025)"
❌ BAD: "Use the comprehensive data loading and analysis capabilities"
```

### 3. Implementation Honest
**Acknowledge limitations and communicate real capabilities.**

**Templates for Limitations:**
```markdown
✅ GOOD: "**Current Limitation**: The validation tool requires manual path setup due to import structure issues"
✅ GOOD: "**Known Issue**: Tutorial files need to be copied to working directory manually"
✅ GOOD: "**Workaround Required**: Add `sys.path.append('lib')` before importing modules"
❌ BAD: "Easy-to-use validation tools" (when they have setup issues)
```

### 4. Code-Synced Examples
**All code examples must be working and up-to-date.**

**Requirements:**
- Every code block must be tested in the documented environment
- Include expected output when relevant
- Add troubleshooting for common issues
- Update examples when code changes

**Example Format:**
```markdown
**Tested Code Example** (verified 2025-06-19):
```python
# Working example - tested successfully
import sys
sys.path.append('lib')
from core.locomotion_analysis import LocomotionData

data = LocomotionData.from_parquet('dataset.parquet')
print("Data loaded successfully")
```

**Expected Output:**
```
Data loaded successfully
```

**Common Issues:**
- Ensure dataset.parquet exists in working directory
- Add lib directory to Python path before importing
```

### 5. User-Tested Workflows
**Document complete, working user workflows from start to finish.**

**Workflow Documentation Requirements:**
- Test complete workflow from fresh environment
- Include all prerequisite steps
- Document common failure points
- Provide troubleshooting steps
- Verify workflows work for target user personas

## Fact-Checking Requirements

### Before Publishing Any Documentation:

**1. Path Verification**
```bash
# Verify every file path mentioned
ls -la /path/mentioned/in/docs
find . -name "file_mentioned.py" -type f
```

**2. Command Testing**
```bash
# Test every command exactly as documented
python3 tool_name.py --help
python3 tutorial_script.py
```

**3. Import Verification**
```python
# Test every import statement
try:
    from module_name import ClassName
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

**4. Feature Testing**
```python
# Test every claimed feature
try:
    result = feature_function()
    print(f"✅ Feature works: {result}")
except Exception as e:
    print(f"❌ Feature broken: {e}")
```

## Content Quality Standards

### Technical Claims
- **Measurable**: Include specific performance metrics where claimed
- **Testable**: Provide exact steps to verify the claim
- **Current**: Include verification date for time-sensitive claims
- **Scoped**: Clearly define what is and isn't covered

### User Instructions
- **Complete**: Include all prerequisite steps
- **Sequential**: Present steps in logical order
- **Tested**: Verify instructions work from clean state
- **Troubleshooting**: Include common failure modes

### Code Documentation
- **Executable**: All code examples must run successfully
- **Commented**: Explain complex or non-obvious code
- **Updated**: Sync with actual implementation
- **Environment**: Specify required dependencies and setup

## Review Checklist

Before publishing documentation, verify:

- [ ] **All file paths verified to exist**
- [ ] **All commands tested and working**
- [ ] **All imports verified functional**
- [ ] **All code examples executed successfully**
- [ ] **All features tested against actual implementation**
- [ ] **Status indicators accurate (Available/Partial/Planned)**
- [ ] **Limitations and workarounds documented**
- [ ] **Complete workflows tested end-to-end**
- [ ] **Troubleshooting sections include real issues**
- [ ] **Verification dates included for time-sensitive content**

## Language Guidelines

### Preferred Phrases
- "Tested working example"
- "Verified functionality"
- "Current implementation supports"
- "Known limitation"
- "Workaround required"
- "Implementation status: [Available/Partial/Planned]"

### Avoid These Phrases
- "Easy-to-use" (without verification)
- "Comprehensive" (without defining scope)
- "Simply run" (without testing)
- "Should work" (uncertainty language)
- "Full support" (without testing edge cases)

## Update Responsibilities

### When Code Changes
1. **Immediate**: Mark affected documentation as "⚠️ Needs Review"
2. **Within 24h**: Test and update affected documentation
3. **Verification**: Re-test all examples and commands
4. **Status Update**: Update verification dates

### Regular Maintenance
- **Weekly**: Spot-check high-traffic documentation
- **Monthly**: Full verification of installation guides
- **Quarterly**: Complete documentation accuracy audit
- **Release**: Full verification before any public release

## Truth Verification Framework

### Documentation Testing Pipeline
1. **Automated Testing**: Include documentation tests in CI/CD
2. **Manual Verification**: Human review of complex workflows
3. **User Testing**: Validate with target personas
4. **Continuous Monitoring**: Track user issues and feedback

### Accuracy Metrics
- **Verification Coverage**: % of claims tested
- **Broken Link Rate**: % of references that fail
- **User Success Rate**: % of users completing documented workflows
- **Issue Resolution Time**: Speed of fixing discovered inaccuracies

This guide ensures that every piece of technical documentation accurately reflects the current state of the codebase and provides users with reliable, working information.