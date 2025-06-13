# C4 System Context Diagrams

## Role-Based Entry Points

### Dataset Contributor Workflow

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    DC["🔬 Dataset Contributor<br/><font size='-1'>I have raw locomotion data</font>"] 
    
    DC --> CONVERT["📝 convert_dataset.py<br/><font size='-1'>Convert raw data to parquet</font>"]
    DC --> VALIDATE["✅ validate_phase_data.py<br/><font size='-1'>Validate converted datasets</font>"]
    DC --> ASSESS["📊 assess_quality.py<br/><font size='-1'>Check data quality metrics</font>"]
    
    style DC fill:#e76f51,color:white
    style CONVERT fill:#1168bd,color:white
    style VALIDATE fill:#1168bd,color:white  
    style ASSESS fill:#1168bd,color:white
    
    linkStyle default stroke:white
```

### Validation Specialist Workflow

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    VS["⚙️ Validation Specialist<br/><font size='-1'>I manage data quality standards</font>"]
    
    VS --> MANAGE["📋 manage_validation_specs.py<br/><font size='-1'>Edit validation rules</font>"]
    VS --> TUNE["🎯 auto_tune_ranges.py<br/><font size='-1'>Optimize validation ranges</font>"]
    VS --> COMPARE["📈 compare_datasets.py<br/><font size='-1'>Cross-dataset analysis</font>"]
    VS --> DEBUG["🔍 debug_validation_failures.py<br/><font size='-1'>Investigate data issues</font>"]
    
    style VS fill:#e76f51,color:white
    style MANAGE fill:#1168bd,color:white
    style TUNE fill:#1168bd,color:white
    style COMPARE fill:#1168bd,color:white
    style DEBUG fill:#1168bd,color:white
    
    linkStyle default stroke:white
```

### System Administrator Workflow

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    SA["👨‍💼 System Administrator<br/><font size='-1'>I manage releases and benchmarks</font>"]
    
    SA --> BENCHMARK["🏆 create_benchmarks.py<br/><font size='-1'>Create ML train/test splits</font>"]
    SA --> PUBLISH["📦 publish_datasets.py<br/><font size='-1'>Prepare public releases</font>"]
    SA --> BATCH["⚡ batch_validate.py<br/><font size='-1'>Validate multiple datasets</font>"]
    
    style SA fill:#f4a261,color:white
    style BENCHMARK fill:#1168bd,color:white
    style PUBLISH fill:#1168bd,color:white
    style BATCH fill:#1168bd,color:white
    
    linkStyle default stroke:white
```

### Dataset Consumer Workflow (Future)

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    DC["🎓 Dataset Consumer<br/><font size='-1'>I want to analyze locomotion data</font>"]
    
    DC --> BROWSE["🌐 Web Portal<br/><font size='-1'>Browse available datasets</font>"]
    DC --> DOWNLOAD["📥 Data Repository<br/><font size='-1'>Download parquet files</font>"]
    DC --> PYTHON["🐍 Python Library<br/><font size='-1'>LocomotionData class</font>"]
    DC --> MATLAB["📊 MATLAB Tools<br/><font size='-1'>Native MATLAB integration</font>"]
    
    style DC fill:#2a9d8f,color:white,stroke-dasharray:3
    style BROWSE fill:#6baed6,color:white,stroke-dasharray:3
    style DOWNLOAD fill:#6baed6,color:white,stroke-dasharray:3
    style PYTHON fill:#6baed6,color:white,stroke-dasharray:3
    style MATLAB fill:#6baed6,color:white,stroke-dasharray:3
    
    linkStyle default stroke:white,stroke-dasharray:3
```

**Legend**: 
- **Solid lines** = Current implementation focus (Contributors/Specialists/Administrators)
- **Dashed lines** = Future development (Consumers)

---

## Level 1A: Simple User Split

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph "Dataset Contributors (9%)"
        contributors["Data Validation Specialists<br/><font size='-2'>Person</font><br/><font size='-1'>Dataset curators and standard developers<br/>who ensure data quality.</font>"]
    end

    subgraph "System Administrators (1%)"
        admins["Infrastructure Managers<br/><font size='-2'>Person</font><br/><font size='-1'>Release managers, benchmark creators,<br/>and community coordinators.</font>"]
    end

    subgraph "Dataset Consumers (90%)"  
        consumers["Research Community<br/><font size='-2'>Person</font><br/><font size='-1'>Graduate students, clinical researchers,<br/>biomechanics engineers, sports scientists.</font>"]
    end

    subgraph "Core System"
        system["Locomotion Data Standardization<br/><font size='-2'>System</font><br/><font size='-1'>Validates, standardizes, and provides<br/>quality-assured locomotion datasets.</font>"]
    end

    contributors -- "Contribute & Validate" --> system
    admins -- "Manage & Release" --> system
    system -- "Provides Quality Data" --> consumers
    
    %% Styling
    style contributors fill:#e76f51,stroke:#d62828,stroke-width:2px,color:#ffffff
    style admins fill:#f4a261,stroke:#e76f51,stroke-width:2px,color:#ffffff
    style consumers fill:#2a9d8f,stroke:#264653,stroke-width:2px,color:#ffffff
    style system fill:#457b9d,stroke:#1d3557,stroke-width:2px,color:#ffffff
    
    linkStyle default stroke:white
```

**Use Case**: Stakeholder communication and high-level system overview

---

## Level 1B: Data Flow Focus

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph "External Data Sources"
        raw["Raw Locomotion Datasets<br/><font size='-2'>External System</font><br/><font size='-1'>GTech, UMich, AddBiomechanics<br/>and other research datasets.</font>"]
    end

    subgraph "Core System"
        system["Locomotion Data Standardization<br/><font size='-2'>System</font><br/><font size='-1'>Converts, validates, and standardizes<br/>locomotion data to common format.</font>"]
    end

    subgraph "Standardized Outputs"
        datasets["Quality-Assured Datasets<br/><font size='-2'>Data</font><br/><font size='-1'>Parquet files with consistent<br/>variables and validated ranges.</font>"]
        docs["Documentation & Standards<br/><font size='-2'>Documentation</font><br/><font size='-1'>Validation specs, tutorials,<br/>and usage guidelines.</font>"]
    end

    raw -- "Converts" --> system
    system -- "Produces" --> datasets
    system -- "Generates" --> docs
    
    %% Styling
    style raw fill:#8d99ae,stroke:#6c757d,stroke-width:2px,color:#ffffff
    style system fill:#457b9d,stroke:#1d3557,stroke-width:2px,color:#ffffff
    style datasets fill:#2a9d8f,stroke:#264653,stroke-width:2px,color:#ffffff
    style docs fill:#f4a261,stroke:#e76f51,stroke-width:2px,color:#ffffff
    
    linkStyle default stroke:white
```

**Use Case**: Technical understanding and data transformation explanation

---

## Level 1C: Intermediate Detail

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph "Users"
        contributors["Dataset Contributors (9%)<br/><font size='-2'>Person</font><br/><font size='-1'>Specialists who validate and contribute data.</font>"]
        admins["System Administrators (1%)<br/><font size='-2'>Person</font><br/><font size='-1'>Release managers and infrastructure specialists.</font>"]
        consumers["Dataset Consumers (90%)<br/><font size='-2'>Person</font><br/><font size='-1'>Researchers who analyze standardized data.</font>"]
    end

    subgraph "External Data Sources"
        raw_datasets["Raw Locomotion Datasets<br/><font size='-2'>External System</font><br/><font size='-1'>GTech, UMich, AddBiomechanics<br/>and other research institutions.</font>"]
    end

    subgraph "Locomotion Data Standardization System"
        validation_engine["Validation & Conversion Engine<br/><font size='-2'>System</font><br/><font size='-1'>Converts raw data to standard format<br/>and validates biomechanical accuracy.</font>"]
        
        analysis_tools["Data Access & Analysis Tools<br/><font size='-2'>System</font><br/><font size='-1'>Python/MATLAB libraries and tools<br/>for efficient data consumption.</font>"]
    end

    subgraph "Standardized Data & Documentation"
        datasets["Quality-Assured Datasets<br/><font size='-2'>Data</font><br/><font size='-1'>Parquet files with validated<br/>biomechanical ranges.</font>"]
        
        validation_specs["Validation Specifications<br/><font size='-2'>Configuration</font><br/><font size='-1'>Biomechanical standards and<br/>validation rules.</font>"]
        
        documentation["User Documentation<br/><font size='-2'>Documentation</font><br/><font size='-1'>Tutorials, API docs, and<br/>getting started guides.</font>"]
    end

    %% Data Flow
    raw_datasets -- "Converts" --> validation_engine
    validation_engine -- "Produces" --> datasets
    validation_engine -- "Uses/Updates" --> validation_specs
    validation_engine -- "Generates" --> documentation

    %% User Interactions - Contributors (Current Focus)
    contributors -- "Uses" --> validation_engine
    contributors -- "Edits" --> validation_specs
    contributors -- "Reviews" --> documentation

    %% User Interactions - Administrators (Infrastructure Focus)
    admins -- "Manages" --> validation_engine
    admins -- "Publishes" --> datasets
    admins -- "Maintains" --> documentation

    %% User Interactions - Consumers (Future Focus)
    consumers -- "Uses" --> analysis_tools
    consumers -- "Downloads" --> datasets
    consumers -- "Reads" --> documentation

    %% System Integration
    analysis_tools -- "Reads" --> datasets
    analysis_tools -- "References" --> validation_specs
    
    %% Quality Assurance Bridge
    validation_engine -.-> analysis_tools

    %% Styling
    style contributors fill:#e76f51,stroke:#d62828,stroke-width:2px,color:#ffffff
    style admins fill:#f4a261,stroke:#e76f51,stroke-width:2px,color:#ffffff
    style consumers fill:#2a9d8f,stroke:#264653,stroke-width:2px,color:#ffffff,stroke-dasharray:3
    style raw_datasets fill:#8d99ae,stroke:#6c757d,stroke-width:2px,color:#ffffff
    style validation_engine fill:#f4a261,stroke:#e76f51,stroke-width:2px,color:#ffffff
    style analysis_tools fill:#94d3a2,stroke:#2a9d8f,stroke-width:2px,color:#ffffff,stroke-dasharray:3
    style datasets fill:#457b9d,stroke:#1d3557,stroke-width:2px,color:#ffffff
    style validation_specs fill:#457b9d,stroke:#1d3557,stroke-width:2px,color:#ffffff
    style documentation fill:#a8dadc,stroke:#457b9d,stroke-width:1px,color:#000000
    
    linkStyle default stroke:white
```

**Use Case**: Architecture planning and detailed system understanding

---

## Context Diagram Usage Guide

### **Level 1A: Simple User Split**
- **Best For**: Executive summaries, grant proposals, stakeholder presentations
- **Shows**: Clear 90/10 user population and basic system value
- **Audience**: Non-technical stakeholders, funding bodies, project sponsors

### **Level 1B: Data Flow Focus** 
- **Best For**: Technical documentation, system integration planning
- **Shows**: What the system does (data transformation) without user complexity
- **Audience**: Technical teams, system architects, data engineers

### **Level 1C: Intermediate Detail**
- **Best For**: Development planning, architecture discussions, team alignment
- **Shows**: System components, user interactions, and development priorities
- **Audience**: Development teams, product managers, technical leads

### **Development Priority Visualization**
- **Solid lines + full color**: Current development focus (contributors, validation engine)
- **Dashed lines + muted color**: Future development focus (consumers, analysis tools)
- **Quality bridge**: How validation ensures consumer confidence behind the scenes

## Strategic Approach

**Phase 1**: Build robust contributor tools (validation engine) to ensure high-quality datasets
**Phase 2**: Develop consumer experience (analysis tools) using proven foundation

The validation system ensures dataset quality behind the scenes, enabling consumer confidence without requiring validation expertise.