# UML Class Diagrams - Core Component Structure

**Fresh UML class diagrams reflecting the enhanced interface specifications and component architecture.**

---

## Critical Priority Components

### PhaseValidator Component Structure

```mermaid
classDiagram
    class PhaseValidator {
        -spec_manager: ValidationSpecManager
        -error_handler: ErrorHandler
        +validate_dataset(file_path: str, generate_plots: bool) PhaseValidationResult
        +get_available_tasks(data: DataFrame) List[str]
        +analyze_standard_spec_coverage(data: DataFrame) Dict
        +filter_valid_strides(data: DataFrame, available_variables: List[str]) StrideFilterResult
        +validate_batch(file_paths: List[str], parallel: bool) BatchValidationResult
        +get_validation_summary(results: List) ValidationSummary
    }

    class TaskDetector {
        -feature_constants: FeatureConstants
        +detect_tasks(data: DataFrame) List[str]
        +validate_tasks_against_known(tasks: List[str]) Tuple[List[str], List[str]]
        +handle_unknown_tasks(unknown_tasks: List[str]) List[str]
    }

    class CoverageAnalyzer {
        -feature_constants: FeatureConstants
        +analyze_coverage(data: DataFrame, tasks: List[str]) Dict
        +calculate_coverage_percentage(available: List[str], standard: List[str]) float
        +identify_missing_variables(data: DataFrame, tasks: List[str]) List[str]
        +determine_validation_scope(coverage_percentage: float) str
    }

    class StrideFilter {
        -range_provider: RangeProvider
        +filter_strides_by_task(data: DataFrame, task: str, available_variables: List[str]) StrideFilterResult
        +validate_stride_against_ranges(stride_data: DataFrame, task: str, ranges: Dict) bool
        +generate_rejection_reasons(stride_data: DataFrame, violations: List) List[str]
        +calculate_stride_pass_rate(total: int, valid: int) float
    }

    class PhaseStructureValidator {
        +validate_150_points_per_cycle(data: DataFrame) bool
        +check_phase_column_integrity(data: DataFrame) bool
        +validate_required_columns(data: DataFrame) List[str]
    }

    class PhaseReportGenerator {
        -coverage_analyzer: CoverageAnalyzer
        +generate_markdown_report(validation_result: PhaseValidationResult, output_path: str) str
        +create_coverage_section(coverage_info: Dict) str
        +create_stride_filtering_section(stride_results: StrideFilterResult) str
        +generate_recommendations(validation_result: PhaseValidationResult) List[str]
    }

    %% Relationships
    PhaseValidator --> TaskDetector : uses
    PhaseValidator --> CoverageAnalyzer : uses  
    PhaseValidator --> StrideFilter : uses
    PhaseValidator --> PhaseStructureValidator : uses
    PhaseValidator --> PhaseReportGenerator : uses
    PhaseValidator --> ValidationSpecManager : depends on
    StrideFilter --> RangeProvider : uses
    PhaseReportGenerator --> CoverageAnalyzer : uses
```

---

### ValidationSpecManager Component Structure ⭐

```mermaid
classDiagram
    class ValidationSpecManager {
        -config_manager: ConfigurationManager
        +edit_validation_ranges(task: str, variable: str, new_ranges: Dict, rationale: str) SpecificationUpdateResult
        +import_ranges_from_literature(literature_source: str, ranges_data: Dict) ImportResult
        +validate_spec_changes(test_dataset_paths: List[str]) SpecValidationResult
        +generate_change_documentation(changes: List) str
        +get_task_ranges(task: str) Dict
        +get_variable_range(task: str, variable: str, phase: str) Dict
    }

    class SpecificationParser {
        +parse_validation_expectations(file_path: str) Dict
        +parse_task_section(content: str, task: str) Dict
        +parse_phase_ranges(table_content: str) Dict
        +extract_phase_specific_bounds(task_data: Dict) Dict
    }

    class RangeProvider {
        -spec_parser: SpecificationParser
        -cached_ranges: Dict
        +get_task_and_phase_ranges(task: str) Dict
        +get_ranges_for_variables(task: str, variables: List[str]) Dict
        +filter_ranges_to_available_variables(ranges: Dict, available_vars: List[str]) Dict
        +get_phase_bounds(task: str, variable: str, phase: str) Dict
    }

    class SpecificationEditor {
        -range_provider: RangeProvider
        +preview_range_changes(task: str, variable: str, new_ranges: Dict) Dict
        +calculate_impact_on_datasets(changes: Dict, dataset_paths: List[str]) Dict
        +validate_range_consistency(new_ranges: Dict) bool
        +show_affected_stride_counts(changes: Dict, datasets: List[str]) Dict
    }

    class SpecificationPersistence {
        +save_specification_changes(file_path: str, updated_ranges: Dict, metadata: Dict) bool
        +create_backup(file_path: str) str
        +track_change_history(change_record: Dict) None
        +restore_from_backup(backup_path: str, target_path: str) bool
    }

    %% Relationships
    ValidationSpecManager --> SpecificationParser : uses
    ValidationSpecManager --> RangeProvider : uses
    ValidationSpecManager --> SpecificationEditor : uses
    ValidationSpecManager --> SpecificationPersistence : uses
    RangeProvider --> SpecificationParser : depends on
    SpecificationEditor --> RangeProvider : uses
```

---

### ValidationSpecVisualizer Component Structure

```mermaid
classDiagram
    class ValidationSpecVisualizer {
        -spec_manager: ValidationSpecManager
        +generate_validation_plots(data: DataFrame, output_dir: str, plot_types: List[str], available_variables: List[str]) PlotGenerationResult
        +generate_validation_gifs(data: DataFrame, output_dir: str) GifGenerationResult
        +generate_validation_spec_plots(tasks: List[str], output_dir: str, variables_subset: List[str]) PlotGenerationResult
    }

    class PlotAdapter {
        -feature_constants: FeatureConstants
        +determine_available_variables(data: DataFrame, standard_variables: List[str]) List[str]
        +adapt_plot_layout(available_variables: List[str], plot_type: str) Dict
        +generate_missing_variable_warnings(requested: List[str], available: List[str]) List[str]
        +filter_plot_types_by_availability(plot_types: List[str], available_vars: List[str]) List[str]
    }

    class CoverageAnnotator {
        +create_coverage_summary(plotted_vars: List[str], total_vars: List[str]) str
        +annotate_plot_titles(plot_metadata: Dict, coverage_info: Dict) Dict
        +generate_coverage_legend(coverage_percentage: float) str
        +add_missing_variable_notes(plot_config: Dict, missing_vars: List[str]) Dict
    }

    class ValidationPlotter {
        -range_provider: RangeProvider
        +create_forward_kinematics_plots(data: DataFrame, task: str, variables: List[str]) List[str]
        +create_phase_filter_plots(data: DataFrame, task: str, variables: List[str]) List[str]
        +overlay_validation_ranges(plot: object, task: str, variable: str) object
        +export_plot_with_metadata(plot: object, output_path: str, metadata: Dict) str
    }

    %% Relationships
    ValidationSpecVisualizer --> PlotAdapter : uses
    ValidationSpecVisualizer --> CoverageAnnotator : uses
    ValidationSpecVisualizer --> ValidationPlotter : uses
    ValidationSpecVisualizer --> ValidationSpecManager : depends on
    ValidationPlotter --> RangeProvider : uses
```

---

## High Priority Components

### QualityAssessor Component Structure

```mermaid
classDiagram
    class QualityAssessor {
        -spec_manager: ValidationSpecManager
        +assess_quality(file_path: str) QualityAssessmentResult
        +identify_bad_strides(data: DataFrame, task: str) List[Dict]
        +calculate_stride_compliance_score(data: DataFrame, task: str) float
        +generate_quality_metrics(data: DataFrame) Dict
    }

    class StrideClassifier {
        -range_provider: RangeProvider
        +classify_stride_quality(stride_data: DataFrame, task: str) bool
        +identify_violations(stride_data: DataFrame, task: str, ranges: Dict) List[Dict]
        +categorize_violation_severity(violations: List[Dict]) Dict
        +generate_stride_rejection_reasons(violations: List[Dict]) List[str]
    }

    class QualityScorer {
        +calculate_stride_pass_rate(total_strides: int, valid_strides: int) float
        +calculate_coverage_scores(coverage_info: Dict) Dict
        +generate_quality_trends(historical_scores: List[Dict]) Dict
        +create_quality_recommendations(scores: Dict, violations: List[Dict]) List[str]
    }

    %% Relationships
    QualityAssessor --> StrideClassifier : uses
    QualityAssessor --> QualityScorer : uses
    QualityAssessor --> ValidationSpecManager : depends on
    StrideClassifier --> RangeProvider : uses
```

---

## Supporting Infrastructure Components

### Core Data Structures

```mermaid
classDiagram
    class PhaseValidationResult {
        +is_valid: bool
        +file_path: str
        +total_strides: int
        +valid_strides: int
        +invalid_strides: int
        +stride_pass_rate: float
        +kept_stride_ids: List[str]
        +deleted_stride_ids: List[str]
        +stride_rejection_reasons: Dict[str, List[str]]
        +detected_tasks: List[str]
        +validated_tasks: List[str]
        +skipped_tasks: List[str]
        +standard_spec_coverage: Dict[str, Dict[str, bool]]
        +available_variables: List[str]
        +missing_standard_variables: List[str]
        +validation_coverage: Dict[str, float]
        +validation_scope: str
        +errors: List[str]
        +warnings: List[str]
        +recommendations: List[str]
        +report_path: str
        +plot_paths: List[str]
        +validation_summary: Dict
    }

    class StrideFilterResult {
        +filtered_data: DataFrame
        +total_strides: int
        +valid_strides: int
        +invalid_strides: int
        +stride_pass_rate: float
        +kept_stride_ids: List[str]
        +deleted_stride_ids: List[str]
        +rejection_reasons: Dict[str, List[str]]
        +validated_variables: List[str]
        +skipped_variables: List[str]
        +validation_coverage_by_task: Dict[str, float]
    }

    class PlotGenerationResult {
        +success: bool
        +generated_plots: Dict[str, List[str]]
        +output_directory: str
        +error_message: str
        +requested_variables: List[str]
        +plotted_variables: List[str]
        +skipped_variables: List[str]
        +coverage_summary: str
        +warnings: List[str]
    }

    class QualityAssessmentResult {
        +file_path: str
        +coverage_stats: Dict
        +stride_pass_rate: float
        +stride_compliance_rate: float
        +quality_scores: Dict
        +rejected_strides: List[Dict]
        +missing_data_patterns: List[str]
        +recommendations: List[str]
    }
```

---

### Configuration and Error Handling

```mermaid
classDiagram
    class ConfigurationManager {
        -config_path: str
        -cached_config: Dict
        +get_validation_ranges(category: str) Dict
        +get_task_ranges(task: str) Dict
        +get_variable_range(task: str, variable: str, phase: str) Dict
        +update_ranges(new_ranges: Dict) None
        +backup_specifications() str
        +load_feature_constants() FeatureConstants
    }

    class ErrorHandler {
        -verbose: bool
        -log_file: str
        +handle_error(error: Exception, context: str) None
        +handle_warning(message: str, context: str) None
        +get_user_friendly_message(error: Exception) str
        +log_error_with_context(error: Exception, context: Dict) None
        +generate_troubleshooting_guidance(error_type: str) List[str]
    }

    class FeatureConstants {
        +get_standard_tasks() List[str]
        +get_standard_kinematic_variables() List[str]
        +get_standard_kinetic_variables() List[str]
        +get_feature_list(mode: str) List[str]
        +is_known_task(task: str) bool
        +is_standard_variable(variable: str) bool
    }

    %% Relationships - These are used by multiple components
    ConfigurationManager --> FeatureConstants : loads
    ErrorHandler <-- PhaseValidator : uses
    ErrorHandler <-- ValidationSpecManager : uses
    FeatureConstants <-- TaskDetector : uses
    FeatureConstants <-- CoverageAnalyzer : uses
```

---

## Key Architectural Patterns

### **Composition over Inheritance**
- Components are composed of smaller, focused sub-components
- Each sub-component has a single responsibility
- Dependencies are injected rather than tightly coupled

### **Strategy Pattern for Flexibility**
- `PlotAdapter` adapts behavior based on available variables
- `StrideFilter` applies different validation strategies per task
- `CoverageAnalyzer` handles different coverage scenarios

### **Observer Pattern for Reporting**
- `PhaseReportGenerator` observes validation results
- `CoverageAnnotator` observes coverage analysis
- `QualityScorer` observes stride classification results

### **Facade Pattern for Complexity**
- `PhaseValidator` provides simple interface to complex validation workflow
- `ValidationSpecManager` hides specification parsing complexity
- `ValidationSpecVisualizer` simplifies plot generation with coverage tracking

---

This UML design reflects the enhanced interface specifications with:
- **Task-specific processing** with graceful unknown task handling
- **Coverage-aware operations** that adapt to available variables
- **Stride-level filtering** with detailed rejection reasons
- **Flexible visualization** that skips missing variables gracefully
- **External collaborator focus** with clear error messages

The structure supports realistic data processing scenarios while maintaining clean separation of concerns.