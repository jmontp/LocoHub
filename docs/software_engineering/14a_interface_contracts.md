# Interface Contracts

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

**Error Response Pattern:**
```python
def handle_error(self, error: LocomotionToolError) -> ErrorResponse:
    """Standardized error handling with user context"""
    return ErrorResponse(
        error_type=type(error).__name__,
        message=error.message,
        file_path=error.file_path,
        context=error.context,
        suggestion=error.suggestion,
        timestamp=datetime.now(),
        exit_code=self._get_exit_code(error)
    )
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

## Integrated Visualization in PhaseValidator

**Note:** Visualization is now integrated within the PhaseValidator component. Plot generation occurs automatically during validation report generation when `generate_plots=True`. Animated GIFs are optionally generated with the `--generate-gifs` flag in the CLI.

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

## DatasetComparator - Multi-Dataset Comparison

**Requirements Traceability:** User Story V01 (Compare Multiple Datasets)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation)  
**CLI Entry Point:** `validation_compare_datasets.py`  
**Workflow Integration:** Enables cross-dataset analysis for validation specialists across multiple data sources

```python
class DatasetComparator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize dataset comparator with standardized dependencies.
        
        Requirements: V01 - Systematic comparison of datasets from different sources
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def compare_datasets(self, file_paths: List[str], output_dir: str = None) -> ComparisonResult:
        """
        Systematically compare datasets from different sources.
        
        Requirements Traceability:
        - V01: Statistical comparison of means, distributions, and ranges
        - V01: Visual comparison plots showing overlays and differences
        - V01: Systematic bias identification between data sources
        - V01: Compatibility reports for dataset combinations
        - V01: Harmonization strategy recommendations for inconsistencies
        
        Interface Standards Compliance:
        - Uses standardized progress reporting for multi-dataset operations
        - Implements consistent error handling and exit codes
        - Follows CLI output patterns for comparison reports
        
        MUST perform statistical comparison of means, distributions, and ranges
        MUST generate visual comparison plots showing overlays and differences
        MUST identify systematic biases between data sources using biomechanical criteria
        MUST generate compatibility reports for dataset combinations
        MUST recommend harmonization strategies for inconsistencies
        MUST assess data quality impact of combining datasets
        
        Raises:
        - DataFormatError: Incompatible dataset formats or structures
        - ValidationError: Insufficient overlap for meaningful comparison
        """
    
    def statistical_comparison(self, datasets: List[pd.DataFrame], 
                             dataset_names: List[str]) -> StatisticalComparisonResult:
        """
        Compare statistical properties across datasets.
        
        Requirements: V01 - Statistical comparison with biomechanical context
        MUST compare means, standard deviations, ranges, and distributions
        MUST identify statistically significant differences
        MUST provide biomechanical interpretation of differences
        MUST calculate effect sizes and confidence intervals
        """
    
    def generate_comparison_plots(self, datasets: List[pd.DataFrame], 
                                dataset_names: List[str], output_dir: str) -> ComparisonPlotResult:
        """
        Generate visual comparison plots.
        
        Requirements: V01 - Visual comparison plots for manual review
        MUST create overlay plots showing dataset differences
        MUST generate task-specific and variable-specific comparisons
        MUST highlight systematic biases and outlier patterns
        MUST provide clear legends and interpretive guidance
        """
    
    def assess_compatibility(self, datasets: List[pd.DataFrame], 
                           dataset_names: List[str]) -> CompatibilityAssessment:
        """
        Assess compatibility for dataset combination.
        
        Requirements: V01 - Compatibility reports and harmonization strategies
        MUST identify variables suitable for combination
        MUST flag incompatible measurement protocols or populations
        MUST recommend data preprocessing for harmonization
        MUST estimate quality impact of dataset combination
        """
```

## ValidationSpecManager - Validation Rules Management

**Requirements Traceability:** User Stories V04 (Manage Validation Specifications), V05 (Optimize Validation Ranges)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation)  
**CLI Entry Points:** `validation_manual_tune_spec.py`, `validation_auto_tune_spec.py`  
**Workflow Integration:** Central to Sequences 2A and 2B - enables specification evolution with literature and statistical inputs

```python
class ValidationSpecManager:
    def __init__(self, config_manager: ConfigurationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize validation specification manager with standardized dependencies.
        
        Requirements: V04, V05 - Comprehensive validation range management
        Dependencies: ConfigurationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def get_validation_ranges(self, task: str, phase: int = None, 
                            variable: str = None) -> ValidationRanges:
        """
        Get validation ranges for specific task and optional phase.
        
        Requirements: Used by all validation components for consistent range application
        MUST retrieve task-specific ranges from markdown specifications
        MUST support phase-specific ranges where available (0%, 25%, 50%, 75%)
        MUST handle missing specifications gracefully with fallback strategies
        MUST cache specifications for performance
        MUST validate specification format and consistency
        
        Raises:
        - ConfigurationError: Invalid or corrupted specifications
        """
    
    def update_validation_ranges(self, task: str, variable: str, ranges: Dict, 
                               rationale: str, generate_gifs: bool = False) -> UpdateResult:
        """
        Edit and update validation rules and ranges.
        
        Requirements Traceability:
        - V04: Interactive editing of validation ranges with preview
        - V04: Import ranges from literature or statistical analysis
        - V04: Track changes with rationale and version control
        - V04: Validate specification changes against test datasets
        - V04: Generate updated validation plots after changes
        - V04: Optional animated GIFs with --generate-gifs flag
        
        Interface Standards Compliance:
        - Follows CLI argument patterns (--generate-gifs flag)
        - Uses standardized progress reporting for specification updates
        
        MUST provide interactive editing with preview of impact
        MUST support importing ranges from literature or statistical analysis
        MUST track changes with rationale and version control integration
        MUST validate specification changes against test datasets before applying
        MUST generate updated validation plots showing new ranges
        MUST create animated GIFs when requested (computationally intensive)
        MUST preserve manual adjustments and exceptions
        
        Raises:
        - ValidationError: Proposed ranges fail validation against test data
        - ConfigurationError: Invalid range format or conflicts
        """
    
    def load_specifications(self, spec_file: str = None) -> SpecificationLoadResult:
        """
        Load validation specifications from markdown files.
        
        Requirements: V04, V05 - Specification loading and parsing
        MUST parse kinematic and kinetic specification files
        MUST validate specification format and completeness
        MUST handle version compatibility and migration
        MUST cache parsed specifications for performance
        """
    
    def export_specifications(self, output_path: str, format: str = "markdown") -> ExportResult:
        """
        Export current specifications to file.
        
        Requirements: V04 - Generate change documentation for release notes
        MUST support multiple export formats (markdown, JSON, YAML)
        MUST include metadata and change history
        MUST preserve formatting and comments from original specifications
        """
    
    def preview_range_changes(self, proposed_changes: Dict[str, Dict], 
                            test_datasets: List[str] = None) -> ChangePreview:
        """
        Preview impact of proposed range changes.
        
        Requirements: V04, V05 - Preview changes with impact analysis
        MUST show before/after validation statistics
        MUST identify datasets affected by changes
        MUST calculate validation pass rate changes
        MUST provide statistical justification for changes
        """
    
    def validate_specification_integrity(self) -> IntegrityReport:
        """
        Validate internal consistency of all specifications.
        
        Requirements: V04 - Ensure specification quality and consistency
        MUST check for conflicting ranges across tasks
        MUST validate reference citations and sources
        MUST identify missing specifications for standard variables
        MUST assess completeness of task coverage
        """
```

## AutomatedFineTuner - Range Optimization

**Requirements Traceability:** User Story V05 (Optimize Validation Ranges)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation)  
**CLI Entry Point:** `validation_auto_tune_spec.py`  
**Workflow Integration:** Core component of Sequence 2B (Automatic Validation) - data-driven specification optimization

```python
class AutomatedFineTuner:
    def __init__(self, spec_manager: ValidationSpecManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize automated range tuner with standardized dependencies.
        
        Requirements: V05 - Automatically tune validation ranges based on dataset statistics
        Dependencies: ValidationSpecManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def auto_tune_ranges(self, datasets: List[str], method: str = "percentile_95", 
                        generate_gifs: bool = False, preview_only: bool = True) -> TuningResult:
        """
        Automatically tune validation ranges based on current dataset statistics.
        
        Requirements Traceability:
        - V05: Multiple statistical methods for range calculation
        - V05: Preview changes before applying with impact analysis
        - V05: Preserve manual adjustments and exceptions
        - V05: Generate tuning reports with statistical justification
        - V05: Generate updated validation plots showing statistical ranges
        - V05: Optional animated GIFs with --generate-gifs flag
        - V05: Integration with specification management workflow
        
        Interface Standards Compliance:
        - Uses standardized CLI argument patterns (--generate-gifs flag)
        - Implements consistent progress reporting for statistical analysis
        - Follows exit codes and error handling patterns
        
        MUST support multiple statistical methods (percentile_95, iqr, z_score, biomechanical)
        MUST preview changes before applying with comprehensive impact analysis
        MUST preserve manual adjustments and domain expert exceptions
        MUST generate tuning reports with statistical justification and literature context
        MUST integrate with ValidationSpecManager workflow for change tracking
        MUST generate updated validation plots showing proposed ranges
        MUST create animated GIFs when requested (computationally intensive)
        MUST respect biomechanical constraints and plausibility
        
        Raises:
        - ValidationError: Insufficient data for reliable statistical analysis
        - ConfigurationError: Invalid statistical method or parameters
        """
    
    def calculate_optimal_ranges(self, data: pd.DataFrame, method: str, 
                               task: str = None, variable: str = None) -> OptimalRanges:
        """
        Calculate statistically optimal ranges using specified method.
        
        Requirements: V05 - Statistical methods with biomechanical validation
        MUST support percentile-based, IQR-based, and z-score methods
        MUST incorporate biomechanical constraints and literature bounds
        MUST handle outliers and edge cases appropriately
        MUST provide confidence intervals and sample size considerations
        """
    
    def compare_tuning_methods(self, data: pd.DataFrame, 
                             methods: List[str] = None) -> MethodComparisonResult:
        """
        Compare different tuning methods on the same dataset.
        
        Requirements: V05 - Method selection guidance for domain experts
        MUST evaluate multiple statistical approaches
        MUST assess impact on validation pass rates
        MUST provide recommendations based on data characteristics
        MUST include biomechanical plausibility assessment
        """
    
    def validate_proposed_ranges(self, proposed_ranges: Dict, 
                               test_datasets: List[str]) -> RangeValidationResult:
        """
        Validate proposed ranges against independent test datasets.
        
        Requirements: V05 - Ensure tuned ranges maintain quality standards
        MUST test against held-out validation datasets
        MUST assess impact on data quality and scientific validity
        MUST identify potential negative consequences of range changes
        MUST provide rollback recommendations for problematic changes
        """
```

## BenchmarkCreator - ML Benchmark Management

**Requirements Traceability:** User Story A01 (Create ML Benchmarks)  
**User Personas:** Alex Kim (System Administrator)  
**CLI Entry Point:** `create_benchmarks.py`  
**Workflow Integration:** Supports Sequence 4 (Future ML Infrastructure) for research community dataset access

```python
class BenchmarkCreator:
    def __init__(self, data_loader: DataLoader, quality_assessor: QualityAssessor,
                 error_handler: ErrorHandler, progress_reporter: ProgressReporter = None):
        """
        Initialize ML benchmark creator with standardized dependencies.
        
        Requirements: A01 - Create standardized benchmarks for ML research
        Dependencies: DataLoader, QualityAssessor, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def create_ml_benchmarks(self, file_paths: List[str], split_strategy: str = "subject_based",
                           output_dir: str = None, export_formats: List[str] = None) -> BenchmarkResult:
        """
        Create standardized train/test/validation splits from quality datasets.
        
        Requirements Traceability:
        - A01: Stratified sampling ensuring no subject leakage between splits
        - A01: Multiple split strategies (temporal, subject-based, task-based)
        - A01: Metadata describing split composition and balance
        - A01: Export in ML-ready formats (scikit-learn, PyTorch, TensorFlow)
        - A01: Benchmark documentation with baseline performance metrics
        
        Interface Standards Compliance:
        - Uses standardized CLI argument patterns (--export-formats)
        - Implements consistent progress reporting for benchmark creation
        - Follows file naming conventions and output standards
        
        MUST ensure stratified sampling with no subject leakage between splits
        MUST support multiple split strategies (temporal, subject-based, task-based)
        MUST generate comprehensive metadata describing split composition and balance
        MUST export in ML-ready formats (scikit-learn, PyTorch, TensorFlow, MATLAB)
        MUST create benchmark documentation with baseline performance metrics
        MUST validate data quality before benchmark creation
        MUST preserve anonymization and scientific integrity
        
        Raises:
        - QualityError: Insufficient data quality for reliable benchmarks
        - ValidationError: Data structure incompatible with ML frameworks
        """
    
    def stratified_split(self, data: pd.DataFrame, strategy: str = "subject_based",
                       train_ratio: float = 0.7, val_ratio: float = 0.15) -> DataSplits:
        """
        Create stratified data splits with no leakage.
        
        Requirements: A01 - Stratified sampling with proper scientific controls
        MUST prevent subject leakage across splits
        MUST maintain task and demographic balance across splits
        MUST handle edge cases (small datasets, rare tasks)
        MUST provide detailed split statistics and validation
        """
    
    def export_ml_formats(self, splits: DataSplits, output_dir: str,
                         formats: List[str] = None) -> ExportResult:
        """
        Export data splits in multiple ML framework formats.
        
        Requirements: A01 - ML-ready formats for multiple frameworks
        MUST support scikit-learn (pickle), PyTorch (tensor), TensorFlow (dataset)
        MUST include MATLAB format for legacy research compatibility
        MUST generate framework-specific loading examples and documentation
        MUST preserve metadata and split information across formats
        """
    
    def generate_baseline_metrics(self, splits: DataSplits, 
                                benchmark_tasks: List[str] = None) -> BaselineMetrics:
        """
        Generate baseline performance metrics for benchmark validation.
        
        Requirements: A01 - Baseline performance metrics for ML validation
        MUST implement simple baseline models (linear regression, random forest)
        MUST calculate performance across standard biomechanical tasks
        MUST provide statistical significance testing for benchmark validity
        MUST generate performance reports for benchmark documentation
        """
    
    def validate_benchmark_quality(self, splits: DataSplits) -> BenchmarkQualityReport:
        """
        Validate benchmark quality and scientific rigor.
        
        Requirements: A01 - Ensure benchmark scientific validity
        MUST assess balance across demographic and task variables
        MUST validate no data leakage between splits
        MUST evaluate representativeness of each split
        MUST provide recommendations for benchmark improvement
        """
```

## Supporting Infrastructure

**Requirements Traceability:** All supporting infrastructure implements Interface Standards (Document 09) patterns for consistent user experience across all tools.

### ConfigurationManager
**Interface Standards Compliance:** Configuration file format, loading patterns, validation

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
    
    def update_config(self, key: str, value: Any) -> None:
        """
        Update configuration value with validation.
        
        MUST validate configuration value types and ranges
        MUST preserve configuration file formatting when possible
        MUST track configuration changes for audit
        """
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load and merge configuration from YAML file.
        
        Interface Standards: Standard YAML configuration format
        MUST support configuration file inheritance and merging
        MUST validate configuration schema and report errors clearly
        MUST handle missing configuration files gracefully
        
        Raises:
        - ConfigurationError: Invalid configuration file or format
        """
    
    def validate_configuration(self) -> List[str]:
        """
        Validate complete configuration for consistency and completeness.
        
        Interface Standards: Configuration validation guidelines
        MUST check for required parameters and valid value ranges
        MUST identify conflicting configuration settings
        MUST provide actionable error messages for configuration issues
        """
```

### ErrorHandler
**Interface Standards Compliance:** Exception hierarchy, error message format, logging standards

```python
class ErrorHandler:
    def __init__(self, tool_name: str, verbose: bool = False):
        """
        Initialize error handler with tool context and logging configuration.
        
        Interface Standards: Standardized error handling and logging
        MUST configure logging according to interface standards
        MUST set up error reporting consistent with CLI patterns
        """
    
    def handle_error(self, error: LocomotionToolError, context: str = "") -> ErrorResponse:
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
    
    def create_error_report(self, errors: List[Exception]) -> ErrorReport:
        """
        Create comprehensive error report for batch operations.
        
        Interface Standards: Structured error reporting
        MUST aggregate errors by type and severity
        MUST provide summary statistics for error patterns
        MUST include remediation strategies for common error types
        """
    
    def log_with_context(self, level: str, message: str, context: Dict = None) -> None:
        """
        Log messages with structured context information.
        
        Interface Standards: Log message format and structure
        MUST follow standardized log formatting
        MUST include relevant context for debugging
        MUST respect verbosity settings and log levels
        """
```

### DataLoader
**Interface Standards Compliance:** File access patterns, validation, progress reporting

```python
class DataLoader:
    def __init__(self, progress_reporter: ProgressReporter = None):
        """
        Initialize data loader with progress reporting capability.
        
        Interface Standards: Consistent progress reporting across tools
        """
    
    def load_parquet(self, file_path: str, validate_structure: bool = True) -> pd.DataFrame:
        """
        Load parquet file with comprehensive error handling and validation.
        
        Interface Standards: File access patterns and error handling
        MUST validate file accessibility and permissions before loading
        MUST provide clear error messages for file access issues
        MUST support progress reporting for large file operations
        MUST validate parquet structure if requested
        
        Raises:
        - DataFormatError: Invalid parquet structure or corruption
        - PermissionError: Insufficient file access permissions
        """
    
    def save_parquet(self, data: pd.DataFrame, file_path: str, 
                    validate_before_save: bool = True, overwrite: bool = False) -> None:
        """
        Save DataFrame to parquet with validation and safety checks.
        
        Interface Standards: File output patterns and safety
        MUST validate data structure before saving
        MUST check for existing files and respect overwrite settings
        MUST provide progress reporting for large save operations
        MUST ensure atomic file operations (temp file + rename)
        
        Raises:
        - DataFormatError: Invalid DataFrame structure for parquet
        - PermissionError: Insufficient directory write permissions
        """
    
    def validate_file_access(self, file_path: str, operation: str = "read") -> AccessResult:
        """
        Validate file accessibility and permissions comprehensively.
        
        Interface Standards: Consistent file access validation
        MUST check file existence, readability, and format
        MUST validate directory permissions for write operations
        MUST provide detailed access diagnostics
        MUST suggest remediation for access issues
        """
    
    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """
        Extract comprehensive metadata from parquet files.
        
        Requirements: Used by validation tools for dataset assessment
        MUST extract dataset size, schema, and statistics
        MUST identify dataset type (time vs phase indexed)
        MUST calculate data quality metrics
        MUST detect potential data issues
        """
```

### ProgressReporter
**Interface Standards Compliance:** Progress display formats, verbosity handling

```python
class ProgressReporter:
    def __init__(self, verbose: bool = False, quiet: bool = False):
        """
        Initialize progress reporter with verbosity settings.
        
        Interface Standards: Progress reporting formats (verbose, normal, quiet)
        """
    
    def start_operation(self, operation: str, total_steps: int, 
                       estimated_time: float = None) -> None:
        """
        Initialize progress tracking with operation context.
        
        Interface Standards: Consistent operation tracking
        MUST display operation start with timestamp (verbose mode)
        MUST initialize progress bar (normal mode)
        MUST provide minimal output (quiet mode)
        """
    
    def update_progress(self, step: int, message: str, 
                       details: Dict = None) -> None:
        """
        Update progress with current step and detailed status.
        
        Interface Standards: Progress display consistency
        MUST update progress bar with percentage and current step
        MUST log detailed progress messages in verbose mode
        MUST respect quiet mode settings
        """
    
    def complete_operation(self, success: bool, summary: str, 
                         execution_time: float) -> None:
        """
        Complete operation with success status and summary.
        
        Interface Standards: Operation completion reporting
        MUST report execution time and final status
        MUST provide operation summary with key metrics
        MUST follow verbosity patterns for completion messages
        """
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