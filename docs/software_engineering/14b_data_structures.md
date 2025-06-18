# Data Structures

**Result classes and type definitions for validation system with interface contract completeness.**

## Cross-Reference to Interface Contracts

This document defines data structures that support the interface contracts in [14a_interface_contracts.md](./14a_interface_contracts.md). Each result type maps to specific interface methods:

- **PhaseValidationResult** → `PhaseValidator.validate_dataset()`
- **StrideFilterResult** → `PhaseValidator.filter_valid_strides()`  
- **TimeValidationResult** → `TimeValidator.validate_dataset()`
- **QualityAssessmentResult** → `QualityAssessor.assess_dataset_quality()`
- **ComparisonResult** → `DatasetComparator.compare_datasets()`
- **TuningResult** → `AutomatedFineTuner.auto_tune_ranges()`
- **BenchmarkResult** → `BenchmarkCreator.create_ml_benchmarks()`

## Validation Completeness Criteria

All result types MUST include:
1. **Processing metadata** - timestamps, processing time, input parameters
2. **Error tracking** - comprehensive error capture with context
3. **Quality metrics** - quantitative measures for decision making
4. **Traceability** - links to source data and intermediate results
5. **Export paths** - file references for generated outputs

## Core Result Types

### PhaseValidationResult
```python
@dataclass
class PhaseValidationResult:
    # Core validation result
    file_path: str
    validation_passed: bool
    stride_statistics: StrideStatistics
    coverage_analysis: CoverageAnalysis
    
    # Output files and paths
    validation_report_path: str
    plot_paths: List[str]
    
    # Error tracking and completeness
    errors: List[ValidationError]
    warnings: List[ValidationError]
    processing_time: float
    validation_timestamp: datetime
    
    # Enhanced metadata for traceability
    metadata: Dict[str, Any]
    input_parameters: Dict[str, Any]
    validation_spec_version: str
    step_classifier_version: str
    
    # Quality assessment integration
    quality_metrics: Optional[QualityMetrics] = None
    
    # Interface contract compliance checks
    def validate_completeness(self) -> CompletionCheck:
        """Verify this result meets interface contract requirements"""
        pass
    
    def export_summary(self, format: str = 'json') -> str:
        """Export validation summary in specified format"""
        pass
```

### StrideFilterResult
```python
@dataclass
class StrideFilterResult:
    # Core filtering results
    filtered_data: pd.DataFrame
    total_strides: int
    valid_strides: int
    invalid_strides: int
    pass_rate: float
    
    # Detailed rejection analysis
    rejection_reasons: List[StrideRejection]
    rejection_categories: Dict[str, int]
    most_common_rejections: List[Tuple[str, int]]
    
    # Coverage and completeness
    coverage_info: CoverageInfo
    task_specific_pass_rates: Dict[str, float]
    variable_specific_pass_rates: Dict[str, float]
    phase_specific_pass_rates: Dict[int, float]
    
    # Traceability and metadata
    filtering_timestamp: datetime
    filtering_parameters: Dict[str, Any]
    validation_spec_applied: str
    step_classifier_config: StepClassifierConfig
    
    # Quality indicators
    data_quality_score: float
    confidence_intervals: Dict[str, Tuple[float, float]]
    
    def get_rejection_summary(self) -> Dict[str, Any]:
        """Generate human-readable rejection summary"""
        pass
    
    def export_filtered_dataset(self, output_path: str) -> str:
        """Export filtered dataset to file"""
        pass
```

### StrideRejection
```python
@dataclass
class StrideRejection:
    # Core identification
    stride_id: str
    subject_id: str
    task: str
    variable: str
    phase: int
    
    # Violation details
    value: float
    expected_min: float
    expected_max: float
    reason: str
    violation_severity: str  # 'minor', 'major', 'critical'
    
    # Context and traceability
    validation_rule_applied: str
    specification_source: str
    detection_timestamp: datetime
    
    # Additional metadata
    phase_percentage: float  # 0.0, 0.25, 0.50, 0.75
    variable_units: str
    typical_range: Optional[Tuple[float, float]]
    population_percentile: Optional[float]
```

### StrideStatistics
```python
@dataclass
class StrideStatistics:
    total_strides: int
    valid_strides: int
    invalid_strides: int
    pass_rate: float
    task_breakdown: Dict[str, int]
    subject_breakdown: Dict[str, int]
```

### CoverageAnalysis
```python
@dataclass
class CoverageAnalysis:
    available_tasks: List[str]
    missing_tasks: List[str]
    variable_coverage: Dict[str, Dict[str, bool]]  # task -> variable -> present
    specification_coverage: float
    total_variables_in_spec: int
    available_variables_in_data: int
```

### TimeValidationResult
```python
@dataclass
class TimeValidationResult:
    file_path: str
    validation_passed: bool
    temporal_integrity: TemporalIntegrityResult
    sampling_validation: SamplingValidationResult
    validation_report_path: str
    errors: List[ValidationError]
    processing_time: float
    metadata: Dict[str, Any]
```

### TemporalIntegrityResult
```python
@dataclass
class TemporalIntegrityResult:
    has_time_gaps: bool
    gap_count: int
    largest_gap_seconds: float
    sampling_rate_consistent: bool
    time_range_valid: bool
    temporal_errors: List[TemporalError]
```

### SamplingValidationResult
```python
@dataclass
class SamplingValidationResult:
    expected_frequency: float
    actual_frequency: float
    frequency_variance: float
    frequency_acceptable: bool
    irregular_sampling_detected: bool
```

### QualityAssessmentResult
```python
@dataclass
class QualityAssessmentResult:
    file_path: str
    coverage_stats: CoverageStats
    outlier_analysis: OutlierAnalysis
    plausibility_scores: PlausibilityScores
    population_comparison: PopulationComparison
    quality_metrics: QualityMetrics
    report_path: str
```

### CoverageStats
```python
@dataclass
class CoverageStats:
    total_subjects: int
    total_tasks: int
    total_gait_cycles: int
    subject_task_matrix: Dict[str, List[str]]
    data_completeness: float
    missing_data_patterns: List[MissingDataPattern]
```

### OutlierAnalysis
```python
@dataclass
class OutlierAnalysis:
    outlier_count: int
    outlier_percentage: float
    outlier_variables: Dict[str, int]
    outlier_subjects: Dict[str, int]
    outlier_tasks: Dict[str, int]
    severe_outliers: List[OutlierDetail]
```

### PlausibilityScores
```python
@dataclass
class PlausibilityScores:
    overall_score: float
    variable_scores: Dict[str, float]
    task_scores: Dict[str, float]
    biomechanical_consistency: float
    temporal_consistency: float
```

### ComparisonResult
```python
@dataclass
class ComparisonResult:
    dataset_names: List[str]
    statistical_comparison: StatisticalComparisonResult
    compatibility_analysis: CompatibilityAnalysis
    bias_detection: BiasDetection
    harmonization_recommendations: List[HarmonizationRecommendation]
    comparison_plots: List[str]
    report_path: str
```

### StatisticalComparisonResult
```python
@dataclass
class StatisticalComparisonResult:
    variable_comparisons: Dict[str, VariableComparison]
    distribution_tests: Dict[str, DistributionTest]
    mean_differences: Dict[str, float]
    variance_ratios: Dict[str, float]
    effect_sizes: Dict[str, float]
```

### VariableComparison
```python
@dataclass
class VariableComparison:
    variable_name: str
    dataset_means: Dict[str, float]
    dataset_stds: Dict[str, float]
    significant_difference: bool
    p_value: float
    effect_size: float
    practical_significance: bool
```

### ValidationRanges
```python
@dataclass
class ValidationRanges:
    task: str
    phase: Optional[int]
    variable_ranges: Dict[str, VariableRange]
    metadata: RangeMetadata
```

### VariableRange
```python
@dataclass
class VariableRange:
    variable_name: str
    min_value: float
    max_value: float
    typical_min: Optional[float]
    typical_max: Optional[float]
    units: str
    source: str
    confidence_level: float
```

### RangeMetadata
```python
@dataclass
class RangeMetadata:
    source_literature: List[str]
    last_updated: datetime
    validation_method: str
    sample_size: int
    population_description: str
```

### TuningResult
```python
@dataclass
class TuningResult:
    method_used: str
    datasets_analyzed: List[str]
    range_changes: Dict[str, RangeChange]
    impact_analysis: ImpactAnalysis
    tuning_report_path: str
    recommended_for_adoption: bool
```

### RangeChange
```python
@dataclass
class RangeChange:
    variable_name: str
    task: str
    old_min: float
    old_max: float
    new_min: float
    new_max: float
    change_reason: str
    confidence_score: float
    supporting_data_points: int
```

### ImpactAnalysis
```python
@dataclass
class ImpactAnalysis:
    datasets_affected: List[str]
    validation_rate_changes: Dict[str, float]
    newly_valid_strides: int
    newly_invalid_strides: int
    overall_impact_score: float
```

### BenchmarkResult
```python
@dataclass
class BenchmarkResult:
    benchmark_name: str
    split_strategy: str
    data_splits: DataSplits
    split_metadata: SplitMetadata
    export_paths: Dict[str, str]  # format -> file_path
    baseline_metrics: Optional[BaselineMetrics]
    documentation_path: str
```

### DataSplits
```python
@dataclass
class DataSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_subjects: List[str]
    validation_subjects: List[str]
    test_subjects: List[str]
```

### SplitMetadata
```python
@dataclass
class SplitMetadata:
    total_samples: int
    train_samples: int
    validation_samples: int
    test_samples: int
    subject_distribution: Dict[str, Dict[str, int]]  # split -> subject -> count
    task_distribution: Dict[str, Dict[str, int]]  # split -> task -> count
    temporal_coverage: Dict[str, Tuple[datetime, datetime]]  # split -> (start, end)
```

## Configuration Types

### ValidationConfig
```python
@dataclass
class ValidationConfig:
    phase_tolerance: float
    outlier_threshold: float
    minimum_stride_count: int
    required_phases: List[int]
    validation_spec_path: str
    plot_generation: bool
    parallel_processing: bool
    max_workers: int
```

### QualityConfig
```python
@dataclass
class QualityConfig:
    coverage_thresholds: Dict[str, float]
    outlier_detection_method: str
    plausibility_weights: Dict[str, float]
    population_norm_source: str
    quality_score_formula: str
```

### ComparisonConfig
```python
@dataclass
class ComparisonConfig:
    statistical_significance_level: float
    effect_size_threshold: float
    distribution_test_method: str
    bias_detection_sensitivity: float
    harmonization_strategy: str
```

## Error Types

### ValidationError
```python
@dataclass
class ValidationError:
    error_type: str
    message: str
    file_path: Optional[str]
    variable_name: Optional[str]
    stride_id: Optional[str]
    phase: Optional[int]
    value: Optional[float]
    context: Dict[str, Any]
    timestamp: datetime
    severity: str  # "error", "warning", "info"
```

### TemporalError
```python
@dataclass
class TemporalError:
    error_type: str
    timestamp_start: float
    timestamp_end: float
    expected_duration: float
    actual_duration: float
    subject_id: str
    task: str
```

### ProcessingError
```python
@dataclass
class ProcessingError:
    stage: str
    error_message: str
    stack_trace: str
    input_parameters: Dict[str, Any]
    recovery_suggestions: List[str]
```

## Validation Workflow Data Structures

**Specialized data structures for validation workflow and dataset_validator_phase.py integration.**

### ValidationWorkflowConfig
```python
@dataclass
class ValidationWorkflowConfig:
    dataset_path: str
    output_directory: str
    generate_plots: bool
    generate_gifs: bool
    validation_spec_path: str
    step_classifier_config: StepClassifierConfig
    plot_config: PlotGenerationConfig
    parallel_processing: bool
    max_workers: int
    memory_limit_gb: float
```

### StepClassifierConfig
```python
@dataclass
class StepClassifierConfig:
    representative_phases: List[int]  # [0, 25, 50, 75]
    validation_tolerance: float
    contralateral_offset: bool
    kinematic_variables: List[str]
    kinetic_variables: List[str]
    required_tasks: List[str]
```

### PlotGenerationConfig
```python
@dataclass
class PlotGenerationConfig:
    create_filters_by_phase: bool
    create_forward_kinematics: bool
    create_validation_gifs: bool
    output_format: str  # 'png', 'svg', 'pdf'
    dpi: int
    color_scheme: PlotColorScheme
    plot_dimensions: Tuple[int, int]
```

### PlotColorScheme
```python
@dataclass
class PlotColorScheme:
    valid_steps: str  # 'gray'
    invalid_steps: str  # 'red'
    other_violations: str  # 'pink'
    background: str
    grid: str
    text: str
```

### ValidationReport
```python
@dataclass
class ValidationReport:
    dataset_name: str
    validation_timestamp: datetime
    total_processing_time: float
    validation_result: PhaseValidationResult
    stride_filter_result: StrideFilterResult
    coverage_analysis: CoverageAnalysis
    generated_plots: List[PlotReference]
    generated_gifs: List[str]
    error_summary: ErrorSummary
    recommendations: List[str]
    report_path: str
```

### PlotReference
```python
@dataclass
class PlotReference:
    plot_type: str  # 'filters_by_phase', 'forward_kinematics', 'validation_gif'
    file_path: str
    title: str
    description: str
    variables_shown: List[str]
    tasks_shown: List[str]
    creation_timestamp: datetime
```

### ErrorSummary
```python
@dataclass
class ErrorSummary:
    total_errors: int
    critical_errors: int
    warnings: int
    info_messages: int
    error_categories: Dict[str, int]
    most_common_errors: List[Tuple[str, int]]
    error_distribution_by_task: Dict[str, int]
    error_distribution_by_variable: Dict[str, int]
```

### BatchValidationResult
```python
@dataclass
class BatchValidationResult:
    batch_id: str
    datasets_processed: List[str]
    successful_validations: List[PhaseValidationResult]
    failed_validations: List[Tuple[str, List[ValidationError]]]
    batch_summary: BatchSummary
    processing_time: float
    resource_usage: ResourceUsage
    batch_report_path: str
```

### BatchSummary
```python
@dataclass
class BatchSummary:
    total_datasets: int
    successful_datasets: int
    failed_datasets: int
    overall_pass_rate: float
    stride_statistics_summary: StrideStatisticsSummary
    coverage_statistics_summary: CoverageStatisticsSummary
    quality_metrics_summary: QualityMetricsSummary
```

### StrideStatisticsSummary
```python
@dataclass
class StrideStatisticsSummary:
    total_strides_across_datasets: int
    total_valid_strides: int
    overall_stride_pass_rate: float
    pass_rate_by_dataset: Dict[str, float]
    pass_rate_by_task: Dict[str, float]
    pass_rate_by_variable: Dict[str, float]
```

### CoverageStatisticsSummary
```python
@dataclass
class CoverageStatisticsSummary:
    total_subjects_across_datasets: int
    total_tasks_across_datasets: int
    common_tasks: List[str]
    unique_tasks_by_dataset: Dict[str, List[str]]
    variable_coverage_matrix: Dict[str, Dict[str, bool]]  # dataset -> variable -> present
    specification_coverage_by_dataset: Dict[str, float]
```

### QualityMetricsSummary
```python
@dataclass
class QualityMetricsSummary:
    average_quality_score: float
    quality_scores_by_dataset: Dict[str, float]
    quality_distribution: Dict[str, int]  # score_range -> count
    quality_trends: Dict[str, float]  # metric -> trend_value
    outlier_summary: OutlierSummary
```

### OutlierSummary
```python
@dataclass
class OutlierSummary:
    total_outliers_across_datasets: int
    outlier_rate_by_dataset: Dict[str, float]
    outlier_rate_by_variable: Dict[str, float]
    severe_outlier_locations: List[OutlierLocation]
```

### OutlierLocation
```python
@dataclass
class OutlierLocation:
    dataset: str
    subject_id: str
    task: str
    variable: str
    stride_id: str
    phase: int
    value: float
    expected_range: Tuple[float, float]
    severity_score: float
```

### ResourceUsage
```python
@dataclass
class ResourceUsage:
    peak_memory_usage_gb: float
    total_cpu_time_seconds: float
    io_operations_count: int
    disk_space_used_gb: float
    parallel_workers_used: int
    cache_hit_rate: float
```

## Validation Completeness Verification

### CompletionCheck
```python
@dataclass
class CompletionCheck:
    result_type: str
    required_fields: List[str]
    optional_fields: List[str]
    validation_rules: List[ValidationRule]
    completeness_score: float
    missing_fields: List[str]
    invalid_values: List[FieldValidationError]
```

### ValidationRule
```python
@dataclass
class ValidationRule:
    field_name: str
    rule_type: str  # 'required', 'type_check', 'range_check', 'cross_reference'
    rule_specification: Dict[str, Any]
    validation_function: callable
    error_message_template: str
```

### FieldValidationError
```python
@dataclass
class FieldValidationError:
    field_name: str
    expected_type: str
    actual_type: str
    expected_value: Any
    actual_value: Any
    validation_rule_violated: str
    error_message: str
```

## Missing Referenced Data Structures

**Data structures referenced in the core types but not previously defined.**

### CoverageInfo
```python
@dataclass
class CoverageInfo:
    available_tasks: List[str]
    available_variables: List[str]
    task_variable_matrix: Dict[str, List[str]]
    missing_combinations: List[Tuple[str, str]]
    coverage_percentage: float
    specification_alignment: float
```

### QualityMetrics
```python
@dataclass
class QualityMetrics:
    overall_quality_score: float
    biomechanical_plausibility: float
    data_completeness: float
    temporal_consistency: float
    statistical_validity: float
    specification_compliance: float
    outlier_rate: float
    noise_level: float
```

### MissingDataPattern
```python
@dataclass
class MissingDataPattern:
    pattern_type: str  # 'subject_specific', 'task_specific', 'variable_specific', 'random'
    affected_count: int
    pattern_description: str
    subjects_affected: List[str]
    tasks_affected: List[str]
    variables_affected: List[str]
    impact_severity: str
```

### OutlierDetail
```python
@dataclass
class OutlierDetail:
    subject_id: str
    task: str
    variable: str
    stride_id: str
    phase: int
    value: float
    z_score: float
    percentile: float
    expected_range: Tuple[float, float]
    outlier_type: str  # 'mild', 'moderate', 'extreme'
```

### PopulationComparison
```python
@dataclass
class PopulationComparison:
    reference_population: str
    comparison_metrics: Dict[str, PopulationMetric]
    significant_differences: List[str]
    bias_indicators: List[BiasIndicator]
    population_representativeness: float
    demographic_alignment: Dict[str, float]
```

### PopulationMetric
```python
@dataclass
class PopulationMetric:
    variable_name: str
    dataset_mean: float
    reference_mean: float
    dataset_std: float
    reference_std: float
    effect_size: float
    p_value: float
    confidence_interval: Tuple[float, float]
```

### BiasIndicator
```python
@dataclass
class BiasIndicator:
    bias_type: str
    variable_affected: str
    bias_magnitude: float
    statistical_significance: float
    bias_direction: str  # 'positive', 'negative', 'bidirectional'
    potential_causes: List[str]
```

### CompatibilityAnalysis
```python
@dataclass
class CompatibilityAnalysis:
    datasets_compared: List[str]
    compatibility_score: float
    incompatible_variables: List[str]
    harmonization_required: List[str]
    direct_combination_feasible: bool
    alignment_recommendations: List[str]
```

### BiasDetection
```python
@dataclass
class BiasDetection:
    systematic_biases_detected: List[SystematicBias]
    bias_severity_score: float
    bias_correction_feasible: bool
    recommended_corrections: List[BiasCorrection]
```

### SystematicBias
```python
@dataclass
class SystematicBias:
    bias_type: str
    variables_affected: List[str]
    datasets_affected: List[str]
    magnitude: float
    confidence: float
    statistical_test_used: str
    p_value: float
```

### BiasCorrection
```python
@dataclass
class BiasCorrection:
    correction_method: str
    variables_to_correct: List[str]
    correction_parameters: Dict[str, float]
    expected_improvement: float
    implementation_complexity: str
```

### HarmonizationRecommendation
```python
@dataclass
class HarmonizationRecommendation:
    recommendation_type: str
    priority: str  # 'critical', 'important', 'optional'
    variables_involved: List[str]
    datasets_involved: List[str]
    harmonization_method: str
    expected_outcome: str
    implementation_effort: str
```

### DistributionTest
```python
@dataclass
class DistributionTest:
    test_name: str
    variable_name: str
    test_statistic: float
    p_value: float
    null_hypothesis: str
    conclusion: str
    datasets_compared: List[str]
```

### OptimalRanges
```python
@dataclass
class OptimalRanges:
    method_used: str
    variable_ranges: Dict[str, VariableRange]
    statistical_justification: Dict[str, StatisticalJustification]
    confidence_level: float
    sample_size_used: int
```

### StatisticalJustification
```python
@dataclass
class StatisticalJustification:
    variable_name: str
    method_description: str
    data_source: str
    sample_statistics: Dict[str, float]
    distribution_analysis: Dict[str, Any]
    outlier_handling: str
    literature_comparison: Optional[str]
```

### ChangePreview
```python
@dataclass
class ChangePreview:
    current_ranges: Dict[str, VariableRange]
    proposed_ranges: Dict[str, VariableRange]
    impact_analysis: Dict[str, ImpactAnalysis]
    validation_rate_changes: Dict[str, float]
    affected_datasets: List[str]
    recommendation: str
```

### BaselineMetrics
```python
@dataclass
class BaselineMetrics:
    model_performance: Dict[str, float]
    benchmark_scores: Dict[str, float]
    performance_by_task: Dict[str, Dict[str, float]]
    performance_by_subject: Dict[str, Dict[str, float]]
    cross_validation_scores: List[float]
    model_configuration: Dict[str, Any]
```

### ExportResult
```python
@dataclass
class ExportResult:
    export_successful: bool
    output_paths: List[str]
    export_format: str
    file_sizes: Dict[str, int]
    export_timestamp: datetime
    metadata_included: bool
    validation_passed: bool
```

### AccessResult
```python
@dataclass
class AccessResult:
    file_accessible: bool
    permissions_valid: bool
    file_exists: bool
    file_size: int
    last_modified: datetime
    read_permissions: bool
    write_permissions: bool
    error_message: Optional[str]
```

### ErrorResponse
```python
@dataclass
class ErrorResponse:
    error_handled: bool
    response_action: str
    recovery_attempted: bool
    recovery_successful: bool
    user_notification: str
    log_entry_created: bool
    escalation_required: bool
```

### ErrorReport
```python
@dataclass
class ErrorReport:
    report_id: str
    total_errors: int
    error_categories: Dict[str, int]
    critical_errors: List[ValidationError]
    error_timeline: List[Tuple[datetime, str]]
    system_context: Dict[str, Any]
    recommended_actions: List[str]
    report_path: str
```

### UpdateResult
```python
@dataclass
class UpdateResult:
    update_successful: bool
    changes_applied: List[str]
    validation_passed: bool
    backup_created: str
    rollback_available: bool
    impact_summary: str
    next_steps: List[str]
```

### SpecificationLoadResult
```python
@dataclass
class SpecificationLoadResult:
    load_successful: bool
    specifications_loaded: int
    parsing_errors: List[str]
    validation_warnings: List[str]
    specification_version: str
    last_updated: datetime
    source_files: List[str]
```

## Data Structure Validation Matrix

**Completeness verification matrix for all data structures against interface contracts.**

| Data Structure | Interface Method | Required Fields | Validation Methods | Export Capabilities | Traceability |
|---|---|---|---|---|---|
| `PhaseValidationResult` | `PhaseValidator.validate_dataset()` | ✓ Complete | `validate_completeness()` | `export_summary()` | Full |
| `StrideFilterResult` | `PhaseValidator.filter_valid_strides()` | ✓ Complete | `get_rejection_summary()` | `export_filtered_dataset()` | Full |
| `TimeValidationResult` | `TimeValidator.validate_dataset()` | ✓ Complete | Built-in | Standard | Full |
| `QualityAssessmentResult` | `QualityAssessor.assess_dataset_quality()` | ✓ Complete | Built-in | Standard | Full |
| `ComparisonResult` | `DatasetComparator.compare_datasets()` | ✓ Complete | Built-in | Standard | Full |
| `TuningResult` | `AutomatedFineTuner.auto_tune_ranges()` | ✓ Complete | Built-in | Standard | Full |
| `BenchmarkResult` | `BenchmarkCreator.create_ml_benchmarks()` | ✓ Complete | Built-in | Standard | Full |

## Implementation Guidelines

### Data Structure Design Principles

1. **Immutability**: All data structures should be immutable after creation
2. **Type Safety**: Use strong typing with Optional types for nullable fields
3. **Serialization**: All structures must be JSON/pickle serializable
4. **Validation**: Include built-in validation methods for completeness
5. **Documentation**: Each field must have clear purpose and constraints

### Validation Completeness Requirements

Each result data structure MUST implement:

```python
def validate_completeness(self) -> CompletionCheck:
    """
    Verify data structure completeness against interface contracts.
    
    Returns:
        CompletionCheck with validation results and missing fields
    """
    
def export_summary(self, format: str = 'json') -> str:
    """
    Export structured summary in specified format.
    
    Args:
        format: Output format ('json', 'yaml', 'dict')
    
    Returns:
        Formatted summary string or dictionary
    """
```

### Error Handling Integration

All error types must be:
- Categorized by severity (info, warning, error, critical)
- Timestamped for temporal analysis
- Contextually rich with debugging information
- Linked to source data for traceability
- Exportable for batch analysis

### Performance Considerations

For large dataset validation:
- Use lazy evaluation for expensive computations
- Implement memory-efficient data structures
- Support streaming/chunked processing
- Provide progress indicators for long operations
- Include resource usage tracking

### Cross-Reference Validation

Data structures must maintain consistency with:
- [14a_interface_contracts.md](./14a_interface_contracts.md) - Method signatures
- Feature constants from `source/lib/python/feature_constants.py`
- Validation specifications from `docs/standard_spec/validation_expectations_*.md`
- Dataset schemas from actual parquet files

This ensures complete traceability from interface contracts to implementation.