# Kinetic Validation Expectations Specification

**Single Source of Truth for Biomechanically Accurate Kinetic Validation Rules**

This document provides biomechanically verified kinetic validation ranges (forces and moments) based on published gait analysis literature. The specification uses a modern phase system (0%, 25%, 50%, 75%) with contralateral offset logic for optimal validation efficiency.

> **📊 Related**: See [validation_expectations_kinematic.md](validation_expectations_kinematic.md) for kinematic validation rules (joint angles).

> **📋 Version Information**: See [validation_expectations_changelog.md](validation_expectations_changelog.md) for detailed version history and changes.  
> **🔬 Research Status**: **REQUIRES LITERATURE RESEARCH** - Kinetic ranges need verification against published biomechanics literature.

## Format Specification

### Two-Tier Validation Structure

**Tier 1: Generic Range Validation**
- Basic biomechanical plausibility checks for forces and moments
- Physiologically possible ranges across all tasks
- Applied to all kinetic variables regardless of task

**Tier 2: Task-Specific Phase Validation**
- Task-specific expected force and moment patterns
- Phase-specific validation at key points: **0%, 25%, 50%, 75%**
- Contralateral leg automatically computed with 50% phase offset
- Focus on ground reaction forces (GRF) and joint moments

### Validation Table Structure

```markdown
### Task: {task_name}

**Phase-Specific Range Validation:**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 25% (Mid-Stance)  
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

**Contralateral Offset Logic:**
- Contralateral leg values automatically computed with 50% phase offset
- Phase 0% ipsilateral = Phase 50% contralateral (heel strike vs toe-off)
- Phase 25% ipsilateral = Phase 75% contralateral (mid-stance vs mid-swing)
```

**Column Definitions:**
- `Variable`: Exact variable name (must match dataset columns)
- `Min_Value`: Minimum expected value at this phase point
- `Max_Value`: Maximum expected value at this phase point
- `Units`: Variable units (N, Nm, etc.)
- `Notes`: Additional context or exceptions

## Kinetic Variable Categories

### Ground Reaction Forces (GRF)
- **vertical_grf_N**: Vertical ground reaction force (body weight support)
- **ap_grf_N**: Anterior-posterior ground reaction force (propulsion/braking)
- **ml_grf_N**: Medial-lateral ground reaction force (balance)

### Joint Moments
- **hip_moment_ipsi_Nm**: Hip flexion/extension moment (ipsilateral)
- **hip_moment_contra_Nm**: Hip flexion/extension moment (contralateral)
- **knee_moment_ipsi_Nm**: Knee flexion/extension moment (ipsilateral)
- **knee_moment_contra_Nm**: Knee flexion/extension moment (contralateral)
- **ankle_moment_ipsi_Nm**: Ankle dorsiflexion/plantarflexion moment (ipsilateral)
- **ankle_moment_contra_Nm**: Ankle dorsiflexion/plantarflexion moment (contralateral)

### Power Variables (Optional)
- **hip_power_ipsi_W**: Hip joint power (ipsilateral)
- **hip_power_contra_W**: Hip joint power (contralateral)
- **knee_power_ipsi_W**: Knee joint power (ipsilateral)
- **knee_power_contra_W**: Knee joint power (contralateral)
- **ankle_power_ipsi_W**: Ankle joint power (ipsilateral)
- **ankle_power_contra_W**: Ankle joint power (contralateral)

## Validation Tables - REQUIRES RESEARCH

> **⚠️ WARNING**: The following validation ranges are **PRELIMINARY** and require verification against published biomechanics literature. Do not use for production validation until research is completed.

### Task: level_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 400 | 1200 | N | Initial loading response - **NEEDS RESEARCH** |
| ap_grf_N | -300 | 100 | N | Initial braking forces - **NEEDS RESEARCH** |
| ml_grf_N | -100 | 100 | N | Lateral balance adjustment - **NEEDS RESEARCH** |
| hip_moment_ipsi_Nm | -50 | 50 | Nm | Hip moment at contact - **NEEDS RESEARCH** |
| knee_moment_ipsi_Nm | -30 | 30 | Nm | Knee moment at contact - **NEEDS RESEARCH** |
| ankle_moment_ipsi_Nm | -20 | 20 | Nm | Ankle moment at contact - **NEEDS RESEARCH** |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 600 | 1000 | N | Single limb support - **NEEDS RESEARCH** |
| ap_grf_N | -200 | 200 | N | Transition from braking to propulsion - **NEEDS RESEARCH** |
| ml_grf_N | -80 | 80 | N | Stable mediolateral forces - **NEEDS RESEARCH** |
| hip_moment_ipsi_Nm | -80 | 80 | Nm | Hip extension moment - **NEEDS RESEARCH** |
| knee_moment_ipsi_Nm | -40 | 40 | Nm | Knee stability moment - **NEEDS RESEARCH** |
| ankle_moment_ipsi_Nm | 50 | 120 | Nm | Ankle dorsiflexor moment - **NEEDS RESEARCH** |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 800 | 1400 | N | Peak push-off forces - **NEEDS RESEARCH** |
| ap_grf_N | 100 | 400 | N | Peak propulsive forces - **NEEDS RESEARCH** |
| ml_grf_N | -120 | 120 | N | Weight transfer forces - **NEEDS RESEARCH** |
| hip_moment_ipsi_Nm | -100 | 100 | Nm | Hip extension for propulsion - **NEEDS RESEARCH** |
| knee_moment_ipsi_Nm | -60 | 60 | Nm | Knee moment for push-off - **NEEDS RESEARCH** |
| ankle_moment_ipsi_Nm | 80 | 180 | Nm | Peak plantarflexor moment - **NEEDS RESEARCH** |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 0 | 200 | N | Minimal forces during swing - **NEEDS RESEARCH** |
| ap_grf_N | -50 | 50 | N | Minimal AP forces during swing - **NEEDS RESEARCH** |
| ml_grf_N | -30 | 30 | N | Minimal ML forces during swing - **NEEDS RESEARCH** |
| hip_moment_ipsi_Nm | -40 | 40 | Nm | Hip swing moment - **NEEDS RESEARCH** |
| knee_moment_ipsi_Nm | -20 | 20 | Nm | Knee swing moment - **NEEDS RESEARCH** |
| ankle_moment_ipsi_Nm | -10 | 10 | Nm | Ankle swing moment - **NEEDS RESEARCH** |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

### Task: incline_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

> **🔬 STATUS**: Requires literature research for incline walking kinetics

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 500 | 1400 | N | Higher impact on incline - **NEEDS RESEARCH** |
| ap_grf_N | -400 | 0 | N | Strong braking forces uphill - **NEEDS RESEARCH** |
| ml_grf_N | -120 | 120 | N | Lateral balance on incline - **NEEDS RESEARCH** |

> **📝 TODO**: Complete incline walking kinetic validation ranges

### Task: run

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

> **🔬 STATUS**: Requires literature research for running kinetics

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| vertical_grf_N | 1200 | 2800 | N | High impact forces - **NEEDS RESEARCH** |
| ap_grf_N | -600 | 200 | N | Strong braking forces - **NEEDS RESEARCH** |
| ml_grf_N | -250 | 250 | N | Lateral balance - **NEEDS RESEARCH** |

> **📝 TODO**: Complete running kinetic validation ranges

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