---
title: Architecture
tags: [architecture]
status: ready
---

# Architecture

!!! info ":building_construction: **You are here** → System Design Hub"
    **Purpose:** Complete architectural view from system context to code specifications
    
    **Who should read this:** Architects, senior developers, system designers, technical leads
    
    **Value:** Understand system structure, design decisions, and component relationships
    
    **Connection:** Implements [User Guide](01_USER_GUIDE.md) insights and [Requirements](02_REQUIREMENTS.md)
    
    **:clock4: Reading time:** 25 minutes | **:building_construction: Architecture levels:** 4 (Context → Container → Component → Code)

!!! tip "**Architecture Navigation**"
    **🌐 Big picture?** → [System Context Architecture](#system-context-architecture)
    
    **📦 Containers?** → [Container Architecture](#container-architecture)
    
    **🔧 Components?** → [Component Architecture](#component-architecture)
    
    **💻 Code details?** → [Code Architecture](#code-architecture)

## 🏗️ Architectural Overview

!!! abstract "**Key Design Principle**"
    **Quality-first approach** where validation infrastructure (10% contributors) enables data reliability for research community (90% consumers).

!!! success "**Primary Integration Point**"
    `validation_dataset_report.py` serves as the central validation tool implementing F1 requirements from [Requirements](02_REQUIREMENTS.md).

**Architecture Philosophy:**
- **C4 Methodology:** Clear abstraction levels from context to code
- **Validation-Centric Design:** All components integrate through validation specifications
- **Quality-First Foundation:** 10% contributor effort enables 90% consumer success

## System Context Architecture

### User Population and Workflows

The system serves external research collaborators through three distinct user populations:

**Dataset Contributors (9%)**: Research collaborators who validate and contribute data
**System Administrators (1%)**: Infrastructure managers and release coordinators  
**Dataset Consumers (90%)**: Research collaborators analyzing quality-assured data

### Context Diagram Reference

**System Context Diagrams**: See [System Context](01b_SYSTEM_CONTEXT.md) for complete context diagrams including intermediate detail and workflow-specific perspectives.

### Role-Based Entry Points

The system provides distinct workflows for three user populations:

- **Dataset Contributors (9%)**: Use `validation_dataset_report.py` as primary tool for data quality validation
- **Validation Specialists**: Manage validation rules via `validation_manual_tune_spec.py` and `validation_auto_tune_spec.py`  
- **System Administrators (1%)**: Infrastructure management and release coordination
- **Dataset Consumers (90%)**: Future focus on analysis tools consuming quality-assured data

## Container Architecture

### Current Implementation (Phase 1)

The system follows a three-phase development approach with the current implementation targeting dataset contributors and validation specialists.

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph "User"
        data_scientist["Data Scientist<br/><font size='-2'>Person</font><br/><font size='-1'>Analyzes and validates locomotion data.</font>"]
    end

    subgraph "Validation System API (Containers)"
        style ValidationSystemBoundary fill:#00000000,stroke:#888,stroke-width:2px,stroke-dasharray:5
        
        subgraph "User-Facing Tools"
            direction LR
            conversion_scripts["Conversion Scripts"]
            reporting_engine["Validation Report Generator"]
            shared_lib["Shared Library"]
        end

        subgraph "Configuration & Tuning Tools"
             direction LR
            spec_manager["Specification Manager"]
            auto_tuner["Automated Tuner"]
        end
    end

    subgraph "Data & Specifications"
        direction LR
        subgraph "Interactive Files"
            style InteractiveFiles fill:#00000000,stroke:#aaa,stroke-width:1px,stroke-dasharray:3
            parquet_storage["Parquet Datasets"]
            validation_spec["Validation Spec<br/><font size='-1'>(Editable Rules)</font>"]
        end
        subgraph "Read-Only Files"
            style ReadOnlyFiles fill:#00000000,stroke:#aaa,stroke-width:1px,stroke-dasharray:3
            validation_report["Validation Report<br/><font size='-1'>(Includes plots, GIFs, etc.)</font>"]
            project_docs["Project Documentation"]
        end
    end


    %% User Relationships
    data_scientist -- "Uses" --> conversion_scripts
    data_scientist -- "Uses" --> reporting_engine
    data_scientist -- "Uses" --> shared_lib
    data_scientist -- "Uses" --> auto_tuner
    data_scientist -- "Read/Write" --> validation_spec
    data_scientist -- "Manages/Reads" --> parquet_storage
    data_scientist -- "Reads" --> validation_report
    data_scientist -- "Reads" --> project_docs


    %% Internal System Relationships
    conversion_scripts -- "Uses" --> shared_lib
    reporting_engine -- "Uses" --> shared_lib
    spec_manager -- "Uses" --> shared_lib
    auto_tuner -- "Uses" --> shared_lib
    
    spec_manager -- "Triggers Redraw" --> reporting_engine
    auto_tuner -- "Suggests Changes" --> spec_manager


    %% System to File Relationships
    conversion_scripts -- "Writes" --> parquet_storage
    shared_lib -- "Reads" --> parquet_storage
    spec_manager -- "Reads/Writes" --> validation_spec
    auto_tuner -- "Reads" --> parquet_storage
    reporting_engine -- "Reads" --> parquet_storage
    reporting_engine -- "Reads" --> validation_spec
    reporting_engine -- "Generates" --> validation_report
    

    %% Styling
    style data_scientist fill:#08427b,color:white
    style conversion_scripts fill:#1168bd,color:white
    style reporting_engine fill:#1168bd,color:white
    style shared_lib fill:#2a9d8f,color:white
    style spec_manager fill:#4a4e69,color:white
    style auto_tuner fill:#4a4e69,color:white
    style parquet_storage fill:#707070,color:white
    style validation_spec fill:#707070,color:white
    style validation_report fill:#707070,color:white
    style project_docs fill:#707070,color:white
    
    linkStyle default stroke:white
```

### Container Workflow Integration

**validation_dataset_report.py serves as the central validation hub** for all contributor workflows:

1. **Dataset Conversion** → **validation_dataset_report.py**
2. **Manual Validation Tuning** → **validation_dataset_report.py** 
3. **Statistical Validation Tuning** → **validation_dataset_report.py**
4. **Quality Assessment** → **validation_dataset_report.py** as primary container

### Three-Phase Development Strategy

- **Phase 1 (Current)**: Manual validation workflows for dataset contributors and specialists (10% users)
- **Phase 2 (Future)**: Advanced contributor workflows with ML-assisted tools and community features  
- **Phase 3 (Future)**: Consumer-focused tools for researchers analyzing quality-assured data (90% users)

## Component Architecture

### Core Infrastructure Components (lib/core/)

Core data handling and manipulation components that provide the foundation for all validation workflows.

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph "Core Infrastructure Container"
        style CoreInfrastructure fill:#00000000,stroke:#438dd5,stroke-width:3px,stroke-dasharray:5
        
        subgraph "LocomotionData Core Components"
            data_loader["DataLoader<br/><font size='-2'>Component</font><br/><font size='-1'>Parquet file loading and memory management</font>"]
            data_validator["DataValidator<br/><font size='-2'>Component</font><br/><font size='-1'>Basic data integrity checks</font>"]
            data_transformer["DataTransformer<br/><font size='-2'>Component</font><br/><font size='-1'>Phase/time indexing, sign convention conversion, and manipulation</font>"]
            data_api["DataAPI<br/><font size='-2'>Component</font><br/><font size='-1'>Public interface for data access</font>"]
            error_handler["ErrorHandler<br/><font size='-2'>Component</font><br/><font size='-1'>Consistent error handling and user feedback</font>"]
        end
        
        subgraph "FeatureConstants Components"
            variable_registry["VariableRegistry<br/><font size='-2'>Component</font><br/><font size='-1'>Variable name mappings and definitions</font>"]
            biomech_conventions["BiomechConventions<br/><font size='-2'>Component</font><br/><font size='-1'>Sign conventions and coordinate systems</font>"]
            config_manager["ConfigurationManager<br/><font size='-2'>Component</font><br/><font size='-1'>System settings and user preferences</font>"]
        end
    end

    subgraph "External Dependencies"
        parquet_files["Parquet Files<br/><font size='-1'>Quality-assured dataset storage</font>"]
        standard_spec["Standard Specification<br/><font size='-1'>Official data format and conventions</font>"]
        spec_manager_api["SpecificationManager API<br/><font size='-1'>Validation rules and requirements</font>"]
        user_config["User Configuration<br/><font size='-1'>Settings, preferences, and system paths</font>"]
    end

    %% Internal Component Relationships
    data_api -- "Uses" --> data_loader
    data_api -- "Uses" --> data_validator
    data_api -- "Uses" --> data_transformer
    data_api -- "Uses" --> error_handler
    
    data_loader -- "Validates with" --> data_validator
    data_loader -- "Reports errors via" --> error_handler
    data_validator -- "Reports errors via" --> error_handler
    data_transformer -- "Reports errors via" --> error_handler
    
    data_transformer -- "References" --> variable_registry
    data_transformer -- "Applies" --> biomech_conventions
    data_transformer -- "Gets settings from" --> config_manager
    
    variable_registry -- "Loads from" --> standard_spec
    biomech_conventions -- "Loads from" --> standard_spec
    config_manager -- "Loads from" --> user_config
    config_manager -- "Loads defaults from" --> standard_spec

    %% External Dependencies
    data_loader -- "Reads" --> parquet_files
    data_validator -- "Gets validation rules from" --> spec_manager_api

    %% Styling
    style data_loader fill:#438dd5,color:white
    style data_validator fill:#438dd5,color:white
    style data_transformer fill:#438dd5,color:white
    style data_api fill:#438dd5,color:white
    style error_handler fill:#e76f51,color:white
    
    style variable_registry fill:#6baed6,color:white
    style biomech_conventions fill:#6baed6,color:white
    style config_manager fill:#96c93d,color:white
    
    style parquet_files fill:#707070,color:white
    style standard_spec fill:#707070,color:white
    style spec_manager_api fill:#6baed6,color:white
    style user_config fill:#707070,color:white
    
    linkStyle default stroke:white
```

### Enhanced Validation Engine Components (validation/)

The primary validation infrastructure implementing the three core validation goals:
1. **Sign Convention Adherence** - Verify biomechanical data follows standard conventions
2. **Outlier Detection** - Identify strides with values outside acceptable ranges  
3. **Phase Segmentation Validation** - Ensure exactly 150 points per gait cycle

**Key Component Groups:**

**PhaseValidator Components:**
- `TaskDetector`: Reads tasks from data['task'] column, validates against feature_constants
- `CoverageAnalyzer`: Analyzes standard spec coverage, identifies missing variables  
- `StrideFilter`: Task-specific stride filtering using validation ranges
- `PhaseStructureValidator`: Validates 150 points per cycle requirement
- `PhaseReportGenerator`: Generates markdown reports with coverage and stride filtering results

**ValidationSpecManager Components:**
- `SpecificationParser`: Parses validation_expectations markdown files
- `RangeProvider`: Provides task and phase-specific validation ranges
- `SpecificationEditor`: Interactive rule modification with impact preview
- `SpecificationPersistence`: File I/O and versioning with backup

**Integrated Visualization Components:**
- `PlotAdapter`: Adapts plots to available variables, skips missing gracefully
- `CoverageAnnotator`: Adds coverage information to plot titles and annotations
- `ValidationPlotter`: Generates plots as part of validation reports

### Component Execution Flow

The validation workflow follows a structured execution pattern implementing three core validation goals:
1. **Sign Convention Adherence** - Verify biomechanical data follows standard conventions
2. **Outlier Detection** - Identify strides with values outside acceptable ranges  
3. **Phase Segmentation Validation** - Ensure exactly 150 points per gait cycle

Key execution sequence: TaskDetector → CoverageAnalyzer → StrideFilter → ValidationPlotter → PhaseReportGenerator

## Code Architecture

### Core Classes and Integration

The architecture centers around key validation classes:

**Core Validation Components:**
- `PhaseValidator`: Main validation orchestrator with `validate_dataset()` method
- `ValidationSpecManager`: Manages validation ranges and biomechanical specifications  
- `QualityAssessor`: Provides quality metrics and outlier analysis
- `AutomatedFineTuner`: Statistical optimization of validation ranges

**Key Data Structures:**
- `PhaseValidationResult`: Complete validation results with metrics and reports
- `StrideFilterResult`: Detailed stride filtering outcomes with pass rates
- `ValidationRanges`: Task and phase-specific validation criteria

**Supporting Infrastructure:**
- `ConfigurationManager`: System settings and preferences
- `ErrorHandler`: Consistent error reporting across components
- `DataLoader`: Parquet file operations and data access

### Primary Integration Point: validation_dataset_report.py

The validation_dataset_report.py CLI tool represents the primary integration point demonstrating component orchestration:

```python
# Primary validation workflow integration
def main():
    # Initialize standardized dependencies
    config_manager = ConfigurationManager("validation_dataset_report")
    error_handler = ErrorHandler("validation_dataset_report", verbose=args.verbose)
    progress_reporter = ProgressReporter(verbose=args.verbose, quiet=args.quiet)
    
    # Initialize validation components
    spec_manager = ValidationSpecManager(config_manager, error_handler, progress_reporter)
    quality_assessor = QualityAssessor(spec_manager, error_handler, progress_reporter)
    phase_validator = PhaseValidator(spec_manager, error_handler, progress_reporter)
    
    # Execute comprehensive validation
    result = phase_validator.validate_dataset(
        file_path=args.dataset_path,
        generate_plots=True,
        generate_gifs=args.generate_gifs,
        output_dir=args.output_dir
    )
    
    # Generate comprehensive report
    report_path = phase_validator.generate_validation_report(result, output_path)
    
    return EXIT_SUCCESS
```

## Design Principles

### Validation-Centric Design
- All components integrate through validation specifications and quality metrics
- Biomechanical context maintained throughout validation pipeline
- validation_dataset_report.py serves as the cornerstone tool

### Quality-First Foundation
- 10% contributor effort enables 90% consumer success through rigorous validation
- Data quality is non-negotiable - fewer high-quality datasets preferred over many questionable ones
- Phase 1 builds quality infrastructure that enables consumer confidence

### Error Handling and Coverage-Aware Design
- Graceful degradation with actionable error messages
- Flexible validation that adapts to available variables vs full specification requirements
- Coverage tracking with percentage metrics and adaptive outputs

## Workflow Sequences

The system supports structured workflows for dataset contributors and validation specialists. These workflows integrate through the validation infrastructure to ensure data quality and consistency.

### Key Contributor Workflows

1. **Dataset Conversion**: Programmers develop conversion scripts using scaffolding and examples
2. **Manual Validation**: Biomechanics experts update validation ranges based on literature
3. **Statistical Validation**: Automated validation range updates using statistical methods
4. **Quality Assessment**: Comprehensive dataset evaluation and reporting

### Workflow Integration Points

- **validation_dataset_report.py**: Central validation hub for all contributor activities
- **ValidationSpecificationManager**: Safe staging and preview of validation rule changes
- **PhaseValidator**: Core validation engine with comprehensive quality metrics
- **Interactive Tools**: No manual markdown editing, automated plot generation

**Detailed Workflows**: See [Sequence Diagrams](03a_SEQUENCE_DIAGRAMS.md) for complete technical workflow specifications.

## Future Architecture

The system evolves through three phases, progressively serving larger user populations:

### Phase 2: Enhanced Contributors (2025-2026)
- **Advanced CLI Tools**: Batch validation, failure analysis, cross-dataset comparison
- **ML & Analytics**: Benchmark creation, automated release preparation, quality dashboards
- **Community Features**: Peer review portals, collaborative documentation, feedback systems
- **Intelligent Processing**: AI-assisted conversion, ML-based quality prediction

### Phase 3: Consumer-Focused (2026-2027)
- **Direct Data Access**: High-performance repository, web portal, programmatic API
- **Programming Libraries**: Native Python, MATLAB, and R integration
- **Learning Resources**: Interactive tutorials, comprehensive documentation, theory guides
- **Research Enablement**: Publication-ready visualizations, algorithm benchmarks

**Detailed Future Plans**: See [Future Architecture](03b_FUTURE_ARCHITECTURE.md) for complete Phase 2 and Phase 3 specifications.

## Strategic Approach

The architecture follows a three-phase strategy:

- **Phase 1 (Current)**: Build robust contributor tools for quality-assured datasets
- **Phase 2 (Future)**: Advanced contributor workflows with community features  
- **Phase 3 (Future)**: Consumer experience using proven validation foundation

**Quality Bridge**: The validation system ensures dataset quality behind the scenes, enabling consumer confidence without requiring validation expertise.

## User Context and Benefits

**Research Collaborators** represent the primary external user base:
- **Contributors (9%)**: Technical specialists focused on data quality validation
- **Consumers (90%)**: Researchers focused on analysis using quality-assured data

**Architecture Benefits**:
- **Risk Reduction**: Validate approach with expert community before scaling
- **Resource Efficiency**: Build quality foundation once, serve many consumers  
- **Sustainable Growth**: Establish validation credibility before widespread adoption

**Primary Tool**: validation_dataset_report.py serves as the central validation infrastructure across all architecture levels.

---

## 📊 Section Contents

<div class="grid cards" markdown>
-   **⚡ [Sequence Diagrams](03a_SEQUENCE_DIAGRAMS.md)**
    
    ---
    
    Technical sequence diagrams for all user workflows
    
    **Key Content:** Dataset conversion, validation tuning, quality assessment workflows
    
    **Time:** 15 minutes
    
    **Best For:** Developers, system integrators

-   **🔮 [Future Architecture](03b_FUTURE_ARCHITECTURE.md)**
    
    ---
    
    Phase 2 and Phase 3 architectural evolution plans
    
    **Key Content:** Consumer tools, advanced features, scalability plans
    
    **Time:** 10 minutes
    
    **Best For:** Product managers, technical leads
</div>

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** System Design & Architecture Hub"
    **⬅️ Previous:** [Requirements](02_REQUIREMENTS.md) - User stories and system requirements
    
    **➡️ Next:** [Interface Spec](04_INTERFACE_SPEC.md) - API and tool interfaces
    
    **📖 Reading time:** 20 minutes
    
    **🎯 Prerequisites:** [User Guide](01_USER_GUIDE.md) and [Requirements](02_REQUIREMENTS.md) - User understanding and system requirements
    
    **🔄 Follow-up sections:** Interface specifications, Implementation guidance

!!! tip "**Cross-References & Related Content**"
    **🔗 Requirements Foundation:** [Requirements - System Architecture](02_REQUIREMENTS.md) - User stories that drive these design decisions
    
    **🔗 User Research:** [User Guide - Journey Maps](01_USER_GUIDE.md#user-journey-maps) - User workflows informing architecture
    
    **🔗 Technical Details:** [Sequence Diagrams](03a_SEQUENCE_DIAGRAMS.md) - Detailed component interactions
    
    **🔗 Future Planning:** [Future Architecture](03b_FUTURE_ARCHITECTURE.md) - Phase 2 and Phase 3 evolution plans
    
    **🔗 Implementation:** [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) - How to build this architecture

---

## 🏗️ Architecture Summary

!!! success "**Key Design Decisions**"
    ✅ **Validation-Centric:** All components integrate through validation specifications
    
    ✅ **Quality-First:** 10% contributor focus enables 90% consumer confidence
    
    ✅ **Phased Evolution:** Phase 1 → validation infrastructure, Phase 2 → consumer tools
    
    ✅ **C4 Methodology:** Clear abstraction levels from system context to code implementation