# Unit Test Specifications

**Component-level tests for individual functions and classes.**

## PhaseValidator Unit Tests

### Parquet File Structure Tests
```python
def test_validate_dataset_file_access():
    """Test file accessibility and basic structure validation"""
    # Valid parquet file
    result = validator.validate_dataset("valid_dataset.parquet")
    assert result.is_valid == True
    
    # Non-existent file
    with pytest.raises(ValidationError):
        validator.validate_dataset("nonexistent.parquet")
    
    # Corrupted parquet file
    result = validator.validate_dataset("corrupted.parquet")
    assert result.is_valid == False
    assert "file corruption" in result.errors[0].lower()

def test_phase_indexing_validation():
    """Test phase indexing requirement (exactly 150 points per cycle)"""
    # Valid phase indexing (150 points per cycle)
    data = create_test_data(phases_per_cycle=150, cycles=10)
    result = validator.validate_dataset(data)
    assert result.is_valid == True
    
    # Invalid phase indexing (incorrect point count)
    data = create_test_data(phases_per_cycle=100, cycles=10)
    result = validator.validate_dataset(data)
    assert result.is_valid == False
    assert "phase indexing" in result.errors[0].lower()

def test_required_columns_validation():
    """Test required column presence"""
    # Missing 'task' column
    data = pd.DataFrame({'subject': ['S001'], 'phase': [0]})
    result = validator.validate_dataset(data)
    assert result.is_valid == False
    assert "task column missing" in result.errors[0].lower()
    
    # Missing 'phase' column
    data = pd.DataFrame({'subject': ['S001'], 'task': ['walking']})
    result = validator.validate_dataset(data)
    assert result.is_valid == False
    assert "phase column missing" in result.errors[0].lower()
```

### Biomechanical Range Validation Tests
```python
def test_stride_level_filtering():
    """Test stride-level validation and filtering"""
    # Create data with some valid and some invalid strides
    data = create_mixed_validity_data()
    result = validator.filter_valid_strides(data)
    
    assert result.total_strides == 20
    assert result.valid_strides == 15
    assert result.invalid_strides == 5
    assert result.pass_rate == 0.75
    assert len(result.kept_stride_ids) == 15
    assert len(result.deleted_stride_ids) == 5

def test_task_specific_validation():
    """Test task-specific validation ranges"""
    # Walking task with valid ranges
    walking_data = create_task_data("walking", valid_ranges=True)
    result = validator.filter_valid_strides(walking_data)
    assert result.pass_rate > 0.95
    
    # Running task with different valid ranges
    running_data = create_task_data("running", valid_ranges=True)
    result = validator.filter_valid_strides(running_data)
    assert result.pass_rate > 0.95
    
    # Unknown task (should warn but continue)
    unknown_data = create_task_data("unknown_task", valid_ranges=True)
    result = validator.filter_valid_strides(unknown_data)
    assert "unknown task" in result.warnings[0].lower()

def test_phase_specific_validation():
    """Test phase-specific validation at key phases"""
    # Valid values at all key phases (0%, 25%, 50%, 75%)
    data = create_phase_specific_data(valid_at_key_phases=True)
    result = validator.filter_valid_strides(data)
    assert result.pass_rate > 0.95
    
    # Invalid values at specific phases
    data = create_phase_specific_data(invalid_at_phase=50)  # 50% phase
    result = validator.filter_valid_strides(data)
    assert result.pass_rate < 0.5
    assert "phase 50" in str(result.rejection_reasons)
```

### Standard Specification Coverage Tests
```python
def test_available_tasks_detection():
    """Test detection of available tasks in dataset"""
    data = create_multi_task_data(["walking", "running", "unknown_task"])
    available_tasks = validator.get_available_tasks(data)
    
    assert "walking" in available_tasks
    assert "running" in available_tasks
    assert "unknown_task" not in available_tasks  # Not in feature_constants

def test_standard_spec_coverage_analysis():
    """Test analysis of standard specification coverage"""
    data = create_partial_coverage_data()  # Missing some standard variables
    coverage = validator.analyze_standard_spec_coverage(data)
    
    assert coverage["walking"]["knee_flexion_angle_ipsi_rad"] == True
    assert coverage["walking"]["missing_variable"] == False
    assert "coverage" in str(coverage)

def test_partial_specification_handling():
    """Test graceful handling of partial specification coverage"""
    # Dataset with variables not in standard specification
    data = create_data_with_extra_variables()
    result = validator.validate_dataset(data)
    
    assert result.is_valid == True  # Should not fail due to extra variables
    assert len(result.warnings) > 0  # Should warn about extra variables
    assert "not in standard specification" in result.warnings[0].lower()
```

## TimeValidator Unit Tests

### Temporal Integrity Tests
```python
def test_sampling_frequency_validation():
    """Test sampling frequency consistency checks"""
    # Consistent sampling rate
    data = create_time_series_data(frequency=100, duration=10)
    result = time_validator.validate_sampling_frequency(data)
    assert result.frequency_acceptable == True
    assert abs(result.actual_frequency - 100) < 0.1
    
    # Inconsistent sampling rate
    data = create_irregular_time_series_data()
    result = time_validator.validate_sampling_frequency(data)
    assert result.frequency_acceptable == False
    assert result.irregular_sampling_detected == True

def test_temporal_gap_detection():
    """Test detection of temporal gaps in data"""
    # Data with gaps
    data = create_time_series_with_gaps(gap_duration=0.5)
    result = time_validator.check_temporal_integrity(data)
    assert result.has_time_gaps == True
    assert result.largest_gap_seconds >= 0.5
    
    # Data without gaps
    data = create_continuous_time_series()
    result = time_validator.check_temporal_integrity(data)
    assert result.has_time_gaps == False
```

## ValidationSpecVisualizer Unit Tests

### Plot Generation Tests
```python
def test_validation_plot_generation():
    """Test generation of validation plots"""
    data = create_test_dataset()
    result = visualizer.generate_validation_plots(data, "test_plots/")
    
    assert result.success == True
    assert len(result.generated_plots["forward_kinematics"]) > 0
    assert os.path.exists(result.output_directory)

def test_specification_only_plots():
    """Test generation of specification plots without data"""
    result = visualizer.generate_validation_plots(
        specs_only=True, 
        tasks=["walking", "running"], 
        output_dir="spec_plots/"
    )
    
    assert result.success == True
    assert "walking" in result.generated_plots
    assert "running" in result.generated_plots

def test_plot_coverage_tracking():
    """Test tracking of variable coverage in plots"""
    data = create_partial_variable_data()  # Missing some variables
    result = visualizer.generate_validation_plots(data, "plots/")
    
    assert len(result.plotted_variables) > 0
    assert len(result.skipped_variables) > 0
    assert result.coverage_summary != ""
    assert len(result.warnings) > 0  # Warnings about missing variables
```

## QualityAssessor Unit Tests

### Coverage Statistics Tests
```python
def test_coverage_statistics_calculation():
    """Test calculation of dataset coverage statistics"""
    data = create_multi_subject_task_data()
    coverage = assessor.calculate_coverage_statistics(data)
    
    assert coverage.total_subjects > 0
    assert coverage.total_tasks > 0
    assert coverage.total_gait_cycles > 0
    assert coverage.data_completeness > 0
    assert isinstance(coverage.subject_task_matrix, dict)

def test_missing_data_pattern_identification():
    """Test identification of missing data patterns"""
    data = create_data_with_missing_patterns()
    outliers = assessor.identify_outliers(data)
    
    assert outliers.outlier_count > 0
    assert outliers.outlier_percentage > 0
    assert len(outliers.outlier_variables) > 0
```

## ValidationSpecManager Unit Tests

### Specification Management Tests
```python
def test_validation_range_retrieval():
    """Test retrieval of validation ranges"""
    # Task and phase specific ranges
    ranges = spec_manager.get_validation_ranges("walking", phase=50)
    assert ranges.task == "walking"
    assert ranges.phase == 50
    assert len(ranges.variable_ranges) > 0
    
    # Task only (no phase specified)
    ranges = spec_manager.get_validation_ranges("walking")
    assert ranges.task == "walking"
    assert ranges.phase is None

def test_specification_loading():
    """Test loading of specifications from markdown files"""
    result = spec_manager.load_specifications("test_specs.md")
    assert result.success == True
    assert len(result.loaded_variables) > 0

def test_range_updates():
    """Test updating validation ranges"""
    original_range = spec_manager.get_validation_ranges("walking")
    
    # Update range
    new_ranges = {"knee_flexion_angle_ipsi_rad": {"min": -10, "max": 80}}
    result = spec_manager.update_validation_ranges("walking", "knee_flexion_angle_ipsi_rad", new_ranges)
    
    assert result.success == True
    
    # Verify update
    updated_range = spec_manager.get_validation_ranges("walking")
    assert updated_range.variable_ranges["knee_flexion_angle_ipsi_rad"].min_value == -10
```

## AutomatedFineTuner Unit Tests

### Range Optimization Tests
```python
def test_optimal_range_calculation():
    """Test calculation of optimal ranges using different methods"""
    data = create_normal_distribution_data()
    
    # Percentile method
    ranges = tuner.calculate_optimal_ranges(data, method="percentile")
    assert ranges["knee_flexion_angle_ipsi_rad"]["min"] < ranges["knee_flexion_angle_ipsi_rad"]["max"]
    
    # Statistical method
    ranges = tuner.calculate_optimal_ranges(data, method="statistical")
    assert ranges["knee_flexion_angle_ipsi_rad"]["confidence"] > 0.9

def test_range_change_preview():
    """Test preview of proposed range changes"""
    current_ranges = get_current_validation_ranges()
    proposed_ranges = get_statistically_optimized_ranges()
    
    preview = tuner.preview_range_changes(current_ranges, proposed_ranges)
    assert preview.datasets_affected > 0
    assert "validation_rate_changes" in preview.__dict__
    assert preview.overall_impact_score >= 0
```

## Supporting Infrastructure Unit Tests

### ConfigurationManager Tests
```python
def test_configuration_loading():
    """Test configuration loading and management"""
    config_manager.load_from_file("test_config.yaml")
    
    assert config_manager.get_config("validation.phase_tolerance") == 0.05
    assert config_manager.get_config("plotting.default_format") == "png"

def test_configuration_updates():
    """Test configuration value updates"""
    config_manager.update_config("validation.outlier_threshold", 3.0)
    assert config_manager.get_config("validation.outlier_threshold") == 3.0
```

### ErrorHandler Tests
```python
def test_validation_error_handling():
    """Test proper handling of validation errors"""
    error = ValidationError("Test validation error", severity="error")
    response = error_handler.handle_validation_error(error)
    
    assert response.handled == True
    assert response.recovery_action is not None

def test_error_report_generation():
    """Test comprehensive error report generation"""
    errors = [ValidationError("Error 1"), ValidationError("Error 2")]
    report = error_handler.create_error_report(errors)
    
    assert len(report.error_summary) == 2
    assert report.total_errors == 2
```

### DataLoader Tests
```python
def test_parquet_file_loading():
    """Test parquet file loading with error handling"""
    # Valid parquet file
    data = data_loader.load_parquet("valid_dataset.parquet")
    assert isinstance(data, pd.DataFrame)
    assert len(data) > 0
    
    # Invalid file
    with pytest.raises(FileNotFoundError):
        data_loader.load_parquet("nonexistent.parquet")

def test_file_access_validation():
    """Test file accessibility validation"""
    # Accessible file
    result = data_loader.validate_file_access("accessible_file.parquet")
    assert result.accessible == True
    
    # Inaccessible file
    result = data_loader.validate_file_access("/restricted/file.parquet")
    assert result.accessible == False
    assert result.error_message != ""
```

## Test Utilities

### Test Data Generation
```python
def create_test_data(phases_per_cycle=150, cycles=10, subjects=["S001"], tasks=["walking"]):
    """Create synthetic test data with specified properties"""
    
def create_mixed_validity_data():
    """Create dataset with mix of valid and invalid strides"""
    
def create_task_data(task_name, valid_ranges=True):
    """Create task-specific test data"""
    
def create_phase_specific_data(valid_at_key_phases=True, invalid_at_phase=None):
    """Create data with phase-specific validation scenarios"""
    
def create_multi_task_data(tasks):
    """Create dataset with multiple tasks"""
    
def create_partial_coverage_data():
    """Create dataset with partial variable coverage"""
```