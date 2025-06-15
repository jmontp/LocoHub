# C4 Level 4: Code Specifications

**Detailed component specifications split into focused documents.**

## Split Documentation

This document has been split into three focused files for better maintainability:

**[Interface Contracts](12a_interface_contracts.md)** - Method signatures and behavioral contracts  
**[Data Structures](12b_data_structures.md)** - Result classes and type definitions  
**[CLI Specifications](12c_cli_specifications.md)** - Command-line interface patterns

## Legacy Content

The content below is preserved for reference but should be migrated to the split documents above.

### PhaseValidator - Validate Converted Datasets (UC-C02)

**Interface Contract:**
```python
class PhaseValidator:
    """
    Comprehensive validation for phase-indexed datasets.
    Satisfies UC-C02: Validate Converted Dataset
    """
    
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler):
        """Dependencies: SpecificationManager, ErrorHandler"""
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True) -> PhaseValidationResult:
        """
        Run comprehensive validation on phase-indexed dataset with stride-level filtering.
        
        VALIDATION REPORT THREE CORE GOALS:
        1. Sign Convention Adherence - Verify biomechanical data follows standard sign conventions
        2. Outlier Detection - Identify strides with biomechanical values outside acceptable ranges  
        3. Phase Segmentation Validation - Ensure exactly 150 points per gait cycle with proper phase indexing
        
        MUST perform stride-level validation and filtering
        MUST show which strides are kept vs deleted in validation report
        MUST report stride pass rate as quality metric
        MUST only fail dataset if NO strides pass validation AND basic structure is invalid
        MUST create visual validation plots for manual review
        MUST export validation summary with stride statistics
        MUST use task-specific and phase-specific validation ranges from validation specifications
        MUST read tasks from data['task'] column
        MUST validate against known tasks from feature_constants
        MUST handle unknown tasks gracefully (warn but continue with available specs)
        MUST track standard specification coverage
        MUST handle partial failures gracefully (report but continue)
        
        Behavioral Contract:
        - Validates file accessibility and basic structure
        - Detects tasks from data['task'] column and validates against feature_constants
        - Checks phase indexing (exactly 150 points per cycle) for each stride
        - Retrieves task-specific validation ranges from SpecificationManager
        - Validates biomechanical ranges against task and phase-specific specifications for each stride
        - Tracks which standard specification variables are available vs missing
        - Filters strides: keeps valid strides, marks invalid strides for deletion
        - Generates markdown report showing kept vs deleted strides with reasons
        - Reports stride-level statistics (total, kept, deleted, pass rate)
        - Reports standard specification coverage and validation scope
        - Only fails if zero strides pass validation AND structure is fundamentally broken
        
        Returns: PhaseValidationResult with stride filtering results, coverage tracking, report path
        Raises: ValidationError only for catastrophic failures (file corruption, etc.)
        """
    
    def filter_valid_strides(self, data: pd.DataFrame, available_variables: List[str] = None) -> StrideFilterResult:
        """
        Filter dataset to keep only valid strides based on task-specific validation specifications.
        
        MUST identify valid vs invalid strides using task and phase-specific ranges
        MUST check each stride against available validation specifications
        MUST validate at 0%, 25%, 50%, 75% phases for each stride
        MUST provide detailed reasons for stride rejection with specific variables and phases
        MUST return filtered dataset with only valid strides
        MUST handle partial specification coverage gracefully
        MUST only validate variables that exist in both data and specifications
        
        Behavioral Contract:
        - Groups data by task from data['task'] column for task-specific validation
        - For each stride, validates available variables at key phases (0%, 25%, 50%, 75%)
        - Uses SpecificationManager to get task-specific upper/lower bounds
        - Skips validation for variables not in standard specification or missing from data
        - Marks stride as invalid if ANY available variable at ANY phase violates bounds
        - Provides rejection reasons specifying variable, phase, value, and expected range
        - Tracks which variables were validated vs skipped
        
        Returns: StrideFilterResult with filtered data, stride statistics, rejection reasons, coverage info
        """
    
    def get_available_tasks(self, data: pd.DataFrame) -> List[str]:
        """
        Get unique tasks from dataset, filtered to known standard tasks.
        
        MUST read from data['task'] column
        MUST filter to tasks known in feature_constants
        MUST warn about unknown tasks but continue processing
        
        Returns: List of valid task names found in dataset
        """
    
    def analyze_standard_spec_coverage(self, data: pd.DataFrame) -> Dict[str, Dict[str, bool]]:
        """
        Analyze which standard specification variables are available in the dataset.
        
        MUST check against feature_constants standard variables
        MUST organize by task and variable
        MUST identify missing vs available variables
        
        Returns: Dictionary of task -> variable -> present(bool)
        """
    
    def validate_batch(self, file_paths: List[str], parallel: bool = True) -> BatchValidationResult:
        """Validate multiple datasets with stride-level summary reporting"""
    
    def get_validation_summary(self, results: List[PhaseValidationResult]) -> ValidationSummary:
        """Generate batch validation summary with stride pass rate statistics"""
```

### TimeValidator - Validate Time-Indexed Datasets (UC-C02)

**Interface Contract:**
```python
class TimeValidator:
    """
    Comprehensive validation for time-indexed datasets.
    Satisfies UC-C02: Validate Converted Dataset
    """
    
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler):
        """Dependencies: SpecificationManager, ErrorHandler"""
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True) -> TimeValidationResult:
        """
        Run comprehensive validation on time-indexed dataset.
        
        MUST validate sampling frequency consistency
        MUST check temporal data integrity
        MUST validate biomechanical ranges where applicable
        MUST generate validation report with time-series plots
        
        Behavioral Contract:
        - Validates consistent sampling frequency
        - Checks for temporal gaps or inconsistencies
        - Validates biomechanical data ranges
        - Generates markdown report with time-series plots
        
        Returns: TimeValidationResult with validation status and reports
        """
```

### Integrated Visualization in PhaseValidator

**Note:** Visualization is now integrated within the PhaseValidator component as part of the validation report generation. Plot generation occurs automatically during validation with the `generate_plots` parameter, and optionally with animated GIFs using the `--generate-gifs` flag.
        
        Returns: GifGenerationResult with generated animation paths
        """
    
    def generate_validation_spec_plots(self, tasks: List[str], output_dir: str, 
                                      variables_subset: List[str] = None) -> PlotGenerationResult:
        """
        Generate plots showing validation specification ranges without data.
        
        MUST visualize validation ranges for specified tasks
        MUST show acceptable biomechanical ranges for each variable
        MUST create reference plots for specification documentation
        MUST handle partial variable coverage when subset is specified
        MUST adapt plot layouts based on available variables
        
        Behavioral Contract:
        - Generates specification range plots for all standard variables by default
        - Filters to variables_subset if provided
        - Creates task-specific range visualizations
        - Adapts plot layouts based on number of variables
        - Annotates plots with variable coverage information
        
        Returns: PlotGenerationResult with specification visualization paths
        """
```

---

## High Priority Components

> **These components satisfy High priority user stories (UC-V01, UC-V02, UC-V04, UC-V05) important for maintaining data quality standards**

### QualityAssessor - Dataset Quality Assessment (UC-V01)

**Interface Contract:**
```python
class QualityAssessor:
    """
    Assesses dataset quality by determining when steps are bad based on validation spec ranges.
    Satisfies UC-V01: Assess Dataset Quality
    """
    
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager for validation ranges"""
    
    def assess_quality(self, file_path: str) -> QualityAssessmentResult:
        """
        Generate quality report focusing on validation spec compliance.
        
        MUST calculate coverage statistics (subjects, tasks, gait cycles, total strides)
        MUST identify bad strides based on task and phase-specific validation spec range violations
        MUST generate biomechanical quality scores based on stride-level compliance rate
        MUST export quality metrics for tracking over time
        
        Behavioral Contract:
        - Calculates subject, task, and stride-level coverage statistics
        - Identifies individual strides that violate task-specific validation specification ranges
        - Scores quality based on percentage of strides that pass task and phase-specific validation
        - Flags systematic violations and outliers at stride level
        - Generates exportable quality metrics including stride compliance rates and stride pass rates
        
        Returns: QualityAssessmentResult with coverage, stride compliance rates, rejected strides
        """
    
    def identify_bad_strides(self, data: pd.DataFrame, task: str) -> List[Dict]:
        """
        Identify individual strides that violate task-specific validation specifications.
        
        MUST check each stride against task and phase-specific validation spec ranges
        MUST identify specific variables, phases, and values that are out of range
        MUST provide detailed reasons for stride rejection with expected ranges
        
        Args:
            data: Phase-indexed dataset with stride-level data
            task: Task name for task-specific validation ranges
        
        Returns: List of bad strides with violation details, task context, and rejection reasons
        """
    
    def calculate_stride_compliance_score(self, data: pd.DataFrame, task: str) -> float:
        """
        Calculate stride-level compliance score based on task-specific validation specifications.
        
        MUST evaluate compliance at individual stride level 
        MUST use task-specific validation ranges for accurate assessment
        MUST consider phase-specific validation for each stride
        
        Args:
            data: Phase-indexed dataset
            task: Task name for task-specific validation
            
        Returns: Float between 0.0 and 1.0 representing stride compliance rate
        """
```

### DatasetComparator - Multi-Dataset Comparison (UC-V02)

**Interface Contract:**
```python
class DatasetComparator:
    """
    Basic comparison of datasets from different sources.
    Satisfies UC-V02: Compare Multiple Datasets
    
    NOTE: LOW PRIORITY - Simple implementation for now, needs further review
    """
    
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager for references"""
    
    def compare_datasets(self, file_paths: List[str]) -> DatasetComparisonResult:
        """
        Basic statistical comparison of datasets.
        
        MUST perform basic statistical comparison of means and ranges
        MUST generate simple comparison report
        
        Behavioral Contract:
        - Basic statistical comparison (means, ranges)
        - Simple comparison report generation
        
        Returns: DatasetComparisonResult with basic statistics
        """
```

### ValidationSpecManager - Manage Validation Rules (UC-V04) ⭐ CRITICAL COMPONENT

**Interface Contract:**
```python
class ValidationSpecManager:
    """
    Manages validation rules and ranges with interactive editing.
    Satisfies UC-V04: Manage Validation Specifications
    
    ⭐ SUPER IMPORTANT: Core component for maintaining validation standards
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        """Dependencies: ConfigurationManager for specification persistence"""
    
    def edit_validation_ranges(self, task: str, variable: str, new_ranges: Dict, 
                              rationale: str) -> SpecificationUpdateResult:
        """
        Interactive editing of validation ranges with preview.
        
        MUST provide interactive editing of validation ranges with preview
        MUST track changes with rationale and version control
        MUST validate specification changes against test datasets
        MUST generate change documentation for release notes
        
        Behavioral Contract:
        - Validates new ranges against existing data
        - Shows preview of impact on current datasets
        - Records change rationale and timestamp
        - Validates changes don't break existing valid datasets
        - Generates change documentation
        
        Returns: SpecificationUpdateResult with validation status, impact preview
        """
    
    def import_ranges_from_literature(self, literature_source: str, 
                                     ranges_data: Dict) -> ImportResult:
        """
        Import ranges from literature or statistical analysis.
        
        MUST import ranges from literature or statistical analysis
        MUST validate imported ranges for consistency
        """
    
    def validate_spec_changes(self, test_dataset_paths: List[str]) -> SpecValidationResult:
        """Validate specification changes against test datasets"""
    
    def generate_change_documentation(self, changes: List[SpecificationUpdate]) -> str:
        """Generate change documentation for release notes"""
```

### AutomatedFineTuner - Range Optimization (UC-V05) ⭐ IMPORTANT COMPONENT

**Interface Contract:**
```python
class AutomatedFineTuner:
    """
    Automatically tunes validation ranges based on dataset statistics.
    Satisfies UC-V05: Optimize Validation Ranges
    
    ⭐ PRETTY IMPORTANT: Key component for data-driven validation standards
    """
    
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager for current ranges"""
    
    def tune_ranges(self, datasets: List[str], method: str = 'percentile', 
                   confidence: float = 0.95) -> TuningResult:
        """
        Automatically tune validation ranges based on dataset statistics.
        
        MUST analyze current dataset statistics to propose optimal ranges
        MUST use configurable statistical methods (percentile, IQR, z-score)
        MUST compare proposed ranges with current ranges
        MUST provide impact analysis showing validation changes
        MUST support batch processing of multiple datasets
        
        Behavioral Contract:
        - Loads and analyzes multiple datasets
        - Calculates optimal ranges using specified statistical method
        - Compares with current ranges and identifies significant changes
        - Analyzes impact on current dataset validation status
        - Provides detailed recommendations with statistical justification
        
        Returns: TuningResult with optimized ranges, comparison, impact analysis
        """
    
    def apply_tuned_ranges(self, tuning_result: TuningResult, backup: bool = True) -> None:
        """Apply optimized ranges to validation specifications with backup"""
    
    def analyze_tuning_impact(self, tuning_result: TuningResult, 
                             test_datasets: List[str]) -> TuningImpactResult:
        """Analyze impact of proposed range changes on existing datasets"""
```

---

## Medium Priority Components

> **⚠️ NEEDS FURTHER REVIEW - These components are not current focus, specifications require refinement**
> 
> **These components satisfy Medium priority user stories and Administrator requirements for release management**

### ValidationDebugger - Debug Validation Failures (UC-V03)

**Interface Contract:**
```python
class ValidationDebugger:
    """
    Investigates validation failures with deep-dive analysis.
    Satisfies UC-V03: Debug Validation Failures
    """
    
    def __init__(self, spec_manager: SpecificationManager, quality_assessor: QualityAssessor):
        """Dependencies: SpecificationManager, QualityAssessor for context"""
    
    def investigate_failures(self, validation_result: PhaseValidationResult) -> DebugAnalysisResult:
        """
        Deep-dive analysis of failed data points with context.
        
        MUST provide deep-dive analysis of failed data points with context
        MUST create visualization of outliers in biomechanical context
        MUST perform statistical analysis of failure patterns
        MUST provide recommendations for data fixes vs. range adjustments
        MUST generate detailed debugging reports with evidence
        
        Behavioral Contract:
        - Analyzes failed data points with statistical context
        - Visualizes outliers in biomechanical reference frame
        - Identifies systematic vs. random failure patterns
        - Provides evidence-based recommendations
        - Generates detailed debugging reports
        
        Returns: DebugAnalysisResult with failure analysis, recommendations, evidence
        """
    
    def analyze_failure_patterns(self, batch_results: List[PhaseValidationResult]) -> FailurePatternAnalysis:
        """Analyze patterns across multiple validation failures"""
    
    def recommend_fixes(self, debug_result: DebugAnalysisResult) -> FixRecommendations:
        """Generate specific recommendations for addressing validation failures"""
```

### BenchmarkCreator - ML Benchmark Management (UC-A02)

**Interface Contract:**
```python
class BenchmarkCreator:
    """
    Creates ML benchmarks with proper train/test/validation splits.
    Satisfies UC-A02: Create ML Benchmarks
    """
    
    def __init__(self, quality_assessor: QualityAssessor):
        """Dependencies: QualityAssessor for data quality validation"""
    
    def create_benchmark(self, dataset_paths: List[str], benchmark_config: BenchmarkConfig) -> BenchmarkCreationResult:
        """
        Create ML benchmark with scientifically sound splits.
        
        MUST create train/test/validation splits with no data leakage
        MUST ensure statistical balance across splits
        MUST validate benchmark quality and representativeness
        MUST generate benchmark documentation and metadata
        MUST support various ML task types (regression, classification)
        
        Behavioral Contract:
        - Creates subject-level splits to prevent data leakage
        - Ensures statistical balance across demographic variables
        - Validates benchmark quality using established metrics
        - Generates comprehensive benchmark documentation
        - Supports multiple ML task configurations
        
        Returns: BenchmarkCreationResult with split data, metadata, quality metrics
        """
    
    def validate_benchmark_quality(self, benchmark: MLBenchmark) -> BenchmarkQualityResult:
        """Validate benchmark meets scientific standards"""
    
    def export_benchmark(self, benchmark: MLBenchmark, output_dir: str, 
                        format: str = 'parquet') -> BenchmarkExportResult:
        """Export benchmark in standard ML formats"""
```

### DatasetPublisher - Public Release Management (UC-A03)

**Interface Contract:**
```python
class DatasetPublisher:
    """
    Manages preparation and publishing of public dataset releases.
    Satisfies UC-A03: Publish Public Datasets
    """
    
    def __init__(self, quality_assessor: QualityAssessor, validation_spec_manager: ValidationSpecManager):
        """Dependencies: QualityAssessor, ValidationSpecManager for release validation"""
    
    def prepare_release(self, dataset_paths: List[str], release_config: ReleaseConfig) -> ReleasePreparationResult:
        """
        Prepare validated datasets for public release.
        
        MUST validate all datasets meet publication quality standards
        MUST generate comprehensive release documentation
        MUST create release metadata with versioning
        MUST ensure compliance with data sharing standards
        MUST prepare citation and attribution documentation
        
        Behavioral Contract:
        - Validates all datasets against publication quality standards
        - Generates release documentation and changelogs
        - Creates proper versioning and metadata
        - Ensures data sharing compliance
        - Prepares citation and attribution materials
        
        Returns: ReleasePreparationResult with validated datasets, documentation
        """
    
    def publish_release(self, release_preparation: ReleasePreparationResult, 
                       publication_target: str) -> PublicationResult:
        """Publish prepared release to target platform"""
    
    def generate_release_documentation(self, datasets: List[str], 
                                     release_notes: str) -> ReleaseDocumentation:
        """Generate comprehensive release documentation"""
```

---

## Supporting Infrastructure

> **Core infrastructure components that support all user-facing functionality**

### ConfigurationManager - Centralized Configuration

**Interface Contract:**
```python
class ConfigurationManager:
    """
    Centralized configuration management with layered hierarchy.
    Manages standard specifications, user preferences, and runtime settings.
    """
    
    def __init__(self, config_path: str = None):
        """Dependencies: File system access to specification files"""
    
    def get_validation_ranges(self, category: str = None) -> Dict:
        """
        Get validation ranges for specified category.
        
        MUST load ranges from standard specification files
        MUST support layered configuration (user overrides > defaults)
        MUST cache configurations for performance
        MUST parse task and phase-specific ranges from validation_expectations files
        
        Behavioral Contract:
        - Loads from docs/standard_spec/validation_expectations_kinematic.md and kinetic files
        - Parses task-specific tables with phase-specific upper/lower bounds (0%, 25%, 50%, 75%)
        - Supports user configuration overrides
        - Caches parsed configurations for performance
        - Returns structured range data by task, variable, and phase
        
        Returns: Dictionary of validation ranges organized by task, variable, and phase (0%, 25%, 50%, 75%)
        """
    
    def get_task_ranges(self, task: str) -> Dict:
        """
        Get validation ranges for a specific task.
        
        MUST return phase-specific ranges for the specified task
        MUST include both kinematic and kinetic validation ranges
        
        Returns: Dictionary with variable -> phase -> {min, max} structure
        Example: {"knee_flexion_angle_ipsi_rad": {"0%": {"min": -0.1, "max": 0.2}, "25%": {...}}}
        """
    
    def get_variable_range(self, task: str, variable: str, phase: str = None) -> Dict:
        """
        Get validation range for a specific variable in a task.
        
        MUST return phase-specific ranges if phase is specified
        MUST return all phases if phase is None
        
        Args:
            task: Task name (walking, running, etc.)
            variable: Variable name (knee_flexion_angle_ipsi_rad, etc.)
            phase: Optional phase ("0%", "25%", "50%", "75%")
        
        Returns: 
            If phase specified: {"min": value, "max": value}
            If phase None: {"0%": {"min": val, "max": val}, "25%": {...}, ...}
        """
    
    def update_ranges(self, new_ranges: Dict) -> None:
        """Update validation ranges with backup and version control"""
    
    def backup_specifications(self) -> str:
        """Create timestamped backup of current specifications"""
```

### ErrorHandler - Centralized Error Management

**Interface Contract:**
```python
class ErrorHandler:
    """
    Centralized error handling with logging and user-friendly messages.
    """
    
    def __init__(self, verbose: bool = False, log_file: str = None):
        """Dependencies: Logging system configuration"""
    
    def handle_error(self, error: Exception, context: str = None) -> None:
        """
        Handle error with appropriate logging and user feedback.
        
        MUST log technical details for debugging
        MUST provide user-friendly error messages
        MUST support verbose mode for detailed output
        MUST record errors for analysis
        
        Behavioral Contract:
        - Logs technical error details with context
        - Provides user-friendly error translations
        - Supports configurable verbosity levels
        - Records errors for trend analysis
        """
    
    def handle_warning(self, message: str, context: str = None) -> None:
        """Handle warning message with appropriate logging"""
    
    def get_user_friendly_message(self, error: Exception) -> str:
        """Convert technical error to user-friendly message"""
```

### DataLoader - File I/O Operations

**Interface Contract:**
```python
class DataLoader:
    """
    Handles all file loading operations with error handling and validation.
    """
    
    def __init__(self, error_handler: ErrorHandler):
        """Dependencies: ErrorHandler for consistent error reporting"""
    
    def load_parquet(self, file_path: str) -> pd.DataFrame:
        """
        Load parquet file with comprehensive error handling.
        
        MUST validate file existence and accessibility
        MUST handle corrupted files gracefully
        MUST provide specific error messages for different failure modes
        
        Behavioral Contract:
        - Validates file exists and is readable
        - Detects and reports file corruption
        - Handles empty files appropriately
        - Provides specific error context
        
        Returns: Loaded DataFrame
        Raises: FileNotFoundError, DataLoadError with specific context
        """
    
    def load_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Load CSV file with error handling"""
    
    def validate_file_structure(self, file_path: str) -> bool:
        """Quick validation of file accessibility and basic structure"""
```

### DataTransformer - Data Processing and Conversion

**Interface Contract:**
```python
class DataTransformer:
    """
    Handles data transformations including biomechanical convention conversions.
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        """Dependencies: ConfigurationManager for conversion rules"""
    
    def convert_biomech_convention(self, data: pd.DataFrame, target_convention: str) -> pd.DataFrame:
        """
        Convert data between different biomechanical sign conventions.
        
        MUST support standard biomechanical conventions (standard, opensim, etc.)
        MUST preserve data integrity during conversion
        MUST handle missing variables gracefully
        
        Behavioral Contract:
        - Validates target convention is supported
        - Applies appropriate sign/scale conversions
        - Preserves all non-biomechanical columns
        - Maintains data structure and metadata
        
        Returns: DataFrame with converted biomechanical data
        """
    
    def normalize_phase_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure phase data has exactly 150 points per cycle.
        
        MUST ensure exactly 150 points per gait cycle
        MUST preserve data relationships during resampling
        
        Returns: DataFrame with normalized phase indexing
        """
```

---

## Interface Contracts

> **Key behavioral contracts that all components must satisfy**

### Error Handling Contract
- All components MUST use dependency-injected ErrorHandler
- All public methods MUST handle exceptions gracefully
- All errors MUST include sufficient context for debugging
- User-facing errors MUST be translated to friendly messages

### Configuration Contract
- All components MUST use ConfigurationManager for settings
- Configuration changes MUST be validated before application
- All specification updates MUST include backup and rollback capability
- Configuration loading MUST support layered overrides

### Validation Contract
- All validation MUST be deterministic and repeatable
- Validation results MUST include specific failure details
- All validation MUST support batch processing
- Validation reports MUST include both summary and detailed views

### Data Processing Contract
- All data operations MUST preserve data integrity
- File operations MUST validate accessibility before processing
- Data transformations MUST be reversible where possible
- All processing MUST support progress reporting for large datasets

---

## Data Structures

> **Result classes and data containers for component communication**

### Core Result Types

```python
@dataclass
class ConversionResult:
    """Result of dataset conversion operation (External scripts only - for reference)"""
    success: bool
    output_path: str = ""
    report_path: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    # NOTE: This is for reference only - external conversion scripts 
    # may use completely different result formats

@dataclass
class PhaseValidationResult:
    """Result of phase-indexed dataset validation with stride-level filtering and coverage tracking"""
    is_valid: bool  # True if ANY strides pass validation AND basic structure is valid
    file_path: str
    
    # Stride filtering results
    total_strides: int = 0
    valid_strides: int = 0
    invalid_strides: int = 0
    stride_pass_rate: float = 0.0
    kept_stride_ids: List[str] = field(default_factory=list)  # IDs of strides to keep
    deleted_stride_ids: List[str] = field(default_factory=list)  # IDs of strides to delete
    stride_rejection_reasons: Dict[str, List[str]] = field(default_factory=dict)  # stride_id -> reasons
    
    # Coverage and scope tracking
    detected_tasks: List[str] = field(default_factory=list)  # Tasks found in data
    validated_tasks: List[str] = field(default_factory=list)  # Tasks with available specs
    skipped_tasks: List[str] = field(default_factory=list)   # Tasks without specs
    standard_spec_coverage: Dict[str, Dict[str, bool]] = field(default_factory=dict)  # task -> variable -> present
    available_variables: List[str] = field(default_factory=list)  # Variables present in dataset
    missing_standard_variables: List[str] = field(default_factory=list)  # Standard variables missing
    validation_coverage: Dict[str, float] = field(default_factory=dict)  # task -> % of standard variables validated
    validation_scope: str = ""  # "full", "partial", "minimal"
    
    # Reports and outputs
    errors: List[str] = field(default_factory=list)  # Catastrophic errors only
    warnings: List[str] = field(default_factory=list)  # Missing variables, unknown tasks, etc.
    recommendations: List[str] = field(default_factory=list)  # Actionable next steps
    report_path: str = ""  # Path to markdown report
    plot_paths: List[str] = field(default_factory=list)
    validation_summary: Dict = field(default_factory=dict)

@dataclass
class TimeValidationResult:
    """Result of time-indexed dataset validation"""
    is_valid: bool
    file_path: str
    sampling_frequency: float = 0.0
    temporal_issues: List[str] = field(default_factory=list)
    validation_summary: Dict = field(default_factory=dict)
    report_path: str = ""  # Path to markdown report

@dataclass
class StrideFilterResult:
    """Result of stride-level filtering operation with coverage tracking"""
    filtered_data: pd.DataFrame  # DataFrame with only valid strides
    total_strides: int
    valid_strides: int
    invalid_strides: int
    stride_pass_rate: float
    kept_stride_ids: List[str] = field(default_factory=list)
    deleted_stride_ids: List[str] = field(default_factory=list)
    rejection_reasons: Dict[str, List[str]] = field(default_factory=dict)  # stride_id -> reasons
    
    # Coverage tracking
    validated_variables: List[str] = field(default_factory=list)  # Variables that were validated
    skipped_variables: List[str] = field(default_factory=list)   # Variables skipped (missing specs/data)
    validation_coverage_by_task: Dict[str, float] = field(default_factory=dict)  # task -> % variables validated

@dataclass
class QualityAssessmentResult:
    """Result of dataset quality assessment with stride-level analysis"""
    file_path: str
    coverage_stats: Dict = field(default_factory=dict)  # subjects, tasks, total_strides
    stride_pass_rate: float = 0.0  # Based on stride-level filtering results
    stride_compliance_rate: float = 0.0  # Based on stride-level compliance assessment
    quality_scores: Dict = field(default_factory=dict)  # Stride-level quality scores
    rejected_strides: List[Dict] = field(default_factory=list)  # stride info + rejection reasons
    missing_data_patterns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

@dataclass
class TuningResult:
    """Result of automated range tuning"""
    optimized_ranges: Dict
    current_ranges: Dict
    comparison: Dict
    method: str
    confidence: float
    datasets_analyzed: int
    impact_analysis: Dict = field(default_factory=dict)

@dataclass
class PlotGenerationResult:
    """Result of plot generation operation with coverage tracking"""
    success: bool
    generated_plots: Dict[str, List[str]] = field(default_factory=dict)  # plot_type -> [paths]
    output_directory: str = ""
    error_message: str = ""
    
    # Coverage tracking
    requested_variables: List[str] = field(default_factory=list)  # Variables requested for plotting
    plotted_variables: List[str] = field(default_factory=list)    # Variables actually plotted
    skipped_variables: List[str] = field(default_factory=list)    # Variables skipped (missing data/specs)
    coverage_summary: str = ""  # Human-readable coverage summary (e.g., "5/8 kinematic variables plotted")
    warnings: List[str] = field(default_factory=list)  # Warnings about missing variables
```

### Configuration Types

```python
@dataclass
class BenchmarkConfig:
    """Configuration for ML benchmark creation"""
    train_ratio: float = 0.7
    test_ratio: float = 0.2
    validation_ratio: float = 0.1
    split_strategy: str = "subject_level"
    demographic_balance: bool = True
    task_distribution: Dict = field(default_factory=dict)

@dataclass
class ReleaseConfig:
    """Configuration for dataset release preparation"""
    version: str
    release_notes: str
    quality_threshold: float = 0.95
    documentation_required: bool = True
    citation_info: Dict = field(default_factory=dict)
```

---

## CLI Entry Point Specifications

> **Command-line interface specifications for critical user stories**

### Critical Priority CLI Tools

**conversion_generate_phase_dataset.py** (UC-C03)
```bash
# Convert time-indexed to phase-indexed dataset
conversion_generate_phase_dataset.py time_dataset.parquet --output phase_dataset.parquet
```

**validation_dataset_report.py** (UC-C02)
```bash
# Comprehensive validation and quality assessment
validation_dataset_report.py dataset.parquet --output-dir validation_results
# With animated visualizations
validation_dataset_report.py dataset.parquet --output-dir validation_results --generate-gifs
```

### High Priority CLI Tools

**validation_compare_datasets.py** (UC-V01)
```bash
# Compare multiple datasets
validation_compare_datasets.py dataset1.parquet dataset2.parquet --output comparison_report.md
```

**validation_auto_tune_spec.py** (UC-V05)
```bash
# Automatically tune validation ranges
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95
# With visualization
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95 --generate-gifs
```

**validation_manual_tune_spec.py** (UC-V04)
```bash
# Manage validation specifications
validation_manual_tune_spec.py --edit kinematic
# With visualization
validation_manual_tune_spec.py --edit kinematic --generate-gifs
```

**validation_investigate_errors.py** (UC-V03)
```bash
# Debug validation failures
validation_investigate_errors.py dataset.parquet --variable knee_flexion_angle_ipsi_rad
```

---

This interface specification document provides the foundation for implementing all critical components while ensuring they satisfy the user story acceptance criteria. The focus is on behavioral contracts, dependencies, and clear interfaces rather than implementation details.
