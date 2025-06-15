# Validation System Implementation Plan

**Practical test-driven development plan using vertical slices and shared infrastructure.**

## Problems with Pure Parallel Development

**Why component-based sub-agents don't work:**
- **Interface chicken-and-egg**: Can't define interfaces without understanding real requirements
- **Shared context needs**: All sub-agents need deep domain knowledge and existing codebase understanding  
- **Tight coupling reality**: SpecificationManager and PhaseValidator are inherently coupled
- **Integration complexity**: Real biomechanical validation has edge cases that simple interfaces can't capture

## Better Strategy: Vertical Slices + Shared Infrastructure

### **Phase 0: Shared Foundation (1 week)**
Single sub-agent builds shared infrastructure that all others depend on

### **Phase 1: Walking Validation Slice (2 weeks)**
Complete walking task validation from spec parsing to CLI report

### **Phase 2: Multi-Task Extension (1 week)**  
Extend to multiple tasks and edge cases

### **Phase 3: Advanced Features (2 weeks)**
Spec editing, auto-tuning, and conversion tools

---

## Phase 1A: Core Components

### **Sub-Agent 1: SpecificationManager** ⭐
**Priority**: Critical - all validation depends on this

**Scope**: Parse validation specifications and provide range lookup
**Files**: `source/lib/validation/specification_manager.py`
**Test File**: `source/tests/test_specification_manager.py`

**Interface Contract**:
```python
class SpecificationManager:
    def get_ranges(self, task: str, variable: str, phase: int) -> Dict[str, float]:
        """Return {min, max} for task/variable/phase. Empty dict if not found."""
    
    def get_all_tasks(self) -> List[str]:
        """Return list of all tasks with validation specifications"""
    
    def get_task_variables(self, task: str) -> List[str]:
        """Return variables available for given task"""
    
    def validate_integrity(self) -> List[str]:
        """Check for NaNs, missing cyclic tasks. Return list of issues."""
    
    def stage_changes(self, changes: Dict) -> StagingResult:
        """Stage specification updates for review"""

@dataclass
class StagingResult:
    success: bool
    staging_file: str
    affected_datasets: List[str]
    warnings: List[str]
```

**Test Requirements**:
- Parse existing `docs/standard_spec/validation_expectations_*.md`
- Return correct ranges for `walking/knee_flexion_angle_ipsi_rad` at phase 50%
- Handle unknown tasks gracefully (return empty, don't crash)
- Detect integrity issues (NaN values, missing tasks)
- Staging workflow creates safe preview files

**Dependencies**: None (core component)

---

### **Sub-Agent 2: PhaseValidator Core** ⭐
**Priority**: Critical - main validation engine

**Scope**: Stride-level validation and filtering logic
**Files**: `source/lib/validation/phase_validator.py`
**Test File**: `source/tests/test_phase_validator.py`

**Interface Contract**:
```python
class PhaseValidator:
    def __init__(self, spec_manager: SpecificationManager):
        pass
    
    def filter_valid_strides(self, data: pd.DataFrame) -> StrideFilterResult:
        """Filter strides using task-specific validation ranges"""
    
    def validate_phase_structure(self, data: pd.DataFrame) -> PhaseStructureResult:
        """Validate 150 points per cycle requirement"""
    
    def analyze_coverage(self, data: pd.DataFrame) -> CoverageResult:
        """Analyze which standard variables are available vs missing"""

@dataclass  
class StrideFilterResult:
    total_strides: int
    valid_strides: int
    invalid_strides: int
    pass_rate: float
    kept_stride_ids: List[str]
    deleted_stride_ids: List[str]
    rejection_reasons: Dict[str, List[str]]

@dataclass
class CoverageResult:
    available_tasks: List[str]
    validated_tasks: List[str]
    skipped_tasks: List[str]
    variable_coverage: Dict[str, Dict[str, bool]]  # task -> variable -> present
```

**Test Requirements**:
- Filter strides correctly using validation ranges
- Validate exactly 150 points per gait cycle
- Handle mixed valid/invalid strides appropriately
- Provide detailed rejection reasons
- Calculate accurate coverage statistics

**Dependencies**: SpecificationManager interface

---

### **Sub-Agent 3: DataLoader Integration** 
**Priority**: High - needed for CLI tools

**Scope**: LocomotionData integration and error handling
**Files**: `source/lib/core/data_integration.py`
**Test File**: `source/tests/test_data_integration.py`

**Interface Contract**:
```python
class ValidationDataLoader:
    def load_dataset(self, file_path: str) -> ValidationDataResult:
        """Load parquet file with validation-specific preprocessing"""
    
    def detect_dataset_type(self, data: pd.DataFrame) -> DatasetType:
        """Detect if dataset is phase-indexed or time-indexed"""
    
    def validate_basic_structure(self, data: pd.DataFrame) -> StructureResult:
        """Check required columns and basic data integrity"""

@dataclass
class ValidationDataResult:
    data: pd.DataFrame
    dataset_type: DatasetType
    structure_valid: bool
    errors: List[str]
    warnings: List[str]

class DatasetType(Enum):
    PHASE_INDEXED = "phase"
    TIME_INDEXED = "time"
    UNKNOWN = "unknown"
```

**Test Requirements**:
- Load parquet files correctly with error handling
- Detect phase vs time datasets accurately  
- Validate required columns (subject, task, phase/time)
- Handle file corruption gracefully
- Integrate with LocomotionData class

**Dependencies**: LocomotionData, FeatureConstants

---

### **Sub-Agent 4: Conversion Core**
**Priority**: High - needed for phase dataset creation

**Scope**: Time-to-phase conversion algorithm
**Files**: `source/lib/conversion/phase_converter.py`  
**Test File**: `source/tests/test_phase_converter.py`

**Interface Contract**:
```python
class PhaseConverter:
    def convert_to_phase(self, time_data: pd.DataFrame) -> ConversionResult:
        """Convert time-indexed to phase-indexed (150 points per cycle)"""
    
    def detect_gait_cycles(self, grf_data: pd.Series) -> List[GaitCycle]:
        """Detect gait cycles from vertical ground reaction force"""
    
    def interpolate_cycle(self, cycle_data: pd.DataFrame) -> pd.DataFrame:
        """Interpolate single gait cycle to exactly 150 points"""

@dataclass
class ConversionResult:
    phase_data: pd.DataFrame
    success: bool
    cycles_detected: int
    cycles_converted: int
    conversion_rate: float
    errors: List[str]
    warnings: List[str]
```

**Test Requirements**:
- Convert time data to exactly 150 points per cycle
- Detect gait cycles from GRF data accurately
- Handle incomplete or irregular cycles
- Preserve all original variables and metadata
- Report conversion statistics

**Dependencies**: Ground reaction force data format knowledge

---

## Phase 1B: CLI Layer

### **Sub-Agent 5: validation_dataset_report.py** ⭐
**Priority**: Critical - main user-facing tool

**Scope**: CLI for comprehensive dataset validation
**Files**: `source/validation/validation_dataset_report.py`
**Test File**: `source/tests/test_cli_validation_report.py`

**Interface Contract**:
```python
def main(args: argparse.Namespace) -> int:
    """Main CLI entry point. Returns exit code."""

def generate_validation_report(dataset_path: str, 
                             output_dir: str,
                             generate_gifs: bool = False) -> ValidationReportResult:
    """Generate comprehensive validation report"""

@dataclass
class ValidationReportResult:
    report_path: str
    plot_paths: List[str]
    is_valid: bool
    stride_statistics: StrideFilterResult
    coverage_analysis: CoverageResult
    quality_metrics: Dict[str, float]
```

**Test Requirements**:
- CLI argument parsing and validation
- Auto-detect dataset type (phase vs time)  
- Generate markdown reports with embedded plots
- Handle --generate-gifs flag correctly
- Batch processing support
- Proper exit codes and error messages

**Dependencies**: PhaseValidator, DataLoader, SpecificationManager

---

### **Sub-Agent 6: validation_manual_tune_spec.py**
**Priority**: High - spec management tool

**Scope**: Interactive validation range editing
**Files**: `source/validation/validation_manual_tune_spec.py`
**Test File**: `source/tests/test_cli_manual_tune.py`

**Interface Contract**:
```python
def main(args: argparse.Namespace) -> int:
    """Main CLI entry point for manual spec tuning"""

def interactive_edit_ranges(task: str, 
                           variable_type: str) -> EditResult:
    """Interactive editing interface for validation ranges"""

@dataclass
class EditResult:
    changes_made: bool
    staging_file: str
    preview_plots: List[str]
    affected_datasets: List[str]
```

**Test Requirements**:
- Interactive range editing interface
- Preview changes before applying
- Staging workflow integration
- Generate preview plots
- Change impact analysis

**Dependencies**: SpecificationManager

---

### **Sub-Agent 7: conversion_generate_phase_dataset.py**
**Priority**: High - phase conversion tool

**Scope**: CLI for time-to-phase conversion
**Files**: `source/conversion/conversion_generate_phase_dataset.py`
**Test File**: `source/tests/test_cli_phase_conversion.py`

**Interface Contract**:
```python
def main(args: argparse.Namespace) -> int:
    """Main CLI entry point for phase conversion"""

def convert_dataset(input_path: str, 
                   output_path: str = None) -> ConversionCLIResult:
    """Convert time dataset to phase format"""

@dataclass
class ConversionCLIResult:
    output_path: str
    success: bool
    conversion_stats: ConversionResult
    validation_report: str
```

**Test Requirements**:
- Convert time datasets to phase format
- Auto-generate output filenames
- Batch processing support  
- Validate converted output automatically
- Progress reporting for large datasets

**Dependencies**: PhaseConverter, ValidationDataLoader

---

### **Sub-Agent 8: validation_auto_tune_spec.py**
**Priority**: Medium - statistical range optimization

**Scope**: Automated validation range tuning
**Files**: `source/validation/validation_auto_tune_spec.py`
**Test File**: `source/tests/test_cli_auto_tune.py`

**Interface Contract**:
```python
def main(args: argparse.Namespace) -> int:
    """Main CLI entry point for auto-tuning"""

def auto_tune_ranges(datasets: List[str], 
                    method: str = "percentile_95") -> AutoTuneResult:
    """Calculate optimal ranges using statistical methods"""

@dataclass
class AutoTuneResult:
    optimized_ranges: Dict[str, Dict[str, Dict[str, float]]]
    justification: Dict[str, str]
    preview_plots: List[str]
    improvement_metrics: Dict[str, float]
```

**Test Requirements**:
- Multiple statistical methods (percentile, IQR)
- Preview mode without applying changes
- Integration with staging workflow
- Statistical justification for changes
- Visual comparison plots

**Dependencies**: SpecificationManager, PhaseValidator

---

## Phase 1C: Integration & Testing

### **Sub-Agent 9: System Integration**
**Priority**: High - ensures everything works together

**Scope**: End-to-end testing and integration
**Files**: `source/tests/test_integration_workflows.py`

**Test Requirements**:
- Complete dataset processing workflows
- Multi-component integration testing
- Performance benchmarking
- Error propagation testing
- Memory usage validation

### **Sub-Agent 10: Documentation & Tutorials**
**Priority**: Medium - ensures usability

**Scope**: Update tutorials and documentation
**Files**: `docs/tutorials/`, `docs/software_engineering/`

**Requirements**:
- Update Python and MATLAB tutorials
- Verify all code examples work
- Update architecture documentation
- Create user guides for new CLI tools

---

## Coordination Protocol

### **Interface Definition Phase** (Week 1)
- Review all interface contracts above
- Create mock implementations for testing
- Resolve any interface conflicts
- Set up shared test data and fixtures

### **Core Development Phase** (Weeks 2-4)
- Sub-Agents 1-4 develop components independently
- Weekly check-ins on interface compliance
- Integration testing with mocks

### **CLI Development Phase** (Weeks 5-7)  
- Sub-Agents 5-8 build CLI tools using core components
- Real integration testing begins
- Performance optimization

### **Integration Phase** (Weeks 8-9)
- Sub-Agents 9-10 complete system integration
- End-to-end testing and validation
- Documentation and tutorial updates

### **Success Criteria**
- All unit tests passing (>95% coverage)
- Integration tests validate complete workflows
- Performance meets requirements (<30s for typical dataset)
- Documentation is current and tested
- CLI tools work as specified in user stories

This plan provides clear boundaries, comprehensive testing, and independent development paths while ensuring all components integrate correctly.