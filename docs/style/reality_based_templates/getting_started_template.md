# Getting Started Guide Template

**Use this template to create reliable, tested getting started guides**

## Header Template

```markdown
# Getting Started with [Tool/Library/System]

**Status**: ✅ Fully Tested | 🚧 Some Issues | 📋 In Progress
**Completion Time**: [X] minutes (measured during testing)
**Success Rate**: [Y]% (based on user testing)
**Last Verified**: YYYY-MM-DD
**Test Environment**: [OS, versions, hardware specs]

## Prerequisites Verification

**Before starting, verify these requirements:**
```bash
# Run these commands to check prerequisites
[command_1]  # Expected: [expected_output_1]
[command_2]  # Expected: [expected_output_2]
[command_3]  # Expected: [expected_output_3]
```

**If any prerequisite check fails**: [Link to setup section]

## Quick Success Check

**Start here to verify you can complete this guide:**
```bash
# Quick test that verifies the main workflow will work
[quick_test_command]
```

**Expected output**:
```
[expected_success_output]
```

**If this fails**: [Link to troubleshooting section]
```

## Step-by-Step Workflow Template

```markdown
## Step 1: [Action Name]

**Purpose**: [Why this step is needed]
**Estimated time**: [X] minutes

### Execution

**Tested command** (verified YYYY-MM-DD):
```bash
# This exact command was tested and works
[exact_command_that_works]
```

**Expected output**:
```
[actual_output_from_testing]
```

### Verification

**Check that step worked**:
```bash
# Verification command
[verification_command]
# Should show: [expected_verification_result]
```

### Common Issues
- **Issue**: [Specific problem that might occur]
  **Symptom**: [What user sees]
  **Solution**: [Tested fix]
  
- **Issue**: [Another common problem]
  **Solution**: [Working workaround]

**Step status**: ✅ Working | 🚧 Requires workaround | ⚠️ Known issues

---

## Step 2: [Next Action Name]

**Purpose**: [What this accomplishes]
**Dependencies**: Must complete Step 1 successfully

### Execution

**Tested commands**:
```bash
# Commands tested in sequence
[command_1]
[command_2]
[command_3]
```

**Progress indicators**:
- After command 1: [what you should see]
- After command 2: [what you should see]  
- After command 3: [final result]

### Verification

**Complete verification test**:
```bash
# Test the full functionality from this step
[comprehensive_test_command]
```

**Success criteria**:
- ✅ [Specific success indicator 1]
- ✅ [Specific success indicator 2]
- ✅ [Specific success indicator 3]

### Troubleshooting
**If verification fails**:
1. Check output of: `[diagnostic_command]`
2. Common cause: [most likely issue]
3. Solution: [tested fix]

**Step status**: ✅ Working
```

## Environment Setup Template

```markdown
## Environment Setup

### System Requirements

**Minimum requirements** (tested on these configs):
- OS: [Specific versions tested]
- RAM: [Minimum amount needed]  
- Disk: [Space required]
- Network: [Connection requirements if any]

**Recommended setup** (for best experience):
- OS: [Recommended versions]
- RAM: [Recommended amount]
- CPU: [Performance recommendations]

### Software Installation

**Required software** (with verified versions):
```bash
# Install required components
[installation_command_1]  # Installs: [what gets installed]
[installation_command_2]  # Installs: [what gets installed]
```

**Version verification**:
```bash
# Check installed versions
[version_check_1]  # Expected: [version_range]
[version_check_2]  # Expected: [version_range]
```

**Installation troubleshooting**:
- **Permission errors**: [Solution for permission issues]
- **Network issues**: [Solution for download problems]  
- **Version conflicts**: [Solution for dependency conflicts]

### Configuration

**Required configuration** (tested settings):
```bash
# Configuration commands that work
[config_command_1]
[config_command_2]
```

**Configuration verification**:
```bash
# Test that configuration is correct
[config_test_command]
# Expected output: [what_correct_config_shows]
```

**Configuration file locations**:
- Primary config: `[file_path]`
- User config: `[file_path]`
- System config: `[file_path]`

### Environment Validation

**Complete environment test** (run this before proceeding):
```bash
#!/bin/bash
# Environment validation script
echo "=== Environment Validation ==="

# Test 1: Required software
echo "Testing required software..."
[software_test_commands]

# Test 2: Configuration
echo "Testing configuration..."
[config_test_commands]

# Test 3: Connectivity (if needed)
echo "Testing connectivity..."
[connectivity_tests]

# Test 4: Permissions
echo "Testing permissions..."
[permission_tests]

echo "=== Validation Complete ==="
```

**If validation fails**: [Link to detailed troubleshooting]
```

## First Success Template

```markdown
## Your First Success

**Goal**: Complete a simple end-to-end workflow to verify everything works.

### Prepare Test Data

**Create test data** (verified working):
```bash
# Create sample data for testing
[data_creation_commands]
```

**Verify test data**:
```bash
# Check that test data is valid
[data_verification_commands]
# Should show: [expected_data_characteristics]
```

### Execute Basic Workflow

**Step-by-step basic workflow** (tested complete):
```bash
# Step 1: Initialize
[init_command]
# Expected: [init_output]

# Step 2: Process
[process_command]
# Expected: [process_output]

# Step 3: Verify results
[verify_command]
# Expected: [verify_output]
```

### Confirm Success

**Success indicators**:
- ✅ Process completes without errors
- ✅ Output files created: [list_specific_files]
- ✅ Results match expected pattern: [describe_pattern]

**Final verification**:
```bash
# Comprehensive success test
[final_test_command]
```

**Expected final output**:
```
[exact_success_output_from_testing]
```

**Celebration checkpoint**: 🎉 If you see the above output, you've successfully completed the basic workflow!

### What You've Accomplished

By completing this workflow, you have:
- ✅ [Specific achievement 1]
- ✅ [Specific achievement 2]  
- ✅ [Specific achievement 3]
- ✅ Proven your environment is working correctly

### Next Steps

**Now that basic functionality works**:
1. **Try advanced features**: [Link to advanced guide]
2. **Work with your own data**: [Link to data import guide]
3. **Explore more capabilities**: [Link to feature overview]
4. **Join the community**: [Link to community resources]
```

## Complete Example Template

```markdown
## Complete Working Example

**Real-world scenario**: [Describe practical use case]

### Problem Setup
**Context**: [Realistic scenario description]
**Goal**: [Specific objective]
**Input**: [What user starts with]
**Expected output**: [What user should achieve]

### Solution Walkthrough

**Complete solution** (tested working):
```python
# Complete working example - verified YYYY-MM-DD
# This exact code produces the documented results

# Step 1: Setup
[setup_code]

# Step 2: Load/prepare data
[data_code]

# Step 3: Main processing
[processing_code]

# Step 4: Generate results
[results_code]

# Step 5: Verification
[verification_code]
```

**Run the complete example**:
```bash
# Save the above code as: complete_example.py
python3 complete_example.py
```

**Expected output**:
```
[actual_output_from_running_complete_example]
```

### Example Breakdown

**What each section does**:
- **Setup section**: [Explanation of setup code]
- **Data section**: [Explanation of data handling]
- **Processing section**: [Explanation of main logic]
- **Results section**: [Explanation of output generation]
- **Verification section**: [How to confirm success]

### Adaptation Guide

**To use with your own data**:
1. Replace `[input_data]` with your data source
2. Adjust `[parameters]` for your use case
3. Modify `[output_format]` as needed

**Parameter guidelines**:
- `param1`: Recommended range [X-Y], tested with [specific_values]
- `param2`: Options are [A, B, C], default is [B]
- `param3`: Set to [value] for most use cases
```

## Progress Tracking Template

```markdown
## Progress Checklist

**Track your completion**:
- [ ] **Prerequisites verified** - all requirements met
- [ ] **Environment setup** - software installed and configured
- [ ] **Basic workflow** - simple end-to-end test completed
- [ ] **First success** - achieved working result
- [ ] **Complete example** - ran full realistic scenario
- [ ] **Verification passed** - all tests show expected results

**Estimated progress time**:
- Prerequisites: [X] minutes
- Environment setup: [Y] minutes  
- Basic workflow: [Z] minutes
- First success: [A] minutes
- Complete example: [B] minutes
- **Total**: [X+Y+Z+A+B] minutes

**If stuck**:
- **On prerequisites**: [Link to prerequisite troubleshooting]
- **On environment**: [Link to setup troubleshooting]
- **On workflow**: [Link to workflow troubleshooting]
- **On examples**: [Link to example troubleshooting]

## Completion Verification

**You've successfully completed this guide when**:
- ✅ All checklist items completed
- ✅ Complete example runs without errors
- ✅ Verification tests pass
- ✅ You understand the basic workflow
- ✅ You can adapt the example to your needs

**Final verification command**:
```bash
# Run this to confirm everything is working
[final_comprehensive_test]
```

**Success output**:
```
[expected_final_success_message]
```

**Certificate of completion**: [Provide some recognition/badge/cert if appropriate]
```

## Support and Next Steps Template

```markdown
## Support Resources

### When You Need Help

**Before asking for help** - gather this information:
```bash
# System information
[system_info_commands]

# Error information  
[error_capture_commands]

# Environment information
[environment_info_commands]
```

**Where to get help**:
- **Documentation**: [Link to comprehensive docs]
- **Community forum**: [Link to community discussions]
- **Issue tracker**: [Link for bug reports]
- **Live chat**: [Link to real-time help if available]

### Next Learning Paths

**Based on your goals**:

**For researchers/analysts**:
1. [Advanced analysis guide]
2. [Data visualization tutorial]
3. [Statistical methods documentation]

**For developers**:
1. [API reference documentation]
2. [Integration guide]  
3. [Custom extension development]

**For system administrators**:
1. [Deployment guide]
2. [Performance tuning]
3. [Monitoring and maintenance]

### Advanced Topics

**Once you've mastered the basics**:
- **Performance optimization**: [Link to performance guide]
- **Advanced configuration**: [Link to config reference]
- **Integration patterns**: [Link to integration examples]
- **Best practices**: [Link to best practices guide]

### Contributing Back

**Ways to help the community**:
- **Report issues**: [How to submit good bug reports]
- **Improve documentation**: [How to contribute to docs]
- **Share examples**: [How to submit example workflows]
- **Answer questions**: [How to help in community forums]

---
**Getting Started Guide**: ✅ All Examples Tested | Last Updated: YYYY-MM-DD
```

## Quality Assurance Checklist

```markdown
## Guide Quality Checklist

**Before publishing this guide, verify**:
- [ ] **All commands tested** in fresh environment
- [ ] **All outputs verified** against actual results
- [ ] **Timing measured** for each section
- [ ] **Prerequisites validated** - nothing missing
- [ ] **Error scenarios tested** - common issues documented
- [ ] **Success criteria clear** - user knows when they've succeeded
- [ ] **Troubleshooting comprehensive** - covers real issues
- [ ] **Next steps provided** - user knows how to continue
- [ ] **Support resources listed** - user knows where to get help
- [ ] **Regular review scheduled** - guide stays current

**Testing environment**:
- **Tester**: [Name]
- **Date**: YYYY-MM-DD
- **Environment**: [Detailed environment specification]
- **Time taken**: [Actual time to complete guide]
- **Issues encountered**: [Any problems found during testing]
- **User feedback**: [Input from target users if available]
```

## Usage Instructions

1. **Copy this template** for your getting started guide
2. **Test every command** in a fresh environment
3. **Measure actual timing** for each section
4. **Document real outputs** from your testing
5. **Include working examples** that you've verified
6. **Test with target users** to validate effectiveness
7. **Update regularly** to maintain accuracy
8. **Track success rates** based on user feedback

This template ensures that getting started guides provide users with a reliable, tested path to success with clear verification at each step.