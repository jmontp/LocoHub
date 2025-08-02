# C4 Container Diagram - Current Implementation

**Current Phase 1 architecture focusing on dataset contributors and validation specialists (10% of user population).**

---

```mermaid
%%{init: {'theme': 'base'}}%%
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
    
    linkStyle default stroke:#666
```

---

## Key Components

### **User-Facing Tools**
- **Conversion Scripts**: Convert raw locomotion data (MATLAB, CSV, B3D) to standardized parquet format
- **Validation Report Generator (validation_dataset_report.py)**: **PRIMARY CONTAINER** - Create comprehensive validation reports with plots and quality metrics
- **Shared Library**: Core LocomotionData library for data loading and manipulation

### **Configuration & Tuning Tools**
- **Specification Manager**: Manage validation rules and biomechanical ranges
- **Automated Tuner**: Optimize validation ranges based on dataset statistics

### **Data Storage**
- **Parquet Datasets**: Quality-assured locomotion datasets in standardized format
- **Validation Spec**: Editable biomechanical validation rules and ranges
- **Validation Report**: Generated quality assessment reports with plots and recommendations
- **Project Documentation**: User guides, tutorials, and technical specifications

---

## Current Implementation Focus

**Target Users**: Dataset contributors, validation specialists, and system administrators (10% of total user population)

**Primary Goals**:
1. **Sign Convention Adherence** - Verify biomechanical data follows standard conventions
2. **Outlier Detection** - Identify strides with values outside acceptable ranges  
3. **Phase Segmentation Validation** - Ensure exactly 150 points per gait cycle

**Success Criteria**: External collaborators can successfully contribute validated datasets that meet quality standards for research use.

---

## Workflow Integration

**validation_dataset_report.py serves as the central validation hub** for all contributor workflows:

### **Container Workflow Mapping**
1. **Dataset Conversion (Sequence 1)**: Conversion Scripts → conversion_generate_phase_dataset.py → **validation_dataset_report.py**
2. **Manual Validation Tuning (Sequence 2A)**: Specification Manager → **validation_dataset_report.py** 
3. **Statistical Validation Tuning (Sequence 2B)**: Automated Tuner → **validation_dataset_report.py**
4. **Quality Assessment (Sequence 3)**: **validation_dataset_report.py** as primary container

### **Validation Data Flow**
```
Raw Data → Conversion Scripts → Parquet Files → validation_dataset_report.py → Quality Reports
Specification Updates → SpecificationManager → validation_dataset_report.py → Updated Validation
```

### **Container Dependencies**
- **All workflows converge** on validation_dataset_report.py for quality assessment
- **Shared Library** provides common data loading and manipulation across all containers
- **Validation specifications** drive the validation logic in the primary container
- **Quality reports** inform both conversion decisions and specification updates