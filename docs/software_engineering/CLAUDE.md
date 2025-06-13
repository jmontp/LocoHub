# CLAUDE.md - Software Engineering Directory

**Critical information for working with the locomotion data standardization architecture and specifications.**

---

## Architecture Overview

**Main Architecture**: C4 Container/Component diagrams showing 90/10 user population split:
- **90% Dataset Consumers** - Simple data access via library classes
- **10% Dataset Contributors** - Complex workflows for adding/validating datasets

**Key Documents**: 
- `04_user_stories_acceptance_criteria.md` - User requirements and entry points
- `08_c4_component.md` - Internal component architecture 
- `09_c4_code.md` - Interface specifications for all components
- `10_test_specifications.md` - Test cases for critical components

---

## Critical Components & Their Relationships

### **Validation System (Critical Priority)**

**PhaseValidator** - Validates phase-indexed datasets with stride-level filtering
- Uses **ValidationSpecManager** to get task-specific validation ranges
- Filters strides: keeps valid strides, marks invalid strides for deletion  
- Only fails dataset if NO strides pass validation
- Reports stride pass rate as quality metric

**ValidationSpecManager** ⭐ CRITICAL COMPONENT
- Uses existing `validation_expectations_parser.py` (SpecificationParser component)
- Manages task and phase-specific validation ranges from markdown files
- Provides ranges organized by: task → variable → phase (0%, 25%, 50%, 75%) → {min, max}

**Key Flow**: External scripts create parquet → PhaseValidator validates using ValidationSpecManager → Stride filtering based on task-specific ranges

---

## Critical Implementation Details

### **Stride Classification & Filtering**
- **Strides** = Full gait cycles (150 data points each in phase-indexed data)
- **Stride Filtering** = Classify each stride as valid/invalid, keep valid strides, delete invalid strides
- **QualityAssessor** = Analyzes stride-level quality and compliance with validation specifications

### **Task-Specific Validation**
- Validation ranges are task-specific: walking, incline_walking, decline_walking
- Each task has different biomechanical ranges at each phase (0%, 25%, 50%, 75%)
- Uses existing `validation_expectations_kinematic.md` and kinetic files
- ValidationSpecManager uses `validation_expectations_parser.py` for parsing

### **External Conversion Reality**
- Conversion scripts come from external collaborators in varying formats
- No standardized conversion interfaces - focus on validating parquet outputs
- PhaseValidator is the critical quality gate for all external conversions

---

## Component Dependencies (Don't Reinvent)

**Component Dependencies**:
```
ValidationSpecManager → Markdown Specification Parser → reads validation_expectations files
PhaseValidator → ValidationSpecManager → gets task/phase-specific ranges for stride filtering
QualityAssessor → ValidationSpecManager → gets ranges for stride quality assessment
```

---

## Critical User Stories (Must Implement)

**UC-C02: Validate Converted Dataset** - PhaseValidator with stride filtering
**UC-C03: Generate Validation Visualizations** - ValidationSpecVisualizer  
**UC-V04: Manage Validation Specifications** - ValidationSpecManager ⭐ CRITICAL

**Priority Matrix**:
- **Critical**: PhaseValidator, ValidationSpecManager, ValidationSpecVisualizer
- **High**: QualityAssessor, AutomatedFineTuner
- **Medium**: ValidationDebugger, BenchmarkCreator, DatasetPublisher

---

## Key Interface Contracts

**PhaseValidator.validate_dataset()** - Must perform stride-level filtering using task-specific ranges
**PhaseValidator.filter_valid_strides()** - Must validate at 0%, 25%, 50%, 75% phases per task
**ValidationSpecManager.get_task_ranges()** - Must return phase-specific ranges by task
**QualityAssessor.identify_bad_strides()** - Must identify strides that violate validation specifications

---

## Test Strategy Focus

**Priority 1 (Critical)**: PhaseValidator parquet validation with stride filtering
- Test task-specific range application (walking vs incline_walking)
- Test stride filtering with mixed good/bad strides  
- Test external conversion script outputs

**Priority 2 (High)**: ValidationSpecManager and QualityAssessor functionality
- Test stride-level compliance scoring
- Test task and phase-specific stride violation detection

---

*This directory contains the complete software engineering specifications for implementing the locomotion data standardization system. Focus on Critical priority components first, use existing modules where available, and follow the stride filtering paradigm with task-specific validation ranges.*