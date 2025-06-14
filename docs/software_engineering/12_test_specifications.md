# Test Specifications

**Test cases split into focused documents for better organization.**

## Split Documentation

This document has been split into three focused files:

**[Unit Tests](12a_unit_tests.md)** - Component-level tests for individual functions  
**[Integration Tests](12b_integration_tests.md)** - Component interaction and workflow tests  
**[Acceptance Tests](12c_acceptance_tests.md)** - User story acceptance criteria validation

## Legacy Content

The content below is preserved for reference but should be migrated to the split documents above.

### 🎯 Testing Philosophy

**PhaseValidator is the critical quality gate** - Since conversion scripts will come from external collaborators in various formats, the PhaseValidator must robustly validate all parquet files regardless of their conversion source.

### Test Categories

**Parquet Validation Tests** - Ensuring parquet file consistency and standards compliance 🔥
**Interface Contract Tests** - Component behavior according to specifications  
**Integration Tests** - Component interaction validation  
**Acceptance Tests** - User story acceptance criteria validation
**Performance Tests** - Large dataset handling validation

### Test Priorities

**Priority 1 (Critical) 🔥** - Must pass for any release - FOCUS: PhaseValidator parquet consistency
**Priority 2 (High)** - Should pass for quality release - FOCUS: High priority components  
**Priority 3 (Lower)** - Basic functionality - FOCUS: DatasetConverter basic operations

### Test Data Strategy

**Parquet File Tests** - Testing various parquet structures from different conversion sources 🔥
**Synthetic Dataset Tests** - Generated test data with known properties and violations
**External Conversion Tests** - Parquet files from external collaborator conversion scripts
**Edge Case Tests** - Boundary conditions and error scenarios
**Performance Tests** - Large datasets for scalability validation

---

## Critical Priority Component Tests

> **These tests validate components required for all new datasets (UC-C02, UC-C03)**
> 
> **🎯 PRIMARY FOCUS: PhaseValidator is the critical quality gate for all parquet files from external conversion scripts**
> **UC-C01 (Dataset Conversion) is handled by external collaborators with varying scripts - we only validate outputs**

### PhaseValidator Tests (UC-C02) - 🔥 HIGHEST PRIORITY

> **PhaseValidator is the most critical component - it's the quality gate that ensures all parquet files (regardless of conversion source) meet standards**
> 
> **VALIDATION REPORT THREE CORE GOALS:**
> 1. **Sign Convention Adherence** - Verify biomechanical data follows standard sign conventions
> 2. **Outlier Detection** - Identify strides with biomechanical values outside acceptable ranges  
> 3. **Phase Segmentation Validation** - Ensure exactly 150 points per gait cycle with proper phase indexing

#### Parquet File Structure Tests - Priority 1 🔥

**Test: validate_standard_parquet_structure**
```python
def test_validate_standard_parquet_structure():
    """Test validation of parquet files with standard structure (MOST CRITICAL TEST)"""
    # Given: Parquet file with correct standard structure including task column
    data = create_standard_phase_parquet_with_tasks(['walking', 'running'])
    test_file = save_test_data(data, "standard_structure.parquet")
    
    # When: Validating parquet structure
    validator = PhaseValidator(spec_manager, error_handler)
    result = validator.validate_dataset(test_file)
    
    # Then: Standard structure validation passes
    assert result.is_valid == True
    assert len(result.errors) == 0
    
    # And: All required columns are present
    required_columns = ['subject_id', 'trial_id', 'cycle_id', 'phase', 'task']
    data = pd.read_parquet(test_file)
    for col in required_columns:
        assert col in data.columns, f"Required column {col} missing"
    
    # And: Tasks are properly detected
    assert result.detected_tasks == ['walking', 'running']
    assert result.validated_tasks == ['walking', 'running']  # Both have specs
    assert len(result.skipped_tasks) == 0
```

**Test: detect_malformed_parquet_structure**
```python
def test_detect_malformed_parquet_structure():
    """Test detection of parquet files with malformed structure"""
    # Given: Parquet file missing required columns
    data = create_malformed_parquet(missing_columns=['subject_id', 'cycle_id'])
    test_file = save_test_data(data, "malformed_structure.parquet")
    
    # When: Validating malformed structure
    result = validator.validate_dataset(test_file)
    
    # Then: Structure validation fails with specific errors
    assert result.is_valid == False
    assert any("subject_id" in error for error in result.errors)
    assert any("cycle_id" in error for error in result.errors)
```

**Test: validate_dataset_missing_task_column**
```python
def test_validate_dataset_missing_task_column():
    """Test handling of dataset missing required task column"""
    # Given: Parquet file missing task column
    data = create_test_phase_data_without_task_column()
    test_file = save_test_data(data, "no_task_column.parquet")
    
    # When: Validating dataset without task column
    result = validator.validate_dataset(test_file)
    
    # Then: Validation fails with clear error message
    assert result.is_valid == False
    assert any("task column" in error.lower() for error in result.errors)
    assert "Unable to detect tasks" in result.validation_scope
```

**Test: validate_dataset_with_unknown_tasks_only**
```python
def test_validate_dataset_with_unknown_tasks_only():
    """Test handling of dataset with only unknown/unsupported tasks"""
    # Given: Dataset with tasks not in feature_constants
    data = create_test_phase_data_with_unknown_tasks(['custom_task', 'experimental_gait'])
    test_file = save_test_data(data, "unknown_tasks.parquet")
    
    # When: Validating dataset with unknown tasks
    result = validator.validate_dataset(test_file)
    
    # Then: Validation handles gracefully but reports issues
    assert result.is_valid == False  # No valid tasks to validate
    assert result.detected_tasks == ['custom_task', 'experimental_gait']
    assert len(result.validated_tasks) == 0
    assert result.skipped_tasks == ['custom_task', 'experimental_gait']
    assert any("unknown task" in warning.lower() for warning in result.warnings)
```

**Test: validate_dataset_with_mixed_known_unknown_tasks**
```python
def test_validate_dataset_with_mixed_known_unknown_tasks():
    """Test handling of dataset mixing known and unknown tasks"""
    # Given: Dataset with both known and unknown tasks
    data = create_test_phase_data_with_mixed_tasks(['walking', 'unknown_task', 'running'])
    test_file = save_test_data(data, "mixed_tasks.parquet")
    
    # When: Validating dataset with mixed tasks
    result = validator.validate_dataset(test_file)
    
    # Then: Validates known tasks, warns about unknown
    assert result.detected_tasks == ['walking', 'unknown_task', 'running']
    assert result.validated_tasks == ['walking', 'running']
    assert result.skipped_tasks == ['unknown_task']
    assert any("unknown_task" in warning for warning in result.warnings)
    # Should be valid if known tasks have valid strides
```

**Test: validate_phase_indexing_exactly_150_points**
```python
def test_validate_phase_indexing_exactly_150_points():
    """Test validation of correct phase indexing (exactly 150 points per cycle)"""
    # Given: Phase dataset with exactly 150 points per cycle
    data = create_test_phase_data(subjects=2, trials=3, cycles=5, points_per_cycle=150)
    test_file = save_test_data(data, "correct_phase.parquet")
    
    # When: Validating phase structure
    result = validator.validate_dataset(test_file)
    
    # Then: Phase validation passes
    assert result.is_valid == True
    assert "phase_structure" in result.validation_summary
    assert result.validation_summary["phase_structure"]["points_per_cycle"] == 150
```

**Test: detect_incorrect_phase_points**
```python
def test_detect_incorrect_phase_points():
    """Test detection of incorrect phase point counts (CRITICAL FAILURE MODE)"""
    # Given: Phase dataset with wrong number of points per cycle
    data = create_test_phase_data(subjects=1, trials=1, cycles=2, points_per_cycle=149)  # Should be 150
    test_file = save_test_data(data, "incorrect_phase.parquet")
    
    # When: Validating phase structure
    result = validator.validate_dataset(test_file)
    
    # Then: Validation fails with specific error
    assert result.is_valid == False
    assert any("150 points" in error for error in result.errors)
    assert "phase_structure" in result.validation_summary
    assert result.validation_summary["phase_structure"]["valid"] == False
```

#### Biomechanical Range Validation Tests - Priority 1 🔥

**Test: validate_stride_filtering_with_good_data**
```python
def test_validate_stride_filtering_with_good_data():
    """Test stride filtering when all data is within specification ranges"""
    # Given: Phase data with all strides within validation spec ranges
    data = create_test_phase_data_within_ranges(task="walking", num_strides=10)
    test_file = save_test_data(data, "good_strides.parquet")
    
    # When: Validating with stride filtering
    result = validator.validate_dataset(test_file)
    
    # Then: All strides are kept
    assert result.is_valid == True
    assert result.total_strides == 10
    assert result.valid_strides == 10
    assert result.invalid_strides == 0
    assert result.stride_pass_rate == 1.0
    assert len(result.kept_stride_ids) == 10
    assert len(result.deleted_stride_ids) == 0
    assert len(result.stride_rejection_reasons) == 0
```

**Test: filter_bad_strides_with_mixed_data**
```python
def test_filter_bad_strides_with_mixed_data():
    """Test stride filtering with mixed good and bad strides (CRITICAL FILTERING)"""
    # Given: Phase data with 7 good strides and 3 bad strides
    data = create_test_phase_data_mixed_quality(
        task="walking", 
        good_strides=7, 
        bad_strides=3,
        bad_stride_issues=["knee_angle_too_high", "hip_moment_out_of_range"]
    )
    test_file = save_test_data(data, "mixed_strides.parquet")
    
    # When: Validating with stride filtering
    result = validator.validate_dataset(test_file)
    
    # Then: Dataset is valid (some strides pass) with proper filtering
    assert result.is_valid == True  # Dataset valid because some strides pass
    assert result.total_strides == 10
    assert result.valid_strides == 7
    assert result.invalid_strides == 3
    assert result.stride_pass_rate == 0.7
    assert len(result.kept_stride_ids) == 7
    assert len(result.deleted_stride_ids) == 3
    
    # And: Rejection reasons are provided for bad strides
    assert len(result.stride_rejection_reasons) == 3
    for stride_id, reasons in result.stride_rejection_reasons.items():
        assert stride_id in result.deleted_stride_ids
        assert len(reasons) > 0
        assert any("knee_angle" in reason or "hip_moment" in reason for reason in reasons)
```

**Test: reject_dataset_with_no_valid_strides**
```python
def test_reject_dataset_with_no_valid_strides():
    """Test rejection when NO strides pass validation"""
    # Given: Phase data where all strides violate validation ranges
    data = create_test_phase_data_all_bad_strides(task="walking", num_strides=5)
    test_file = save_test_data(data, "all_bad_strides.parquet")
    
    # When: Validating completely bad dataset
    result = validator.validate_dataset(test_file)
    
    # Then: Dataset is rejected (no valid strides)
    assert result.is_valid == False  # Dataset invalid because NO strides pass
    assert result.total_strides == 5
    assert result.valid_strides == 0
    assert result.invalid_strides == 5
    assert result.stride_pass_rate == 0.0
    assert len(result.kept_stride_ids) == 0
    assert len(result.deleted_stride_ids) == 5
    
    # And: All strides have rejection reasons
    assert len(result.stride_rejection_reasons) == 5
```

**Test: filter_valid_strides_function**
```python
def test_filter_valid_strides_function():
    """Test the stride filtering function directly"""
    # Given: DataFrame with mixed stride quality
    data = create_test_phase_data_mixed_quality(
        task="walking", good_strides=8, bad_strides=2
    )
    
    # When: Filtering valid strides directly
    filter_result = validator.filter_valid_strides(data)
    
    # Then: Filtering results are correct
    assert filter_result.total_strides == 10
    assert filter_result.valid_strides == 8
    assert filter_result.invalid_strides == 2
    assert filter_result.stride_pass_rate == 0.8
    
    # And: Filtered data contains only valid strides
    assert len(filter_result.filtered_data) > 0
    valid_stride_data = filter_result.filtered_data['cycle_id'].unique()
    assert len(valid_stride_data) == 8
    
    # And: All kept strides are in the filtered data
    for stride_id in filter_result.kept_stride_ids:
        assert stride_id in filter_result.filtered_data['cycle_id'].values
    
    # And: No deleted strides are in the filtered data
    for stride_id in filter_result.deleted_stride_ids:
        assert stride_id not in filter_result.filtered_data['cycle_id'].values
```

**Test: validate_multiple_tasks_in_single_file**
```python
def test_validate_multiple_tasks_in_single_file():
    """Test validation of parquet files containing multiple tasks"""
    # Given: Parquet file with walking and running data
    walking_data = create_test_phase_data_within_ranges(task="walking")
    running_data = create_test_phase_data_within_ranges(task="running")
    combined_data = pd.concat([walking_data, running_data], ignore_index=True)
    test_file = save_test_data(combined_data, "multi_task.parquet")
    
    # When: Validating multi-task dataset
    result = validator.validate_dataset(test_file)
    
    # Then: Each task is validated against its specific ranges
    assert result.is_valid == True
    assert "task_breakdown" in result.validation_summary
    assert "walking" in result.validation_summary["task_breakdown"]
    assert "running" in result.validation_summary["task_breakdown"]
```

#### Parquet Consistency Tests - Priority 1 🔥

**Test: validate_data_types_and_formats**
```python
def test_validate_data_types_and_formats():
    """Test validation of proper data types in parquet files"""
    # Given: Parquet file with correct data types
    data = create_test_data_with_correct_types()
    test_file = save_test_data(data, "correct_types.parquet")
    
    # When: Validating data types
    result = validator.validate_dataset(test_file)
    
    # Then: Data type validation passes
    assert result.is_valid == True
    
    # And: Specific type checks
    data = pd.read_parquet(test_file)
    assert data['subject_id'].dtype == 'object'  # String
    assert data['phase'].dtype in ['float64', 'int64']  # Numeric
    assert pd.api.types.is_numeric_dtype(data['knee_flexion_angle_ipsi_rad'])
```

**Test: detect_inconsistent_subject_trial_structure**
```python
def test_detect_inconsistent_subject_trial_structure():
    """Test detection of inconsistent subject/trial/cycle structure"""
    # Given: Parquet file with inconsistent ID structure
    data = create_test_data_with_inconsistent_ids()
    test_file = save_test_data(data, "inconsistent_ids.parquet")
    
    # When: Validating ID structure
    result = validator.validate_dataset(test_file)
    
    # Then: Inconsistencies detected
    assert result.is_valid == False
    assert any("subject_id" in error or "trial_id" in error for error in result.errors)
```

#### Standard Specification Coverage Tests - Priority 1 🔥

**Test: validate_dataset_missing_all_kinematic_variables**
```python
def test_validate_dataset_missing_all_kinematic_variables():
    """Test handling of dataset missing all kinematic variables"""
    # Given: Dataset with only kinetic variables (no joint angles)
    data = create_test_phase_data_kinetic_only(task="walking")
    test_file = save_test_data(data, "kinetic_only.parquet")
    
    # When: Validating dataset missing kinematic variables
    result = validator.validate_dataset(test_file)
    
    # Then: Validation continues with available variables
    assert result.validation_scope == "partial"
    assert len(result.missing_standard_variables) > 0
    assert "kinematic" in str(result.missing_standard_variables)
    assert any("missing kinematic" in warning.lower() for warning in result.warnings)
    # Should still validate kinetic variables if present
```

**Test: validate_dataset_with_partial_standard_spec_coverage**
```python
def test_validate_dataset_with_partial_standard_spec_coverage():
    """Test handling of dataset with partial standard specification coverage"""
    # Given: Dataset with only 3 of 8 standard kinematic variables
    partial_variables = ['knee_flexion_angle_ipsi', 'hip_flexion_angle_ipsi', 'ankle_flexion_angle_ipsi']
    data = create_test_phase_data_with_subset_variables(task="walking", variables=partial_variables)
    test_file = save_test_data(data, "partial_coverage.parquet")
    
    # When: Validating partially covered dataset
    result = validator.validate_dataset(test_file)
    
    # Then: Validates available variables and reports coverage
    assert result.validation_scope == "partial"
    assert result.available_variables == partial_variables
    assert len(result.missing_standard_variables) > 0
    assert result.validation_coverage['walking'] < 1.0  # Partial coverage
    assert result.standard_spec_coverage['walking']  # Has coverage mapping
```

**Test: validate_dataset_with_non_standard_variables_only**
```python
def test_validate_dataset_with_non_standard_variables_only():
    """Test handling of dataset with only non-standard variables"""
    # Given: Dataset with custom variables not in standard specification
    custom_variables = ['custom_metric_1', 'proprietary_angle', 'experimental_force']
    data = create_test_phase_data_with_custom_variables(task="walking", variables=custom_variables)
    test_file = save_test_data(data, "non_standard_only.parquet")
    
    # When: Validating dataset with no standard variables
    result = validator.validate_dataset(test_file)
    
    # Then: Reports inability to validate
    assert result.validation_scope == "minimal"
    assert len(result.available_variables) == 0  # No standard variables
    assert len(result.missing_standard_variables) > 0
    assert any("no standard variables" in warning.lower() for warning in result.warnings)
```

#### User Experience Tests - Priority 1 🔥

**Test: error_messages_specify_which_variables_missing**
```python
def test_error_messages_specify_which_variables_missing():
    """Test that error messages clearly specify missing variables"""
    # Given: Dataset missing specific standard variables
    data = create_test_phase_data_missing_specific_variables(
        task="walking",
        missing_variables=['knee_flexion_angle_ipsi', 'ankle_moment_ipsi']
    )
    test_file = save_test_data(data, "missing_variables.parquet")
    
    # When: Validating dataset with missing variables
    result = validator.validate_dataset(test_file)
    
    # Then: Warning messages specifically mention missing variables
    warning_text = ' '.join(result.warnings).lower()
    assert 'knee_flexion_angle_ipsi' in warning_text
    assert 'ankle_moment_ipsi' in warning_text
    assert 'missing' in warning_text or 'not found' in warning_text
```

**Test: validation_report_provides_actionable_next_steps**
```python
def test_validation_report_provides_actionable_next_steps():
    """Test that validation reports include actionable recommendations"""
    # Given: Dataset with various issues (partial coverage, some bad strides)
    problematic_data = create_test_phase_data_with_issues(
        task="walking",
        missing_variables=['ankle_flexion_angle_ipsi'],
        bad_stride_percentage=0.3
    )
    test_file = save_test_data(problematic_data, "problematic.parquet")
    
    # When: Validating problematic dataset
    result = validator.validate_dataset(test_file)
    
    # Then: Recommendations are specific and actionable
    assert len(result.recommendations) > 0
    recommendations_text = ' '.join(result.recommendations).lower()
    assert any(word in recommendations_text for word in ['add', 'fix', 'check', 'review'])
    assert any(word in recommendations_text for word in ['variable', 'stride', 'data'])
```

**Test: validation_report_shows_spec_coverage_clearly**
```python
def test_validation_report_shows_spec_coverage_clearly():
    """Test that validation reports clearly show specification coverage"""
    # Given: Dataset with partial standard specification coverage
    partial_data = create_test_phase_data_with_partial_coverage(task="walking")
    test_file = save_test_data(partial_data, "partial_coverage.parquet")
    
    # When: Validating and generating report
    result = validator.validate_dataset(test_file, generate_plots=True)
    
    # Then: Report clearly shows coverage information
    assert os.path.exists(result.report_path)
    with open(result.report_path, 'r') as f:
        report_content = f.read()
    
    assert "Standard Specification Coverage" in report_content
    assert "Available Variables" in report_content
    assert "Missing Variables" in report_content
    assert result.validation_scope in report_content  # "full", "partial", "minimal"
```

**Test: external_collaborator_can_understand_validation_failures**
```python
def test_external_collaborator_can_understand_validation_failures():
    """Test that validation failures are understandable for external collaborators"""
    # Given: Dataset from external collaborator with common issues
    external_data = create_external_collaborator_problematic_data(
        issues=['wrong_column_names', 'missing_task_column', 'incorrect_phase_count']
    )
    test_file = save_test_data(external_data, "external_problematic.parquet")
    
    # When: Validating external collaborator data
    result = validator.validate_dataset(test_file)
    
    # Then: Error messages are clear for non-experts
    error_text = ' '.join(result.errors + result.warnings).lower()
    # Should avoid technical jargon and provide clear guidance
    assert any(word in error_text for word in ['required', 'expected', 'should'])
    # Should mention specific issues clearly
    assert 'task' in error_text  # Missing task column
    assert '150' in error_text   # Incorrect phase count
```

#### External Collaborator Integration Tests - Priority 1

**Test: validate_external_matlab_conversion**
```python
def test_validate_parquet_from_external_matlab_conversion():
    """Test validation of parquet files converted by external collaborators from MATLAB"""
    # Given: Parquet file converted by external MATLAB script (potential quality issues)
    test_file = "test_data/external_matlab_converted.parquet"
    
    # When: Validating externally converted file
    result = validator.validate_dataset(test_file)
    
    # Then: Validator catches any structural or range issues
    # (This test verifies the validator works regardless of conversion source)
    assert result is not None  # Should not crash
    if not result.is_valid:
        assert len(result.errors) > 0  # Should provide specific feedback
        assert result.report_path.endswith('.md')  # Should generate report
```

**Test: validate_external_csv_conversion**
```python
def test_validate_parquet_from_external_csv_conversion():
    """Test validation of parquet files converted by external collaborators from CSV"""
    # Given: Parquet file from external CSV conversion (different naming conventions)
    test_file = "test_data/external_csv_converted.parquet"
    
    # When: Validating externally converted file
    result = validator.validate_dataset(test_file)
    
    # Then: Validator provides clear feedback on any standard violations
    assert result is not None
    # Validator should identify any non-standard column names or structures
```

#### Integration Tests - Priority 1

**Test: generate_stride_filtering_validation_report**
```python
def test_generate_stride_filtering_validation_report():
    """Test generation of stride filtering validation report"""
    # Given: Mixed quality dataset with known good/bad strides
    data = create_test_phase_data_mixed_quality(
        task="walking", good_strides=6, bad_strides=4
    )
    test_file = save_test_data(data, "mixed_stride_quality.parquet")
    
    # When: Running full validation with stride filtering
    result = validator.validate_dataset(test_file, generate_plots=True)
    
    # Then: Complete markdown report generated with stride details
    assert os.path.exists(result.report_path)
    assert result.report_path.endswith('.md')
    
    # And: Report contains stride filtering sections
    with open(result.report_path, 'r') as f:
        report_content = f.read()
    
    assert "# Stride Filtering Validation Report" in report_content
    assert "## Stride Summary" in report_content
    assert "## Kept Strides" in report_content
    assert "## Deleted Strides" in report_content
    assert "## Rejection Reasons" in report_content
    assert "## Quality Metrics" in report_content
    
    # And: Stride statistics are in the report
    assert f"Total Strides: {result.total_strides}" in report_content
    assert f"Valid Strides: {result.valid_strides}" in report_content
    assert f"Pass Rate: {result.stride_pass_rate:.1%}" in report_content
    
    # And: Individual stride details are listed
    for stride_id in result.kept_stride_ids[:3]:  # Check first few
        assert stride_id in report_content
    for stride_id in result.deleted_stride_ids[:3]:  # Check first few
        assert stride_id in report_content
    
    # And: Plots are generated and referenced
    assert len(result.plot_paths) > 0
    assert all(os.path.exists(plot) for plot in result.plot_paths)
```

### External Conversion Script Integration Tests

> **NOTE: We do not test conversion scripts themselves since they vary widely from external collaborators.
> Instead, we test how well PhaseValidator handles various parquet outputs from different conversion approaches.**

#### External Script Output Validation Tests - Priority 1

**Test: validate_various_external_conversions**
```python
def test_validate_parquet_from_various_external_sources():
    """Test PhaseValidator robustness with parquet files from different conversion sources"""
    
    # Test files representing different external conversion approaches
    external_conversions = [
        "test_data/external_matlab_script_output.parquet",
        "test_data/external_python_csv_converter_output.parquet", 
        "test_data/external_r_script_output.parquet",
        "test_data/external_addbiomechanics_converter_output.parquet"
    ]
    
    # When: Validating each external conversion output
    validator = PhaseValidator(spec_manager, error_handler)
    results = []
    
    for test_file in external_conversions:
        result = validator.validate_dataset(test_file)
        results.append(result)
    
    # Then: Validator provides clear feedback for each conversion approach
    for i, result in enumerate(results):
        assert result is not None, f"Validator crashed on {external_conversions[i]}"
        
        # Each result should have clear validation status
        if not result.is_valid:
            assert len(result.errors) > 0, f"Invalid file should have specific errors: {external_conversions[i]}"
            assert result.report_path.endswith('.md'), f"Should generate markdown report: {external_conversions[i]}"
```

**Test: handle_malformed_external_conversions**
```python
def test_handle_malformed_parquet_from_external_scripts():
    """Test PhaseValidator handling of malformed parquet files from external scripts"""
    
    # Test files with common issues from external conversion scripts
    problematic_conversions = [
        "test_data/external_missing_columns.parquet",  # Missing required columns
        "test_data/external_wrong_phase_count.parquet",  # Wrong number of phase points
        "test_data/external_incorrect_datatypes.parquet",  # Wrong data types
        "test_data/external_inconsistent_structure.parquet"  # Inconsistent subject/trial structure
    ]
    
    # When: Validating problematic external conversions
    for test_file in problematic_conversions:
        result = validator.validate_dataset(test_file)
        
        # Then: Validator gracefully handles issues and provides helpful feedback
        assert result is not None, f"Validator should not crash on malformed file: {test_file}"
        assert result.is_valid == False, f"Malformed file should fail validation: {test_file}"
        assert len(result.errors) > 0, f"Should provide specific error messages: {test_file}"
        
        # And: Errors are helpful for external collaborators
        error_text = ' '.join(result.errors).lower()
        assert any(keyword in error_text for keyword in 
                  ['column', 'structure', 'phase', 'points', 'format']), \
               f"Errors should be descriptive for external users: {test_file}"
```

### TimeValidator Tests (UC-C02)
```python
def test_validate_correct_phase_structure():
    """Test validation of correctly structured phase data"""
    # Given: Phase dataset with exactly 150 points per cycle
    data = create_test_phase_data(subjects=2, trials=3, cycles=5, points_per_cycle=150)
    test_file = save_test_data(data, "correct_phase.parquet")
    
    # When: Validating phase structure
    validator = PhaseValidator(spec_manager, error_handler)
    result = validator.validate_dataset(test_file)
    
    # Then: Validation passes
    assert result.is_valid == True
    assert len(result.errors) == 0
    assert result.report_path.endswith('.md')
    assert os.path.exists(result.report_path)
```

**Test: detect_incorrect_phase_points**
```python
def test_detect_incorrect_phase_points():
    """Test detection of incorrect phase point counts"""
    # Given: Phase dataset with wrong number of points per cycle
    data = create_test_phase_data(subjects=1, trials=1, cycles=2, points_per_cycle=149)  # Should be 150
    test_file = save_test_data(data, "incorrect_phase.parquet")
    
    # When: Validating phase structure
    result = validator.validate_dataset(test_file)
    
    # Then: Validation fails with specific error
    assert result.is_valid == False
    assert any("150 points" in error for error in result.errors)
```

**Test: validate_biomechanical_ranges**
```python
def test_validate_biomechanical_ranges_within_spec():
    """Test validation when all data is within specification ranges"""
    # Given: Phase data with values within validation spec ranges
    data = create_test_phase_data_within_ranges(task="walking")
    test_file = save_test_data(data, "within_ranges.parquet")
    
    # When: Validating biomechanical ranges
    result = validator.validate_dataset(test_file)
    
    # Then: Range validation passes
    assert result.is_valid == True
    assert "range validation" in result.validation_summary
    assert result.validation_summary["range_validation"]["passed"] == True
```

**Test: detect_range_violations**
```python
def test_detect_biomechanical_range_violations():
    """Test detection of values outside specification ranges"""
    # Given: Phase data with values outside validation ranges
    data = create_test_phase_data_with_outliers(task="walking")
    test_file = save_test_data(data, "range_violations.parquet")
    
    # When: Validating biomechanical ranges
    result = validator.validate_dataset(test_file)
    
    # Then: Range violations detected
    assert result.is_valid == False
    assert any("range" in error.lower() for error in result.errors)
    assert len(result.errors) > 0
```

#### Integration Tests - Priority 1

**Test: generate_validation_report**
```python
def test_generate_complete_validation_report():
    """Test generation of complete markdown validation report"""
    # Given: Mixed quality dataset (some good, some bad data)
    data = create_mixed_quality_phase_data()
    test_file = save_test_data(data, "mixed_quality.parquet")
    
    # When: Running full validation
    result = validator.validate_dataset(test_file, generate_plots=True)
    
    # Then: Complete report generated
    assert os.path.exists(result.report_path)
    assert result.report_path.endswith('.md')
    
    # And: Report contains expected sections
    with open(result.report_path, 'r') as f:
        report_content = f.read()
    
    assert "# Validation Report" in report_content
    assert "## Summary" in report_content
    assert "## Structure Validation" in report_content
    assert "## Range Validation" in report_content
    assert "## Recommendations" in report_content
    
    # And: Plots are generated and referenced
    assert len(result.plot_paths) > 0
    assert all(os.path.exists(plot) for plot in result.plot_paths)
```

**Test: batch_validation**
```python
def test_batch_validation_with_summary():
    """Test batch validation of multiple datasets"""
    # Given: Multiple test datasets
    test_files = [
        save_test_data(create_valid_phase_data(), "valid1.parquet"),
        save_test_data(create_valid_phase_data(), "valid2.parquet"),
        save_test_data(create_invalid_phase_data(), "invalid1.parquet")
    ]
    
    # When: Running batch validation
    results = validator.validate_batch(test_files)
    summary = validator.get_validation_summary(results)
    
    # Then: Batch results are correct
    assert len(results) == 3
    assert summary.total_datasets == 3
    assert summary.passed_datasets == 2
    assert summary.pass_rate == 2/3
    
    # And: Common errors are identified
    assert len(summary.common_errors) > 0
```

#### Performance Tests - Priority 2

**Test: large_dataset_validation**
```python
def test_validate_large_dataset():
    """Test validation performance with large datasets"""
    # Given: Large phase dataset (1000 cycles)
    data = create_test_phase_data(subjects=10, trials=10, cycles=10, points_per_cycle=150)
    test_file = save_test_data(data, "large_dataset.parquet")
    
    # When: Validating large dataset
    start_time = time.time()
    result = validator.validate_dataset(test_file)
    end_time = time.time()
    
    # Then: Validation completes within reasonable time
    assert end_time - start_time < 30  # Should complete within 30 seconds
    assert result is not None
```

### TimeValidator Tests (UC-C02)

#### Unit Tests - Priority 1

**Test: validate_sampling_frequency**
```python
def test_validate_consistent_sampling_frequency():
    """Test validation of consistent sampling frequency"""
    # Given: Time-indexed data with consistent 100Hz sampling
    data = create_test_time_data(duration=10, sampling_freq=100)
    test_file = save_test_data(data, "consistent_freq.parquet")
    
    # When: Validating sampling frequency
    validator = TimeValidator(spec_manager, error_handler)
    result = validator.validate_dataset(test_file)
    
    # Then: Sampling frequency validation passes
    assert result.is_valid == True
    assert result.sampling_frequency == 100.0
    assert len(result.temporal_issues) == 0
```

**Test: detect_sampling_frequency_inconsistencies**
```python
def test_detect_sampling_frequency_inconsistencies():
    """Test detection of inconsistent sampling frequency"""
    # Given: Time-indexed data with inconsistent sampling
    data = create_test_time_data_with_gaps()
    test_file = save_test_data(data, "inconsistent_freq.parquet")
    
    # When: Validating sampling frequency
    result = validator.validate_dataset(test_file)
    
    # Then: Inconsistencies detected
    assert result.is_valid == False
    assert len(result.temporal_issues) > 0
    assert any("sampling" in issue.lower() for issue in result.temporal_issues)
```

### ValidationSpecVisualizer Tests (UC-C03)

#### Unit Tests - Priority 1

**Test: generate_validation_plots_with_data**
```python
def test_generate_validation_plots_with_data():
    """Test generation of validation plots with dataset overlay"""
    # Given: Valid phase dataset and output directory
    data = create_test_phase_data_within_ranges(task="walking")
    output_dir = "test_output/plots"
    
    # When: Generating validation plots
    visualizer = ValidationSpecVisualizer(spec_manager)
    result = visualizer.generate_validation_plots(data, output_dir)
    
    # Then: Plots are generated successfully
    assert result.success == True
    assert len(result.generated_plots) > 0
    
    # And: Expected plot types are created
    assert 'forward_kinematics' in result.generated_plots
    assert 'phase_filters_kinematic' in result.generated_plots
    assert 'phase_filters_kinetic' in result.generated_plots
    
    # And: All plot files exist
    for plot_type, plots in result.generated_plots.items():
        assert len(plots) > 0
        for plot_path in plots:
            assert os.path.exists(plot_path)
            assert plot_path.endswith('.png')
```

**Test: generate_validation_spec_plots**
```python
def test_generate_validation_spec_plots_without_data():
    """Test generation of validation specification plots without data"""
    # Given: Task specifications and output directory
    tasks = ["walking", "running"]
    output_dir = "test_output/spec_plots"
    
    # When: Generating specification plots
    result = visualizer.generate_validation_spec_plots(tasks, output_dir)
    
    # Then: Specification plots are generated
    assert result.success == True
    assert len(result.generated_plots) == len(tasks)
    
    # And: Plots show validation ranges for each task
    for task in tasks:
        task_plots = result.generated_plots[f'{task}_ranges']
        assert len(task_plots) > 0
        for plot_path in task_plots:
            assert os.path.exists(plot_path)
            assert task in plot_path
```

**Test: generate_validation_gifs**
```python
def test_generate_validation_gifs():
    """Test generation of animated validation GIFs"""
    # Given: Phase dataset with complete gait cycles
    data = create_test_phase_data_complete_cycles()
    output_dir = "test_output/gifs"
    
    # When: Generating validation GIFs
    result = visualizer.generate_validation_gifs(data, output_dir)
    
    # Then: GIFs are generated successfully
    assert result.success == True
    assert len(result.generated_animations) > 0
    
    # And: GIF files exist and are valid
    for gif_path in result.generated_animations:
        assert os.path.exists(gif_path)
        assert gif_path.endswith('.gif')
        # Basic file size check (GIFs should not be empty)
        assert os.path.getsize(gif_path) > 1000  # At least 1KB
```

---

## High Priority Component Tests

> **These tests validate components important for maintaining data quality standards**

### QualityAssessor Tests (UC-V01)

#### Unit Tests - Priority 1

**Test: assess_spec_compliance**
```python
def test_assess_quality_with_good_stride_compliance():
    """Test quality assessment for dataset with good stride-level spec compliance"""
    # Given: Dataset with 95% of strides within validation spec ranges
    data = create_test_data_with_stride_compliance_rate(0.95, task="walking")
    test_file = save_test_data(data, "good_stride_compliance.parquet")
    
    # When: Assessing quality using stride-level assessment
    assessor = QualityAssessor(spec_manager)
    result = assessor.assess_quality(test_file)
    
    # Then: High quality score based on stride-level compliance
    assert result.quality_scores['stride_compliance'] >= 0.90
    assert result.stride_compliance_rate >= 0.90  # High stride compliance rate
    assert result.stride_pass_rate >= 0.90  # High stride pass rate
    assert len(result.recommendations) >= 0
    
    # And: Coverage statistics calculated at stride level
    assert 'subjects' in result.coverage_stats
    assert 'tasks' in result.coverage_stats
    assert 'cycles' in result.coverage_stats
    assert 'total_strides' in result.coverage_stats  # Stride-level coverage tracking
```

**Test: identify_bad_steps**
```python
def test_identify_bad_strides_with_violations():
    """Test identification of strides that violate validation specifications"""
    # Given: Dataset with known validation spec violations
    data = create_test_data_with_known_violations()
    
    # When: Identifying bad strides
    bad_strides = assessor.identify_bad_strides(data, "walking")
    
    # Then: Bad strides are correctly identified
    assert len(bad_strides) > 0
    for bad_stride in bad_strides:
        assert 'subject_id' in bad_stride
        assert 'cycle_id' in bad_stride
        assert 'phase' in bad_stride
        assert 'violations' in bad_stride
        assert len(bad_stride['violations']) > 0
```

**Test: calculate_spec_compliance_score**
```python
def test_calculate_spec_compliance_score():
    """Test calculation of overall specification compliance score"""
    # Given: Dataset with known compliance characteristics
    data_perfect = create_test_data_with_compliance_rate(1.0)
    data_poor = create_test_data_with_compliance_rate(0.5)
    
    # When: Calculating compliance scores
    score_perfect = assessor.calculate_spec_compliance_score(data_perfect)
    score_poor = assessor.calculate_spec_compliance_score(data_poor)
    
    # Then: Scores reflect compliance rates
    assert score_perfect == 1.0
    assert score_poor == 0.5
    assert 0.0 <= score_perfect <= 1.0
    assert 0.0 <= score_poor <= 1.0
```

### ValidationSpecManager Tests (UC-V04) ⭐ CRITICAL

#### Unit Tests - Priority 1

**Test: edit_validation_ranges**
```python
def test_edit_validation_ranges_with_preview():
    """Test interactive editing of validation ranges with impact preview"""
    # Given: Current validation specifications
    task = "walking"
    variable = "knee_flexion_angle_ipsi_rad"
    new_ranges = {"min": -0.2, "max": 1.8, "mean_range": [0.1, 1.2]}
    rationale = "Updated based on new dataset analysis"
    
    # When: Editing validation ranges
    spec_manager = ValidationSpecManager(config_manager)
    result = spec_manager.edit_validation_ranges(task, variable, new_ranges, rationale)
    
    # Then: Changes are validated and previewed
    assert result.validation_status == "valid"
    assert 'impact_preview' in result
    assert 'affected_datasets' in result.impact_preview
    
    # And: Change is recorded with rationale
    assert result.change_record['rationale'] == rationale
    assert 'timestamp' in result.change_record
```

**Test: validate_spec_changes_against_test_datasets**
```python
def test_validate_spec_changes_against_test_datasets():
    """Test validation of specification changes against existing datasets"""
    # Given: Proposed specification changes and test datasets
    new_ranges = {"knee_flexion_angle_ipsi_rad": {"min": -0.1, "max": 1.5}}
    test_datasets = ["test_data/dataset1.parquet", "test_data/dataset2.parquet"]
    
    # When: Validating specification changes
    result = spec_manager.validate_spec_changes(test_datasets)
    
    # Then: Impact on existing datasets is assessed
    assert 'datasets_affected' in result
    assert 'new_failures' in result
    assert 'resolved_failures' in result
    
    # And: Recommendation provided
    assert 'recommendation' in result
    assert result.recommendation in ['approve', 'review', 'reject']
```

**Test: import_ranges_from_literature**
```python
def test_import_ranges_from_literature():
    """Test importing validation ranges from literature sources"""
    # Given: Literature-based ranges data
    literature_source = "Smith et al. 2023, Journal of Biomechanics"
    ranges_data = {
        "walking": {
            "knee_flexion_angle_ipsi_rad": {"min": -0.1, "max": 1.6, "citation": "Table 2"}
        }
    }
    
    # When: Importing ranges from literature
    result = spec_manager.import_ranges_from_literature(literature_source, ranges_data)
    
    # Then: Import succeeds with validation
    assert result.success == True
    assert 'imported_ranges' in result
    assert 'validation_results' in result
    
    # And: Source is properly attributed
    assert result.source_attribution == literature_source
```

#### Integration Tests - Priority 1

**Test: end_to_end_spec_management_workflow**
```python
def test_complete_spec_management_workflow():
    """Test complete specification management workflow"""
    # Given: Current specifications and new range proposals
    original_ranges = spec_manager.get_task_ranges("walking")
    
    # When: Going through complete workflow
    # 1. Edit ranges
    edit_result = spec_manager.edit_validation_ranges(
        "walking", "knee_flexion_angle_ipsi_rad", 
        {"min": -0.15, "max": 1.7}, "Test workflow"
    )
    
    # 2. Validate against test datasets
    validation_result = spec_manager.validate_spec_changes(test_datasets)
    
    # 3. Generate change documentation
    documentation = spec_manager.generate_change_documentation([edit_result])
    
    # Then: Complete workflow succeeds
    assert edit_result.validation_status == "valid"
    assert validation_result.recommendation in ['approve', 'review']
    assert len(documentation) > 0
    assert "knee_flexion_angle_ipsi_rad" in documentation
```

### AutomatedFineTuner Tests (UC-V05) ⭐ IMPORTANT

#### Unit Tests - Priority 1

**Test: tune_ranges_with_percentile_method**
```python
def test_tune_ranges_percentile_method():
    """Test range tuning using percentile statistical method"""
    # Given: Multiple datasets for analysis
    datasets = [
        create_test_dataset_with_known_stats("dataset1.parquet", mean=0.5, std=0.2),
        create_test_dataset_with_known_stats("dataset2.parquet", mean=0.6, std=0.15),
        create_test_dataset_with_known_stats("dataset3.parquet", mean=0.4, std=0.25)
    ]
    
    # When: Tuning ranges using percentile method
    tuner = AutomatedFineTuner(spec_manager)
    result = tuner.tune_ranges(datasets, method='percentile', confidence=0.95)
    
    # Then: Optimized ranges are calculated
    assert len(result.optimized_ranges) > 0
    assert 'walking' in result.optimized_ranges
    assert result.method == 'percentile'
    assert result.confidence == 0.95
    
    # And: Comparison with current ranges provided
    assert 'comparison' in result
    assert len(result.comparison) > 0
```

**Test: tune_ranges_with_iqr_method**
```python
def test_tune_ranges_iqr_method():
    """Test range tuning using IQR statistical method"""
    # Given: Datasets with known outliers
    datasets = create_datasets_with_outliers()
    
    # When: Tuning ranges using IQR method
    result = tuner.tune_ranges(datasets, method='iqr')
    
    # Then: IQR-based ranges are more robust to outliers
    assert result.method == 'iqr'
    
    # And: Outliers are handled appropriately
    for task, task_ranges in result.optimized_ranges.items():
        for variable, ranges in task_ranges.items():
            assert 'min' in ranges
            assert 'max' in ranges
            assert ranges['max'] > ranges['min']
```

**Test: analyze_tuning_impact**
```python
def test_analyze_tuning_impact():
    """Test analysis of impact from proposed range changes"""
    # Given: Tuning results and test datasets
    tuning_result = create_sample_tuning_result()
    test_datasets = ["test_data/validation_set1.parquet", "test_data/validation_set2.parquet"]
    
    # When: Analyzing tuning impact
    impact_result = tuner.analyze_tuning_impact(tuning_result, test_datasets)
    
    # Then: Impact analysis is comprehensive
    assert 'current_failures' in impact_result
    assert 'projected_failures' in impact_result
    assert 'datasets_improved' in impact_result
    assert 'datasets_degraded' in impact_result
    
    # And: Net impact calculation provided
    assert 'net_improvement' in impact_result
    assert isinstance(impact_result.net_improvement, bool)
```

**Test: apply_tuned_ranges**
```python
def test_apply_tuned_ranges_with_backup():
    """Test application of tuned ranges with backup"""
    # Given: Tuning results and backup requirement
    tuning_result = create_valid_tuning_result()
    
    # When: Applying tuned ranges with backup
    tuner.apply_tuned_ranges(tuning_result, backup=True)
    
    # Then: Backup is created before applying changes
    backup_files = glob.glob("**/spec_backup_*", recursive=True)
    assert len(backup_files) > 0
    
    # And: New ranges are applied to specifications
    updated_ranges = spec_manager.get_task_ranges("walking")
    assert updated_ranges != original_ranges  # Should be different
```

#### Performance Tests - Priority 2

**Test: tune_ranges_large_dataset_collection**
```python
def test_tune_ranges_with_large_dataset_collection():
    """Test range tuning performance with large dataset collection"""
    # Given: Large collection of datasets
    datasets = [f"large_dataset_{i}.parquet" for i in range(50)]
    
    # When: Tuning ranges on large collection
    start_time = time.time()
    result = tuner.tune_ranges(datasets, method='percentile')
    end_time = time.time()
    
    # Then: Tuning completes within reasonable time
    assert end_time - start_time < 300  # Should complete within 5 minutes
    assert result.datasets_analyzed == 50
```

---

## Integration Test Scenarios

> **End-to-end workflows testing component interactions**

### Complete Dataset Processing Workflow

**Test: external_conversion_to_validated_workflow**
```python
def test_complete_external_conversion_to_validated_workflow():
    """Test complete workflow from external conversion output to validated, assessed dataset"""
    # Given: Parquet file produced by external conversion script
    external_converted_file = "test_data/external_collaborator_output.parquet"
    
    # When: Running complete validation and assessment workflow
    # Step 1: Validate externally converted data  
    validator = PhaseValidator(spec_manager, error_handler)
    validation_result = validator.validate_dataset(external_converted_file)
    
    # Step 2: Assess quality (if validation passes)
    if validation_result.is_valid:
        assessor = QualityAssessor(spec_manager)
        quality_result = assessor.assess_quality(external_converted_file)
        
        # Step 3: Generate visualizations
        visualizer = ValidationSpecVisualizer(spec_manager)
        plot_result = visualizer.generate_validation_plots(
            pd.read_parquet(external_converted_file), "plots/"
        )
    else:
        quality_result = None
        plot_result = None
    
    # Then: Workflow provides clear feedback regardless of external conversion quality
    assert validation_result is not None
    assert os.path.exists(validation_result.report_path)
    
    # And: If data is valid, complete analysis is performed
    if validation_result.is_valid:
        assert quality_result is not None
        assert plot_result.success == True
        assert len(plot_result.generated_plots) > 0
    
    # And: If data is invalid, clear feedback is provided to external collaborator
    else:
        assert len(validation_result.errors) > 0
        with open(validation_result.report_path, 'r') as f:
            report = f.read()
        # Report should be helpful for external collaborators
        assert any(keyword in report.lower() for keyword in 
                  ['structure', 'columns', 'phase', 'requirements', 'fix'])
```

### Specification Management Workflow

**Test: specification_update_workflow**
```python
def test_specification_update_and_revalidation_workflow():
    """Test workflow for updating specifications and revalidating datasets"""
    # Given: Existing validated datasets and proposed specification changes
    existing_datasets = ["dataset1.parquet", "dataset2.parquet", "dataset3.parquet"]
    
    # When: Running specification update workflow
    # Step 1: Analyze current datasets for range optimization
    tuner = AutomatedFineTuner(spec_manager)
    tuning_result = tuner.tune_ranges(existing_datasets)
    
    # Step 2: Review and apply specification changes
    spec_manager = ValidationSpecManager(config_manager)
    update_result = spec_manager.edit_validation_ranges(
        "walking", "knee_flexion_angle_ipsi_rad",
        tuning_result.optimized_ranges["walking"]["knee_flexion_angle_ipsi_rad"],
        "Updated based on statistical analysis"
    )
    
    # Step 3: Revalidate all datasets with new specifications
    validator = PhaseValidator(spec_manager, error_handler)
    revalidation_results = validator.validate_batch(existing_datasets)
    
    # Then: Workflow maintains data quality
    assert tuning_result.datasets_analyzed == len(existing_datasets)
    assert update_result.validation_status == "valid"
    
    # And: Revalidation shows improvement or no degradation
    pass_rate = sum(1 for r in revalidation_results if r.is_valid) / len(revalidation_results)
    assert pass_rate >= 0.7  # At least 70% should still pass
```

---

## Test Data Requirements

### Synthetic Test Data Generation

**Phase-indexed test data:**
```python
def create_test_phase_data(subjects=2, trials=3, cycles=5, points_per_cycle=150, task="walking"):
    """Generate synthetic phase-indexed test data with known properties"""
    
def create_test_phase_data_within_ranges(task="walking"):
    """Generate test data with all values within validation specification ranges"""
    
def create_test_phase_data_with_outliers(task="walking"):
    """Generate test data with known outliers outside validation ranges"""
    
def create_mixed_quality_phase_data():
    """Generate test data with mix of good and problematic data points"""
```

**Time-indexed test data:**
```python
def create_test_time_data(duration=10, sampling_freq=100):
    """Generate synthetic time-indexed test data with consistent sampling"""
    
def create_test_time_data_with_gaps():
    """Generate time data with temporal gaps and inconsistencies"""
```

**Real test datasets:**
- Small sample datasets from each supported format (MATLAB, CSV, B3D)
- Datasets with known validation spec violations
- Large datasets for performance testing
- Corrupted files for error handling testing

### Test Environment Setup

**Required test infrastructure:**
```python
@pytest.fixture
def temp_test_dir():
    """Provide temporary directory for test outputs"""
    
@pytest.fixture  
def spec_manager():
    """Provide configured SpecificationManager for tests"""
    
@pytest.fixture
def error_handler():
    """Provide configured ErrorHandler for tests"""

@pytest.fixture
def test_datasets():
    """Provide collection of test datasets"""
```

---

## Test Execution Framework

### Test Runner Configuration

**Priority-based test execution:**
```bash
# Run only Critical priority tests (fast feedback)
pytest -m "priority1" tests/

# Run Critical + High priority tests (comprehensive)
pytest -m "priority1 or priority2" tests/

# Run all tests including performance tests
pytest tests/
```

**Component-specific test execution:**
```bash
# Test specific components
pytest tests/test_dataset_converter.py
pytest tests/test_phase_validator.py
pytest tests/test_validation_spec_manager.py
pytest tests/test_automated_fine_tuner.py
```

**Integration test execution:**
```bash
# Run integration tests only
pytest tests/integration/

# Run end-to-end workflow tests
pytest tests/integration/test_workflows.py
```

### Continuous Integration

**Test pipeline stages:**
1. **Fast Tests** - Unit tests for critical components (< 5 minutes)
2. **Integration Tests** - Component interaction tests (< 15 minutes)  
3. **Performance Tests** - Large dataset handling (< 30 minutes)
4. **Acceptance Tests** - User story validation (< 45 minutes)

**Success criteria:**
- All Priority 1 tests must pass
- 95% of Priority 2 tests must pass
- Performance tests must meet time requirements
- No test should take longer than defined timeouts

### Test Reporting

**Test result artifacts:**
- Test coverage reports (minimum 90% for Critical components)
- Performance benchmark results
- Failed test analysis with recommendations
- User story acceptance criteria verification

This comprehensive test specification ensures all Critical and High priority components meet their interface contracts and satisfy user story acceptance criteria.