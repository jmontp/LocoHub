# Integration Test Specifications

**Component interaction and workflow validation tests.**

## Complete Dataset Processing Workflow

### End-to-End Dataset Validation Workflow
```python
def test_complete_dataset_processing_pipeline():
    """Test complete workflow from raw dataset to validated output"""
    # 1. Load dataset
    data_loader = DataLoader()
    dataset = data_loader.load_parquet("test_dataset.parquet")
    
    # 2. Validate with PhaseValidator
    phase_validator = PhaseValidator(spec_manager, error_handler)
    validation_result = phase_validator.validate_dataset("test_dataset.parquet", generate_plots=True)
    
    # 3. Verify plots were generated during validation
    assert len(validation_result.plot_paths) > 0
    assert all(os.path.exists(path) for path in validation_result.plot_paths)
    
    # 4. Assess quality
    assessor = QualityAssessor(spec_manager)
    quality_result = assessor.assess_dataset_quality("test_dataset.parquet")
    
    # Verify complete workflow
    assert validation_result.is_valid == True
    assert quality_result.quality_metrics["overall_score"] > 0.8
    assert os.path.exists(validation_result.report_path)

def test_multi_dataset_comparison_workflow():
    """Test workflow for comparing multiple datasets"""
    # 1. Load multiple datasets
    datasets = ["dataset1.parquet", "dataset2.parquet", "dataset3.parquet"]
    
    # 2. Validate each dataset
    validation_results = []
    for dataset in datasets:
        result = phase_validator.validate_dataset(dataset)
        validation_results.append(result)
        assert result.is_valid == True
    
    # 3. Compare datasets
    comparator = DatasetComparator(spec_manager)
    comparison_result = comparator.compare_datasets(datasets)
    
    # 4. Generate comparison report
    assert comparison_result.compatibility_analysis is not None
    assert len(comparison_result.comparison_plots) > 0
    assert comparison_result.report_path != ""
    assert os.path.exists(comparison_result.report_path)

def test_benchmark_creation_workflow():
    """Test ML benchmark creation from validated datasets"""
    # 1. Validate datasets first
    datasets = ["dataset1.parquet", "dataset2.parquet"]
    for dataset in datasets:
        result = phase_validator.validate_dataset(dataset)
        assert result.is_valid == True
        assert result.stride_statistics.pass_rate > 0.9
    
    # 2. Create ML benchmarks
    benchmark_creator = BenchmarkCreator(data_loader)
    benchmark_result = benchmark_creator.create_ml_benchmarks(
        datasets, 
        split_strategy="subject"
    )
    
    # 3. Verify benchmark quality
    assert benchmark_result.data_splits.train is not None
    assert benchmark_result.data_splits.test is not None
    assert benchmark_result.data_splits.validation is not None
    assert len(set(benchmark_result.data_splits.train_subjects) & 
               set(benchmark_result.data_splits.test_subjects)) == 0  # No subject leakage
    assert benchmark_result.documentation_path != ""
```

## Specification Management Workflow

### Range Tuning and Management Integration
```python
def test_specification_tuning_workflow():
    """Test automated range tuning and specification management integration"""
    # 1. Load current specifications
    spec_manager = ValidationSpecManager(config_manager)
    current_specs = spec_manager.load_specifications("current_specs.md")
    assert current_specs.success == True
    
    # 2. Use interactive tuner for range optimization
    # Note: This is now a manual GUI-based workflow
    # python contributor_tools/interactive_validation_tuner.py
    
    # 3. Load tuned ranges from YAML file
    tuned_ranges_path = "contributor_tools/validation_ranges/tuned_ranges.yaml"
    with open(tuned_ranges_path, 'r') as f:
        tuned_ranges = yaml.safe_load(f)
    
    # 4. Apply changes to specifications
    update_result = spec_manager.update_validation_ranges(
        "walking", 
        "knee_flexion_angle_ipsi_rad", 
        tuned_ranges["walking"]["knee_flexion_angle_ipsi_rad"]
    )
    assert update_result.success == True
    
    # 5. Validate updated specifications
    test_result = phase_validator.validate_dataset("test_dataset.parquet")
    assert test_result.is_valid == True

def test_specification_version_control_workflow():
    """Test specification change tracking and version control"""
    # 1. Record current state
    original_ranges = spec_manager.get_validation_ranges("walking")
    
    # 2. Make changes with rationale
    new_ranges = {"knee_flexion_angle_ipsi_rad": {"min": -15, "max": 85}}
    update_result = spec_manager.update_validation_ranges(
        "walking", 
        "knee_flexion_angle_ipsi_rad", 
        new_ranges,
        rationale="Updated based on latest literature review"
    )
    assert update_result.success == True
    
    # 3. Verify change tracking
    history = spec_manager.get_change_history("walking", "knee_flexion_angle_ipsi_rad")
    assert len(history) > 0
    assert "literature review" in history[-1].rationale
    
    # 4. Test rollback capability
    rollback_result = spec_manager.rollback_changes("walking", "knee_flexion_angle_ipsi_rad", 1)
    assert rollback_result.success == True
    
    # 5. Verify rollback
    current_ranges = spec_manager.get_validation_ranges("walking")
    assert current_ranges.variable_ranges["knee_flexion_angle_ipsi_rad"].min_value == original_ranges.variable_ranges["knee_flexion_angle_ipsi_rad"].min_value
```

## External System Integration

### External Conversion Script Integration
```python
def test_external_matlab_converter_integration():
    """Test integration with external MATLAB conversion scripts"""
    # 1. Run external MATLAB converter (simulated)
    matlab_output = simulate_matlab_conversion("test_data.mat")
    assert os.path.exists(matlab_output)
    assert matlab_output.endswith(".parquet")
    
    # 2. Validate converted output
    validation_result = phase_validator.validate_dataset(matlab_output)
    
    # 3. Check for common MATLAB conversion issues
    assert validation_result.coverage_analysis.available_tasks is not None
    assert len(validation_result.errors) == 0  # Should handle MATLAB quirks gracefully
    
    # 4. Verify data integrity
    data = data_loader.load_parquet(matlab_output)
    assert "task" in data.columns
    assert "phase" in data.columns
    assert data["phase"].max() <= 149  # 0-indexed, 150 points per cycle

def test_external_csv_converter_integration():
    """Test integration with external CSV conversion scripts"""
    # 1. Run external CSV converter (simulated)
    csv_output = simulate_csv_conversion("test_data.csv")
    assert os.path.exists(csv_output)
    
    # 2. Validate converted output
    validation_result = phase_validator.validate_dataset(csv_output)
    
    # 3. Check for common CSV conversion issues
    assert validation_result.is_valid == True or len(validation_result.warnings) > 0
    
    # 4. Verify variable name mapping
    data = data_loader.load_parquet(csv_output)
    variable_names = [col for col in data.columns if col not in ["subject", "task", "phase"]]
    assert any("_rad" in var or "_Nm" in var for var in variable_names)  # Check unit naming

def test_addbiomechanics_b3d_integration():
    """Test integration with AddBiomechanics B3D conversion"""
    # 1. Run B3D converter (simulated)
    b3d_output = simulate_b3d_conversion("test_data.b3d")
    assert os.path.exists(b3d_output)
    
    # 2. Validate converted output
    validation_result = phase_validator.validate_dataset(b3d_output)
    
    # 3. Check AddBiomechanics specific features
    assert validation_result.coverage_analysis.available_variables is not None
    
    # 4. Verify biomechanical data quality
    data = data_loader.load_parquet(b3d_output)
    assert len(data) > 0
    assert data["phase"].nunique() == 150  # Should have exactly 150 phases
```

## Component Integration Tests

### Validator and Visualizer Integration
```python
def test_validator_visualizer_integration():
    """Test integration between validation and visualization components"""
    # 1. Run validation with plot generation
    validation_result = phase_validator.validate_dataset(
        "test_dataset.parquet", 
        generate_plots=True
    )
    assert validation_result.is_valid == True
    assert len(validation_result.plot_paths) > 0
    
    # 2. Use validation results to inform visualization
    visualizer = ValidationSpecVisualizer(spec_manager)
    enhanced_plots = visualizer.generate_validation_plots(
        "test_dataset.parquet",
        "enhanced_plots/",
        validation_context=validation_result
    )
    
    # 3. Verify enhanced visualization
    assert enhanced_plots.success == True
    assert enhanced_plots.coverage_summary != ""
    
    # 4. Check plot content coordination
    for plot_path in enhanced_plots.generated_plots["forward_kinematics"]:
        assert os.path.exists(plot_path)
        # Verify plots include validation range overlays

def test_quality_assessor_validator_integration():
    """Test integration between quality assessment and validation"""
    # 1. Run validation
    validation_result = phase_validator.validate_dataset("test_dataset.parquet")
    
    # 2. Use validation results in quality assessment
    assessor = QualityAssessor(spec_manager)
    quality_result = assessor.assess_dataset_quality(
        "test_dataset.parquet",
        validation_context=validation_result
    )
    
    # 3. Verify quality assessment uses validation data
    assert quality_result.coverage_stats.stride_pass_rate == validation_result.stride_statistics.pass_rate
    assert quality_result.quality_metrics["validation_compliance"] > 0
    
    # 4. Check quality recommendations
    assert len(quality_result.recommendations) > 0
    if validation_result.stride_statistics.pass_rate < 0.9:
        assert any("validation" in rec.lower() for rec in quality_result.recommendations)
```

## Error Handling Integration

### Cross-Component Error Propagation
```python
def test_error_handling_across_components():
    """Test error handling and propagation across component boundaries"""
    # 1. Inject error in data loading
    with pytest.raises(ValidationError) as exc_info:
        corrupted_data = create_corrupted_parquet_file()
        validation_result = phase_validator.validate_dataset(corrupted_data)
    
    # 2. Verify error propagation
    assert "file corruption" in str(exc_info.value).lower()
    
    # 3. Test graceful degradation
    partially_corrupted = create_partially_corrupted_data()
    validation_result = phase_validator.validate_dataset(partially_corrupted)
    
    assert validation_result.is_valid == False
    assert len(validation_result.errors) > 0
    assert len(validation_result.warnings) > 0
    assert validation_result.report_path != ""  # Should still generate report

def test_recovery_workflow_integration():
    """Test error recovery and workflow continuation"""
    # 1. Dataset with validation failures
    problematic_dataset = create_dataset_with_known_issues()
    validation_result = phase_validator.validate_dataset(problematic_dataset)
    
    # 2. Use debugging tools to investigate
    debugger = ValidationDebugger(spec_manager)
    debug_result = debugger.investigate_errors(
        problematic_dataset,
        validation_failures=validation_result.errors
    )
    
    # 3. Apply recommended fixes
    fixed_dataset = apply_debug_recommendations(problematic_dataset, debug_result.recommendations)
    
    # 4. Re-validate after fixes
    final_validation = phase_validator.validate_dataset(fixed_dataset)
    assert final_validation.stride_statistics.pass_rate > validation_result.stride_statistics.pass_rate
```

## Performance Integration Tests

### Large Dataset Processing Integration
```python
def test_large_dataset_processing_integration():
    """Test integrated workflow with large datasets"""
    # 1. Create large test dataset
    large_dataset = create_large_test_dataset(subjects=100, tasks=["walking", "running"], cycles_per_subject=50)
    
    # 2. Validate with performance monitoring
    start_time = time.time()
    validation_result = phase_validator.validate_dataset(large_dataset, parallel=True)
    validation_time = time.time() - start_time
    
    # 3. Performance assertions
    assert validation_time < 300  # Should complete within 5 minutes
    assert validation_result.is_valid == True
    assert validation_result.stride_statistics.total_strides > 5000
    
    # 4. Memory usage validation
    import psutil
    process = psutil.Process()
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    assert memory_usage < 2048  # Should use less than 2GB RAM

def test_batch_processing_integration():
    """Test batch processing of multiple large datasets"""
    # 1. Create multiple datasets
    datasets = [
        create_large_test_dataset(subjects=50, name="dataset_1"),
        create_large_test_dataset(subjects=50, name="dataset_2"),
        create_large_test_dataset(subjects=50, name="dataset_3")
    ]
    
    # 2. Batch validation
    batch_results = phase_validator.validate_batch(datasets, parallel=True)
    
    # 3. Verify batch processing
    assert len(batch_results.individual_results) == 3
    assert all(result.is_valid for result in batch_results.individual_results)
    assert batch_results.summary_report_path != ""
    
    # 4. Verify parallel efficiency
    assert batch_results.total_processing_time < sum(result.processing_time for result in batch_results.individual_results)
```

## Configuration Integration Tests

### Configuration Propagation
```python
def test_configuration_integration_across_components():
    """Test configuration propagation across all components"""
    # 1. Set custom configuration
    config_manager.update_config("validation.phase_tolerance", 0.02)
    config_manager.update_config("plotting.default_format", "svg")
    config_manager.update_config("quality.coverage_thresholds.minimum_tasks", 2)
    
    # 2. Initialize components with shared config
    validator = PhaseValidator(spec_manager, error_handler)
    visualizer = ValidationSpecVisualizer(spec_manager)
    assessor = QualityAssessor(spec_manager)
    
    # 3. Verify configuration usage
    validation_result = validator.validate_dataset("test_dataset.parquet")
    plot_result = visualizer.generate_validation_plots("test_dataset.parquet", "plots/")
    quality_result = assessor.assess_dataset_quality("test_dataset.parquet")
    
    # 4. Check configuration effects
    assert validation_result.metadata["phase_tolerance"] == 0.02
    assert all(path.endswith(".svg") for path in plot_result.generated_plots["forward_kinematics"])
    assert quality_result.quality_metrics["minimum_tasks_threshold"] == 2
```

## Test Utilities for Integration Tests

### Test Data Creation
```python
def create_large_test_dataset(subjects=100, tasks=["walking"], cycles_per_subject=20, name="large_dataset"):
    """Create large synthetic dataset for performance testing"""
    
def create_corrupted_parquet_file():
    """Create intentionally corrupted parquet file for error testing"""
    
def create_dataset_with_known_issues():
    """Create dataset with known validation issues for debugging tests"""
    
def simulate_matlab_conversion(input_file):
    """Simulate external MATLAB conversion script"""
    
def simulate_csv_conversion(input_file):
    """Simulate external CSV conversion script"""
    
def simulate_b3d_conversion(input_file):
    """Simulate AddBiomechanics B3D conversion"""
```