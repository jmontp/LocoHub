# Tutorial Template: Reality-Based Documentation

**Use this template for all tutorial content to ensure accuracy and verifiability**

## Header Template

```markdown
# [Tutorial Title]

**Status**: ✅ Verified Working | 🚧 Partial Issues | ❌ Known Problems | 📋 Planned

**Last Verified**: [YYYY-MM-DD]
**Test Environment**: [OS, Python version, etc.]
**Estimated Time**: [X minutes] (measured in verification testing)

## Quick Verification

**Before following this tutorial, verify prerequisites:**
```bash
# Test commands that must work before starting
python3 --version  # Must be 3.8+
pip list | grep pandas  # Must show pandas installed
# Add other prerequisite checks
```

**Expected output:**
```
Python 3.9.16
pandas 1.5.3
```

**If verification fails**: [Link to setup/troubleshooting guide]
```

## Content Structure Template

### Step-by-Step Format
```markdown
## Step N: [Action Description]

**What this step does**: [Brief explanation of purpose]

**Verified command/code**:
```[language]
# Tested working example - verified [date]
[exact code that was tested]
```

**Expected output**:
```
[actual output from testing]
```

**Verification checkpoint**:
```bash
# Quick test to ensure step worked
[verification command]
# Expected result: [description]
```

**Common issues**:
- **Issue**: [Specific error message or problem]
  **Solution**: [Exact steps to resolve]
  **Why this happens**: [Brief explanation]

**Status**: ✅ Working | ⚠️ Requires workaround | ❌ Known issue
```

## Code Block Requirements

**Every code block must include:**
- **Verification date**: When it was last tested
- **Environment info**: Where it was tested
- **Success criteria**: What constitutes "working"
- **Error handling**: Expected failure modes

```markdown
**Tested Code Example** (verified YYYY-MM-DD on [environment]):
```python
# This exact code was executed and verified working
import pandas as pd

# Load test data
data = pd.read_csv('sample_data.csv')
print(f"Loaded {len(data)} rows successfully")
```

**Expected output**:
```
Loaded 150 rows successfully
```

**Testing verification**:
```bash
# Commands used to verify this example
ls -la sample_data.csv  # File must exist
python3 -c "import pandas; print('pandas working')"
```
```

## Prerequisites Section Template

```markdown
## Prerequisites

**Required (tested and verified)**:
- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] Pandas library (`pip list | grep pandas`)
- [ ] Sample data files in working directory (`ls sample_data.csv`)

**Verification script**:
```bash
#!/bin/bash
# Prerequisite verification script - run this first
echo "Checking prerequisites..."

# Check Python version
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Check required packages
python3 -c "import pandas" || { echo "❌ Pandas not installed"; exit 1; }

# Check data files
ls sample_data.csv >/dev/null 2>&1 || { echo "❌ Sample data missing"; exit 1; }

echo "✅ All prerequisites verified"
```

**If verification fails**:
- **Python not found**: [Link to Python installation guide]
- **Pandas not installed**: Run `pip install pandas`
- **Data files missing**: [Link to data download section]
```

## Troubleshooting Section Template

```markdown
## Troubleshooting

**Common Issues** (collected from actual user reports):

### Issue: [Specific Error Message]
**Error output**:
```
[Exact error message from testing]
```

**Root cause**: [What actually causes this error]

**Solution** (tested working):
```bash
# Exact commands to fix the issue
[step-by-step solution]
```

**Verification**:
```bash
# How to confirm the fix worked
[verification command]
```

**Status**: ✅ Solution verified | 🚧 Workaround only | 📋 Fix planned

### Issue: Import Errors
**Typical error**:
```
ModuleNotFoundError: No module named 'xyz'
```

**Working solution**:
```python
# Add this at the beginning of your script
import sys
sys.path.append('path/to/modules')  # Adjust path as needed
import xyz
```

**Why this is needed**: [Explanation of the underlying issue]
```

## Testing Checklist Template

```markdown
## Tutorial Verification Checklist

**Before publishing, verify:**
- [ ] **Fresh environment test**: Tutorial tested from clean state
- [ ] **All code blocks executed**: Every example runs successfully
- [ ] **Prerequisites verified**: All requirements actually needed
- [ ] **Error cases tested**: Common failures documented with solutions
- [ ] **Time estimate accurate**: Tutorial completed within stated time
- [ ] **Output verification**: All expected outputs match actual results
- [ ] **Platform testing**: Verified on target operating systems
- [ ] **Dependency versions**: Compatible versions documented and tested

**Testing environment details**:
- **Date**: YYYY-MM-DD
- **Tester**: [Name]
- **Platform**: [OS, versions]
- **Duration**: [Actual time taken]
- **Issues found**: [List any problems discovered]
- **Success rate**: [X/Y steps completed successfully]
```

## Status and Maintenance Template

```markdown
## Tutorial Status

**Current Status**: ✅ Fully Working
**Last Updated**: YYYY-MM-DD
**Next Review Due**: YYYY-MM-DD

**Version Compatibility**:
- Python 3.8-3.11: ✅ Tested working
- Pandas 1.3+: ✅ Compatible
- Windows 10/11: ✅ Verified
- Ubuntu 20.04+: ✅ Verified
- macOS 12+: 🚧 Limited testing

**Known Limitations**:
- [Specific limitation 1]: [Impact and workaround]
- [Specific limitation 2]: [Impact and workaround]

**Update Triggers**:
- Code library updates
- Python version changes
- User-reported issues
- Quarterly review cycle

**Maintenance Notes**:
- [Date]: Updated for library v2.1 compatibility
- [Date]: Fixed import path issues reported by users
- [Date]: Added Windows-specific troubleshooting
```

## Footer Template

```markdown
## Verification Information

**This tutorial was verified working with:**
- **Environment**: [Specific versions and setup]
- **Test Date**: YYYY-MM-DD
- **Completion Time**: XX minutes (measured)
- **Success Criteria**: [What defines successful completion]

**Issues or improvements?**
- Report problems: [Link to issue tracker]
- Suggest improvements: [Link to contribution guide]
- Community discussion: [Link to forum/chat]

**Related Resources**:
- [Link to prerequisite setup guide]
- [Link to troubleshooting knowledge base]  
- [Link to advanced topics]

---
**Documentation Status**: ✅ Verified Accurate | Last Updated: YYYY-MM-DD
```

## Usage Instructions

1. **Copy this template** for new tutorials
2. **Fill in all verification sections** with actual test results
3. **Test the complete tutorial** in a fresh environment
4. **Document all issues found** during testing
5. **Include real error messages** and working solutions
6. **Update status indicators** based on actual testing results
7. **Schedule regular re-verification** to maintain accuracy

This template ensures that every tutorial provides users with reliable, tested instructions that actually work in real environments.