# Test Specifications

**Comprehensive test cases derived from user story acceptance criteria for Critical and High priority components.**

---

## Table of Contents

1. [Test Strategy Overview](#test-strategy-overview)
2. [Critical Priority Component Tests](#critical-priority-component-tests)
3. [High Priority Component Tests](#high-priority-component-tests)
4. [Integration Test Scenarios](#integration-test-scenarios)
5. [Test Data Requirements](#test-data-requirements)
6. [Test Execution Framework](#test-execution-framework)

---

## Test Strategy Overview

### Test Categories

**Unit Tests** - Individual component behavior validation
**Integration Tests** - Component interaction validation  
**Acceptance Tests** - User story acceptance criteria validation
**Contract Tests** - Interface specification compliance
**Performance Tests** - Large dataset handling validation

### Test Priorities

**Priority 1 (Critical)** - Must pass for any release
**Priority 2 (High)** - Should pass for quality release
**Priority 3 (Medium)** - Nice to have for complete coverage

### Test Data Strategy

**Real Dataset Tests** - Using actual converted datasets
**Synthetic Dataset Tests** - Generated test data with known properties
**Edge Case Tests** - Boundary conditions and error scenarios
**Performance Tests** - Large datasets for scalability validation

---

## Critical Priority Component Tests

> **These tests validate components required for all new datasets (UC-C01, UC-C02, UC-C03)**

### DatasetConverter Tests (UC-C01)

#### Unit Tests - Priority 1

**Test: convert_matlab_to_parquet**
```python
def test_convert_matlab_to_parquet_success():
    """Test successful MATLAB .mat file conversion"""
    # Given: Valid MATLAB file with biomechanical data
    input_file = "test_data/sample_gait.mat"
    output_file = "test_output/converted.parquet"
    
    # When: Converting with DatasetConverter
    converter = DatasetConverter(error_handler)
    result = converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Conversion succeeds with proper output
    assert result.success == True
    assert os.path.exists(output_file)
    assert os.path.exists(result.report_path)
    
    # And: Output has standard structure
    data = pd.read_parquet(output_file)
    assert 'subject_id' in data.columns
    assert 'trial_id' in data.columns
    assert 'cycle_id' in data.columns
    assert len(data) > 0
```

**Test: convert_csv_to_parquet** 
```python
def test_convert_csv_to_parquet_with_mapping():
    """Test CSV conversion with variable mapping"""
    # Given: CSV file with non-standard variable names
    input_file = "test_data/custom_variables.csv" 
    mapping_config = {
        "knee_angle": "knee_flexion_angle_ipsi_rad",
        "hip_torque": "hip_moment_contra_Nm"
    }
    
    # When: Converting with mapping configuration
    result = converter.convert_dataset(input_file, output_file, "csv", mapping_config)
    
    # Then: Variables are properly mapped
    assert result.success == True
    data = pd.read_parquet(result.output_path)
    assert 'knee_flexion_angle_ipsi_rad' in data.columns
    assert 'hip_moment_contra_Nm' in data.columns
    assert 'knee_angle' not in data.columns  # Original name removed
```

**Test: handle_missing_variables**
```python
def test_handle_missing_variables_with_warnings():
    """Test graceful handling of missing standard variables"""
    # Given: Input file missing some standard variables
    input_file = "test_data/incomplete_dataset.mat"
    
    # When: Converting incomplete dataset
    result = converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Conversion succeeds with warnings
    assert result.success == True
    assert len(result.warnings) > 0
    assert any("missing" in warning.lower() for warning in result.warnings)
    
    # And: Available variables are converted properly
    data = pd.read_parquet(result.output_path)
    assert len(data.columns) > 0
```

**Test: preserve_metadata**
```python
def test_preserve_original_metadata():
    """Test original metadata preservation during conversion"""
    # Given: Input file with metadata
    input_file = "test_data/dataset_with_metadata.mat"
    
    # When: Converting dataset
    result = converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Original metadata is preserved
    data = pd.read_parquet(result.output_path)
    # Check for metadata columns or separate metadata file
    assert 'source_metadata' in result.metadata
    assert 'conversion_timestamp' in result.metadata
    assert 'tool_version' in result.metadata
```

#### Integration Tests - Priority 1

**Test: end_to_end_conversion_workflow**
```python
def test_complete_conversion_workflow():
    """Test complete conversion workflow from raw data to validated output"""
    # Given: Raw dataset file
    input_file = "test_data/gtech_sample.mat"
    
    # When: Running complete conversion workflow
    converter = DatasetConverter(error_handler)
    result = converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Output is ready for validation
    assert result.success == True
    
    # And: Can be loaded by PhaseValidator
    validator = PhaseValidator(spec_manager, error_handler)
    validation_result = validator.validate_dataset(result.output_path)
    assert validation_result is not None  # Should not crash
```

#### Error Handling Tests - Priority 1

**Test: invalid_input_file**
```python
def test_conversion_with_invalid_input_file():
    """Test error handling for invalid input files"""
    # Given: Non-existent input file
    input_file = "nonexistent/path/file.mat"
    
    # When: Attempting conversion
    with pytest.raises(ConversionError) as exc_info:
        converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Clear error message provided
    assert "not found" in str(exc_info.value).lower()
```

**Test: corrupted_input_file**
```python
def test_conversion_with_corrupted_file():
    """Test error handling for corrupted input files"""
    # Given: Corrupted MATLAB file
    input_file = "test_data/corrupted.mat"
    
    # When: Attempting conversion  
    with pytest.raises(ConversionError) as exc_info:
        converter.convert_dataset(input_file, output_file, "matlab")
    
    # Then: Specific corruption error reported
    assert "corrupted" in str(exc_info.value).lower() or "invalid format" in str(exc_info.value).lower()
```

### PhaseValidator Tests (UC-C02)

#### Unit Tests - Priority 1

**Test: validate_phase_structure**
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
def test_assess_quality_with_good_spec_compliance():
    """Test quality assessment for dataset with good spec compliance"""
    # Given: Dataset with 95% of steps within validation spec ranges
    data = create_test_data_with_compliance_rate(0.95, task="walking")
    test_file = save_test_data(data, "good_compliance.parquet")
    
    # When: Assessing quality
    assessor = QualityAssessor(spec_manager)
    result = assessor.assess_quality(test_file)
    
    # Then: High quality score assigned
    assert result.quality_scores['spec_compliance'] >= 0.90
    assert len(result.recommendations) >= 0
    
    # And: Coverage statistics calculated
    assert 'subjects' in result.coverage_stats
    assert 'tasks' in result.coverage_stats
    assert 'cycles' in result.coverage_stats
```

**Test: identify_bad_steps**
```python
def test_identify_bad_steps_with_violations():
    """Test identification of steps that violate validation specifications"""
    # Given: Dataset with known validation spec violations
    data = create_test_data_with_known_violations()
    
    # When: Identifying bad steps
    bad_steps = assessor.identify_bad_steps(data, "walking")
    
    # Then: Bad steps are correctly identified
    assert len(bad_steps) > 0
    for bad_step in bad_steps:
        assert 'subject_id' in bad_step
        assert 'cycle_id' in bad_step
        assert 'phase' in bad_step
        assert 'violations' in bad_step
        assert len(bad_step['violations']) > 0
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

**Test: raw_to_validated_dataset_workflow**
```python
def test_complete_raw_to_validated_workflow():
    """Test complete workflow from raw data to validated, assessed dataset"""
    # Given: Raw MATLAB dataset
    raw_file = "test_data/raw_gait_data.mat"
    
    # When: Running complete processing workflow
    # Step 1: Convert raw data
    converter = DatasetConverter(error_handler)
    conversion_result = converter.convert_dataset(raw_file, "converted.parquet", "matlab")
    
    # Step 2: Validate converted data  
    validator = PhaseValidator(spec_manager, error_handler)
    validation_result = validator.validate_dataset(conversion_result.output_path)
    
    # Step 3: Assess quality
    assessor = QualityAssessor(spec_manager)
    quality_result = assessor.assess_quality(conversion_result.output_path)
    
    # Step 4: Generate visualizations
    visualizer = ValidationSpecVisualizer(spec_manager)
    plot_result = visualizer.generate_validation_plots(
        pd.read_parquet(conversion_result.output_path), "plots/"
    )
    
    # Then: Complete workflow succeeds
    assert conversion_result.success == True
    assert validation_result is not None
    assert quality_result is not None
    assert plot_result.success == True
    
    # And: All outputs are properly linked
    assert os.path.exists(validation_result.report_path)
    assert len(plot_result.generated_plots) > 0
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