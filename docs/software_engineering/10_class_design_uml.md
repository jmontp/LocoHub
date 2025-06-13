# UML Class Diagrams - Core Components

## DatasetConverter Class Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class DatasetConverter {
        -FormatDetector format_detector
        -VariableMapper variable_mapper
        -QualityValidator quality_validator
        -MetadataManager metadata_manager
        -ProgressReporter progress_reporter
        +convert_dataset(input_path: str, output_dir: str, options: ConversionOptions) ConversionResult
        +detect_format(file_path: str) FormatType
        +validate_conversion(result: ConversionResult) bool
        -orchestrate_workflow(input_path: str, options: ConversionOptions) ConversionResult
        -handle_conversion_error(error: Exception) None
    }
    
    class FormatDetector {
        -Dict~FormatType, FormatHandler~ handlers
        +detect_format(file_path: str) FormatType
        +get_handler(format_type: FormatType) FormatHandler
        +validate_format(file_path: str, expected_format: FormatType) bool
        -analyze_file_structure(file_path: str) FormatInfo
        -extract_metadata(file_path: str) Dict
    }
    
    class VariableMapper {
        -FeatureConstants feature_constants
        -Dict~str, str~ custom_mappings
        +map_variables(input_vars: List[str], format_type: FormatType) VariableMapping
        +get_standard_names(input_vars: List[str]) Dict~str, str~
        +validate_mapping(mapping: VariableMapping) List[ValidationIssue]
        -load_format_mappings(format_type: FormatType) Dict
        -handle_unmapped_variables(variables: List[str]) List[str]
    }
    
    class QualityValidator {
        -ValidationSpecs validation_specs
        -float min_quality_threshold
        +validate_basic_quality(data: LocomotionData) QualityResult
        +check_data_completeness(data: LocomotionData) CompletenessResult
        +assess_signal_quality(data: LocomotionData) SignalQualityResult
        -calculate_quality_score(results: List[QualityMetric]) float
        -generate_quality_report(results: List[QualityResult]) QualityReport
    }
    
    class ConversionResult {
        +bool success
        +str input_path
        +str output_path
        +FormatType detected_format
        +VariableMapping variable_mapping
        +QualityResult quality_assessment
        +List~ValidationIssue~ warnings
        +List~Exception~ errors
        +DateTime processing_time
        +Dict metadata
    }
    
    class ConversionOptions {
        +Optional~FormatType~ force_format
        +Optional~str~ custom_mapping_file
        +PhaseCalculationMethod phase_method
        +ValidationLevel validation_level
        +ReportFormat report_format
        +bool overwrite_existing
        +bool generate_plots
        +Dict~str, Any~ advanced_options
    }
    
    DatasetConverter *-- FormatDetector
    DatasetConverter *-- VariableMapper
    DatasetConverter *-- QualityValidator
    DatasetConverter --> ConversionResult
    DatasetConverter --> ConversionOptions
    VariableMapper --> FeatureConstants
    QualityValidator --> ValidationSpecs
```

---

## PhaseValidator Class Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class PhaseValidator {
        -SpecificationManager spec_manager
        -RangeValidator range_validator
        -StructureValidator structure_validator
        -ConsistencyValidator consistency_validator
        -StatisticalAnalyzer statistical_analyzer
        +validate_dataset(dataset_path: str, mode: ValidationMode) ValidationResults
        +run_structural_validation(data: LocomotionData) StructureResults
        +run_range_validation(data: LocomotionData, specs: ValidationSpecs) RangeResults
        +run_consistency_validation(data: LocomotionData) ConsistencyResults
        -aggregate_results(results: List[ValidationResult]) ValidationSummary
        -generate_comprehensive_report(results: ValidationResults) ValidationReport
    }
    
    class RangeValidator {
        -Dict~str, BiomechanicalRange~ range_specs
        -List~int~ phase_points
        +validate_ranges(data: LocomotionData, specs: ValidationSpecs) RangeResults
        +check_phase_specific_ranges(data: PhaseData, phase: int, specs: PhaseSpecs) PhaseRangeResults
        +identify_outliers(values: ndarray, range_spec: BiomechanicalRange) List[OutlierInfo]
        -calculate_range_violations(values: ndarray, min_val: float, max_val: float) List[Violation]
        -generate_range_statistics(violations: List[Violation]) RangeStatistics
    }
    
    class StructureValidator {
        -int expected_phase_points
        -List~str~ required_variables
        +validate_structure(data: LocomotionData) StructureResults
        +check_phase_continuity(data: PhaseData) ContinuityResults
        +validate_data_types(data: LocomotionData) TypeResults
        +verify_required_variables(data: LocomotionData) VariableResults
        -check_gait_cycle_consistency(data: PhaseData) ConsistencyCheck
        -validate_phase_indexing(data: PhaseData) IndexingResults
    }
    
    class ConsistencyValidator {
        -List~ConsistencyRule~ consistency_rules
        +validate_cross_variable_consistency(data: LocomotionData) ConsistencyResults
        +check_biomechanical_relationships(data: LocomotionData) RelationshipResults
        +validate_temporal_consistency(data: PhaseData) TemporalResults
        -apply_consistency_rule(rule: ConsistencyRule, data: LocomotionData) RuleResult
        -check_joint_angle_relationships(data: LocomotionData) AngleConsistencyResults
    }
    
    class ValidationResults {
        +bool overall_pass
        +ValidationSummary summary
        +StructureResults structure_results
        +RangeResults range_results
        +ConsistencyResults consistency_results
        +List~ValidationWarning~ warnings
        +List~ValidationError~ errors
        +Dict~str, Any~ statistics
        +DateTime validation_timestamp
    }
    
    class BiomechanicalRange {
        +float min_value
        +float max_value
        +str validation_method
        +Optional~float~ typical_value
        +RangeSource source
        +str units
        +bool is_phase_specific
        +validate_value(value: float) bool
        +get_violation_severity(value: float) SeverityLevel
    }
    
    PhaseValidator *-- RangeValidator
    PhaseValidator *-- StructureValidator
    PhaseValidator *-- ConsistencyValidator
    PhaseValidator --> ValidationResults
    RangeValidator --> BiomechanicalRange
    RangeValidator --> SpecificationManager
```

---

## SpecificationManager Class Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class SpecificationManager {
        -str specs_directory
        -Dict~ValidationMode, ValidationSpecs~ loaded_specs
        -MarkdownParser parser
        +read_validation_data(file_path: str, mode: ValidationMode) Dict
        +write_validation_data(file_path: str, data: Dict, mode: ValidationMode) None
        +load_validation_specs(mode: ValidationMode) ValidationSpecs
        +update_validation_ranges(updates: Dict, mode: ValidationMode) None
        +get_phase_specifications(task: str, phase: int, mode: ValidationMode) PhaseSpecs
        -parse_markdown_file(file_path: str, mode: ValidationMode) ParsedSpecs
        -validate_specification_format(specs: Dict) List[FormatError]
    }
    
    class MarkdownParser {
        -List~str~ supported_modes
        -List~int~ standard_phases
        +parse_validation_markdown(content: str, mode: ValidationMode) ParsedData
        +generate_validation_markdown(data: Dict, mode: ValidationMode) str
        +extract_table_data(markdown_content: str) List[TableRow]
        +format_table_data(data: Dict) str
        -parse_table_row(row: str) TableRow
        -validate_table_structure(tables: List[Table]) bool
        -format_biomechanical_range(variable: str, range_data: RangeData) str
    }
    
    class ValidationSpecs {
        +ValidationMode mode
        +Dict~str, TaskSpecs~ task_specifications
        +Dict~str, BiomechanicalRange~ global_ranges
        +DateTime last_updated
        +str source_file
        +get_task_specs(task: str) TaskSpecs
        +get_variable_range(variable: str, task: str, phase: int) BiomechanicalRange
        +update_range(variable: str, task: str, phase: int, new_range: BiomechanicalRange) None
        +validate_specs_consistency() List[ConsistencyIssue]
    }
    
    class TaskSpecs {
        +str task_name
        +Dict~int, PhaseSpecs~ phase_specifications
        +Dict~str, BiomechanicalRange~ task_global_ranges
        +get_phase_specs(phase: int) PhaseSpecs
        +get_all_variables() List[str]
        +update_phase_range(phase: int, variable: str, range: BiomechanicalRange) None
    }
    
    class PhaseSpecs {
        +int phase_percent
        +Dict~str, BiomechanicalRange~ variable_ranges
        +get_variable_range(variable: str) BiomechanicalRange
        +set_variable_range(variable: str, range: BiomechanicalRange) None
        +get_all_variables() List[str]
        +validate_phase_consistency() bool
    }
    
    SpecificationManager *-- MarkdownParser
    SpecificationManager --> ValidationSpecs
    ValidationSpecs *-- TaskSpecs
    TaskSpecs *-- PhaseSpecs
    PhaseSpecs --> BiomechanicalRange
```

---

## AutomatedTuner Class Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class AutomatedTuner {
        -LocomotionData dataset
        -ValidationMode mode
        -StatisticalMethod method
        -FeatureConstants feature_constants
        -SpecificationManager spec_manager
        +calculate_statistical_ranges(method: StatisticalMethod) Dict
        +tune_validation_ranges(current_specs: ValidationSpecs) TuningResults
        +generate_tuning_report(results: TuningResults) TuningReport
        +apply_tuning_results(results: TuningResults) None
        -extract_variable_data(variable: str, task: str, phase: int) ndarray
        -calculate_percentile_ranges(data: ndarray, percentile: float) BiomechanicalRange
        -calculate_statistical_bounds(data: ndarray, method: StatisticalMethod) BiomechanicalRange
    }
    
    class StatisticalMethod {
        <<enumeration>>
        PERCENTILE_95
        PERCENTILE_99
        STANDARD_DEVIATION_2
        STANDARD_DEVIATION_3
        INTERQUARTILE_RANGE
        MEDIAN_ABSOLUTE_DEVIATION
        CUSTOM
    }
    
    class TuningResults {
        +StatisticalMethod method_used
        +Dict~str, RangeTuningResult~ variable_results
        +TuningSummary summary
        +List~TuningWarning~ warnings
        +DateTime tuning_timestamp
        +get_updated_ranges() Dict
        +get_significant_changes() List[RangeChange]
        +export_for_review() Dict
    }
    
    class RangeTuningResult {
        +str variable_name
        +str task_name
        +int phase_percent
        +BiomechanicalRange original_range
        +BiomechanicalRange suggested_range
        +StatisticalSummary data_statistics
        +float confidence_level
        +bool recommended_for_update
        +str change_rationale
    }
    
    class StatisticalSummary {
        +int sample_size
        +float mean
        +float median
        +float std_deviation
        +float min_value
        +float max_value
        +float percentile_05
        +float percentile_95
        +float percentile_99
        +List~float~ outliers
        +calculate_range_coverage(range: BiomechanicalRange) float
        +assess_distribution_normality() NormalityTest
    }
    
    class TuningSummary {
        +int total_variables_analyzed
        +int ranges_suggested_for_update
        +int ranges_within_tolerance
        +int insufficient_data_variables
        +float overall_confidence_score
        +List~str~ high_impact_changes
        +Dict~str, int~ changes_by_category
    }
    
    AutomatedTuner --> StatisticalMethod
    AutomatedTuner --> TuningResults
    AutomatedTuner --> FeatureConstants
    AutomatedTuner --> SpecificationManager
    TuningResults *-- RangeTuningResult
    TuningResults --> TuningSummary
    RangeTuningResult --> StatisticalSummary
    RangeTuningResult --> BiomechanicalRange
```

---

## BenchmarkCreator Class Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class BenchmarkCreator {
        -DatasetSelector dataset_selector
        -SplitStrategy split_strategy
        -FeatureExtractor feature_extractor
        -BenchmarkValidator benchmark_validator
        +create_benchmark(datasets: List[str], config: BenchmarkConfig) BenchmarkSuite
        +select_quality_datasets(datasets: List[str], min_quality: float) List[str]
        +create_data_splits(data: LocomotionData, strategy: SplitConfig) DataSplits
        +generate_ml_features(data: LocomotionData, feature_config: FeatureConfig) MLFeatures
        +validate_benchmark_quality(benchmark: BenchmarkSuite) BenchmarkValidation
        -ensure_no_data_leakage(splits: DataSplits) LeakageAnalysis
    }
    
    class SplitStrategy {
        +SplitType strategy_type
        +SplitConfig configuration
        +create_splits(data: LocomotionData, config: SplitConfig) DataSplits
        +validate_split_balance(splits: DataSplits) BalanceAnalysis
        +detect_data_leakage(splits: DataSplits) LeakageReport
        -apply_subject_split(data: LocomotionData, ratios: SplitRatios) SubjectSplits
        -apply_temporal_split(data: LocomotionData, ratios: SplitRatios) TemporalSplits
        -apply_stratified_split(data: LocomotionData, ratios: SplitRatios) StratifiedSplits
    }
    
    class FeatureExtractor {
        -FeatureConfig feature_configuration
        -List~str~ supported_ml_frameworks
        +extract_features(data: LocomotionData, config: FeatureConfig) MLFeatures
        +create_sklearn_format(features: MLFeatures) SklearnDataset
        +create_pytorch_format(features: MLFeatures) TorchDataset
        +create_tensorflow_format(features: MLFeatures) TFDataset
        +normalize_features(features: MLFeatures, method: NormalizationMethod) MLFeatures
        -handle_missing_data(features: MLFeatures, strategy: ImputationStrategy) MLFeatures
        -extract_biomechanical_features(data: LocomotionData) BiomechanicalFeatures
    }
    
    class BenchmarkValidator {
        -List~ValidationRule~ validation_rules
        +validate_benchmark_suite(benchmark: BenchmarkSuite) BenchmarkValidation
        +check_demographic_balance(splits: DataSplits) DemographicAnalysis
        +assess_split_quality(splits: DataSplits) SplitQualityReport
        +detect_data_leakage(splits: DataSplits) LeakageAnalysis
        -validate_feature_consistency(features: MLFeatures) FeatureValidation
        -check_label_distribution(splits: DataSplits) LabelDistribution
    }
    
    class BenchmarkSuite {
        +str benchmark_id
        +DataSplits data_splits
        +MLFeatures features
        +BenchmarkMetadata metadata
        +BaselineResults baseline_performance
        +BenchmarkDocumentation documentation
        +export_framework_format(framework: MLFramework) FrameworkDataset
        +get_split_statistics() SplitStatistics
        +validate_integrity() IntegrityReport
    }
    
    class DataSplits {
        +LocomotionData training_set
        +LocomotionData validation_set
        +LocomotionData test_set
        +SplitMetadata metadata
        +get_split_sizes() Dict~str, int~
        +get_demographic_distribution() DemographicStats
        +check_subject_overlap() bool
        +export_split_info() Dict
    }
    
    class MLFeatures {
        +ndarray feature_matrix
        +List~str~ feature_names
        +ndarray labels
        +List~str~ label_names
        +FeatureMetadata metadata
        +normalize(method: NormalizationMethod) MLFeatures
        +select_features(selector: FeatureSelector) MLFeatures
        +export_format(framework: MLFramework) FrameworkDataset
    }
    
    BenchmarkCreator *-- DatasetSelector
    BenchmarkCreator *-- SplitStrategy
    BenchmarkCreator *-- FeatureExtractor
    BenchmarkCreator *-- BenchmarkValidator
    BenchmarkCreator --> BenchmarkSuite
    SplitStrategy --> DataSplits
    FeatureExtractor --> MLFeatures
    BenchmarkSuite *-- DataSplits
    BenchmarkSuite *-- MLFeatures
```

---

## Shared Core Classes

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class FeatureConstants {
        +Dict~str, VariableDefinition~ kinematic_variables
        +Dict~str, VariableDefinition~ kinetic_variables
        +List~str~ standard_tasks
        +List~int~ standard_phases
        +get_variable_definition(variable_name: str) VariableDefinition
        +get_variable_units(variable_name: str) str
        +get_variables_by_type(variable_type: VariableType) List[str]
        +validate_variable_name(name: str) bool
        +get_standard_mapping(source_name: str) Optional[str]
    }
    
    class VariableDefinition {
        +str standard_name
        +str description
        +str units
        +VariableType type
        +List~str~ alternative_names
        +BiomechanicalRange typical_range
        +bool is_required
        +get_display_name() str
        +matches_alternative(name: str) bool
        +validate_units(units: str) bool
    }
    
    class LocomotionData {
        +DataFrame data
        +DataMetadata metadata
        +from_parquet(file_path: str) LocomotionData
        +filter_by_task(task: str) LocomotionData
        +filter_by_subject(subject_id: str) LocomotionData
        +get_phase_data(phases: List[int]) PhaseData
        +get_time_data() TimeData
        +get_available_tasks() List[str]
        +get_available_subjects() List[str]
        +validate_schema() bool
        +calculate_statistics() DataStatistics
        +export_to_parquet(file_path: str) None
    }
    
    class ProgressReporter {
        +start_operation(operation: str, total_steps: int) None
        +update_progress(step: int, message: str) None
        +complete_operation(success: bool, summary: str) None
        +log_warning(message: str) None
        +log_error(error: Exception) None
        +get_progress_percentage() float
        +set_quiet_mode(quiet: bool) None
    }
    
    class ConfigurationManager {
        +Dict~str, Any~ default_config
        +load_config(config_file: str) Dict
        +save_config(config: Dict, file_path: str) None
        +get_setting(key: str, default: Any) Any
        +update_setting(key: str, value: Any) None
        +validate_configuration(config: Dict) List[ConfigError]
        +merge_configurations(base: Dict, override: Dict) Dict
    }
    
    FeatureConstants --> VariableDefinition
    LocomotionData --> DataMetadata
```

---

## Interface and Abstract Base Classes

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class FormatHandler {
        <<abstract>>
        +detect_format(file_path: str) bool*
        +load_data(file_path: str) RawData*
        +extract_metadata(file_path: str) Dict*
        +validate_format(file_path: str) FormatValidation*
        +get_supported_extensions() List[str]*
    }
    
    class MatlabHandler {
        +detect_format(file_path: str) bool
        +load_data(file_path: str) RawData
        +extract_metadata(file_path: str) Dict
        +validate_format(file_path: str) FormatValidation
        +get_supported_extensions() List[str]
        -load_mat_file(file_path: str) Dict
        -extract_variable_info(mat_data: Dict) VariableInfo
    }
    
    class CSVHandler {
        +detect_format(file_path: str) bool
        +load_data(file_path: str) RawData
        +extract_metadata(file_path: str) Dict
        +validate_format(file_path: str) FormatValidation
        +get_supported_extensions() List[str]
        -infer_csv_structure(file_path: str) CSVStructure
        -validate_csv_headers(headers: List[str]) bool
    }
    
    class ValidationRule {
        <<abstract>>
        +apply_rule(data: LocomotionData) RuleResult*
        +get_rule_description() str*
        +get_severity_level() SeverityLevel*
        +is_applicable(data: LocomotionData) bool*
    }
    
    class RangeValidationRule {
        +BiomechanicalRange range_specification
        +apply_rule(data: LocomotionData) RuleResult
        +get_rule_description() str
        +get_severity_level() SeverityLevel
        +is_applicable(data: LocomotionData) bool
        -check_value_range(values: ndarray) List[Violation]
    }
    
    class ConsistencyValidationRule {
        +List~str~ dependent_variables
        +apply_rule(data: LocomotionData) RuleResult
        +get_rule_description() str
        +get_severity_level() SeverityLevel
        +is_applicable(data: LocomotionData) bool
        -check_variable_consistency(data: LocomotionData) ConsistencyResult
    }
    
    FormatHandler <|-- MatlabHandler
    FormatHandler <|-- CSVHandler
    ValidationRule <|-- RangeValidationRule
    ValidationRule <|-- ConsistencyValidationRule
```

These UML class diagrams provide comprehensive specifications for implementing the core components of the locomotion data standardization system, with clear inheritance hierarchies, composition relationships, and method signatures that can drive test-driven development.