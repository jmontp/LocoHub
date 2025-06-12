# User Journey Maps

## Dataset Consumers (90% - Future Focus)

The following journeys represent the primary users who will consume standardized datasets for research and analysis.

## Journey 1: Graduate Student Needs Gait Data for Exoskeleton Control

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Graduate Student: Building Exoskeleton Control System
    section Discovery
      Research existing datasets: 3: Graduate Student
      Find locomotion data repo: 5: Graduate Student
      Review available tasks: 4: Graduate Student
      Check data quality metrics: 4: Graduate Student
    section Understanding
      Read dataset documentation: 3: Graduate Student
      Understand variable names: 2: Graduate Student
      Learn phase indexing: 3: Graduate Student
      Review biomechanical conventions: 2: Graduate Student
    section Access
      Download parquet files: 5: Graduate Student
      Load data in Python: 4: Graduate Student
      Check data dimensions: 4: Graduate Student
      Verify expected variables: 3: Graduate Student
    section Analysis
      Extract control-relevant features: 5: Graduate Student
      Analyze gait phase patterns: 5: Graduate Student
      Identify control parameters: 4: Graduate Student
      Validate with literature: 3: Graduate Student
    section Implementation
      Train control algorithms: 5: Graduate Student
      Test with validation data: 4: Graduate Student
      Benchmark performance: 4: Graduate Student
      Document methodology: 2: Graduate Student
```

**Pain Points:**
- Confusing variable naming conventions across datasets
- Unclear biomechanical coordinate systems and sign conventions
- Missing documentation about data collection protocols
- Difficulty extracting phase-specific control parameters

**Emotional Journey:**
- **Discovery**: Excitement finding standardized locomotion data
- **Understanding**: Frustration with complex biomechanical conventions
- **Access**: Relief that data loads easily into existing workflow
- **Analysis**: Satisfaction with rich, clean datasets
- **Implementation**: Confidence in robust control system development

---

## Journey 2: Clinical Researcher Compares Patient Data to Healthy Norms

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Clinical Researcher: Patient Comparison Study
    section Project Setup
      Define research question: 5: Clinical Researcher
      Search for healthy norms: 4: Clinical Researcher
      Find standardized datasets: 5: Clinical Researcher
      Check population demographics: 3: Clinical Researcher
    section Data Preparation
      Download reference datasets: 5: Clinical Researcher
      Load with Python library: 4: Clinical Researcher
      Filter by demographics: 3: Clinical Researcher
      Calculate population statistics: 4: Clinical Researcher
    section Patient Analysis
      Load patient data: 3: Clinical Researcher
      Convert to standard format: 2: Clinical Researcher
      Compare to healthy norms: 5: Clinical Researcher
      Identify deviations: 5: Clinical Researcher
    section Interpretation
      Understand clinical significance: 4: Clinical Researcher
      Correlate with symptoms: 5: Clinical Researcher
      Generate patient report: 3: Clinical Researcher
      Discuss with clinicians: 5: Clinical Researcher
    section Publication
      Write methods section: 4: Clinical Researcher
      Cite dataset properly: 3: Clinical Researcher
      Submit to journal: 4: Clinical Researcher
      Share findings: 5: Clinical Researcher
```

**Pain Points:**
- Uncertainty about appropriate healthy reference populations
- Converting patient data to match standard format
- Understanding statistical significance of deviations
- Proper attribution and citation requirements

**Emotional Journey:**
- **Project Setup**: Confidence in finding quality reference data
- **Data Preparation**: Satisfaction with easy data access
- **Patient Analysis**: Excitement discovering clear patterns
- **Interpretation**: Professional fulfillment helping patients
- **Publication**: Pride in contributing to clinical knowledge

---

## Journey 3: Biomechanics Engineer Tests Algorithm Performance

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Biomechanics Engineer: Algorithm Development
    section Algorithm Design
      Define processing goals: 5: Biomechanics Engineer
      Review existing methods: 4: Biomechanics Engineer
      Design new approach: 5: Biomechanics Engineer
      Need validation data: 4: Biomechanics Engineer
    section Data Discovery
      Search for test datasets: 3: Biomechanics Engineer
      Find standardized repository: 5: Biomechanics Engineer
      Review data diversity: 4: Biomechanics Engineer
      Check sampling rates: 4: Biomechanics Engineer
    section Implementation
      Download test datasets: 5: Biomechanics Engineer
      Load without library: 4: Biomechanics Engineer
      Process with algorithms: 5: Biomechanics Engineer
      Compare results: 4: Biomechanics Engineer
    section Validation
      Test across multiple tasks: 5: Biomechanics Engineer
      Analyze edge cases: 3: Biomechanics Engineer
      Benchmark performance: 4: Biomechanics Engineer
      Identify limitations: 3: Biomechanics Engineer
    section Documentation
      Document performance: 3: Biomechanics Engineer
      Create usage examples: 2: Biomechanics Engineer
      Publish algorithm: 4: Biomechanics Engineer
      Share with community: 5: Biomechanics Engineer
```

**Pain Points:**
- Finding datasets with sufficient diversity for robust testing
- Understanding data preprocessing and filtering applied
- Ensuring fair comparison across different collection protocols
- Managing large datasets efficiently

**Emotional Journey:**
- **Algorithm Design**: Creative excitement about new methods
- **Data Discovery**: Relief finding comprehensive test data
- **Implementation**: Technical satisfaction with clean data access
- **Validation**: Confidence in robust algorithm performance
- **Documentation**: Professional pride in advancing the field

---

## Journey 4: Sports Scientist Analyzes Athletic Performance

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Sports Scientist: Athletic Performance Analysis
    section Research Planning
      Define performance questions: 5: Sports Scientist
      Review sport-specific needs: 4: Sports Scientist
      Search for relevant datasets: 3: Sports Scientist
      Find locomotion standards: 4: Sports Scientist
    section Data Exploration
      Browse available datasets: 4: Sports Scientist
      Check task relevance: 3: Sports Scientist
      Review subject demographics: 3: Sports Scientist
      Download sample data: 4: Sports Scientist
    section Analysis Setup
      Load data with MATLAB: 4: Sports Scientist
      Learn phase conventions: 2: Sports Scientist
      Identify performance metrics: 5: Sports Scientist
      Extract key variables: 4: Sports Scientist
    section Performance Analysis
      Calculate efficiency metrics: 5: Sports Scientist
      Compare to normative data: 4: Sports Scientist
      Identify optimization targets: 5: Sports Scientist
      Correlate with outcomes: 4: Sports Scientist
    section Application
      Design training interventions: 5: Sports Scientist
      Monitor athlete progress: 4: Sports Scientist
      Validate improvements: 4: Sports Scientist
      Share with coaches: 5: Sports Scientist
```

**Pain Points:**
- Limited sport-specific locomotion tasks in datasets
- Uncertainty about relevance to athletic populations
- Need for real-time analysis capabilities
- Translating research findings to practical training

**Emotional Journey:**
- **Research Planning**: Enthusiasm for evidence-based training
- **Data Exploration**: Disappointment with limited sport-specific data
- **Analysis Setup**: Frustration learning biomechanical conventions
- **Performance Analysis**: Excitement discovering performance insights
- **Application**: Fulfillment improving athlete outcomes

---

## Journey 5: Undergraduate Student Learns Biomechanics

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Undergraduate: Learning Gait Analysis
    section Course Assignment
      Receive project assignment: 3: Undergraduate Student
      Research gait analysis: 2: Undergraduate Student
      Find example datasets: 2: Undergraduate Student
      Read getting started guide: 4: Undergraduate Student
    section Learning
      Follow Python tutorial: 4: Undergraduate Student
      Understand data structure: 3: Undergraduate Student
      Learn biomechanical terms: 2: Undergraduate Student
      Complete guided exercises: 4: Undergraduate Student
    section Analysis
      Load sample dataset: 4: Undergraduate Student
      Plot gait patterns: 5: Undergraduate Student
      Calculate basic metrics: 4: Undergraduate Student
      Compare different tasks: 4: Undergraduate Student
    section Understanding
      Interpret results: 3: Undergraduate Student
      Connect to physiology: 4: Undergraduate Student
      Discuss with classmates: 4: Undergraduate Student
      Present findings: 3: Undergraduate Student
    section Mastery
      Complete advanced exercises: 4: Undergraduate Student
      Develop own analysis: 5: Undergraduate Student
      Build portfolio project: 4: Undergraduate Student
      Consider graduate studies: 5: Undergraduate Student
```

**Pain Points:**
- Overwhelming biomechanical terminology and conventions
- Steep learning curve for data analysis concepts
- Difficulty connecting data patterns to real physiology
- Limited programming experience with scientific data

**Emotional Journey:**
- **Course Assignment**: Anxiety about complex technical project
- **Learning**: Growing confidence with clear tutorials
- **Analysis**: Excitement seeing real biomechanical patterns
- **Understanding**: Satisfaction connecting theory to data
- **Mastery**: Pride in developing analytical skills

---

## Cross-Journey Insights

### **Primary User Needs (90% of users)**
1. **Easy data access** - Simple download and load workflows
2. **Clear documentation** - Understand what the data represents
3. **Standard formats** - Compatible with existing analysis tools
4. **Quality assurance** - Trust in data reliability and validity
5. **Proper attribution** - Know how to cite and reference datasets

### **Common Success Factors**
1. **Standardized variable names** across all datasets
2. **Rich documentation** explaining biomechanical conventions
3. **Multiple access methods** (direct parquet, Python library, MATLAB tools)
4. **Quality metrics** visible to build user confidence
5. **Clear tutorials** for different experience levels

### **Universal Pain Points**
1. **Biomechanical complexity** - coordinate systems, sign conventions
2. **Format conversion** between different analysis tools
3. **Population matching** for appropriate comparisons
4. **Real-time constraints** for some applications
5. **Limited task diversity** for specialized applications

### **User Personas Breakdown**
- **90% Dataset Consumers**: Researchers using standardized data for analysis
  - Graduate students (exoskeleton control, gait analysis)
  - Clinical researchers (patient comparisons, diagnostics)
  - Engineers (algorithm development, validation)
  - Sports scientists (performance analysis)
  - Students (learning biomechanics)

- **10% Dataset Contributors**: Researchers adding to the standard
  - Data validation specialists
  - Dataset curators
  - Standard developers

### **Emotional Journey Patterns**
- **Discovery Phase**: Initial excitement finding quality datasets
- **Learning Curve**: Frustration with biomechanical complexity
- **Data Access**: Relief with easy loading and standard formats
- **Analysis**: Satisfaction with rich, clean data enabling insights
- **Application**: Professional fulfillment applying research to real problems

The validation system operates behind the scenes to ensure the 90% of users can trust and effectively use the datasets without needing to understand the complex validation processes.

---

## Dataset Contributors (10% - Current Focus)

The following journeys represent the specialists who contribute to and validate the standardization ecosystem.

## Journey 6: Data Scientist Validates a New Dataset

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Data Scientist Validates New Dataset
    section Discovery
      Check dataset format: 3: Data Scientist
      Review validation docs: 4: Data Scientist
      Understand requirements: 4: Data Scientist
    section Setup
      Convert to parquet: 2: Data Scientist
      Check variable names: 3: Data Scientist
      Verify phase alignment: 2: Data Scientist
    section Validation
      Run phase validation: 5: Data Scientist
      Review validation report: 4: Data Scientist
      Check failure details: 2: Data Scientist
    section Visualization
      Generate validation plots: 5: Data Scientist
      Create animated GIFs: 4: Data Scientist
      Review visual patterns: 5: Data Scientist
    section Decision
      Assess data quality: 4: Data Scientist
      Document findings: 3: Data Scientist
      Approve for analysis: 5: Data Scientist
```

**Pain Points:**
- Variable name mismatches cause confusion
- Validation failures lack clear guidance
- Plot generation takes time for large datasets

**Emotional Journey:**
- **Discovery**: Cautious optimism about new data
- **Setup**: Frustration with format inconsistencies  
- **Validation**: Anxiety about potential failures
- **Visualization**: Excitement seeing data patterns
- **Decision**: Confidence in data quality assessment

---

## Journey 7: Data Scientist Tunes Validation Ranges

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Data Scientist Tunes Validation Ranges
    section Investigation
      Analyze validation failures: 2: Data Scientist
      Review biomechanical literature: 3: Data Scientist
      Examine outlier patterns: 2: Data Scientist
    section Analysis
      Run automated tuning: 5: Data Scientist
      Review statistical ranges: 4: Data Scientist
      Compare with literature: 3: Data Scientist
    section Adjustment
      Edit validation specs: 3: Data Scientist
      Test with sample data: 4: Data Scientist
      Iterate on ranges: 2: Data Scientist
    section Validation
      Re-run full validation: 4: Data Scientist
      Generate updated plots: 4: Data Scientist
      Verify improvements: 5: Data Scientist
    section Documentation
      Update range rationale: 3: Data Scientist
      Document changes: 2: Data Scientist
      Share with team: 4: Data Scientist
```

**Pain Points:**
- Manual range editing is tedious
- Unclear impact of range changes
- No version control for validation specs

**Emotional Journey:**
- **Investigation**: Frustration with validation failures
- **Analysis**: Hope that automation will help
- **Adjustment**: Satisfaction with data-driven ranges
- **Validation**: Relief when validation passes
- **Documentation**: Pride in improved validation system

---

## Journey 8: Data Scientist Generates Validation Reports

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Data Scientist Generates Validation Reports
    section Planning
      Define report scope: 4: Data Scientist
      Select datasets: 4: Data Scientist
      Choose visualization types: 3: Data Scientist
    section Generation
      Run validation pipeline: 5: Data Scientist
      Generate static plots: 4: Data Scientist
      Create animated GIFs: 4: Data Scientist
    section Review
      Check plot quality: 4: Data Scientist
      Verify data patterns: 5: Data Scientist
      Identify anomalies: 3: Data Scientist
    section Compilation
      Organize outputs: 3: Data Scientist
      Write summary: 3: Data Scientist
      Prepare presentation: 4: Data Scientist
    section Sharing
      Present to stakeholders: 4: Data Scientist
      Discuss findings: 5: Data Scientist
      Archive results: 2: Data Scientist
```

**Pain Points:**
- Long generation times for comprehensive reports
- Manual organization of multiple output files
- Inconsistent plot formatting across datasets

**Emotional Journey:**
- **Planning**: Excitement about showcasing data insights
- **Generation**: Anticipation mixed with concern about processing time
- **Review**: Satisfaction with visual data quality
- **Compilation**: Mild frustration with manual organization
- **Sharing**: Pride in comprehensive validation results

---

## Journey 9: Data Scientist Debugs Validation Failures

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Data Scientist Debugs Validation Failures
    section Detection
      Receive failure notification: 1: Data Scientist
      Open validation report: 2: Data Scientist
      Identify failure scope: 2: Data Scientist
    section Investigation
      Examine failed variables: 2: Data Scientist
      Check validation ranges: 3: Data Scientist
      Review raw data: 2: Data Scientist
    section Analysis
      Compare with standards: 3: Data Scientist
      Identify root cause: 4: Data Scientist
      Assess data vs rules: 4: Data Scientist
    section Resolution
      Fix data issues: 3: Data Scientist
      Adjust validation ranges: 4: Data Scientist
      Re-run validation: 5: Data Scientist
    section Verification
      Confirm fixes work: 5: Data Scientist
      Document resolution: 3: Data Scientist
      Update procedures: 2: Data Scientist
```

**Pain Points:**
- Unclear error messages make debugging difficult
- No guidance on whether to fix data or ranges
- Time-consuming iterative process

**Emotional Journey:**
- **Detection**: Anxiety about data quality issues
- **Investigation**: Frustration with unclear diagnostics
- **Analysis**: Growing confidence as patterns emerge
- **Resolution**: Satisfaction with problem-solving
- **Verification**: Relief and confidence in data quality

---

## Combined Insights

### **Consumer vs Contributor Patterns**
- **Consumers**: Focus on data access, analysis, and application
- **Contributors**: Focus on quality assurance, validation, and system improvement
- **Shared Need**: Clear documentation and reliable tools
- **Key Difference**: Contributors need debugging/tuning tools, consumers need analysis tools