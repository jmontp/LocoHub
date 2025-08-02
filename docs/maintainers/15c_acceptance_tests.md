# Acceptance Test Specifications

**User story acceptance criteria validation tests.**

## Dataset Curator Acceptance Tests (UC-C02, UC-C03)

### UC-C02: Validate Converted Dataset
```python
def test_dataset_curator_validation_workflow():
    """
    As a dataset curator I want to validate a newly converted dataset 
    against biomechanical standards so I can ensure conversion success 
    and data quality.
    """
    # Given: A newly converted dataset
    converted_dataset = "newly_converted_dataset.parquet"
    
    # When: I run comprehensive validation
    result = phase_validator.validate_dataset(converted_dataset, generate_plots=True)
    
    # Then: I receive comprehensive validation results
    # Acceptance Criteria: Run comprehensive validation on both phase and time-indexed data
    assert result is not None
    assert hasattr(result, 'is_valid')
    
    # Acceptance Criteria: Generate detailed validation report with pass/fail status
    assert result.report_path != ""
    assert os.path.exists(result.report_path)
    with open(result.report_path, 'r') as f:
        report_content = f.read()
        assert "VALIDATION SUMMARY" in report_content
        assert "PASS" in report_content or "FAIL" in report_content
    
    # Acceptance Criteria: Show specific failures with recommended fixes
    if not result.is_valid:
        assert len(result.errors) > 0
        for error in result.errors:
            assert error.message != ""
            assert "recommendation" in error.context or len(result.recommendations) > 0
    
    # Acceptance Criteria: Visual validation plots for manual review
    assert len(result.plot_paths) > 0
    for plot_path in result.plot_paths:
        assert os.path.exists(plot_path)
        assert plot_path.endswith(('.png', '.svg', '.pdf'))
    
    # Acceptance Criteria: Export validation summary for documentation
    assert result.validation_summary is not None
    assert "stride_statistics" in result.validation_summary
    assert "coverage_analysis" in result.validation_summary

def test_stride_level_filtering_acceptance():
    """
    Acceptance criteria: Dataset validation must perform stride-level filtering
    and show which strides are kept vs deleted in validation report.
    """
    # Given: Dataset with mixed stride quality
    mixed_quality_dataset = create_dataset_with_mixed_stride_quality()
    
    # When: I validate the dataset
    result = phase_validator.validate_dataset(mixed_quality_dataset)
    
    # Then: I receive stride-level filtering results
    assert result.stride_statistics.total_strides > 0
    assert result.stride_statistics.valid_strides >= 0
    assert result.stride_statistics.invalid_strides >= 0
    assert result.stride_statistics.pass_rate >= 0.0
    
    # And: Validation report shows kept vs deleted strides
    with open(result.report_path, 'r') as f:
        report_content = f.read()
        assert "strides kept" in report_content.lower()
        assert "strides deleted" in report_content.lower()
        assert str(result.stride_statistics.valid_strides) in report_content
        assert str(result.stride_statistics.invalid_strides) in report_content

def test_task_specific_validation_acceptance():
    """
    Acceptance criteria: Use task-specific and phase-specific validation ranges,
    read tasks from data['task'] column, validate against known tasks.
    """
    # Given: Multi-task dataset
    multi_task_data = create_multi_task_dataset(["walking", "running", "unknown_task"])
    
    # When: I validate the dataset
    result = phase_validator.validate_dataset(multi_task_data)
    
    # Then: Tasks are read from data['task'] column
    assert result.coverage_analysis.available_tasks is not None
    assert "walking" in result.coverage_analysis.available_tasks
    assert "running" in result.coverage_analysis.available_tasks
    
    # And: Unknown tasks are handled gracefully
    assert len(result.warnings) > 0
    assert any("unknown task" in warning.lower() for warning in result.warnings)
    
    # And: Task-specific validation ranges are used
    assert result.validation_summary["task_specific_validation"] == True
```

### UC-C03: Generate Validation Visualizations
```python
def test_dataset_curator_visualization_workflow():
    """
    As a dataset curator I want to create plots and animations of validated 
    datasets so I can manually verify biomechanical reasonableness.
    """
    # Given: A validated dataset
    validated_dataset = "validated_dataset.parquet"
    output_dir = "curator_plots/"
    
    # When: I generate validation visualizations
    result = visualizer.generate_validation_plots(validated_dataset, output_dir)
    
    # Then: I receive comprehensive visualizations
    # Acceptance Criteria: Generate static plots showing joint angles and moments across gait phases
    assert result.success == True
    assert "forward_kinematics" in result.generated_plots
    assert len(result.generated_plots["forward_kinematics"]) > 0
    
    # Acceptance Criteria: Create animated GIFs showing walking patterns
    gif_result = visualizer.generate_validation_gifs(validated_dataset, output_dir)
    assert gif_result.success == True
    assert len(gif_result.generated_gifs) > 0
    for gif_path in gif_result.generated_gifs:
        assert os.path.exists(gif_path)
        assert gif_path.endswith('.gif')
    
    # Acceptance Criteria: Overlay validation ranges on visualizations
    for plot_path in result.generated_plots["forward_kinematics"]:
        # Verify plots contain validation range overlays (metadata check)
        assert os.path.exists(plot_path)
        # In real implementation, would check plot metadata or image analysis
    
    # Acceptance Criteria: Export plots in publication-ready formats
    assert any(path.endswith('.png') for path in result.generated_plots["forward_kinematics"])
    assert any(path.endswith('.svg') for path in result.generated_plots["forward_kinematics"])
    
    # Acceptance Criteria: Batch generation for multiple tasks and subjects
    batch_result = visualizer.generate_validation_plots(
        [validated_dataset, "second_dataset.parquet"], 
        output_dir,
        batch_mode=True
    )
    assert batch_result.success == True
    assert len(batch_result.batch_summary.processed_datasets) == 2
```

## Validation Specialist Acceptance Tests (UC-V01, UC-V02, UC-V04, UC-V05)

### UC-V01: Assess Dataset Quality
```python
def test_validation_specialist_quality_assessment():
    """
    As a validation specialist I want to generate comprehensive quality 
    reports so I can understand data completeness, coverage, and potential issues.
    """
    # Given: A dataset for quality assessment
    dataset_path = "assessment_dataset.parquet"
    
    # When: I assess dataset quality
    result = assessor.assess_dataset_quality(dataset_path)
    
    # Then: I receive comprehensive quality analysis
    # Acceptance Criteria: Calculate coverage statistics (subjects, tasks, gait cycles)
    assert result.coverage_stats.total_subjects > 0
    assert result.coverage_stats.total_tasks > 0
    assert result.coverage_stats.total_gait_cycles > 0
    assert result.coverage_stats.data_completeness >= 0.0
    
    # Acceptance Criteria: Identify missing data patterns and outliers
    assert result.outlier_analysis.outlier_count >= 0
    assert result.outlier_analysis.outlier_percentage >= 0.0
    assert len(result.missing_data_patterns) >= 0
    
    # Acceptance Criteria: Generate biomechanical plausibility scores
    assert result.plausibility_scores.overall_score >= 0.0
    assert result.plausibility_scores.biomechanical_consistency >= 0.0
    
    # Acceptance Criteria: Compare against population norms from literature
    assert result.population_comparison is not None
    assert hasattr(result.population_comparison, 'literature_references')
    
    # Acceptance Criteria: Export quality metrics for tracking over time
    assert result.report_path != ""
    quality_metrics_path = result.report_path.replace('.md', '_metrics.json')
    assert os.path.exists(quality_metrics_path)
    
    with open(quality_metrics_path, 'r') as f:
        metrics = json.load(f)
        assert 'timestamp' in metrics
        assert 'overall_quality_score' in metrics
        assert 'coverage_statistics' in metrics
```

### UC-V02: Compare Multiple Datasets
```python
def test_validation_specialist_dataset_comparison():
    """
    As a validation specialist I want to systematically compare datasets 
    from different sources so I can identify inconsistencies and ensure 
    cross-dataset compatibility.
    """
    # Given: Multiple datasets from different sources
    datasets = ["source1_dataset.parquet", "source2_dataset.parquet", "source3_dataset.parquet"]
    
    # When: I compare the datasets
    result = comparator.compare_datasets(datasets)
    
    # Then: I receive systematic comparison results
    # Acceptance Criteria: Statistical comparison of means, distributions, and ranges
    assert result.statistical_comparison is not None
    assert len(result.statistical_comparison.variable_comparisons) > 0
    for var_name, comparison in result.statistical_comparison.variable_comparisons.items():
        assert comparison.significant_difference is not None
        assert comparison.p_value >= 0.0
        assert comparison.effect_size is not None
    
    # Acceptance Criteria: Visual comparison plots showing overlays and differences
    assert len(result.comparison_plots) > 0
    for plot_path in result.comparison_plots:
        assert os.path.exists(plot_path)
        assert "comparison" in os.path.basename(plot_path).lower()
    
    # Acceptance Criteria: Identify systematic biases between data sources
    assert result.bias_detection is not None
    assert hasattr(result.bias_detection, 'detected_biases')
    
    # Acceptance Criteria: Generate compatibility reports for dataset combinations
    assert result.compatibility_analysis is not None
    assert hasattr(result.compatibility_analysis, 'compatibility_score')
    
    # Acceptance Criteria: Recommend harmonization strategies for inconsistencies
    assert len(result.harmonization_recommendations) >= 0
    for recommendation in result.harmonization_recommendations:
        assert recommendation.strategy != ""
        assert recommendation.rationale != ""
```

### UC-V04: Manage Validation Specifications
```python
def test_validation_specialist_spec_management():
    """
    As a validation specialist I want to edit and update validation rules 
    and ranges so I can maintain current biomechanical standards as knowledge evolves.
    """
    # Given: Current validation specifications
    current_specs = spec_manager.load_specifications("current_specs.md")
    original_range = spec_manager.get_validation_ranges("walking", "knee_flexion_angle_ipsi_rad")
    
    # When: I update validation ranges
    new_ranges = {"min": -20, "max": 90, "rationale": "Updated based on latest literature"}
    
    # Then: I can manage specifications effectively
    # Acceptance Criteria: Interactive editing of validation ranges with preview
    preview = spec_manager.preview_range_changes("walking", "knee_flexion_angle_ipsi_rad", new_ranges)
    assert preview.impact_analysis is not None
    assert preview.datasets_affected >= 0
    
    # Acceptance Criteria: Import ranges from literature or statistical analysis
    literature_ranges = load_literature_ranges("knee_flexion_literature.json")
    import_result = spec_manager.import_ranges_from_literature("walking", literature_ranges)
    assert import_result.success == True
    assert import_result.imported_variables > 0
    
    # Acceptance Criteria: Track changes with rationale and version control
    update_result = spec_manager.update_validation_ranges(
        "walking", 
        "knee_flexion_angle_ipsi_rad", 
        new_ranges
    )
    assert update_result.success == True
    
    change_history = spec_manager.get_change_history("walking", "knee_flexion_angle_ipsi_rad")
    assert len(change_history) > 0
    assert change_history[-1].rationale == "Updated based on latest literature"
    
    # Acceptance Criteria: Validate specification changes against test datasets
    validation_result = spec_manager.validate_spec_changes_against_datasets(
        ["test_dataset1.parquet", "test_dataset2.parquet"]
    )
    assert validation_result.changes_valid == True
    assert validation_result.impact_summary is not None
    
    # Acceptance Criteria: Generate change documentation for release notes
    change_doc = spec_manager.generate_change_documentation(
        from_version="1.0", 
        to_version="1.1"
    )
    assert change_doc.documentation_path != ""
    assert os.path.exists(change_doc.documentation_path)
```

### UC-V05: Optimize Validation Ranges
```python
def test_validation_specialist_range_optimization():
    """
    As a validation specialist I want to automatically tune validation ranges 
    based on current dataset statistics so ranges reflect the best available 
    data while maintaining quality.
    """
    # Given: Multiple datasets for range optimization
    datasets = ["dataset1.parquet", "dataset2.parquet", "dataset3.parquet"]
    
    # When: I optimize validation ranges
    result = tuner.auto_tune_ranges(datasets, method="percentile", confidence=0.95)
    
    # Then: I receive optimized ranges with analysis
    # Acceptance Criteria: Multiple statistical methods for range calculation
    percentile_result = tuner.auto_tune_ranges(datasets, method="percentile")
    statistical_result = tuner.auto_tune_ranges(datasets, method="statistical")
    robust_result = tuner.auto_tune_ranges(datasets, method="robust")
    
    assert percentile_result.method_used == "percentile"
    assert statistical_result.method_used == "statistical"
    assert robust_result.method_used == "robust"
    
    # Acceptance Criteria: Preview changes before applying with impact analysis
    preview = tuner.preview_range_changes(
        spec_manager.get_current_ranges(), 
        result.optimized_ranges
    )
    assert preview.overall_impact_score >= 0.0
    assert preview.validation_rate_changes is not None
    
    # Acceptance Criteria: Preserve manual adjustments and exceptions
    manual_adjustments = {"knee_flexion_angle_ipsi_rad": {"manual_override": True}}
    tuning_with_preservation = tuner.auto_tune_ranges(
        datasets, 
        preserve_manual=manual_adjustments
    )
    assert tuning_with_preservation.preserved_manual_ranges is not None
    
    # Acceptance Criteria: Generate tuning reports with statistical justification
    assert result.tuning_report_path != ""
    assert os.path.exists(result.tuning_report_path)
    with open(result.tuning_report_path, 'r') as f:
        report_content = f.read()
        assert "statistical justification" in report_content.lower()
        assert "confidence interval" in report_content.lower()
    
    # Acceptance Criteria: Integration with specification management workflow
    if result.recommended_for_adoption:
        integration_result = spec_manager.integrate_tuned_ranges(result)
        assert integration_result.success == True
        assert integration_result.updated_specifications > 0
```

## Administrator Acceptance Tests (UC-A01, UC-A02, UC-A03)

### UC-A01: Create ML Benchmarks
```python
def test_administrator_benchmark_creation():
    """
    As an administrator I want to create standardized train/test/validation 
    splits from quality datasets so ML researchers have consistent benchmarks.
    """
    # Given: High-quality validated datasets
    quality_datasets = ["high_quality_dataset1.parquet", "high_quality_dataset2.parquet"]
    
    # When: I create ML benchmarks
    result = benchmark_creator.create_ml_benchmarks(
        quality_datasets, 
        split_strategy="subject"
    )
    
    # Then: I receive ML-ready benchmarks
    # Acceptance Criteria: Stratified sampling ensuring no subject leakage between splits
    train_subjects = set(result.data_splits.train_subjects)
    test_subjects = set(result.data_splits.test_subjects)
    val_subjects = set(result.data_splits.validation_subjects)
    
    assert len(train_subjects & test_subjects) == 0  # No overlap
    assert len(train_subjects & val_subjects) == 0   # No overlap
    assert len(test_subjects & val_subjects) == 0    # No overlap
    
    # Acceptance Criteria: Support multiple split strategies
    temporal_result = benchmark_creator.create_ml_benchmarks(
        quality_datasets, 
        split_strategy="temporal"
    )
    assert temporal_result.split_strategy == "temporal"
    assert temporal_result.split_metadata.temporal_coverage is not None
    
    # Acceptance Criteria: Generate metadata describing split composition and balance
    metadata = result.split_metadata
    assert metadata.total_samples > 0
    assert metadata.train_samples > 0
    assert metadata.test_samples > 0
    assert metadata.validation_samples > 0
    assert metadata.subject_distribution is not None
    assert metadata.task_distribution is not None
    
    # Acceptance Criteria: Export in ML-ready formats
    assert "scikit" in result.export_paths
    assert "pytorch" in result.export_paths
    assert "tensorflow" in result.export_paths
    for format_name, path in result.export_paths.items():
        assert os.path.exists(path)
    
    # Acceptance Criteria: Create benchmark documentation with baseline performance metrics
    assert result.documentation_path != ""
    assert os.path.exists(result.documentation_path)
    if result.baseline_metrics:
        assert result.baseline_metrics.accuracy_metrics is not None
```

### UC-A02: Publish Dataset Release
```python
def test_administrator_dataset_publication():
    """
    As an administrator I want to prepare validated datasets for public 
    hosting and download so researchers worldwide can access high-quality data.
    """
    # Given: Validated dataset ready for release
    validated_dataset = "publication_ready_dataset.parquet"
    release_config = {
        "version": "1.0.0",
        "formats": ["parquet", "csv", "matlab"],
        "documentation": True,
        "checksums": True
    }
    
    # When: I prepare the dataset for publication
    result = publisher.publish_dataset_release(validated_dataset, release_config)
    
    # Then: I receive publication-ready package
    # Acceptance Criteria: Package datasets with comprehensive documentation
    assert result.package_path != ""
    assert os.path.exists(result.package_path)
    assert os.path.exists(os.path.join(result.package_path, "README.md"))
    assert os.path.exists(os.path.join(result.package_path, "CITATION.md"))
    
    # Acceptance Criteria: Generate checksums and integrity verification files
    assert os.path.exists(os.path.join(result.package_path, "checksums.sha256"))
    assert os.path.exists(os.path.join(result.package_path, "integrity_verification.md"))
    
    # Acceptance Criteria: Create download manifests and installation instructions
    assert os.path.exists(os.path.join(result.package_path, "download_manifest.json"))
    assert os.path.exists(os.path.join(result.package_path, "INSTALL.md"))
    
    # Acceptance Criteria: Anonymize sensitive information while preserving scientific value
    anonymization_report = result.anonymization_report
    assert anonymization_report.sensitive_fields_removed >= 0
    assert anonymization_report.scientific_value_preserved == True
    
    # Acceptance Criteria: Prepare multiple format options
    assert os.path.exists(os.path.join(result.package_path, "data.parquet"))
    assert os.path.exists(os.path.join(result.package_path, "data.csv"))
    assert os.path.exists(os.path.join(result.package_path, "data.mat"))
```

### UC-A03: Manage Dataset Versions
```python
def test_administrator_version_management():
    """
    As an administrator I want to track dataset versions and manage release 
    documentation so users understand dataset evolution and choose appropriate versions.
    """
    # Given: Multiple dataset versions
    versions = ["dataset_v1.0.0.parquet", "dataset_v1.1.0.parquet", "dataset_v2.0.0.parquet"]
    
    # When: I manage dataset versions
    result = version_manager.manage_dataset_versions(versions)
    
    # Then: I receive comprehensive version management
    # Acceptance Criteria: Semantic versioning for datasets with clear change categories
    version_info = result.version_analysis
    assert version_info["1.0.0"]["change_type"] == "initial"
    assert version_info["1.1.0"]["change_type"] in ["patch", "minor"]
    assert version_info["2.0.0"]["change_type"] == "major"
    
    # Acceptance Criteria: Automated changelog generation from validation and quality metrics
    changelog = result.automated_changelog
    assert changelog.path != ""
    assert os.path.exists(changelog.path)
    with open(changelog.path, 'r') as f:
        changelog_content = f.read()
        assert "## Version" in changelog_content
        assert "validation metrics" in changelog_content.lower()
    
    # Acceptance Criteria: Backwards compatibility analysis and migration guides
    compatibility_analysis = result.compatibility_analysis
    assert compatibility_analysis["1.0.0_to_1.1.0"]["backwards_compatible"] == True
    assert compatibility_analysis["1.1.0_to_2.0.0"]["backwards_compatible"] == False
    assert compatibility_analysis["1.1.0_to_2.0.0"]["migration_guide_path"] != ""
    
    # Acceptance Criteria: Citation guidance and DOI management integration
    citation_info = result.citation_management
    assert citation_info.citation_template != ""
    assert citation_info.doi_integration_status in ["pending", "assigned", "published"]
    
    # Acceptance Criteria: Release timeline and deprecation planning
    timeline = result.release_timeline
    assert timeline.next_release_date is not None
    assert timeline.deprecation_schedule is not None
    assert len(timeline.planned_features) >= 0
```

## Cross-Component Acceptance Tests

### Complete User Workflow Acceptance
```python
def test_complete_dataset_contributor_workflow():
    """
    Test complete workflow from dataset conversion through publication.
    Validates that all user stories work together seamlessly.
    """
    # Phase 1: Dataset Curator workflow
    # UC-C01: Convert dataset (external script simulation)
    converted_dataset = simulate_external_conversion("raw_dataset.mat")
    
    # UC-C02: Validate converted dataset
    validation_result = phase_validator.validate_dataset(converted_dataset, generate_plots=True)
    assert validation_result.is_valid == True
    
    # UC-C03: Generate validation visualizations
    viz_result = visualizer.generate_validation_plots(converted_dataset, "validation_plots/")
    assert viz_result.success == True
    
    # Phase 2: Validation Specialist workflow
    # UC-V01: Assess dataset quality
    quality_result = assessor.assess_dataset_quality(converted_dataset)
    assert quality_result.quality_metrics["overall_score"] > 0.8
    
    # UC-V04: Manage validation specifications (if needed)
    if quality_result.quality_metrics["overall_score"] < 0.9:
        spec_update = spec_manager.update_validation_ranges_based_on_quality(quality_result)
        assert spec_update.success == True
    
    # Phase 3: Administrator workflow
    # UC-A01: Create ML benchmarks
    benchmark_result = benchmark_creator.create_ml_benchmarks([converted_dataset], "subject")
    assert benchmark_result.split_metadata.total_samples > 100
    
    # UC-A02: Publish dataset release
    release_result = publisher.publish_dataset_release(converted_dataset, {"version": "1.0.0"})
    assert release_result.package_ready == True
    
    # Verify end-to-end workflow success
    assert all([
        validation_result.is_valid,
        viz_result.success,
        quality_result.quality_metrics["overall_score"] > 0.8,
        benchmark_result.split_metadata.total_samples > 100,
        release_result.package_ready
    ])
```

## Performance Acceptance Tests

### Scale and Performance Requirements
```python
def test_performance_acceptance_criteria():
    """
    Validate that all components meet performance requirements for production use.
    """
    # Large dataset processing
    large_dataset = create_large_test_dataset(subjects=1000, cycles_per_subject=100)
    
    # Performance requirements
    start_time = time.time()
    validation_result = phase_validator.validate_dataset(large_dataset, parallel=True)
    validation_time = time.time() - start_time
    
    # Acceptance criteria: Process large datasets within reasonable time
    assert validation_time < 600  # 10 minutes max for very large datasets
    assert validation_result.is_valid is not None  # Should complete successfully
    
    # Memory usage acceptance criteria
    import psutil
    process = psutil.Process()
    peak_memory = process.memory_info().peak_wss if hasattr(process.memory_info(), 'peak_wss') else process.memory_info().rss
    assert peak_memory < 4 * 1024 * 1024 * 1024  # Less than 4GB RAM
    
    # Batch processing performance
    multiple_datasets = [create_test_dataset(f"dataset_{i}") for i in range(10)]
    batch_start = time.time()
    batch_result = phase_validator.validate_batch(multiple_datasets, parallel=True)
    batch_time = time.time() - batch_start
    
    # Should be faster than sequential processing
    sequential_time_estimate = validation_time * 10
    assert batch_time < sequential_time_estimate * 0.8  # At least 20% faster
```