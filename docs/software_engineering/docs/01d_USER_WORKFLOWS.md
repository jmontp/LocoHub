---
title: User Workflows
tags: [workflows, guides, sequences]
status: ready
---

# User Workflows

!!! info ":walking: **You are here** → User Workflow Guides"
    **Purpose:** Step-by-step workflow guides for dataset contributors and validators
    
    **Who should read this:** Dataset curators, biomechanical validators, system users
    
    **Value:** Practical guidance for common tasks with clear success indicators
    
    **Connection:** User-friendly guides based on [Architecture - Sequence Diagrams](03a_SEQUENCE_DIAGRAMS.md)
    
    **:clock4: Reading time:** 20 minutes | **:walking: Workflows:** 4 comprehensive guides

!!! abstract "TL;DR"
    **User-friendly workflow guides for common tasks:**
    
    - **Convert raw datasets** to standard format (30-60 min)
    - **Update validation ranges** manually or automatically (15-30 min)
    - **Generate quality reports** for dataset assessment (5-15 min)
    - **Troubleshoot common issues** with clear solutions

**Practical step-by-step guides for dataset contributors and validators.**

---

## Workflow 1: Converting Raw Dataset to Standard Format

**Purpose:** Transform raw biomechanical data into standardized parquet format
**Time:** 30-60 minutes | **Users:** Dataset curators with programming experience

### Prerequisites

- Raw dataset files (typically `.mat` files)
- Python environment with required dependencies
- Access to example conversion scripts

### Step-by-Step Instructions

#### Step 1: Review Documentation and Examples (10-15 min)
1. **Read validation scaffolding docs**
   - Check `docs/standard_spec/` for format requirements
   - Review variable naming conventions and units
   
2. **Study example conversion scripts**
   - Examine GTech2023: `source/conversion_scripts/Gtech_2023/`
   - Review UMich2021: `source/conversion_scripts/Umich_2021/`
   - Check AddBiomechanics: `source/conversion_scripts/AddBiomechanics/`

#### Step 2: Analyze Raw Dataset (10-15 min)
1. **Examine file structure**
   ```python
   # Load and inspect your raw data
   import scipy.io
   data = scipy.io.loadmat('your_dataset.mat')
   print(data.keys())  # See available variables
   ```

2. **Map variable names to standards**
   - Create mapping from raw names to standard names
   - Check units match specification requirements
   - Identify required vs optional variables

#### Step 3: Develop Conversion Script (15-30 min)
1. **Create dataset-specific script**
   ```python
   # Follow this general pattern
   def convert_dataset():
       # Read raw data files
       raw_data = load_raw_files()
       
       # Map variables to standard names
       standard_data = map_to_standard_format(raw_data)
       
       # Write time-indexed parquet file
       write_parquet(standard_data, 'dataset_time.parquet')
   ```

2. **Test conversion on sample data**
   - Start with one subject/trial
   - Verify output structure matches standards

#### Step 4: Generate Phase-Indexed Dataset (5 min)
```bash
python conversion_generate_phase_dataset.py dataset_time.parquet
```

**What this does:**
- Detects gait cycles from vertical ground reaction forces
- Interpolates each cycle to exactly 150 points
- Creates `dataset_phase.parquet` automatically

#### Step 5: Validate Conversion Quality (5-10 min)
```bash
python validation_dataset_report.py dataset_phase.parquet
```

**Expected outputs:**
- Comprehensive quality report in `reports/` directory
- Summary of validation passes/failures
- Quality metrics and recommendations

### Success Indicators
- ✅ Phase dataset has exactly 150 points per gait cycle
- ✅ All required variables present with correct units
- ✅ Validation report shows acceptable failure rates
- ✅ No critical data integrity issues

### Common Troubleshooting

**Issue:** Phase conversion fails
- **Solution:** Check if vertical GRF data exists and has clear heel strikes
- **Command:** Inspect GRF data: `python -c "import pandas as pd; df=pd.read_parquet('dataset_time.parquet'); print(df.filter(regex='vertical').columns)"`

**Issue:** High validation failure rates
- **Solution:** Review variable mapping and units
- **Action:** Compare with working example scripts

**Issue:** Missing required variables
- **Solution:** Check if variables exist in raw data or can be calculated
- **Reference:** See `docs/standard_spec/standard_spec.md` for requirements

---

## Workflow 2: Manual Validation Range Updates

**Purpose:** Update validation ranges based on biomechanical literature
**Time:** 15-30 minutes | **Users:** Biomechanical validators with domain expertise

### Prerequisites

- Recent biomechanical literature with updated ranges
- Understanding of validation impact on existing datasets

### Step-by-Step Instructions

#### Step 1: Prepare Literature Review (5-10 min)
1. **Gather updated ranges with citations**
   - Document specific joint angles, moments, or powers
   - Note population characteristics and methodology
   - Prepare rationale for changes

#### Step 2: Launch Interactive Editor (1 min)
```bash
python validation_manual_tune_spec.py --edit kinematic
# or for kinetic variables:
python validation_manual_tune_spec.py --edit kinetic
```

**What opens:**
- Interactive interface showing current validation ranges
- Input fields for new ranges with citation support
- Preview of changes before committing

#### Step 3: Input New Ranges (5-10 min)
1. **Select variables to update**
   - Choose specific joint angles or moments
   - Select relevant locomotion tasks
   
2. **Enter new ranges with citations**
   - Input minimum and maximum values
   - Add literature citations and rationale
   - Review integrity warnings for NaNs or missing data

#### Step 4: Preview Impact (2-3 min)
- **Review affected datasets:** See which datasets will be impacted
- **Check validation plots:** Automatic generation of range visualizations
- **Verify integrity:** Ensure no missing cyclic tasks or data issues

#### Step 5: Apply Changes (1-2 min)
1. **Review staging plots**
   - Compare current vs proposed ranges
   - Verify ranges look reasonable on actual data
   
2. **Commit to live specifications**
   - Approve changes if plots look good
   - System automatically updates validation specs
   - Receive success confirmation

### Success Indicators
- ✅ Staging plots show reasonable ranges on real data
- ✅ No integrity warnings about missing cyclic tasks
- ✅ Literature citations properly documented
- ✅ Impact analysis shows acceptable dataset effects

### Common Troubleshooting

**Issue:** Ranges too restrictive (high failure rates)
- **Solution:** Review literature methodology vs dataset characteristics
- **Action:** Adjust ranges based on population differences

**Issue:** Missing cyclic task warnings
- **Solution:** Ensure all locomotion tasks have appropriate ranges
- **Reference:** Check `docs/standard_spec/task_definitions.md`

**Issue:** Plots show data outside new ranges
- **Solution:** Verify if this represents true outliers or overly strict ranges
- **Action:** Consider percentile-based adjustments

---

## Workflow 3: Automatic Validation Range Optimization

**Purpose:** Update validation ranges using statistical analysis of existing datasets
**Time:** 10-20 minutes | **Users:** Biomechanical validators seeking data-driven ranges

### Prerequisites

- Combined dataset file with multiple studies
- Understanding of statistical methods for range calculation

### Step-by-Step Instructions

#### Step 1: Launch Statistical Analysis (1 min)
```bash
python validation_auto_tune_spec.py --dataset combined_data.parquet --method percentile_95
```

**Available methods:**
- `percentile_95`: Use 2.5th to 97.5th percentiles
- `iqr_extended`: Interquartile range with 1.5x extension
- `mean_3std`: Mean ± 3 standard deviations

#### Step 2: Review Statistical Proposals (5-10 min)
1. **Examine proposed ranges**
   - Statistical justification for each variable
   - Comparison with current ranges
   - Impact analysis on existing datasets

2. **Validate methodology appropriateness**
   - Check if method suits variable distribution
   - Review outlier handling approach
   - Verify population representation

#### Step 3: Preview and Validate (3-5 min)
- **Automatic plot generation:** Shows data distribution vs proposed ranges
- **Integrity checking:** Validates no missing cyclic tasks or NaN values
- **Impact assessment:** Previews effects on validation pass rates

#### Step 4: Review Range Visualizations (2-3 min)
1. **Check distribution plots**
   - Verify ranges capture appropriate data spread
   - Look for bimodal or skewed distributions
   - Assess outlier inclusion/exclusion

2. **Compare with biomechanical expectations**
   - Ensure ranges align with physiological limits
   - Check for unrealistic values

#### Step 5: Apply or Refine (1-2 min)
1. **If ranges look good:**
   - Commit staging to live specifications
   - Receive confirmation of successful update
   
2. **If refinement needed:**
   - Adjust statistical method parameters
   - Regenerate plots with refined ranges
   - Repeat validation process

### Success Indicators
- ✅ Statistical ranges align with biomechanical expectations
- ✅ Data distribution plots show appropriate coverage
- ✅ No significant increase in false positive failures
- ✅ Methodology appropriate for variable characteristics

### Common Troubleshooting

**Issue:** Ranges too wide (miss true outliers)
- **Solution:** Use more restrictive statistical method
- **Action:** Try `percentile_90` or `iqr_standard`

**Issue:** Ranges too narrow (high false positive rate)
- **Solution:** Use more inclusive statistical method
- **Action:** Try `percentile_99` or `mean_4std`

**Issue:** Bimodal distributions create poor ranges
- **Solution:** Consider task-specific or population-specific ranges
- **Action:** Split analysis by locomotion task or demographic groups

---

## Workflow 4: Generating Dataset Quality Reports

**Purpose:** Assess dataset quality for contribution decisions or analysis planning
**Time:** 5-15 minutes | **Users:** Dataset curators and researchers

### Prerequisites

- Phase-indexed parquet dataset file
- Understanding of quality metrics interpretation

### Step-by-Step Instructions

#### Step 1: Run Quality Assessment (1-2 min)
```bash
python validation_dataset_report.py your_dataset_phase.parquet
```

**Optional flags:**
- `--generate-gifs`: Create animated visualizations (adds 5-10 min)
- `--verbose`: Show detailed validation messages
- `--output-dir reports/`: Specify report location

#### Step 2: Review Report Summary (2-3 min)
**Displayed immediately:**
- Dataset type detection (phase vs time-indexed)
- Overall validation pass rate
- Critical issues requiring attention
- Quality score summary

#### Step 3: Examine Detailed Report (5-10 min)
**Report location:** `reports/quality_report_[dataset]_[timestamp].html`

**Key sections to review:**
1. **Coverage Statistics**
   - Number of subjects, trials, and gait cycles
   - Variable completeness rates
   - Task distribution

2. **Validation Results**
   - Pass/fail summary by variable and task
   - Specific failures with values and thresholds
   - Failure pattern analysis

3. **Quality Metrics**
   - Biomechanical plausibility scores
   - Data completeness assessment
   - Outlier and anomaly detection

4. **Recommendations**
   - Data quality improvement suggestions
   - Conversion script debugging hints
   - Usage recommendations for researchers

#### Step 4: Interpret Quality Metrics (2-5 min)
**High quality indicators:**
- ✅ Validation pass rate >90%
- ✅ Complete data for core biomechanical variables
- ✅ Reasonable task distribution
- ✅ Few systematic outliers

**Quality concerns:**
- ⚠️ Pass rate 70-90%: Acceptable with caveats
- ❌ Pass rate <70%: Significant quality issues
- ❌ Missing core variables (GRF, joint angles)
- ❌ Systematic validation failures

#### Step 5: Make Dataset Decisions (Variable time)
**For contributors:**
- High quality: Proceed with contribution preparation
- Medium quality: Address specific issues flagged in report
- Low quality: Debug conversion script and data processing

**For researchers:**
- High quality: Suitable for most analysis purposes
- Medium quality: Check if limitations affect specific research questions
- Low quality: Consider data exclusion criteria

### Success Indicators
- ✅ Report generates successfully without errors
- ✅ Quality metrics align with intended use case
- ✅ Clear action items identified from recommendations
- ✅ Understanding of dataset strengths and limitations

### Common Troubleshooting

**Issue:** Report generation fails
- **Solution:** Check dataset file integrity and format
- **Command:** `python -c "import pandas as pd; print(pd.read_parquet('dataset.parquet').info())"`

**Issue:** Unexpectedly low quality scores
- **Solution:** Review validation failures for systematic issues
- **Action:** Check variable units, naming, and data processing

**Issue:** High validation pass rate but biomechanically implausible data
- **Solution:** Validation ranges may need updating
- **Reference:** Use Workflow 2 or 3 to update ranges

**Issue:** Missing quality report sections
- **Solution:** Ensure dataset has required variables for all analyses
- **Check:** See `docs/standard_spec/standard_spec.md` for requirements

---

## Cross-Workflow Tips

### General Best Practices
1. **Start with examples:** Always review existing conversion scripts before creating new ones
2. **Validate early:** Run quality reports on small samples before processing full datasets
3. **Document decisions:** Keep notes on conversion choices and validation range updates
4. **Version control:** Use git to track changes to conversion scripts and validation specs

### Integration Points
- **Quality reports inform conversion debugging:** Use failure patterns to improve conversion scripts
- **Validation updates affect quality scores:** Coordinate range updates with dataset contributors
- **Statistical optimization complements literature updates:** Use both approaches for comprehensive validation

### Time-Saving Tips
- **Batch processing:** Run multiple datasets through quality reports simultaneously
- **Template reuse:** Adapt existing conversion scripts rather than starting from scratch
- **Automated visualization:** Use `--generate-gifs` flag only when needed for presentations
- **Staging workflow:** Always preview validation changes before committing to live specs

---

## Getting Help

### Documentation References
- **Technical details:** [Architecture - Sequence Diagrams](03a_SEQUENCE_DIAGRAMS.md)
- **System architecture:** [Architecture Overview](03_ARCHITECTURE.md)
- **Standard specification:** `docs/standard_spec/standard_spec.md`
- **Example scripts:** `source/conversion_scripts/` directories

### Common Support Scenarios
1. **Conversion script debugging:** Check example scripts and validation error messages
2. **Validation range questions:** Review literature support and statistical justification
3. **Quality interpretation:** Compare metrics with known high-quality datasets
4. **Tool errors:** Check file formats, dependencies, and input requirements

**Remember:** These workflows are designed to be iterative. Quality reports provide feedback for improving conversions, and validation updates improve quality assessments.