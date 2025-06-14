# Data Structures

**Result classes and type definitions for validation system.**

## Core Result Types

### PhaseValidationResult
```python
@dataclass
class PhaseValidationResult:
    file_path: str
    validation_passed: bool
    stride_statistics: StrideStatistics
    coverage_analysis: CoverageAnalysis
    validation_report_path: str
    plot_paths: List[str]
    errors: List[ValidationError]
    processing_time: float
    metadata: Dict[str, Any]
```

### StrideFilterResult
```python
@dataclass
class StrideFilterResult:
    filtered_data: pd.DataFrame
    total_strides: int
    valid_strides: int
    invalid_strides: int
    pass_rate: float
    rejection_reasons: List[StrideRejection]
    coverage_info: CoverageInfo
```

### StrideRejection
```python
@dataclass
class StrideRejection:
    stride_id: str
    subject_id: str
    task: str
    variable: str
    phase: int
    value: float
    expected_min: float
    expected_max: float
    reason: str
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