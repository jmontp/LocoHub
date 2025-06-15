# Sequence Workflows

**Technical sequence diagrams for all user workflows.**

## Current Focus: Dataset Contributor Workflows

### Sequence 1: Dataset Curator (Programmer) Develops Conversion Script

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DC as Dataset Curator (Programmer)
    participant VS as Validation Scaffolding
    participant ES as Example Scripts
    participant RD as Raw Dataset
    participant CS as Conversion Script
    participant PF as Time Parquet File
    participant GP as conversion_generate_phase_dataset.py
    participant PP as Phase Parquet File
    participant DR as validation_dataset_report.py
    participant QR as Quality Report

    DC->>VS: access validation scaffolding docs
    VS-->>DC: provide standard specification and guidelines
    
    DC->>ES: review example conversion scripts
    ES-->>DC: show GTech2023, UMich2021, AddBio examples
    
    DC->>RD: analyze raw dataset structure
    RD-->>DC: show .mat files, variable names, metadata
    
    DC->>CS: develop dataset-specific conversion script
    CS->>RD: read raw data files
    RD-->>CS: return raw locomotion data
    CS->>CS: map variables to standard names
    CS->>PF: write time-indexed parquet file
    PF-->>CS: confirm write success
    CS-->>DC: time-indexed conversion complete
    
    DC->>GP: python conversion_generate_phase_dataset.py time_dataset.parquet
    GP->>PF: read time-indexed parquet with ground reaction forces
    PF-->>GP: return time-series locomotion data
    GP->>GP: detect gait cycles from vertical GRF
    GP->>GP: interpolate each cycle to 150 points
    GP->>PP: write phase-indexed parquet file
    PP-->>GP: confirm phase dataset creation
    GP-->>DC: phase-indexed dataset ready
    
    DC->>DR: python validation_dataset_report.py phase_dataset.parquet
    DR->>PP: analyze phase-indexed dataset
    PP-->>DR: return dataset structure and data
    DR->>DR: auto-detect dataset type and run comprehensive validation
    DR->>DR: calculate quality metrics and coverage statistics
    DR->>QR: generate comprehensive quality and validation report
    QR-->>DR: report file path
    DR-->>DC: display report summary
    
    DC->>QR: review validation results and quality metrics
    QR-->>DC: show validation failures, quality issues, and recommendations
    
    alt Dataset meets quality standards
        DC->>DC: document conversion decisions
        DC->>DC: prepare contribution materials
    else Dataset has issues
        DC->>CS: debug and fix conversion issues
        DC->>DR: re-assess dataset quality
    end
```

---

### Sequence 2A: Manual Validation (Literature-Based Updates)

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant BV as Biomechanical Validator
    participant LT as Literature Review
    participant MS as validation_manual_tune_spec.py
    participant IE as Interactive Editor
    participant SM as SpecificationManager
    participant SF as Staging File
    participant VP as Validation Plots
    participant VS as Live Validation Specs

    BV->>LT: review recent biomechanical literature
    LT-->>BV: identify updated normal ranges with citations
    
    BV->>MS: python validation_manual_tune_spec.py --edit kinematic
    MS->>SM: load_current_specs()
    SM-->>MS: return current validation ranges
    MS->>IE: launch interactive editor
    IE-->>BV: display current ranges with literature input fields
    
    BV->>IE: input new ranges with literature citations
    IE->>SM: preview_changes(proposed_ranges)
    SM->>SM: validate_integrity(check NaNs, missing cyclic tasks)
    SM-->>IE: show impact analysis and validation results
    IE-->>BV: display affected datasets and integrity warnings
    
    BV->>IE: approve changes for staging
    IE->>SF: write_staging_specs(proposed_ranges, rationale)
    SF-->>IE: confirm staging file created
    
    IE->>IE: auto-generate validation plots from staging specs
    IE->>VP: create updated validation plots
    VP-->>IE: confirm plots generated
    
    BV->>VP: review updated validation plots
    VP-->>BV: show range visualizations with current vs proposed
    
    alt Plots look good
        BV->>IE: commit staging to live specs
        IE->>SM: apply_staged_changes(staging_file)
        SM->>SM: final_validation_check()
        SM->>VS: write updated validation specifications
        VS-->>SM: confirm spec update
        SM-->>IE: confirm changes applied
        IE-->>BV: display success confirmation
    else Plots need adjustment
        BV->>IE: modify ranges and regenerate plots
        IE->>IE: auto-regenerate plots with new ranges
    end
```

---

### Sequence 2B: Automatic Validation (Statistics-Based Updates)

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant BV as Biomechanical Validator
    participant AT as validation_auto_tune_spec.py
    participant PD as Parquet Datasets
    participant SM as SpecificationManager
    participant SF as Staging File
    participant VP as Validation Plots
    participant VS as Live Validation Specs

    BV->>AT: python validation_auto_tune_spec.py --dataset combined_data.parquet --method percentile_95
    AT->>PD: analyze statistical distributions across all tasks
    PD-->>AT: return variable statistics by task and phase
    
    AT->>AT: calculate proposed ranges using statistical method
    AT->>SM: preview_statistical_ranges(proposed_ranges)
    SM->>SM: validate_integrity(check NaNs, missing cyclic tasks)
    SM-->>AT: return validation results and impact analysis
    AT-->>BV: display proposed ranges with statistical justification
    
    BV->>AT: approve statistical proposals for staging
    AT->>SF: write_staging_specs(statistical_ranges, methodology)
    SF-->>AT: confirm staging file created
    
    AT->>AT: auto-generate validation plots from staging specs
    AT->>VP: create updated validation plots showing statistical ranges
    VP-->>AT: confirm plots generated
    
    BV->>VP: review statistical range plots
    VP-->>BV: show data distribution vs proposed ranges
    
    alt Statistical ranges acceptable
        BV->>AT: commit staging to live specs
        AT->>SM: apply_staged_changes(staging_file)
        SM->>SM: final_validation_check()
        SM->>VS: write updated validation specifications
        VS-->>SM: confirm spec update
        SM-->>AT: confirm changes applied
        AT-->>BV: display success confirmation
    else Need manual refinement
        BV->>AT: suggest adjustments to statistical method
        AT->>AT: recalculate with adjusted parameters
        AT->>AT: auto-regenerate plots with refined ranges
    end
```

---

### Sequence 3: Dataset Curator Generates Quality Report

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DC as Dataset Curator
    participant GR as validation_dataset_report.py
    participant LD as LocomotionData
    participant PF as Parquet File
    participant SM as SpecificationManager
    participant VS as Validation Specs
    participant QR as Quality Report

    DC->>GR: python validation_dataset_report.py dataset.parquet
    GR->>LD: load_dataset(dataset_path)
    LD->>PF: read parquet file
    PF-->>LD: return locomotion data
    LD-->>GR: return LocomotionData object
    
    GR->>GR: auto-detect dataset type (phase vs time-indexed)
    GR->>SM: load_validation_specs(detected_type)
    SM->>VS: read validation rules
    VS-->>SM: return validation ranges
    SM-->>GR: return parsed specifications
    
    par Dataset Analysis
        GR->>GR: calculate coverage statistics
        GR->>GR: identify missing data patterns
        GR->>GR: detect outliers and anomalies
    and Validation Assessment
        GR->>GR: run comprehensive validation
        GR->>GR: generate pass/fail summary
        GR->>GR: analyze failure patterns
    and Quality Metrics
        GR->>GR: calculate biomechanical plausibility scores
        GR->>GR: compare against population norms
        GR->>GR: assess data completeness
    end
    
    GR->>QR: compile comprehensive quality report
    QR-->>GR: report file path
    GR-->>DC: display report summary
    
    DC->>QR: review detailed quality metrics
    QR-->>DC: show coverage, validation results, recommendations
    DC->>DC: make data quality decisions
```

---

### Sequence 4: System Administrator (Future) - ML Benchmark Creation

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant SA as System Administrator
    participant BC as create_benchmarks.py
    participant QD as Quality Datasets
    participant BS as Benchmark Suite
    participant DR as Data Repository

    Note over SA: Low Priority - Future Implementation
    
    SA->>QD: review validated dataset quality scores
    QD-->>SA: show quality metrics and coverage
    
    SA->>BC: python create_benchmarks.py --split-strategy subject datasets/
    BC->>QD: load quality-validated datasets
    QD-->>BC: return combined locomotion data
    
    BC->>BC: create subject-based train/validation/test splits
    BC->>BC: validate no data leakage between splits
    BC->>BC: generate ML-ready formats
    
    BC->>BS: create benchmark suite with documentation
    BS-->>BC: confirm benchmark creation
    BC-->>SA: display benchmark summary
    
    SA->>DR: deploy benchmark to repository
    DR-->>SA: confirm deployment success
```

---

## Workflow Patterns

### Core Contributor Workflows
1. **Conversion Development**: Programmers create dataset-specific scripts using scaffolding
2. **Validation Management**: Biomechanics experts maintain and update validation ranges
3. **Quality Assessment**: Both roles use comprehensive reporting for dataset evaluation

### Key Integration Points
- **ValidationSpecificationManager**: Central validation rule management
- **PhaseValidator**: Core validation engine used by all workflows
- **Quality Reporting**: Unified assessment across all contributor activities

### Success Factors
- **Clear Scaffolding**: Examples and guidelines enable conversion script development
- **Phase Generation Tool**: `conversion_generate_phase_dataset.py` automates gait cycle detection and interpolation
- **Safe Staging Workflow**: Preview changes before committing to live validation specs
- **Automatic Validation**: SpecificationManager checks for NaNs and missing cyclic tasks
- **Integrated Visualization**: Automatic plot generation within validation workflows
- **Optional Animation**: `--generate-gifs` flag for computationally intensive animations
- **Dual Validation Approaches**: Literature-based manual and statistics-based automatic workflows
- **Interactive Editing**: No error-prone manual markdown editing
- **Comprehensive Reporting**: Quality metrics guide contribution decisions
- **Iterative Debugging**: Validation feedback enables continuous improvement

---

## Future: Consumer Workflows *(90% of users - Phase 2)*

Consumer workflows will focus on simple data access and analysis:
- Direct parquet file downloads
- Python/MATLAB library usage for common analysis patterns
- Educational tutorials for different skill levels
- Quality metrics to guide dataset selection

The validation infrastructure ensures consumer confidence without requiring technical validation knowledge.