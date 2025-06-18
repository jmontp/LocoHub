---
title: Data Contracts
tags: [data, contracts, interfaces]
status: ready
---

# Data Contracts

**Method signatures and behavioral contracts for all critical components.**

*Detailed specifications with requirements traceability and standardized error handling patterns.*

## Requirements Traceability

Each interface contract directly supports specific user requirements from Document 10 and workflow sequences from Document 06:

### Workflow Integration Mapping
- **Sequence 1 (Dataset Conversion)** → PhaseValidator, TimeValidator, QualityAssessor
- **Sequence 2A (Manual Validation)** → ValidationSpecManager, PhaseValidator  
- **Sequence 2B (Automatic Validation)** → AutomatedFineTuner, ValidationSpecManager
- **Sequence 3 (Quality Assessment)** → PhaseValidator, QualityAssessor
- **Sequence 4 (ML Benchmarks)** → BenchmarkCreator

### Requirements Mapping (Document 10)
- **PhaseValidator** → Requirements F1 (Dataset Validation Infrastructure), User Stories C02, V01, V03
- **TimeValidator** → Requirements F4 (Phase-Indexed Dataset Generation), User Story C03
- **QualityAssessor** → Requirements F1 (Dataset Validation Infrastructure), User Story C02
- **DatasetComparator** → Requirements F5 (Dataset Comparison), User Story V01
- **ValidationSpecManager** → Requirements F2 (Validation Specification Management), User Stories V04, V05
- **AutomatedFineTuner** → Requirements F2 (Validation Specification Management), User Story V05
- **BenchmarkCreator** → Requirements F6 (Administrative Tools), User Story A01

## Consolidated Error Handling

All components implement standardized error handling patterns from Interface Standards (Document 09):

```python
class LocomotionToolError(Exception):
    """Base exception for all locomotion tools with user context"""
    def __init__(self, message: str, file_path: str = None, context: str = None, suggestion: str = None):
        self.message = message
        self.file_path = file_path
        self.context = context
        self.suggestion = suggestion
        super().__init__(self.message)

class DataFormatError(LocomotionToolError):
    """Issues with data format or structure"""
    pass

class ValidationError(LocomotionToolError):
    """Data validation failures"""
    pass

class QualityError(LocomotionToolError):
    """Data quality issues"""
    pass

class ConfigurationError(LocomotionToolError):
    """Configuration file or parameter issues"""
    pass
```

## PhaseValidator - Phase-Indexed Dataset Validation

**Requirements Traceability:** User Stories C02 (Dataset Quality Assessment), V01 (Dataset Comparison), V03 (Debug Validation Failures)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)  
**CLI Entry Point:** `validation_dataset_report.py` (implements interface via dataset_validator_phase.py)  
**Workflow Integration:** Core component in Sequences 1, 2A, 2B, 3 - all validation workflows converge on this tool

```python
class PhaseValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler, 
                 progress_reporter: ProgressReporter = None):
        """
        Initialize validator with dependencies and standardized interfaces.
        
        Requirements: C02 - Auto-detect dataset type, comprehensive validation
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True, 
                        generate_gifs: bool = False, output_dir: str = None) -> PhaseValidationResult:
        """
        Run comprehensive validation on phase-indexed dataset with stride-level filtering.
        
        Requirements Traceability:
        - C02: Comprehensive validation against biomechanical standards
        - C02: Dataset summary statistics and metadata
        - C02: Coverage statistics (subjects, tasks, gait cycles)
        - C02: Missing data patterns and outlier identification
        - C02: Detailed validation report with pass/fail status
        - C02: Automatically generated static validation plots
        - C02: Optional animated GIFs with --generate-gifs flag
        - V03: Deep-dive analysis of failed data points with context
        
        Interface Standards Compliance:
        - Uses standardized ProgressReporter for operation tracking
        - Implements standardized error handling with context
        - Follows CLI argument patterns (--generate-gifs flag)
        - Returns structured results with exit codes
        
        MUST perform stride-level validation and filtering
        MUST show which strides are kept vs deleted in validation report
        MUST report stride pass rate as quality metric
        MUST only fail dataset if NO strides pass validation AND basic structure is invalid
        MUST create visual validation plots for manual review (generate_plots=True)
        MUST create animated GIFs when requested (generate_gifs=True, computationally intensive)
        MUST export validation summary with stride statistics
        MUST use task-specific and phase-specific validation ranges
        MUST read tasks from data['task'] column
        MUST validate against known tasks from feature_constants
        MUST handle unknown tasks gracefully with clear error messages
        MUST integrate with LocomotionData library for efficient 3D operations
        MUST use StepClassifier.validate_data_against_specs() for consistency
        
        Raises:
        - DataFormatError: Invalid parquet structure or missing required columns
        - ValidationError: Critical validation failures preventing analysis
        - ConfigurationError: Invalid output directory or configuration
        """
    
    def filter_valid_strides(self, data: pd.DataFrame, available_variables: List[str] = None) -> StrideFilterResult:
        """
        Filter dataset to keep only valid strides based on task-specific validation specifications.
        
        Requirements: C02 - Biomechanical plausibility scores, V03 - Investigation analysis
        
        MUST identify valid vs invalid strides using task and phase-specific ranges
        MUST check each stride against available validation specifications
        MUST validate at 0%, 25%, 50%, 75% phases for each stride (representative phases)
        MUST provide detailed reasons for stride rejection with biomechanical context
        MUST return filtered dataset with only valid strides
        MUST maintain audit trail of filtering decisions
        
        Raises:
        - ValidationError: No valid strides found or specification loading failure
        """
    
    def get_available_tasks(self, data: pd.DataFrame) -> List[str]:
        """
        Get unique tasks from dataset, filtered to known standard tasks.
        
        Requirements: C02 - Task coverage analysis
        MUST validate against feature_constants.TASK_DEFINITIONS
        MUST log warnings for unknown tasks
        """
    
    def analyze_standard_spec_coverage(self, data: pd.DataFrame) -> Dict[str, Dict[str, bool]]:
        """
        Analyze which standard specification variables are available in the dataset.
        
        Requirements: C02 - Coverage statistics, missing data patterns
        MUST check against kinematic and kinetic variable specifications
        MUST identify missing variables by task type
        MUST calculate coverage percentages
        """
    
    def validate_batch(self, file_paths: List[str], parallel: bool = True, 
                      max_workers: int = None) -> BatchValidationResult:
        """
        Validate multiple datasets with stride-level summary reporting.
        
        Requirements: V01 - Systematic comparison across datasets
        MUST provide parallel processing for efficiency
        MUST aggregate stride-level statistics across datasets
        MUST identify cross-dataset inconsistencies
        MUST respect memory limits and provide progress reporting
        
        Raises:
        - ResourceError: Insufficient memory or processing resources
        """
    
    def generate_validation_report(self, result: PhaseValidationResult, 
                                 output_path: str) -> ReportGenerationResult:
        """
        Generate comprehensive markdown validation report.
        
        Requirements: C02 - Export comprehensive report for contribution documentation
        Interface Standards: Follows report structure standards from Document 09
        
        MUST follow standardized report format with tool metadata
        MUST include summary, validation results, quality metrics, recommendations
        MUST provide actionable insights for dataset improvement
        """
```

## TimeValidator - Time-Indexed Dataset Validation

**Requirements Traceability:** User Story C03 (Generate Phase-Indexed Dataset - requires time validation)  
**User Personas:** Marcus Rodriguez (Programmer)  
**CLI Entry Point:** `conversion_generate_phase_dataset.py` (validates input before conversion)  
**Workflow Integration:** Essential for Sequence 1 (Dataset Conversion) when time-indexed data needs phase conversion

```python
class TimeValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize time-indexed validator with standardized dependencies.
        
        Requirements: C03 - Input time-indexed parquet validation
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True, 
                        output_dir: str = None) -> TimeValidationResult:
        """
        Run comprehensive validation on time-indexed dataset.
        
        Requirements Traceability:
        - C03: Input time-indexed parquet with vertical ground reaction forces
        - C03: Robust handling of incomplete or irregular gait cycles
        - C03: Quality report showing cycle detection success rates
        
        Interface Standards Compliance:
        - Uses standardized error handling and progress reporting
        - Follows CLI argument patterns and exit codes
        
        MUST validate sampling frequency consistency across all data
        MUST check temporal data integrity and identify gaps
        MUST validate biomechanical ranges where applicable
        MUST verify ground reaction force data for gait cycle detection
        MUST identify incomplete or irregular cycles for conversion readiness
        MUST generate quality metrics for temporal data assessment
        
        Raises:
        - DataFormatError: Invalid time-indexed structure or missing time columns
        - ValidationError: Critical temporal integrity issues
        """
    
    def check_temporal_integrity(self, data: pd.DataFrame) -> TemporalIntegrityResult:
        """
        Validate time series consistency and gaps.
        
        Requirements: C03 - Robust handling of incomplete data
        MUST identify time gaps, duplicates, and inconsistent sampling
        MUST calculate data completeness percentages
        MUST flag problematic time series for review
        """
    
    def validate_sampling_frequency(self, data: pd.DataFrame) -> SamplingValidationResult:
        """
        Check sampling rate consistency across subjects and tasks.
        
        Requirements: C03 - Preservation of original variables and metadata
        MUST detect sampling frequency variations
        MUST validate frequency consistency within subjects
        MUST identify resampling requirements for conversion
        """
    
    def assess_gait_cycle_readiness(self, data: pd.DataFrame) -> GaitCycleReadinessResult:
        """
        Assess data readiness for gait cycle detection and phase conversion.
        
        Requirements: C03 - Automatic gait cycle detection from force data
        MUST verify presence and quality of vertical ground reaction forces
        MUST identify potential gait cycles and estimate success rate
        MUST provide recommendations for improving cycle detection
        """
```

## QualityAssessor - Dataset Quality Assessment

**Requirements Traceability:** User Story C02 (Assess Dataset Quality and Validation)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)  
**Integration:** Used by PhaseValidator for comprehensive quality assessment  
**Workflow Integration:** Supports Sequences 1 and 3 for dataset quality evaluation and contribution decisions

```python
class QualityAssessor:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize quality assessor with standardized dependencies.
        
        Requirements: C02 - Quality assessment as part of validation pipeline
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def assess_dataset_quality(self, file_path: str, generate_comparisons: bool = True) -> QualityAssessmentResult:
        """
        Generate comprehensive quality reports for datasets.
        
        Requirements Traceability:
        - C02: Coverage statistics (subjects, tasks, gait cycles)
        - C02: Missing data patterns and outlier identification
        - C02: Biomechanical plausibility scores and population comparisons
        - C02: Export comprehensive report for contribution documentation
        
        Interface Standards Compliance:
        - Uses standardized progress reporting and error handling
        - Provides structured quality metrics for tracking
        
        MUST calculate coverage statistics (subjects, tasks, gait cycles)
        MUST identify missing data patterns and outliers with biomechanical context
        MUST generate biomechanical plausibility scores using task-specific criteria
        MUST compare against population norms from literature (when available)
        MUST export quality metrics for tracking over time
        MUST provide actionable recommendations for data improvement
        
        Raises:
        - QualityError: Insufficient data for reliable quality assessment
        - DataFormatError: Invalid dataset structure preventing analysis
        """
    
    def calculate_coverage_statistics(self, data: pd.DataFrame) -> CoverageStats:
        """
        Calculate subject, task, and cycle coverage metrics.
        
        Requirements: C02 - Coverage statistics reporting
        MUST calculate completeness percentages by variable and task
        MUST identify data sparsity patterns
        MUST assess balance across subjects and conditions
        """
    
    def identify_outliers(self, data: pd.DataFrame, method: str = "biomechanical") -> OutlierAnalysis:
        """
        Identify outlier patterns and data quality issues.
        
        Requirements: C02 - Outlier identification with biomechanical context
        MUST use biomechanical criteria for outlier detection
        MUST distinguish between statistical outliers and biomechanical impossibilities
        MUST provide detailed context for each outlier identification
        MUST suggest potential causes and remediation strategies
        """
    
    def generate_population_comparison(self, data: pd.DataFrame) -> PopulationComparisonResult:
        """
        Compare dataset against established population norms.
        
        Requirements: C02 - Population comparisons for validation context
        MUST compare means, ranges, and distributions against literature
        MUST identify systematic deviations from expected values
        MUST provide interpretation guidance for observed differences
        """
```

## DatasetComparator - Multi-Dataset Statistical Comparison

**Requirements Traceability:** User Story V01 (Compare Multiple Datasets)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)  
**CLI Entry Point:** `validation_compare_datasets.py` (implements statistical comparison workflows)  
**Workflow Integration:** Supports research activities requiring cross-dataset analysis and population studies

```python
class DatasetComparator:
    def __init__(self, config_manager: ConfigurationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize dataset comparator with standardized dependencies.
        
        Requirements: V01 - Multi-dataset statistical comparison capabilities
        Dependencies: ConfigurationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def compare_datasets(self, dataset_paths: List[str], 
                        comparison_config: ComparisonConfig) -> ComparisonResult:
        """
        Perform comprehensive statistical comparison of multiple datasets.
        
        Requirements Traceability:
        - V01: Statistical comparison with significance testing
        - V01: Cross-dataset consistency analysis
        - V01: Population-level trend identification
        - V01: Comparative quality assessment
        
        Interface Standards Compliance:
        - Uses standardized progress reporting and error handling
        - Follows CLI argument patterns for comparison parameters
        
        MUST load and validate all datasets before comparison
        MUST perform statistical significance testing (t-tests, ANOVA)
        MUST calculate effect sizes and confidence intervals
        MUST identify systematic differences between datasets
        MUST generate comparative visualizations
        MUST export comparison report with statistical details
        MUST handle missing data and coverage differences gracefully
        
        Raises:
        - DataFormatError: Incompatible dataset structures or formats
        - ValidationError: Insufficient data for reliable comparison
        - ConfigurationError: Invalid comparison parameters
        """
    
    def calculate_effect_sizes(self, datasets: List[LocomotionData], 
                              variables: List[str]) -> EffectSizeAnalysis:
        """
        Calculate effect sizes between datasets for specified variables.
        
        Requirements: V01 - Effect size analysis for practical significance
        MUST calculate Cohen's d for continuous variables
        MUST provide confidence intervals for effect sizes
        MUST categorize effect sizes (small, medium, large)
        MUST account for sample size differences
        """
    
    def identify_systematic_differences(self, comparison_result: ComparisonResult) -> SystematicDifferenceAnalysis:
        """
        Identify systematic patterns in dataset differences.
        
        Requirements: V01 - Population-level trend identification
        MUST detect consistent direction of differences
        MUST identify variables with largest between-dataset variation
        MUST assess potential confounding factors
        MUST provide interpretive guidance for differences
        """
    
    def generate_comparison_report(self, result: ComparisonResult, 
                                 output_path: str) -> ReportGenerationResult:
        """
        Generate comprehensive comparison report with statistical details.
        
        Requirements: V01 - Export detailed comparison analysis
        Interface Standards: Follows report structure standards
        
        MUST include statistical test results with p-values
        MUST provide effect size interpretations
        MUST include comparative visualizations
        MUST provide recommendations for dataset usage
        """
```

## AutomatedFineTuner - Statistical Validation Range Optimization

**Requirements Traceability:** User Story V05 (Automated Validation Range Optimization)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation)  
**CLI Entry Point:** `validation_auto_tune_spec.py` (automated statistical range optimization)  
**Workflow Integration:** Implements Sequence 2B for statistics-based validation range updates

```python
class AutomatedFineTuner:
    def __init__(self, spec_manager: ValidationSpecManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize automated fine-tuner with validation specification management.
        
        Requirements: V05 - Automated statistical optimization of validation ranges
        Dependencies: ValidationSpecManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def analyze_dataset_distributions(self, dataset_paths: List[str]) -> DistributionAnalysis:
        """
        Analyze statistical distributions across datasets for range optimization.
        
        Requirements Traceability:
        - V05: Statistical analysis of variable distributions by task and phase
        - V05: Identification of outliers and statistical boundaries
        
        Interface Standards Compliance:
        - Uses standardized progress reporting for long analysis operations
        - Provides detailed diagnostics via verbose logging
        
        MUST calculate distribution statistics (mean, std, percentiles) by task and phase
        MUST identify outliers using multiple statistical methods
        MUST assess distribution normality and appropriate statistical tests
        MUST handle missing data and incomplete coverage gracefully
        MUST provide confidence intervals for statistical estimates
        
        Raises:
        - DataFormatError: Invalid datasets or incompatible structures
        - ValidationError: Insufficient data for reliable statistical analysis
        """
    
    def optimize_validation_ranges(self, distribution_analysis: DistributionAnalysis,
                                 optimization_config: OptimizationConfig) -> TuningResult:
        """
        Optimize validation ranges using statistical methods with biomechanical constraints.
        
        Requirements Traceability:
        - V05: Multiple statistical methods (percentile_95, IQR, robust statistics)
        - V05: Biomechanical plausibility constraints during optimization
        - V05: Statistical justification for proposed ranges
        
        MUST support multiple statistical methods for range calculation
        MUST apply biomechanical plausibility constraints
        MUST calculate expected validation pass rate changes
        MUST provide statistical confidence measures for proposed ranges
        MUST generate detailed methodology documentation
        MUST compare proposed ranges with current specifications
        
        Raises:
        - ConfigurationError: Invalid optimization parameters
        - ValidationError: Optimization results fail biomechanical constraints
        """
    
    def validate_optimization_results(self, tuning_result: TuningResult,
                                    test_datasets: List[str]) -> OptimizationValidation:
        """
        Validate optimization results against test datasets.
        
        Requirements: V05 - Validation of optimized ranges against independent data
        MUST test optimized ranges on independent validation datasets
        MUST calculate actual vs predicted validation pass rates
        MUST identify potential overfitting or underfitting issues
        MUST assess biomechanical reasonableness of optimization results
        """
    
    def generate_optimization_report(self, tuning_result: TuningResult,
                                   validation_result: OptimizationValidation,
                                   output_path: str) -> ReportGenerationResult:
        """
        Generate comprehensive optimization report with statistical details.
        
        Requirements: V05 - Export detailed optimization methodology and results
        Interface Standards: Follows report structure standards
        
        MUST document statistical methodology and parameters used
        MUST include before/after range comparisons
        MUST provide validation pass rate predictions
        MUST include biomechanical interpretation of changes
        MUST provide recommendations for range adoption
        """
```

## BenchmarkCreator - ML Benchmark Creation

**Requirements Traceability:** User Story A01 (Create ML Benchmarks)  
**User Personas:** System Administrator  
**CLI Entry Point:** `create_benchmarks.py` (ML benchmark suite creation)  
**Workflow Integration:** Supports future research activities requiring standardized ML benchmarks

```python
class BenchmarkCreator:
    def __init__(self, config_manager: ConfigurationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize benchmark creator with standardized dependencies.
        
        Requirements: A01 - ML benchmark creation with stratified data splits
        Dependencies: ConfigurationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def create_ml_benchmark(self, dataset_paths: List[str], 
                          benchmark_config: BenchmarkConfig) -> BenchmarkResult:
        """
        Create comprehensive ML benchmark suite with stratified data splits.
        
        Requirements Traceability:
        - A01: Subject-level stratified splits to prevent data leakage
        - A01: Multiple ML framework format exports (scikit-learn, PyTorch, TensorFlow)
        - A01: Baseline performance metrics and evaluation protocols
        - A01: Comprehensive documentation and metadata
        
        Interface Standards Compliance:
        - Uses standardized progress reporting for benchmark creation
        - Follows CLI argument patterns for split strategies and formats
        
        MUST create subject-level stratified train/validation/test splits
        MUST ensure no data leakage between splits (same subject not in multiple splits)
        MUST validate split quality and balance across tasks and subjects
        MUST export data in multiple ML framework formats
        MUST calculate baseline performance metrics
        MUST generate comprehensive benchmark documentation
        MUST include metadata for reproducibility
        
        Raises:
        - DataFormatError: Invalid datasets or insufficient quality for benchmarking
        - ValidationError: Unable to create balanced splits with available data
        - ConfigurationError: Invalid benchmark configuration parameters
        """
    
    def validate_split_quality(self, split_result: DataSplitResult) -> SplitQualityAssessment:
        """
        Validate quality and balance of train/validation/test splits.
        
        Requirements: A01 - Ensure high-quality, balanced splits for reliable ML benchmarks
        MUST check for data leakage between splits
        MUST assess balance across tasks, subjects, and conditions
        MUST calculate split size adequacy for ML training
        MUST identify potential bias sources in splits
        """
    
    def calculate_baseline_metrics(self, benchmark_data: BenchmarkData) -> BaselineMetrics:
        """
        Calculate baseline performance metrics for benchmark evaluation.
        
        Requirements: A01 - Baseline performance metrics for comparative evaluation
        MUST implement simple baseline algorithms (linear models, naive predictors)
        MUST calculate standard ML metrics (RMSE, MAE, R², accuracy for classification)
        MUST provide task-specific evaluation metrics
        MUST establish performance targets for benchmark users
        """
    
    def export_benchmark_formats(self, benchmark_data: BenchmarkData,
                               formats: List[str], output_dir: str) -> ExportResult:
        """
        Export benchmark data in multiple ML framework formats.
        
        Requirements: A01 - Multi-format exports for broad ML framework compatibility
        MUST support scikit-learn format (numpy arrays, pandas DataFrames)
        MUST support PyTorch format (tensors, DataLoader-compatible)
        MUST support TensorFlow format (tf.data.Dataset compatible)
        MUST include consistent metadata across all formats
        MUST provide framework-specific usage examples
        """
    
    def generate_benchmark_documentation(self, benchmark_result: BenchmarkResult,
                                       output_path: str) -> DocumentationResult:
        """
        Generate comprehensive benchmark documentation and usage guides.
        
        Requirements: A01 - Comprehensive documentation for benchmark usage
        Interface Standards: Follows documentation structure standards
        
        MUST document benchmark creation methodology
        MUST include data split details and rationale
        MUST provide usage examples for each ML framework
        MUST document baseline performance expectations
        MUST include citation guidelines and dataset attribution
        """
```

## Supporting Infrastructure Interfaces

### ConfigurationManager
```python
class ConfigurationManager:
    def __init__(self, tool_name: str):
        """
        Initialize configuration manager with tool-specific defaults.
        
        Requirements: Interface Standards - Standardized configuration management
        MUST load default configuration for tool
        MUST support configuration file overrides (--config flag)
        MUST validate configuration format and required parameters
        """
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support.
        
        Interface Standards: get_setting("processing.memory_limit_gb", 4)
        MUST support nested key access with dot notation
        MUST provide sensible defaults for missing keys
        MUST log configuration access for debugging
        """
    
    def load_config_file(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file with validation.
        
        MUST validate configuration file format
        MUST merge with existing configuration hierarchically
        MUST handle file not found gracefully
        """
    
    def validate_configuration(self) -> ConfigValidationResult:
        """
        Validate current configuration for completeness and correctness.
        
        MUST check required parameters are present
        MUST validate parameter types and ranges
        MUST identify deprecated or unknown parameters
        """

### ErrorHandler
```python
class ErrorHandler:
    def __init__(self, tool_name: str, verbose: bool = False):
        """
        Initialize error handler with tool context and logging configuration.
        
        Interface Standards: Standardized error handling and logging
        MUST configure logging according to interface standards
        MUST set up error reporting consistent with CLI patterns
        """
    
    def handle_error(self, error: LocomotionToolError, context: ErrorContext = None) -> ErrorResponse:
        """
        Handle all tool errors with standardized response format.
        
        Interface Standards: Error message format and exit codes
        MUST format errors according to standardized pattern:
        ERROR: {error_type}: {error_description}
          File: {file_path}
          Context: {additional_context}
          Suggestion: {recommended_action}
        
        MUST map exceptions to appropriate exit codes
        MUST log errors with appropriate severity levels
        MUST provide actionable suggestions based on error type
        """
    
    def log_warning(self, message: str, context: ErrorContext = None) -> None:
        """
        Log warning message with context.
        
        MUST format warnings consistently
        MUST include relevant context information
        MUST maintain warning counts for reporting
        """
    
    def get_error_summary(self) -> ErrorSummary:
        """
        Get summary of errors and warnings encountered.
        
        MUST provide counts by error type
        MUST include most common error patterns
        MUST suggest remediation strategies
        """

### ProgressReporter
```python
class ProgressReporter:
    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize progress reporter with output level configuration.
        
        Interface Standards: Standardized progress reporting
        MUST configure output according to verbosity settings
        MUST provide consistent progress display patterns
        """
    
    def start_operation(self, operation_name: str, total_steps: int = None) -> None:
        """
        Start tracking progress for a named operation.
        
        MUST display operation start message
        MUST initialize progress tracking
        MUST record operation start time
        """
    
    def update_progress(self, current_step: int, message: str = None) -> None:
        """
        Update progress with current step and optional message.
        
        MUST display progress appropriate to verbosity level
        MUST show percentage completion when total_steps known
        MUST include elapsed time information
        """
    
    def complete_operation(self, success: bool = True, summary: str = None) -> None:
        """
        Complete operation tracking with success status.
        
        MUST display completion message with total time
        MUST show final summary if provided
        MUST clear progress display appropriately
        """
    
    def log_milestone(self, milestone: str, details: str = None) -> None:
        """
        Log significant milestone in operation progress.
        
        MUST display milestone according to verbosity settings
        MUST include timestamp for verbose mode
        MUST maintain milestone history
        """
```

## Additional Supporting Data Structures

```python
# Additional result and configuration types
@dataclass
class ComparisonConfig:
    """Configuration for dataset comparison operations"""
    statistical_methods: List[str]  # ['t_test', 'anova', 'mann_whitney']
    significance_level: float  # 0.05
    effect_size_thresholds: Dict[str, float]  # {'small': 0.2, 'medium': 0.5, 'large': 0.8}
    variables_to_compare: List[str]
    tasks_to_compare: List[str]
    generate_plots: bool
    
@dataclass
class OptimizationConfig:
    """Configuration for validation range optimization"""
    method: str  # 'percentile_95', 'iqr', 'robust'
    percentile_range: Tuple[float, float]  # (2.5, 97.5)
    outlier_threshold: float  # 3.0
    biomechanical_constraints: bool
    minimum_sample_size: int
    confidence_level: float  # 0.95

@dataclass
class BenchmarkConfig:
    """Configuration for ML benchmark creation"""
    split_strategy: str  # 'subject', 'temporal', 'task'
    train_ratio: float  # 0.7
    validation_ratio: float  # 0.15
    test_ratio: float  # 0.15
    export_formats: List[str]  # ['scikit', 'pytorch', 'tensorflow']
    include_baseline_metrics: bool
    stratify_by: List[str]  # ['task', 'subject_demographics']

@dataclass
class ConfigValidationResult:
    """Configuration validation result"""
    valid: bool
    issues: List[str]
    warnings: List[str]
    suggested_fixes: List[str]
```

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
    gif_paths: List[str]  # Animated visualizations (when --generate-gifs used)
    
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
    stride_filter_result: StrideFilterResult
    task_coverage: Dict[str, CoverageInfo]
    variable_coverage: Dict[str, float]  # Percentage coverage by variable
    
    # Batch processing support
    batch_context: Optional[BatchContext] = None
    
    def validate_completeness(self) -> CompletionCheck:
        """Verify this result meets interface contract requirements"""
        missing_fields = []
        if not self.file_path:
            missing_fields.append('file_path')
        if self.stride_statistics is None:
            missing_fields.append('stride_statistics')
        if self.coverage_analysis is None:
            missing_fields.append('coverage_analysis')
        if self.stride_filter_result is None:
            missing_fields.append('stride_filter_result')
            
        return CompletionCheck(
            complete=len(missing_fields) == 0,
            missing_fields=missing_fields,
            validation_timestamp=datetime.now()
        )
    
    def export_summary(self, format: str = 'json') -> str:
        """Export validation summary in specified format"""
        summary = {
            'file_path': self.file_path,
            'validation_passed': self.validation_passed,
            'total_strides': self.stride_statistics.total_count,
            'valid_strides': self.stride_statistics.valid_count,
            'pass_rate': self.stride_statistics.pass_rate,
            'processing_time': self.processing_time,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
        
        if format == 'json':
            return json.dumps(summary, indent=2)
        elif format == 'yaml':
            return yaml.dump(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
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
    rejection_categories: Dict[str, int]  # Category -> count mapping
    most_common_rejections: List[Tuple[str, int]]  # Top rejection reasons
    
    # Coverage and completeness
    coverage_info: CoverageInfo
    task_specific_pass_rates: Dict[str, float]  # Task -> pass rate
    variable_specific_pass_rates: Dict[str, float]  # Variable -> pass rate
    phase_specific_pass_rates: Dict[int, float]  # Phase -> pass rate (0, 25, 50, 75)
    
    # Traceability and metadata
    filtering_timestamp: datetime
    filtering_parameters: Dict[str, Any]
    validation_spec_applied: str
    step_classifier_config: StepClassifierConfig
    
    # Quality indicators
    data_quality_score: float  # Overall quality score (0-100)
    confidence_intervals: Dict[str, Tuple[float, float]]  # Variable -> (lower, upper)
    biomechanical_plausibility: Dict[str, float]  # Task -> plausibility score
    
    # Audit trail
    audit_trail: List[FilteringDecision]
    processing_stats: ProcessingStats
    
    def get_rejection_summary(self) -> Dict[str, Any]:
        """Generate human-readable rejection summary"""
        return {
            'total_rejections': self.invalid_strides,
            'rejection_rate': (self.invalid_strides / self.total_strides) * 100,
            'top_reasons': self.most_common_rejections[:5],
            'by_category': self.rejection_categories,
            'by_task': {task: (1.0 - rate) * 100 for task, rate in self.task_specific_pass_rates.items()},
            'by_variable': {var: (1.0 - rate) * 100 for var, rate in self.variable_specific_pass_rates.items()},
            'recommendations': self._generate_recommendations()
        }
    
    def export_filtered_dataset(self, output_path: str) -> str:
        """Export filtered dataset to file"""
        if output_path.endswith('.parquet'):
            self.filtered_data.to_parquet(output_path, index=False)
        elif output_path.endswith('.csv'):
            self.filtered_data.to_csv(output_path, index=False)
        else:
            raise ValueError(f"Unsupported file format: {output_path}")
        return output_path
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on filtering results"""
        recommendations = []
        
        if self.pass_rate < 0.5:
            recommendations.append("Low pass rate suggests validation ranges may be too strict")
        
        for variable, rate in self.variable_specific_pass_rates.items():
            if rate < 0.3:
                recommendations.append(f"Variable '{variable}' has very low pass rate ({rate:.1%}) - check data quality")
        
        if len(self.most_common_rejections) > 0:
            top_reason = self.most_common_rejections[0][0]
            recommendations.append(f"Most common rejection: {top_reason} - focus improvement efforts here")
        
        return recommendations
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
    
    # Biomechanical context
    biomechanical_context: str  # Human-readable explanation
    remediation_suggestion: Optional[str]  # Suggested fix
    
    def to_human_readable(self) -> str:
        """Generate human-readable rejection description"""
        return f"{self.task} - {self.variable} at {self.phase_percentage:.0%} phase: "
               f"value {self.value:.2f} {self.variable_units} outside expected range "
               f"[{self.expected_min:.2f}, {self.expected_max:.2f}]. {self.biomechanical_context}"
```

### QualityAssessmentResult
```python
@dataclass
class QualityAssessmentResult:
    file_path: str
    assessment_timestamp: datetime
    
    # Core quality components
    coverage_stats: CoverageStats
    outlier_analysis: OutlierAnalysis
    plausibility_scores: PlausibilityScores
    population_comparison: PopulationComparison
    quality_metrics: QualityMetrics
    
    # Output and reporting
    report_path: str
    quality_score: float  # Overall quality score (0-100)
    quality_grade: str  # A, B, C, D, F
    
    # Recommendations and actions
    recommendations: List[QualityRecommendation]
    critical_issues: List[QualityIssue]
    
    # Processing metadata
    processing_time: float
    assessment_parameters: Dict[str, Any]
    
    def get_quality_summary(self) -> Dict[str, Any]:
        """Generate summary of quality assessment"""
        return {
            'overall_score': self.quality_score,
            'grade': self.quality_grade,
            'coverage_percentage': self.coverage_stats.overall_coverage,
            'outlier_percentage': self.outlier_analysis.outlier_rate,
            'plausibility_score': self.plausibility_scores.overall_score,
            'critical_issues_count': len(self.critical_issues),
            'recommendations_count': len(self.recommendations)
        }
```

### ValidationConfig
```python
@dataclass
class ValidationConfig:
    # Core validation parameters
    phase_tolerance: float  # Tolerance for phase calculations
    outlier_threshold: float  # Statistical outlier detection threshold
    minimum_stride_count: int  # Minimum strides required for validation
    required_phases: List[int]  # Phases to validate (e.g., [0, 25, 50, 75])
    
    # File and specification paths
    validation_spec_path: str  # Path to validation specifications
    output_directory: str  # Output directory for reports and plots
    
    # Processing options
    plot_generation: bool  # Generate validation plots
    gif_generation: bool  # Generate animated GIFs (computationally intensive)
    parallel_processing: bool  # Enable parallel validation
    max_workers: int  # Maximum parallel workers
    
    # Quality assessment options
    quality_assessment: bool  # Run quality assessment
    population_comparison: bool  # Compare against population norms
    biomechanical_context: bool  # Include biomechanical explanations
    
    # Reporting options
    report_format: str  # 'markdown', 'html', 'json'
    verbose_reporting: bool  # Include detailed diagnostics
    
    # Memory and performance
    memory_limit_gb: float  # Memory limit for processing
    chunk_size: int  # Data processing chunk size
    
    def validate_config(self) -> ConfigValidationResult:
        """Validate configuration parameters"""
        issues = []
        
        if self.phase_tolerance <= 0 or self.phase_tolerance > 1:
            issues.append("phase_tolerance must be between 0 and 1")
        
        if self.minimum_stride_count < 1:
            issues.append("minimum_stride_count must be positive")
        
        if not all(0 <= phase <= 100 for phase in self.required_phases):
            issues.append("required_phases must be between 0 and 100")
        
        if self.max_workers < 1:
            issues.append("max_workers must be positive")
        
        return ConfigValidationResult(
            valid=len(issues) == 0,
            issues=issues
        )
```

## Validation Workflow Data Structures

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

## Additional Data Structures

### ValidationSpecification
```python
@dataclass
class ValidationSpecification:
    """Complete validation specification with ranges and metadata"""
    # Specification metadata
    version: str
    creation_date: datetime
    last_modified: datetime
    description: str
    
    # Task-specific validation ranges
    kinematic_ranges: Dict[str, Dict[str, ValidationRange]]  # task -> variable -> range
    kinetic_ranges: Dict[str, Dict[str, ValidationRange]]    # task -> variable -> range
    
    # Specification sources and citations
    literature_sources: List[LiteratureReference]
    statistical_sources: List[StatisticalReference]
    
    # Validation metadata
    supported_tasks: List[str]
    supported_variables: List[str]
    required_phases: List[int]  # [0, 25, 50, 75]
    
    def get_range(self, task: str, variable: str, phase: int) -> Optional[ValidationRange]:
        """Get validation range for specific task, variable, and phase"""
        pass
    
    def validate_completeness(self) -> SpecCompletenessResult:
        """Validate specification completeness and integrity"""
        pass

@dataclass
class ValidationRange:
    """Single validation range with metadata"""
    min_value: float
    max_value: float
    units: str
    phase: int  # 0, 25, 50, 75
    confidence_level: float  # Statistical confidence (e.g., 0.95)
    source_type: str  # 'literature', 'statistical', 'expert'
    source_reference: str
    last_updated: datetime
    
    def contains(self, value: float) -> bool:
        """Check if value is within range"""
        return self.min_value <= value <= self.max_value
    
    def violation_severity(self, value: float) -> str:
        """Determine violation severity based on how far outside range"""
        if self.contains(value):
            return 'none'
        
        range_size = self.max_value - self.min_value
        if value < self.min_value:
            excess = (self.min_value - value) / range_size
        else:
            excess = (value - self.max_value) / range_size
        
        if excess < 0.1:
            return 'minor'
        elif excess < 0.5:
            return 'major'
        else:
            return 'critical'
```

### ErrorContext and Handling
```python
@dataclass
class ErrorContext:
    """Standardized error context for all locomotion tools"""
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    user_action: Optional[str] = None  # What the user was trying to do
    system_state: Optional[Dict[str, Any]] = None  # Relevant system state
    biomechanical_context: Optional[str] = None  # Domain-specific context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and reporting"""
        return {
            k: v for k, v in asdict(self).items() 
            if v is not None
        }

@dataclass
class ErrorResponse:
    """Standardized error response with exit codes and suggestions"""
    error_type: str
    error_message: str
    exit_code: int
    context: ErrorContext
    suggestion: str
    technical_details: Optional[str] = None
    
    def format_for_user(self) -> str:
        """Format error message for user display"""
        msg = f"ERROR: {self.error_type}: {self.error_message}\n"
        
        if self.context.file_path:
            msg += f"  File: {self.context.file_path}\n"
        
        if self.context.biomechanical_context:
            msg += f"  Context: {self.context.biomechanical_context}\n"
        
        msg += f"  Suggestion: {self.suggestion}\n"
        
        return msg

# Additional supporting data structures
@dataclass
class StrideStatistics:
    """Stride-level statistics for validation results"""
    total_count: int
    valid_count: int
    invalid_count: int
    pass_rate: float
    by_task: Dict[str, int]  # Task -> stride count
    by_subject: Dict[str, int]  # Subject -> stride count
    quality_distribution: Dict[str, int]  # Quality grade -> count

@dataclass
class CoverageAnalysis:
    """Dataset coverage analysis results"""
    overall_coverage: float  # Percentage (0-100)
    variable_coverage: Dict[str, float]  # Variable -> coverage percentage
    task_coverage: Dict[str, float]  # Task -> coverage percentage
    phase_coverage: Dict[int, float]  # Phase -> coverage percentage
    missing_variables: List[str]
    unexpected_variables: List[str]
    coverage_gaps: List[CoverageGap]
    
@dataclass
class CoverageGap:
    """Specific coverage gap with context"""
    variable: str
    task: Optional[str]
    expected_count: int
    actual_count: int
    gap_percentage: float
    impact_assessment: str  # 'minor', 'moderate', 'major'

@dataclass
class BatchValidationResult:
    """Results from batch validation of multiple datasets"""
    dataset_results: List[PhaseValidationResult]
    summary_statistics: BatchSummaryStats
    cross_dataset_analysis: CrossDatasetAnalysis
    batch_report_path: str
    processing_time: float
    
@dataclass
class BatchSummaryStats:
    """Summary statistics across batch validation"""
    total_datasets: int
    passed_datasets: int
    failed_datasets: int
    average_pass_rate: float
    total_strides: int
    total_valid_strides: int
    common_failure_patterns: List[Tuple[str, int]]

@dataclass
class TimeValidationResult:
    """Results from time-indexed dataset validation"""
    file_path: str
    validation_passed: bool
    temporal_integrity: TemporalIntegrityResult
    sampling_validation: SamplingValidationResult
    gait_cycle_readiness: GaitCycleReadinessResult
    quality_metrics: QualityMetrics
    processing_time: float
    validation_timestamp: datetime
    errors: List[ValidationError]
    warnings: List[ValidationError]

@dataclass
class TemporalIntegrityResult:
    """Time series integrity validation results"""
    has_time_gaps: bool
    gap_count: int
    largest_gap_duration: float
    has_duplicates: bool
    duplicate_count: int
    sampling_consistency: float  # 0-1 score
    completeness_percentage: float

@dataclass
class SamplingValidationResult:
    """Sampling frequency validation results"""
    detected_frequency: float
    frequency_consistency: bool
    frequency_variations: List[FrequencyVariation]
    recommended_resampling: Optional[float]
    
@dataclass
class GaitCycleReadinessResult:
    """Assessment of data readiness for gait cycle detection"""
    has_vertical_grf: bool
    grf_quality_score: float
    estimated_cycles: int
    cycle_detection_confidence: float
    potential_issues: List[str]
    recommendations: List[str]
```

## Critical Interface: validation_dataset_report.py

The **validation_dataset_report.py** CLI tool is the primary entry point for dataset quality assessment and represents the integration of multiple interface contracts:

### Implementation Architecture
```python
# validation_dataset_report.py - CLI Entry Point
def main():
    """
    Primary CLI for comprehensive dataset validation and quality assessment.
    
    Requirements Traceability: User Story C02 (Dataset Quality Assessment)
    User Personas: Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)
    
    Interface Integration:
    - PhaseValidator: Core validation logic and stride-level filtering
    - QualityAssessor: Quality metrics and population comparisons
    - ValidationSpecManager: Specification loading and range application
    - ErrorHandler: Standardized error handling and user feedback
    - ProgressReporter: User experience and operation tracking
    - DataLoader: File access and metadata extraction
    """
    
    # CLI Argument Processing (Interface Standards Compliance)
    parser = argparse.ArgumentParser(description="Comprehensive dataset validation and quality assessment")
    parser.add_argument("dataset_path", help="Path to phase-indexed parquet dataset")
    parser.add_argument("--output-dir", default="./validation_reports", help="Output directory for reports")
    parser.add_argument("--generate-gifs", action="store_true", help="Generate animated GIF visualizations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output for automation")
    
    # Interface Contract Implementation
    try:
        # Initialize standardized dependencies (Interface Standards)
        config_manager = ConfigurationManager("validation_dataset_report")
        error_handler = ErrorHandler("validation_dataset_report", verbose=args.verbose)
        progress_reporter = ProgressReporter(verbose=args.verbose, quiet=args.quiet)
        
        # Initialize validation components (Interface Contracts)
        spec_manager = ValidationSpecManager(config_manager, error_handler, progress_reporter)
        quality_assessor = QualityAssessor(spec_manager, error_handler, progress_reporter)
        phase_validator = PhaseValidator(spec_manager, error_handler, progress_reporter)
        
        # Execute comprehensive validation (Requirements C02)
        result = phase_validator.validate_dataset(
            file_path=args.dataset_path,
            generate_plots=True,
            generate_gifs=args.generate_gifs,
            output_dir=args.output_dir
        )
        
        # Generate comprehensive report (Requirements C02)
        report_path = os.path.join(args.output_dir, f"{dataset_name}_validation_report.md")
        phase_validator.generate_validation_report(result, report_path)
        
        return EXIT_SUCCESS
        
    except LocomotionToolError as e:
        return error_handler.handle_error(e).exit_code
```

### Interface Standards Compliance Summary

All interface contracts ensure consistency with Document 09 (Interface Standards):

1. **CLI Argument Patterns**: Consistent `--generate-gifs`, `--verbose`, `--quiet` flags
2. **Exit Codes**: Standardized error codes for different failure types
3. **Error Handling**: Structured error messages with context and suggestions
4. **Progress Reporting**: Consistent progress display across verbosity levels
5. **Configuration Management**: Standard YAML configuration loading and validation
6. **File Operations**: Consistent file access patterns and safety checks

### Requirements Traceability Summary

**User Story C02 (Dataset Quality Assessment)** - Complete implementation through:
- PhaseValidator: Comprehensive validation and stride-level filtering
- QualityAssessor: Coverage statistics and biomechanical plausibility
- ValidationSpecManager: Task-specific validation ranges
- Supporting Infrastructure: Consistent user experience and error handling

**Dr. Sarah Chen (Biomechanical Validation)** needs:
✅ Biomechanical correctness validation (PhaseValidator)
✅ Statistical analysis and outlier identification (QualityAssessor)  
✅ Validation range management (ValidationSpecManager)
✅ Clear error reporting and actionable suggestions (ErrorHandler)

**Marcus Rodriguez (Programmer)** needs:
✅ Clear validation feedback for conversion debugging (PhaseValidator)
✅ Progress reporting for long-running operations (ProgressReporter)
✅ Consistent CLI interface patterns (Interface Standards)
✅ Comprehensive error messages with context (ErrorHandler)

This interface contract specification ensures all components work together seamlessly to deliver the comprehensive dataset validation capabilities required by the locomotion data standardization project.