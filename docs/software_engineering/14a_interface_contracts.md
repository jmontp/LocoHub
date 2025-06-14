# Interface Contracts

**Method signatures and behavioral contracts for all critical components.**

## PhaseValidator - Phase-Indexed Dataset Validation

```python
class PhaseValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler):
        """Dependencies: SpecificationManager, ErrorHandler"""
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True) -> PhaseValidationResult:
        """
        Run comprehensive validation on phase-indexed dataset with stride-level filtering.
        
        MUST perform stride-level validation and filtering
        MUST show which strides are kept vs deleted in validation report
        MUST report stride pass rate as quality metric
        MUST only fail dataset if NO strides pass validation AND basic structure is invalid
        MUST create visual validation plots for manual review
        MUST export validation summary with stride statistics
        MUST use task-specific and phase-specific validation ranges
        MUST read tasks from data['task'] column
        MUST validate against known tasks from feature_constants
        MUST handle unknown tasks gracefully
        """
    
    def filter_valid_strides(self, data: pd.DataFrame, available_variables: List[str] = None) -> StrideFilterResult:
        """
        Filter dataset to keep only valid strides based on task-specific validation specifications.
        
        MUST identify valid vs invalid strides using task and phase-specific ranges
        MUST check each stride against available validation specifications
        MUST validate at 0%, 25%, 50%, 75% phases for each stride
        MUST provide detailed reasons for stride rejection
        MUST return filtered dataset with only valid strides
        """
    
    def get_available_tasks(self, data: pd.DataFrame) -> List[str]:
        """Get unique tasks from dataset, filtered to known standard tasks."""
    
    def analyze_standard_spec_coverage(self, data: pd.DataFrame) -> Dict[str, Dict[str, bool]]:
        """Analyze which standard specification variables are available in the dataset."""
    
    def validate_batch(self, file_paths: List[str], parallel: bool = True) -> BatchValidationResult:
        """Validate multiple datasets with stride-level summary reporting"""
```

## TimeValidator - Time-Indexed Dataset Validation

```python
class TimeValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler):
        """Dependencies: SpecificationManager, ErrorHandler"""
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True) -> TimeValidationResult:
        """
        Run comprehensive validation on time-indexed dataset.
        
        MUST validate sampling frequency consistency
        MUST check temporal data integrity
        MUST validate biomechanical ranges where applicable
        """
    
    def check_temporal_integrity(self, data: pd.DataFrame) -> TemporalIntegrityResult:
        """Validate time series consistency and gaps"""
    
    def validate_sampling_frequency(self, data: pd.DataFrame) -> SamplingValidationResult:
        """Check sampling rate consistency across subjects and tasks"""
```

## ValidationSpecVisualizer - Validation Plot Generation

```python
class ValidationSpecVisualizer:
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager"""
    
    def generate_validation_plots(self, file_path: str, output_dir: str) -> ValidationPlotResult:
        """
        Generate static plots showing joint angles and moments across gait phases.
        
        MUST generate plots for all available tasks
        MUST overlay validation ranges on visualizations
        MUST export plots in publication-ready formats
        MUST support batch generation for multiple subjects
        """
    
    def generate_validation_gifs(self, file_path: str, output_dir: str) -> ValidationGifResult:
        """Create animated GIFs showing walking patterns with validation overlays"""
    
    def create_phase_range_plots(self, task: str, output_path: str) -> PlotResult:
        """Generate phase-specific range visualization for a task"""
```

## QualityAssessor - Dataset Quality Assessment

```python
class QualityAssessor:
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager"""
    
    def assess_dataset_quality(self, file_path: str) -> QualityAssessmentResult:
        """
        Generate comprehensive quality reports for datasets.
        
        MUST calculate coverage statistics (subjects, tasks, gait cycles)
        MUST identify missing data patterns and outliers
        MUST generate biomechanical plausibility scores
        MUST compare against population norms from literature
        MUST export quality metrics for tracking over time
        """
    
    def calculate_coverage_statistics(self, data: pd.DataFrame) -> CoverageStats:
        """Calculate subject, task, and cycle coverage metrics"""
    
    def identify_outliers(self, data: pd.DataFrame) -> OutlierAnalysis:
        """Identify outlier patterns and data quality issues"""
```

## DatasetComparator - Multi-Dataset Comparison

```python
class DatasetComparator:
    def __init__(self, spec_manager: SpecificationManager):
        """Dependencies: SpecificationManager"""
    
    def compare_datasets(self, file_paths: List[str]) -> ComparisonResult:
        """
        Systematically compare datasets from different sources.
        
        MUST perform statistical comparison of means, distributions, and ranges
        MUST generate visual comparison plots showing overlays and differences
        MUST identify systematic biases between data sources
        MUST generate compatibility reports for dataset combinations
        MUST recommend harmonization strategies for inconsistencies
        """
    
    def statistical_comparison(self, datasets: List[pd.DataFrame]) -> StatisticalComparisonResult:
        """Compare statistical properties across datasets"""
    
    def generate_comparison_plots(self, datasets: List[pd.DataFrame], output_dir: str) -> ComparisonPlotResult:
        """Generate visual comparison plots"""
```

## ValidationSpecManager - Validation Rules Management

```python
class ValidationSpecManager:
    def __init__(self, config_manager: ConfigurationManager):
        """Dependencies: ConfigurationManager"""
    
    def get_validation_ranges(self, task: str, phase: int = None) -> ValidationRanges:
        """
        Get validation ranges for specific task and optional phase.
        
        MUST retrieve task-specific ranges from specifications
        MUST support phase-specific ranges where available
        MUST handle missing specifications gracefully
        """
    
    def update_validation_ranges(self, task: str, variable: str, ranges: Dict) -> UpdateResult:
        """
        Edit and update validation rules and ranges.
        
        MUST provide interactive editing with preview
        MUST support importing ranges from literature or statistical analysis
        MUST track changes with rationale and version control
        MUST validate specification changes against test datasets
        """
    
    def load_specifications(self, spec_file: str) -> SpecificationLoadResult:
        """Load validation specifications from markdown files"""
    
    def export_specifications(self, output_path: str) -> ExportResult:
        """Export current specifications to file"""
```

## AutomatedFineTuner - Range Optimization

```python
class AutomatedFineTuner:
    def __init__(self, spec_manager: ValidationSpecManager):
        """Dependencies: ValidationSpecManager"""
    
    def auto_tune_ranges(self, datasets: List[str], method: str = "percentile") -> TuningResult:
        """
        Automatically tune validation ranges based on current dataset statistics.
        
        MUST support multiple statistical methods for range calculation
        MUST preview changes before applying with impact analysis
        MUST preserve manual adjustments and exceptions
        MUST generate tuning reports with statistical justification
        MUST integrate with specification management workflow
        """
    
    def calculate_optimal_ranges(self, data: pd.DataFrame, method: str) -> OptimalRanges:
        """Calculate statistically optimal ranges using specified method"""
    
    def preview_range_changes(self, current_ranges: Dict, proposed_ranges: Dict) -> ChangePreview:
        """Preview impact of proposed range changes"""
```

## BenchmarkCreator - ML Benchmark Management

```python
class BenchmarkCreator:
    def __init__(self, data_loader: DataLoader):
        """Dependencies: DataLoader"""
    
    def create_ml_benchmarks(self, file_paths: List[str], split_strategy: str) -> BenchmarkResult:
        """
        Create standardized train/test/validation splits from quality datasets.
        
        MUST ensure stratified sampling with no subject leakage between splits
        MUST support multiple split strategies (temporal, subject-based, task-based)
        MUST generate metadata describing split composition and balance
        MUST export in ML-ready formats (scikit-learn, PyTorch, TensorFlow)
        MUST create benchmark documentation with baseline performance metrics
        """
    
    def stratified_split(self, data: pd.DataFrame, strategy: str) -> DataSplits:
        """Create stratified data splits with no leakage"""
    
    def export_ml_formats(self, splits: DataSplits, output_dir: str) -> ExportResult:
        """Export data splits in multiple ML framework formats"""
```

## Supporting Infrastructure

### ConfigurationManager
```python
class ConfigurationManager:
    def get_config(self, key: str) -> Any:
        """Get configuration value for key"""
    
    def update_config(self, key: str, value: Any) -> None:
        """Update configuration value"""
    
    def load_from_file(self, config_path: str) -> None:
        """Load configuration from file"""
```

### ErrorHandler
```python
class ErrorHandler:
    def handle_validation_error(self, error: ValidationError) -> ErrorResponse:
        """Handle validation errors with appropriate response"""
    
    def log_error(self, error: Exception, context: Dict) -> None:
        """Log error with context information"""
    
    def create_error_report(self, errors: List[Exception]) -> ErrorReport:
        """Create comprehensive error report"""
```

### DataLoader
```python
class DataLoader:
    def load_parquet(self, file_path: str) -> pd.DataFrame:
        """Load parquet file with error handling"""
    
    def save_parquet(self, data: pd.DataFrame, file_path: str) -> None:
        """Save DataFrame to parquet with validation"""
    
    def validate_file_access(self, file_path: str) -> AccessResult:
        """Validate file accessibility and permissions"""
```