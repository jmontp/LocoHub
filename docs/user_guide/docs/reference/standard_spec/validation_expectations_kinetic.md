# Kinetic Validation Expectations Specification

**Single Source of Truth for Biomechanically Accurate Kinetic Validation Rules**

This document provides biomechanically verified kinetic validation ranges (forces and moments) based on published gait analysis literature. The specification uses a modern phase system (0%, 25%, 50%, 75%) with contralateral offset logic for optimal validation efficiency.

> **📊 Related**: See [validation_expectations_kinematic.md](validation_expectations_kinematic.md) for kinematic validation rules (joint angles).

> **📋 Version Information**: See [validation_expectations_changelog.md](validation_expectations_changelog.md) for detailed version history and changes.  
> **🔬 Research Status**: **REQUIRES LITERATURE RESEARCH** - Kinetic ranges need verification against published biomechanics literature.

> **🔄 Plot Generation**: 
> 
> **One-click regeneration (VS Code):** `Ctrl+Shift+P` → `Tasks: Run Task` → `🔄 Regenerate Kinetic Plots`
> 
> **GitHub Actions:** [![Regenerate Kinetic Plots](https://img.shields.io/badge/🔄_Regenerate-Kinetic_Plots-blue?style=for-the-badge&logo=github)](https://github.com/jmontp/locomotion-data-standardization/actions/workflows/regenerate-validation-plots.yml)
> 
> **Manual command:**
> ```bash
> python3 source/validation/generate_validation_plots.py --filters-only
> ```


## Validation Tables


**🤖 AUTOMATED TUNING - DECLINE_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 12:33:33


### Task: decline_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

| Variable | | 0% | | | 25% | | | 50% | | | 75% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | | |

**Filters by Phase Validation:**

![Decline Walking Kinetic Filters by Phase](validation/decline_walking_kinetic_filters_by_phase.png)

---

**🤖 AUTOMATED TUNING - INCLINE_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 12:33:33


### Task: incline_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

| Variable | | 0% | | | 25% | | | 50% | | | 75% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | | |

**Filters by Phase Validation:**

![Incline Walking Kinetic Filters by Phase](validation/incline_walking_kinetic_filters_by_phase.png)

---

**🤖 AUTOMATED TUNING - LEVEL_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 12:33:33


### Task: level_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

| Variable | | 0% | | | 25% | | | 50% | | | 75% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | | |

**Filters by Phase Validation:**

![Level Walking Kinetic Filters by Phase](validation/level_walking_kinetic_filters_by_phase.png)

## Research Requirements

### Literature Sources Needed
1. **Ground Reaction Forces**:
   - Normal walking GRF patterns and magnitudes
   - Incline/decline walking force modifications
   - Running vs walking force differences
   - Stair climbing/descending force patterns

2. **Joint Moments**:
   - Hip, knee, ankle moment patterns during gait
   - Task-specific moment modifications
   - Age and anthropometric scaling factors
   - Pathological vs normal moment patterns

3. **Power Analysis**:
   - Joint power generation and absorption patterns
   - Energy transfer between joints
   - Efficiency metrics across tasks

### Key Research Questions
1. What are typical GRF magnitudes relative to body weight?
2. How do joint moments scale with anthropometric measures?
3. What are the phase-specific patterns for different locomotion tasks?
4. How do kinetic patterns differ between ipsilateral and contralateral legs?
5. What are acceptable ranges for healthy adult populations?

### Recommended Literature Sources
- Winter, D. A. (2009). Biomechanics and Motor Control of Human Movement
- Perry, J., & Burnfield, J. M. (2010). Gait Analysis: Normal and Pathological Function
- Robertson, D. G. E., et al. (2013). Research Methods in Biomechanics
- Journal of Biomechanics - recent gait analysis studies
- Gait & Posture - locomotion-specific research
- IEEE Transactions on Biomedical Engineering - force platform studies

## Parser Usage

This markdown file can be parsed programmatically using the same parser as kinematic validation:

```python
from validation_markdown_parser import ValidationMarkdownParser

parser = ValidationMarkdownParser()
kinetic_rules = parser.parse_file('validation_expectations_kinetic.md')

# Get rules for specific task
level_walking_kinetics = kinetic_rules['level_walking']

# Validate kinetic data against rules
results = parser.validate_data(kinetic_data, 'level_walking')
```

## Maintenance Guidelines

1. **Adding New Tasks**: Follow the exact table format used for kinematics
2. **Variable Names**: Must match dataset column names exactly
3. **Phase Ranges**: Use format "start-end" (e.g., "0-100", "45-55")  
4. **Units**: Must match standard specification units (N, Nm, W)
5. **Research Verification**: All ranges must be verified against literature before production use

## References

> **⚠️ PLACEHOLDER**: Literature references need to be added after research completion

These ranges will be verified against:
1. Winter, D. A. (2009). Biomechanics and Motor Control of Human Movement (4th ed.)
2. Perry, J., & Burnfield, J. M. (2010). Gait Analysis: Normal and Pathological Function (2nd ed.)
3. Robertson, D. G. E., et al. (2013). Research Methods in Biomechanics (2nd ed.)
4. [Additional peer-reviewed sources to be added after research]

> **📋 Version History**: See [validation_expectations_changelog.md](validation_expectations_changelog.md) for complete version history and detailed change documentation.
> **🧪 Parser Testing**: See [test_validation_parser.md](test_validation_parser.md) for markdown parser unit test data.