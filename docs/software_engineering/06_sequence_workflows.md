# Sequence Diagrams - Dataset Consumer Workflows

## Sequence 1: Graduate Student Loads Data for Exoskeleton Control

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant GS as Graduate Student
    participant BR as Browser/GitHub
    participant DR as Data Repository
    participant PF as Parquet File
    participant PY as Python Environment
    participant LD as LocomotionData
    participant NP as NumPy/Analysis
    participant EX as Exoskeleton System

    GS->>BR: search "standardized gait data"
    BR-->>GS: find locomotion-data-standardization repo
    
    GS->>DR: browse available datasets
    DR-->>GS: show GTech2023, UMich2021, AddBio datasets
    
    GS->>DR: download gtech_2023_phase.parquet
    DR->>PF: transfer dataset file
    PF-->>GS: save to local machine
    
    GS->>PY: import locomotion_analysis
    GS->>LD: data = LocomotionData.from_parquet("gtech_2023_phase.parquet")
    LD->>PF: read parquet file
    PF-->>LD: return structured data
    LD-->>GS: return LocomotionData object
    
    GS->>LD: tasks = data.get_available_tasks()
    LD-->>GS: ['level_walking', 'incline_walking']
    
    GS->>LD: walking_data = data.filter_by_task('level_walking')
    LD-->>GS: filtered LocomotionData object
    
    GS->>LD: phase_data = walking_data.get_phase_data([0, 25, 50, 75])
    LD-->>GS: phase-specific joint angles and moments
    
    GS->>NP: extract control features (hip, knee, ankle angles)
    NP-->>GS: control parameter arrays
    
    GS->>NP: train control algorithms with gait patterns
    NP-->>GS: trained control models
    
    GS->>EX: deploy control algorithms to exoskeleton
    EX-->>GS: real-time gait assistance feedback
    
    GS->>GS: document methodology and performance
```

---

## Sequence 2: Clinical Researcher Compares Patient Data to Healthy Norms

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant CR as Clinical Researcher
    participant DR as Data Repository
    participant HD as Healthy Dataset
    participant PD as Patient Data
    participant PY as Python Environment
    participant LD as LocomotionData
    participant SP as SciPy/Stats
    participant RP as Research Publication

    CR->>DR: search for healthy reference data
    DR-->>CR: provide normative datasets with demographics
    
    CR->>DR: download healthy adult walking data
    DR->>HD: transfer reference dataset
    HD-->>CR: healthy_norms.parquet
    
    CR->>PY: import locomotion_analysis, scipy.stats
    CR->>LD: healthy_data = LocomotionData.from_parquet("healthy_norms.parquet")
    LD->>HD: read healthy reference data
    HD-->>LD: return healthy locomotion patterns
    LD-->>CR: healthy LocomotionData object
    
    CR->>LD: patient_data = LocomotionData.from_parquet("patient_gait.parquet")
    LD->>PD: read patient data
    PD-->>LD: return patient locomotion patterns
    LD-->>CR: patient LocomotionData object
    
    CR->>LD: healthy_stats = healthy_data.calculate_population_stats()
    LD-->>CR: mean, std, percentiles for each variable
    
    CR->>LD: patient_values = patient_data.get_joint_angles('level_walking')
    LD-->>CR: patient joint angle patterns
    
    CR->>SP: z_scores = calculate_deviations(patient_values, healthy_stats)
    SP-->>CR: standardized deviation scores
    
    CR->>SP: p_values = perform_statistical_tests(patient_values, healthy_stats)
    SP-->>CR: statistical significance results
    
    CR->>CR: identify clinically significant deviations
    CR->>CR: correlate with patient symptoms
    
    CR->>RP: write methods: "Healthy reference data from standardized repository"
    CR->>RP: report statistical comparisons and clinical findings
    RP-->>CR: published clinical research
```

---

## Sequence 3: Biomechanics Engineer Tests Algorithm Without Library

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant BE as Biomechanics Engineer
    participant DR as Data Repository
    participant PF as Parquet File
    participant PD as Pandas
    participant AL as Algorithm
    participant VT as Validation Tests
    participant PU as Publication

    BE->>DR: download diverse locomotion datasets
    DR->>PF: transfer multiple parquet files
    PF-->>BE: [gtech2023.parquet, umich2021.parquet, addbio.parquet]
    
    BE->>PD: df = pd.read_parquet("gtech2023.parquet")
    PD->>PF: read parquet directly
    PF-->>PD: return pandas DataFrame
    PD-->>BE: raw locomotion data
    
    BE->>PD: inspect data structure and variable names
    PD-->>BE: show columns, data types, sample values
    
    BE->>PD: walking_data = df[df['task'] == 'level_walking']
    PD-->>BE: filtered walking data
    
    BE->>PD: joint_angles = walking_data[['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad']]
    PD-->>BE: joint angle time series
    
    BE->>AL: processed_data = algorithm.process(joint_angles)
    AL-->>BE: algorithm output (e.g., gait events, features)
    
    loop Test across multiple datasets
        BE->>PD: load next dataset
        PD-->>BE: different population data
        BE->>AL: test algorithm performance
        AL-->>BE: performance metrics
        BE->>VT: record accuracy, robustness
    end
    
    BE->>VT: aggregate performance across datasets
    VT-->>BE: overall algorithm validation results
    
    BE->>BE: identify algorithm limitations and edge cases
    BE->>AL: refine algorithm based on diverse data
    
    BE->>PU: document algorithm performance on standardized datasets
    BE->>PU: provide reproducible validation methodology
    PU-->>BE: published algorithm with validation
```

---

## Sequence 4: Sports Scientist Analyzes Performance with MATLAB

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant SS as Sports Scientist
    participant DR as Data Repository
    participant PF as Parquet File
    participant ML as MATLAB
    participant LM as Locomotion MATLAB Lib
    participant SA as Statistical Analysis
    participant CO as Coaching

    SS->>DR: browse for athletic-relevant locomotion data
    DR-->>SS: show available tasks and populations
    
    SS->>DR: download incline walking and running data
    DR->>PF: transfer locomotion datasets
    PF-->>SS: athletic_locomotion.parquet
    
    SS->>ML: open MATLAB environment
    SS->>LM: addpath('locomotion_matlab_lib')
    SS->>LM: data = load_locomotion_data('athletic_locomotion.parquet')
    LM->>PF: read parquet using MATLAB tools
    PF-->>LM: return structured locomotion data
    LM-->>SS: MATLAB struct with locomotion data
    
    SS->>LM: tasks = get_available_tasks(data)
    LM-->>SS: {'level_walking', 'incline_walking'}
    
    SS->>LM: incline_data = filter_by_task(data, 'incline_walking')
    LM-->>SS: filtered incline walking data
    
    SS->>LM: power_metrics = calculate_power_efficiency(incline_data)
    LM-->>SS: mechanical power and efficiency measures
    
    SS->>SA: [efficiency_stats] = analyze_performance_patterns(power_metrics)
    SA-->>SS: statistical summaries and trends
    
    SS->>LM: visualize_gait_patterns(incline_data, 'power_efficiency')
    LM-->>SS: MATLAB plots showing efficiency patterns
    
    SS->>SA: correlate efficiency with performance outcomes
    SA-->>SS: correlation analysis results
    
    SS->>SS: identify optimization targets for training
    SS->>CO: design evidence-based training interventions
    CO-->>SS: improved athletic performance protocols
    
    SS->>SS: document findings for sports science publication
```

---

## Sequence 5: Undergraduate Student Follows Tutorial

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant US as Undergraduate Student
    participant TU as Tutorial Documentation
    participant DR as Data Repository
    participant TD as Tutorial Data
    participant PY as Python Environment
    participant LD as LocomotionData
    participant EX as Exercise Solutions
    participant PR as Professor

    US->>TU: open "Getting Started with Locomotion Data" tutorial
    TU-->>US: step-by-step Python tutorial with examples
    
    US->>DR: follow tutorial link to download sample data
    DR->>TD: provide tutorial_sample.parquet
    TD-->>US: small, educational dataset
    
    US->>PY: install locomotion_analysis package
    PY-->>US: package installation confirmation
    
    US->>TU: follow Tutorial Step 1: Loading Data
    TU-->>US: "data = LocomotionData.from_parquet('tutorial_sample.parquet')"
    
    US->>LD: execute tutorial code
    LD->>TD: load tutorial dataset
    TD-->>LD: return sample locomotion data
    LD-->>US: tutorial LocomotionData object
    
    US->>TU: follow Tutorial Step 2: Exploring Data Structure
    TU-->>US: "print(data.get_available_tasks())"
    US->>LD: explore data structure
    LD-->>US: show available tasks and variables
    
    US->>TU: follow Tutorial Step 3: Basic Analysis
    TU-->>US: guided exercise to plot gait patterns
    US->>LD: plot joint angles over gait cycle
    LD-->>US: matplotlib plots showing biomechanical patterns
    
    US->>TU: complete tutorial exercises
    TU-->>US: provide exercise questions and expected outputs
    US->>EX: work through guided problems
    EX-->>US: understanding of gait analysis concepts
    
    US->>US: connect data patterns to biomechanics theory
    US->>PR: discuss findings and ask questions
    PR-->>US: feedback and deeper biomechanical insights
    
    US->>US: develop confidence in locomotion data analysis
    US->>US: consider advanced projects and research opportunities
```

---

## Cross-Sequence Insights

### **Primary User Interaction Patterns**

1. **Data Discovery**: Users find datasets through documentation, repositories, or tutorials
2. **Direct Access**: Most users download parquet files directly without complex setup
3. **Flexible Loading**: Users choose between library tools (Python/MATLAB) or direct pandas access
4. **Domain-Specific Analysis**: Each user group has specific analysis patterns and goals
5. **Quality Trust**: Users rely on behind-the-scenes validation without direct interaction

### **Key System Components for Consumers**

1. **Data Repository**: Central source for standardized parquet files
2. **LocomotionData Library**: Python library for common analysis patterns
3. **MATLAB Tools**: MATLAB library for MATLAB-native workflows
4. **Documentation System**: Tutorials, API docs, and getting started guides
5. **Quality Assurance**: Invisible validation system that builds user confidence

### **Consumer Success Factors**

1. **Easy Discovery**: Clear documentation and searchable dataset catalogs
2. **Multiple Access Methods**: Library tools AND direct parquet access
3. **Rich Metadata**: Demographics, collection protocols, quality metrics
4. **Standard Formats**: Consistent variable names and data structures
5. **Educational Resources**: Tutorials for different experience levels

### **Performance & Usability Considerations**

1. **Download Speed**: Efficient data repository with fast access
2. **Memory Efficiency**: Library tools handle large datasets gracefully
3. **Platform Compatibility**: Works in Python, MATLAB, R, and direct parquet readers
4. **Error Handling**: Clear error messages when data loading fails
5. **Documentation**: Always up-to-date with working code examples

### **Validation System Role**

The validation system operates **behind the scenes** to ensure:
- **Data Quality**: All published datasets meet biomechanical standards
- **Consistency**: Standardized variable names and formats across datasets
- **Trust**: Users can confidently use data without validating it themselves
- **Discoverability**: Quality metrics help users choose appropriate datasets

### **User-Centric Design Principles**

1. **90% of users consume data**: Focus on easy access and analysis tools
2. **10% of users contribute data**: Validation tools support quality assurance
3. **Multiple skill levels**: From undergraduate tutorials to advanced research
4. **Multiple domains**: Clinical, engineering, sports, academic applications
5. **Multiple tools**: Python, MATLAB, R, and direct data access

These consumer-focused sequences show how the standardized locomotion data ecosystem serves its primary users while the validation system ensures quality behind the scenes.

---

## Dataset Contributor Workflows (10% - Current Focus)

The following sequences represent the technical workflows for specialists who validate and contribute datasets.

## Sequence 6: Data Scientist Validates a New Dataset

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DS as Data Scientist
    participant VP as validate_phase_data.py
    participant PV as PhaseValidator
    participant LD as LocomotionData
    participant SM as SpecificationManager
    participant VS as Validation Specs
    participant PD as Parquet Dataset
    participant VR as Validation Report

    DS->>VP: python validate_phase_data.py dataset.parquet
    VP->>PV: validate_dataset(dataset_path)
    
    PV->>LD: load_dataset(dataset_path)
    LD->>PD: read parquet file
    PD-->>LD: return locomotion data
    LD-->>PV: return LocomotionData object
    
    PV->>SM: load_validation_specs(mode='kinematic')
    SM->>VS: read validation rules
    VS-->>SM: return validation ranges
    SM-->>PV: return parsed specifications
    
    loop For each task-phase-variable
        PV->>PV: check_value_ranges(data, specs)
        alt Value in range
            PV->>PV: record_pass()
        else Value out of range
            PV->>PV: record_failure(details)
        end
    end
    
    PV->>VR: generate_validation_report(results)
    VR-->>PV: report file path
    PV-->>VP: return validation results
    VP-->>DS: display summary + report path
    
    DS->>DS: review validation report
    DS->>DS: decide on data quality
```

---

## Sequence 7: Data Scientist Tunes Validation Ranges

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DS as Data Scientist
    participant AT as auto_tune_ranges.py
    participant ATL as AutomatedTuner
    participant LD as LocomotionData
    participant PD as Parquet Dataset
    participant SM as SpecificationManager
    participant VS as Validation Specs
    participant FC as FeatureConstants

    DS->>AT: python auto_tune_ranges.py --dataset data.parquet --method percentile_95
    AT->>ATL: AutomatedTuner(dataset_path, mode)
    
    ATL->>LD: load_dataset(dataset_path)
    LD->>PD: read parquet file
    PD-->>LD: return locomotion data
    LD-->>ATL: return LocomotionData object
    
    ATL->>FC: get_feature_list(mode)
    FC-->>ATL: return standard features
    
    loop For each task
        loop For each phase [0%, 25%, 50%, 75%]
            loop For each variable
                ATL->>ATL: extract_phase_values(task, phase, variable)
                ATL->>ATL: calculate_statistical_range(values, method)
            end
        end
    end
    
    ATL->>ATL: generate_statistics_report(ranges, method)
    ATL->>SM: write_validation_data(ranges, mode)
    SM->>VS: update validation specifications
    VS-->>SM: confirm write
    SM-->>ATL: confirm update
    
    ATL-->>AT: return tuning results
    AT-->>DS: display tuning summary + statistics
    
    DS->>DS: review statistical ranges
    DS->>DS: approve automated changes
```

---

## Sequence 8: Data Scientist Generates Validation Reports

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DS as Data Scientist
    participant GP as generate_validation_plots.py
    participant PE as PlotEngine
    participant GG as generate_validation_gifs.py
    participant GE as GifEngine
    participant LD as LocomotionData
    participant SM as SpecificationManager
    participant PD as Parquet Dataset
    participant VS as Validation Specs
    participant VR as Validation Report

    par Generate Static Plots
        DS->>GP: python generate_validation_plots.py --dataset data.parquet
        GP->>PE: PlotEngine(dataset_path)
        
        PE->>LD: load_dataset(dataset_path)
        LD->>PD: read parquet file
        PD-->>LD: return locomotion data
        LD-->>PE: return LocomotionData object
        
        PE->>SM: load_validation_specs()
        SM->>VS: read validation rules
        VS-->>SM: return validation ranges
        SM-->>PE: return parsed specifications
        
        loop For each task
            PE->>PE: generate_filters_by_phase_plot(task)
            PE->>PE: generate_forward_kinematics_plots(task)
            PE->>VR: save plot files
        end
        
        PE-->>GP: return plot generation results
        GP-->>DS: display plot summary
    
    and Generate Animated GIFs
        DS->>GG: python generate_validation_gifs.py --dataset data.parquet
        GG->>GE: GifEngine(dataset_path)
        
        GE->>LD: load_dataset(dataset_path)
        LD->>PD: read parquet file
        PD-->>LD: return locomotion data
        LD-->>GE: return LocomotionData object
        
        loop For each task
            GE->>GE: create_walking_animation(task)
            GE->>GE: overlay_validation_ranges()
            GE->>VR: save GIF files
        end
        
        GE-->>GG: return GIF generation results
        GG-->>DS: display GIF summary
    end
    
    DS->>VR: organize validation outputs
    DS->>DS: compile comprehensive report
    DS->>DS: present findings to stakeholders
```

---

## Sequence 9: Data Scientist Debugs Validation Failures

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant DS as Data Scientist
    participant VP as validate_phase_data.py
    participant PV as PhaseValidator
    participant MS as manage_validation_specs.py
    participant SM as SpecificationManager
    participant VS as Validation Specs
    participant VR as Validation Report

    DS->>VP: python validate_phase_data.py dataset.parquet
    VP->>PV: validate_dataset(dataset_path)
    PV-->>VP: return validation failures
    VP-->>DS: display failure summary
    
    DS->>VR: review detailed failure report
    VR-->>DS: show failed variables and ranges
    
    alt Fix validation ranges
        DS->>MS: python manage_validation_specs.py --edit kinematic
        MS->>SM: load_current_specs()
        SM->>VS: read current validation rules
        VS-->>SM: return current ranges
        SM-->>MS: return editable specifications
        
        MS-->>DS: open interactive editor
        DS->>MS: modify validation ranges
        MS->>SM: save_updated_specs(modified_ranges)
        SM->>VS: write updated validation rules
        VS-->>SM: confirm save
        SM-->>MS: confirm update
        MS-->>DS: display save confirmation
        
    else Fix data issues
        DS->>DS: identify data quality problems
        DS->>DS: clean or filter problematic data
        DS->>DS: regenerate parquet file
    end
    
    DS->>VP: python validate_phase_data.py dataset.parquet
    VP->>PV: validate_dataset(dataset_path)
    
    alt Validation passes
        PV-->>VP: return success
        VP-->>DS: display validation success
        DS->>DS: document resolution steps
    else Validation still fails
        PV-->>VP: return remaining failures
        VP-->>DS: display updated failure summary
        DS->>DS: iterate debugging process
    end
```

---

## Combined Sequence Analysis

### **Consumer vs Contributor Interaction Patterns**

**Consumer Patterns:**
1. **Simple Data Access**: Direct parquet loading or library usage
2. **Domain-Specific Analysis**: Each user group has specific workflows
3. **Quality Trust**: Users rely on behind-the-scenes validation
4. **Multiple Access Methods**: Library tools AND direct data access

**Contributor Patterns:**  
1. **Complex Validation Workflows**: Multi-step quality assurance processes
2. **Iterative Problem Solving**: Debugging and range tuning cycles
3. **Tool Integration**: Multiple specialized tools working together
4. **Quality Assurance**: Focus on ensuring data meets standards

### **Shared Integration Points**
1. **LocomotionData**: Central data access layer for both user types
2. **SpecificationManager**: Validation rules accessed by contributors, trusted by consumers  
3. **FeatureConstants**: Shared variable definitions ensure consistency
4. **Quality Bridge**: Validation system enables consumer confidence

---

## Sequence 10: System Administrator Creates ML Benchmark Release

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant SA as System Administrator
    participant BC as create_benchmarks.py
    participant QA as Quality Assessment
    participant VS as Validated Datasets
    participant BS as Benchmark Suite
    participant DR as Data Repository
    participant CI as CI/CD Pipeline
    participant CM as Community

    SA->>QA: review validated dataset quality scores
    QA-->>SA: show quality metrics and coverage statistics
    
    SA->>BC: python create_benchmarks.py --split-strategy subject gtech2023.parquet umich2021.parquet ./ml_benchmarks/
    BC->>VS: load quality-validated datasets
    VS-->>BC: return combined locomotion data
    
    BC->>BC: create subject-based train/validation/test splits
    BC->>BC: validate no data leakage between splits
    BC->>BC: extract ML-ready features (scikit-learn, PyTorch, TensorFlow)
    BC->>BC: train baseline models for performance targets
    
    BC->>BS: generate benchmark suite with documentation
    BS-->>BC: confirm benchmark creation
    BC-->>SA: display benchmark creation summary
    
    SA->>BS: review benchmark quality metrics
    BS-->>SA: show split demographics, leakage analysis, baseline performance
    
    SA->>CI: commit benchmark suite to release branch
    CI->>CI: run automated tests and validation
    CI->>DR: deploy benchmark to public data repository
    DR-->>CI: confirm deployment success
    CI-->>SA: release deployment notification
    
    SA->>CM: announce new ML benchmark release
    CM-->>SA: community feedback and adoption metrics
    
    SA->>SA: monitor benchmark usage and performance
    SA->>SA: document lessons learned for future releases
```

---

The combined workflows show how all three user types contribute to the locomotion data standardization ecosystem:
- **Consumers (90%)** rely on simple, reliable data access
- **Contributors (9%)** ensure data quality through validation workflows  
- **Administrators (1%)** manage infrastructure and enable community growth

The contributor workflows ensure the quality that enables simple consumer workflows, while administrator workflows ensure the infrastructure supports both groups effectively.