# C4 Level 4: Interface Specifications

**Interface contracts, behavioral specifications, and component dependencies for all critical components satisfying user story acceptance criteria.**

---

## Table of Contents

1. [Critical Priority Components](#critical-priority-components)
2. [High Priority Components](#high-priority-components)
3. [Medium Priority Components](#medium-priority-components)
4. [Supporting Infrastructure](#supporting-infrastructure)
5. [Interface Contracts](#interface-contracts)
6. [Data Structures](#data-structures)

---

## Critical Priority Components

> **These components satisfy Critical priority user stories (UC-C02, UC-C03) that are required for all new datasets**
> 
> **Note: UC-C01 (Dataset Conversion) is handled by external scripts that vary widely. 
> We only validate the parquet outputs they produce.**

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
        Run comprehensive validation on phase-indexed dataset.
        
        MUST run comprehensive validation on phase-indexed data
        MUST generate detailed validation report with pass/fail status
        MUST show specific failures with recommended fixes
        MUST create visual validation plots for manual review
        MUST export validation summary for documentation
        
        Behavioral Contract:
        - Validates file accessibility and basic structure
        - Checks phase indexing (exactly 150 points per cycle)
        - Validates biomechanical ranges against specifications
        - Generates markdown report with embedded plot references
        - Provides specific failure details with fix recommendations
        - Creates validation summary suitable for documentation
        
        Returns: PhaseValidationResult with validation status, report path, plot paths
        Raises: ValidationError if file cannot be processed
        """
    
    def validate_batch(self, file_paths: List[str], parallel: bool = True) -> BatchValidationResult:
        """Validate multiple datasets with summary reporting"""
    
    def get_validation_summary(self, results: List[PhaseValidationResult]) -> ValidationSummary:
        """Generate batch validation summary with pass/fail statistics"""
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

### ValidationSpecVisualizer - Generate Validation Specifications (UC-C03)

**Interface Contract:**
```python
class ValidationSpecVisualizer:
    """
    Creates visualizations of validation specifications and validation plots for datasets.
    Satisfies UC-C03: Generate Validation Visualizations
    """
    
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager for validation ranges"""
    
    def generate_validation_plots(self, data: pd.DataFrame, output_dir: str, 
                                 plot_types: List[str] = None) -> PlotGenerationResult:
        """
        Generate static validation plots with data overlaid on specification ranges.
        
        MUST generate static plots showing joint angles and moments across gait phases
        MUST overlay validation ranges on visualizations
        MUST export plots in publication-ready formats
        MUST support batch generation for multiple tasks and subjects
        
        Behavioral Contract:
        - Creates forward kinematics plots at key phases (0%, 25%, 50%, 75%)
        - Generates phase filter plots for kinematic and kinetic variables
        - Overlays validation ranges as reference bands
        - Exports in high-quality PNG format (150 DPI minimum)
        - Organizes plots by task and variable category
        
        Returns: PlotGenerationResult with generated plot paths
        """
    
    def generate_validation_gifs(self, data: pd.DataFrame, output_dir: str) -> GifGenerationResult:
        """
        Generate animated GIFs showing walking patterns.
        
        MUST create animated GIFs showing walking patterns
        MUST show biomechanical progression through gait cycle
        
        Returns: GifGenerationResult with generated animation paths
        """
    
    def generate_validation_spec_plots(self, tasks: List[str], output_dir: str) -> PlotGenerationResult:
        """
        Generate plots showing validation specification ranges without data.
        
        MUST visualize validation ranges for specified tasks
        MUST show acceptable biomechanical ranges for each variable
        MUST create reference plots for specification documentation
        
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
        
        MUST calculate coverage statistics (subjects, tasks, gait cycles)
        MUST identify bad steps based on validation spec range violations
        MUST generate biomechanical quality scores based on spec compliance
        MUST export quality metrics for tracking over time
        
        Behavioral Contract:
        - Calculates subject, task, and cycle coverage
        - Identifies steps that violate validation specification ranges
        - Scores quality based on percentage of steps within spec ranges
        - Flags systematic violations and outliers
        - Generates exportable quality metrics
        
        Returns: QualityAssessmentResult with coverage, spec compliance scores, bad steps
        """
    
    def identify_bad_steps(self, data: pd.DataFrame, task: str) -> List[Dict]:
        """
        Identify individual steps that violate validation specifications.
        
        MUST check each step against validation spec ranges
        MUST identify specific variables and values that are out of range
        
        Returns: List of bad steps with violation details
        """
    
    def calculate_spec_compliance_score(self, data: pd.DataFrame) -> float:
        """Calculate overall compliance score with validation specifications"""
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
        
        Behavioral Contract:
        - Loads from docs/standard_spec/ markdown files
        - Supports user configuration overrides
        - Caches parsed configurations
        - Returns structured range data by task and variable
        
        Returns: Dictionary of validation ranges organized by task and variable
        """
    
    def get_task_ranges(self, task: str) -> Dict:
        """Get validation ranges for a specific task"""
    
    def get_variable_range(self, task: str, variable: str) -> Dict:
        """Get validation range for a specific variable in a task"""
    
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
    """Result of phase-indexed dataset validation"""
    is_valid: bool
    file_path: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
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
class QualityAssessmentResult:
    """Result of dataset quality assessment"""
    file_path: str
    coverage_stats: Dict = field(default_factory=dict)
    quality_scores: Dict = field(default_factory=dict)
    missing_data_patterns: List[str] = field(default_factory=list)
    outliers: List[Dict] = field(default_factory=list)
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
    """Result of plot generation operation"""
    success: bool
    generated_plots: Dict[str, List[str]] = field(default_factory=dict)
    output_directory: str = ""
    error_message: str = ""
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

**convert_dataset.py** (UC-C01) - External Scripts Only
```bash
# NOTE: Conversion scripts are provided by external collaborators and vary widely
# We do not provide standardized conversion interfaces - only validation of outputs
# Example external conversion scripts might look like:
python external_matlab_converter.py input.mat output.parquet
python collaborator_csv_converter.py input.csv output.parquet --custom-mapping
```

**validate_phase_data.py** (UC-C02)
```bash
# Validate phase-indexed dataset
validate_phase_data.py dataset.parquet --output-dir validation_results --plots
```

**validate_time_data.py** (UC-C02)
```bash
# Validate time-indexed dataset
validate_time_data.py dataset.parquet --output-dir validation_results
```

**generate_validation_plots.py** (UC-C03)
```bash
# Generate validation plots and specification visualizations
generate_validation_plots.py --data dataset.parquet --output plots/ --types forward_kinematics
# Generate validation specification plots (without data)
generate_validation_plots.py --specs-only --tasks walking running --output spec_plots/
```

### High Priority CLI Tools

**assess_quality.py** (UC-V01)
```bash
# Assess dataset quality
assess_quality.py dataset.parquet --export-metrics quality_timeline.json
```

**compare_datasets.py** (UC-V02)
```bash
# Compare multiple datasets
compare_datasets.py dataset1.parquet dataset2.parquet --output comparison_report.html
```

**auto_tune_ranges.py** (UC-V05)
```bash
# Automatically tune validation ranges
auto_tune_ranges.py data/*.parquet --method percentile --confidence 0.95 --apply
```

**manage_validation_specs.py** (UC-V04)
```bash
# Manage validation specifications
manage_validation_specs.py --edit walking knee_flexion_angle_ipsi_rad --interactive
```

---

This interface specification document provides the foundation for implementing all critical components while ensuring they satisfy the user story acceptance criteria. The focus is on behavioral contracts, dependencies, and clear interfaces rather than implementation details.
