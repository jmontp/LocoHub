# Kinematic Validation Expectations Specification

**Single Source of Truth for Biomechanically Accurate Kinematic Validation Rules**

This document provides biomechanically verified kinematic validation ranges (joint angles) based on published gait analysis literature. The specification uses a modern phase system (0%, 25%, 50%, 75%) with contralateral offset logic for optimal validation efficiency.

> **📊 Related**: See [validation_expectations_kinetic.md](validation_expectations_kinetic.md) for kinetic validation rules (forces and moments).

> **📋 Version Information**: See [../development/validation_expectations_changelog.md](../development/validation_expectations_changelog.md) for detailed version history and changes.  
> **🎨 Image Generation**: See [../development/kinematic_visualization_guide.md](../development/kinematic_visualization_guide.md) for generating validation images.

> **🔄 Plot Generation**: 
> 
> **One-click regeneration (VS Code):** `Ctrl+Shift+P` → `Tasks: Run Task` → `🔄 Regenerate Kinematic Plots`
> 
> **GitHub Actions:** [![Regenerate Kinematic Plots](https://img.shields.io/badge/🔄_Regenerate-Kinematic_Plots-green?style=for-the-badge&logo=github)](https://github.com/jmontp/locomotion-data-standardization/actions/workflows/regenerate-validation-plots.yml)
> 
> **Manual commands:**
> ```bash
> python3 source/validation/generate_validation_plots.py
> # Or for specific tasks:
> python3 source/validation/generate_validation_plots.py --tasks level_walking incline_walking
> # Or for specific plot types:
> python3 source/validation/generate_validation_plots.py --forward-kinematic-only
> python3 source/validation/generate_validation_plots.py --filters-only
> ```

## Format Specification

### Two-Tier Validation Structure

**Tier 1: Generic Range Validation**
- Basic biomechanical plausibility checks
- Anatomically possible ranges across all tasks
- Applied to all variables regardless of task

**Tier 2: Task-Specific Phase Validation**
- Task-specific expected ranges and patterns
- Phase-specific validation at key points: **0%, 25%, 50%, 75%**
- Contralateral leg automatically computed with 50% phase offset
- Visual kinematic validation with min/max pose images

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

**Forward Kinematics Range Visualization:**
![Task Forward Kinematics - Phase 0%](validation/{task_name}_forward_kinematics_phase_00_range.png)
![Task Forward Kinematics - Phase 25%](validation/{task_name}_forward_kinematics_phase_25_range.png)
![Task Forward Kinematics - Phase 50%](validation/{task_name}_forward_kinematics_phase_50_range.png)
![Task Forward Kinematics - Phase 75%](validation/{task_name}_forward_kinematics_phase_75_range.png)
```

**Column Definitions:**
- `Variable`: Exact variable name (must match dataset columns)
- `Min_Value`: Minimum expected value at this phase point
- `Max_Value`: Maximum expected value at this phase point
- `Units`: Variable units (rad, N, m, etc.)
- `Notes`: Additional context or exceptions

## Validation Tables - VERIFIED

### Task: level_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.15 | 0.6 | rad | Initial contact with hip flexion |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.15 | rad | Nearly extended at contact - OpenSim convention |
| ankle_flexion_angle_ipsi_rad | -0.05 | 0.05 | rad | Neutral ankle position at contact |
| vertical_grf_N | 400 | 1200 | N | Initial loading response |
| ap_grf_N | -300 | 100 | N | Initial braking forces |
| ml_grf_N | -100 | 100 | N | Lateral balance adjustment |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.05 | 0.35 | rad | Hip moving toward extension |
| knee_flexion_angle_ipsi_rad | 0.05 | 0.25 | rad | Slight flexion during stance |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.25 | rad | **VERIFIED: Dorsiflexion during stance** |
| vertical_grf_N | 600 | 1000 | N | Single limb support |
| ap_grf_N | -200 | 200 | N | Transition from braking to propulsion |
| ml_grf_N | -80 | 80 | N | Stable mediolateral forces |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.35 | 0.0 | rad | Hip extension for propulsion |
| knee_flexion_angle_ipsi_rad | 0.5 | 0.8 | rad | **VERIFIED: Knee flexion for push-off** |
| ankle_flexion_angle_ipsi_rad | -0.4 | -0.2 | rad | **VERIFIED: Plantarflexion for propulsion** |
| vertical_grf_N | 800 | 1400 | N | Peak push-off forces |
| ap_grf_N | 100 | 400 | N | Peak propulsive forces |
| ml_grf_N | -120 | 120 | N | Weight transfer forces |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.3 | 0.9 | rad | Hip flexion for limb advancement |
| knee_flexion_angle_ipsi_rad | 0.8 | 1.3 | rad | Peak knee flexion for clearance |
| ankle_flexion_angle_ipsi_rad | -0.1 | 0.2 | rad | Dorsiflexion for foot clearance |
| vertical_grf_N | 0 | 200 | N | Minimal forces during swing |
| ap_grf_N | -50 | 50 | N | Minimal AP forces during swing |
| ml_grf_N | -30 | 30 | N | Minimal ML forces during swing |

#### Phase 100% (Heel Strike - Cycle Complete)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.15 | 0.6 | rad | Return to initial contact (same as 0%) |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.15 | rad | Return to nearly extended (same as 0%) |
| ankle_flexion_angle_ipsi_rad | -0.05 | 0.05 | rad | Return to neutral position (same as 0%) |
| vertical_grf_N | 400 | 1200 | N | Return to initial loading (same as 0%) |
| ap_grf_N | -300 | 100 | N | Return to initial braking (same as 0%) |
| ml_grf_N | -100 | 100 | N | Return to initial balance (same as 0%) |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Level Walking Forward Kinematics Heel Strike](validation/level_walking_forward_kinematics_phase_00_range.png) | ![Level Walking Forward Kinematics Mid-Stance](validation/level_walking_forward_kinematics_phase_25_range.png) | ![Level Walking Forward Kinematics Toe-Off](validation/level_walking_forward_kinematics_phase_50_range.png) | ![Level Walking Forward Kinematics Mid-Swing](validation/level_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Level Walking Kinematic Filters by Phase](validation/level_walking_kinematic_filters_by_phase.png)

### Task: incline_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.25 | 0.8 | rad | Increased hip flexion for incline approach |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.25 | rad | Controlled loading on incline |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.25 | rad | Dorsiflexion for incline contact |
| vertical_grf_N | 500 | 1400 | N | Higher impact on incline |
| ap_grf_N | -400 | 0 | N | Strong braking forces uphill |
| ml_grf_N | -120 | 120 | N | Lateral balance on incline |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.0 | 0.5 | rad | Hip extension for propulsion |
| knee_flexion_angle_ipsi_rad | 0.1 | 0.4 | rad | Stability with increased flexion |
| ankle_flexion_angle_ipsi_rad | 0.1 | 0.3 | rad | **VERIFIED: Greater dorsiflexion** |
| vertical_grf_N | 700 | 1200 | N | Single limb support |
| ap_grf_N | -300 | 100 | N | Transition to propulsion |
| ml_grf_N | -100 | 100 | N | Lateral stability |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.2 | 0.3 | rad | Hip extension for incline propulsion |
| knee_flexion_angle_ipsi_rad | 0.6 | 0.9 | rad | **VERIFIED: Increased push-off flexion** |
| ankle_flexion_angle_ipsi_rad | -0.3 | -0.1 | rad | **VERIFIED: Moderate plantarflexion** |
| vertical_grf_N | 900 | 1600 | N | Peak propulsive forces |
| ap_grf_N | -100 | 200 | N | Limited propulsion uphill |
| ml_grf_N | -150 | 150 | N | Weight transfer |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.4 | 1.0 | rad | Increased hip flexion for clearance |
| knee_flexion_angle_ipsi_rad | 0.9 | 1.5 | rad | Maximum clearance flexion |
| ankle_flexion_angle_ipsi_rad | 0.0 | 0.35 | rad | Enhanced dorsiflexion |
| vertical_grf_N | 0 | 100 | N | Minimal swing forces |
| ap_grf_N | -30 | 30 | N | Minimal swing forces |
| ml_grf_N | -20 | 20 | N | Minimal swing forces |

#### Phase 100% (Heel Strike - Cycle Complete)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.25 | 0.8 | rad | Return to increased hip flexion for incline (same as 0%) |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.25 | rad | Return to controlled loading (same as 0%) |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.25 | rad | Return to dorsiflexion for incline contact (same as 0%) |
| vertical_grf_N | 500 | 1400 | N | Return to higher incline impact (same as 0%) |
| ap_grf_N | -400 | 0 | N | Return to strong braking uphill (same as 0%) |
| ml_grf_N | -120 | 120 | N | Return to lateral balance (same as 0%) |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Incline Walking Forward Kinematics Heel Strike](validation/incline_walking_forward_kinematics_phase_00_range.png) | ![Incline Walking Forward Kinematics Mid-Stance](validation/incline_walking_forward_kinematics_phase_25_range.png) | ![Incline Walking Forward Kinematics Toe-Off](validation/incline_walking_forward_kinematics_phase_50_range.png) | ![Incline Walking Forward Kinematics Mid-Swing](validation/incline_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Incline Walking Kinematic Filters by Phase](validation/incline_walking_kinematic_filters_by_phase.png)

---

### Task: decline_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.4 | rad | Reduced hip flexion for decline approach |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.2 | rad | Controlled loading for descent |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.0 | rad | Slight plantarflexion for control |
| vertical_grf_N | 300 | 1000 | N | Controlled impact on decline |
| ap_grf_N | -200 | 200 | N | Balance of braking and propulsion |
| ml_grf_N | -100 | 100 | N | Lateral balance control |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.3 | 0.2 | rad | Hip extension for control |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.3 | rad | Eccentric control |
| ankle_flexion_angle_ipsi_rad | -0.05 | 0.15 | rad | **VERIFIED: Controlled dorsiflexion** |
| vertical_grf_N | 500 | 900 | N | Single limb support |
| ap_grf_N | 0 | 400 | N | Forward progression |
| ml_grf_N | -80 | 80 | N | Lateral stability |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.4 | 0.1 | rad | Maximum hip extension |
| knee_flexion_angle_ipsi_rad | 0.4 | 0.7 | rad | **VERIFIED: Push-off initiation** |
| ankle_flexion_angle_ipsi_rad | -0.45 | -0.25 | rad | **VERIFIED: Plantarflexion for propulsion** |
| vertical_grf_N | 600 | 1100 | N | Controlled push-off |
| ap_grf_N | 200 | 500 | N | Forward propulsion |
| ml_grf_N | -120 | 120 | N | Weight transfer |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.1 | 0.7 | rad | Hip flexion for advancement |
| knee_flexion_angle_ipsi_rad | 0.7 | 1.2 | rad | Swing flexion for clearance |
| ankle_flexion_angle_ipsi_rad | -0.1 | 0.2 | rad | Dorsiflexion for clearance |
| vertical_grf_N | 0 | 150 | N | Minimal swing forces |
| ap_grf_N | -40 | 40 | N | Minimal swing forces |
| ml_grf_N | -25 | 25 | N | Minimal swing forces |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Decline Walking Forward Kinematics Heel Strike](validation/decline_walking_forward_kinematics_phase_00_range.png) | ![Decline Walking Forward Kinematics Mid-Stance](validation/decline_walking_forward_kinematics_phase_25_range.png) | ![Decline Walking Forward Kinematics Toe-Off](validation/decline_walking_forward_kinematics_phase_50_range.png) | ![Decline Walking Forward Kinematics Mid-Swing](validation/decline_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Decline Walking Kinematic Filters by Phase](validation/decline_walking_kinematic_filters_by_phase.png)

### Task: up_stairs

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Step Contact)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.3 | 0.7 | rad | Moderate hip flexion for step approach |
| knee_flexion_angle_ipsi_rad | 0.1 | 0.6 | rad | Controlled loading on step |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.3 | rad | Dorsiflexion for step contact |
| vertical_grf_N | 600 | 1800 | N | High vertical forces for lifting |
| ap_grf_N | -500 | 0 | N | Strong braking for control |
| ml_grf_N | -200 | 200 | N | Balance on step |

#### Phase 25% (Loading)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.4 | 0.8 | rad | Hip flexion for lifting |
| knee_flexion_angle_ipsi_rad | 0.5 | 1.0 | rad | Eccentric to concentric transition |
| ankle_flexion_angle_ipsi_rad | 0.15 | 0.4 | rad | **VERIFIED: Dorsiflexion maintenance** |
| vertical_grf_N | 800 | 2000 | N | Peak vertical lifting forces |
| ap_grf_N | -400 | 100 | N | Transition to propulsion |
| ml_grf_N | -150 | 150 | N | Lateral balance |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.2 | 0.6 | rad | Hip extension for vertical lift |
| knee_flexion_angle_ipsi_rad | 0.9 | 1.5 | rad | **VERIFIED: Concentric extension phase** |
| ankle_flexion_angle_ipsi_rad | -0.3 | -0.1 | rad | **VERIFIED: Plantarflexion for push-off** |
| vertical_grf_N | 1000 | 2200 | N | Maximum lifting forces |
| ap_grf_N | -200 | 200 | N | Balanced horizontal forces |
| ml_grf_N | -180 | 180 | N | Balance during lift |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.4 | 0.8 | rad | Hip flexion for swing clearance |
| knee_flexion_angle_ipsi_rad | 1.2 | 1.7 | rad | Swing leg peak flexion |
| ankle_flexion_angle_ipsi_rad | 0.3 | 0.5 | rad | Maximum dorsiflexion |
| vertical_grf_N | 0 | 300 | N | Minimal forces during swing |
| ap_grf_N | -60 | 60 | N | Minimal swing forces |
| ml_grf_N | -40 | 40 | N | Minimal swing forces |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (step contact) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (loading) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (step contact)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (loading)

**Forward Kinematics Range Visualization:**

| Phase 0% (Step Contact) | Phase 25% (Loading) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Up Stairs Forward Kinematics Step Contact](validation/up_stairs_forward_kinematics_phase_00_range.png) | ![Up Stairs Forward Kinematics Loading](validation/up_stairs_forward_kinematics_phase_25_range.png) | ![Up Stairs Forward Kinematics Toe-Off](validation/up_stairs_forward_kinematics_phase_50_range.png) | ![Up Stairs Forward Kinematics Mid-Swing](validation/up_stairs_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Up Stairs Kinematic Filters by Phase](validation/up_stairs_kinematic_filters_by_phase.png)

### Task: down_stairs

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Step Contact)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.0 | 0.4 | rad | Controlled hip position for descent |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.4 | rad | Initial contact absorption |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.05 | rad | Controlled landing |
| vertical_grf_N | 800 | 2200 | N | High impact absorption |
| ap_grf_N | -100 | 400 | N | Forward momentum control |
| ml_grf_N | -150 | 150 | N | Lateral balance |

#### Phase 25% (Loading)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.2 | rad | Hip extension for control |
| knee_flexion_angle_ipsi_rad | 0.3 | 0.8 | rad | Eccentric loading peak |
| ankle_flexion_angle_ipsi_rad | 0.0 | 0.2 | rad | **VERIFIED: Controlled dorsiflexion** |
| vertical_grf_N | 1000 | 2500 | N | Peak eccentric loading |
| ap_grf_N | 100 | 600 | N | Forward progression |
| ml_grf_N | -120 | 120 | N | Lateral control |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.2 | 0.1 | rad | Hip extension for push-off |
| knee_flexion_angle_ipsi_rad | 0.7 | 1.1 | rad | **VERIFIED: Controlled extension** |
| ankle_flexion_angle_ipsi_rad | -0.35 | -0.15 | rad | **VERIFIED: Push-off preparation** |
| vertical_grf_N | 600 | 1800 | N | Controlled push-off |
| ap_grf_N | 200 | 600 | N | Forward propulsion |
| ml_grf_N | -140 | 140 | N | Weight transfer |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.2 | 0.6 | rad | Swing hip flexion |
| knee_flexion_angle_ipsi_rad | 1.0 | 1.4 | rad | Swing clearance |
| ankle_flexion_angle_ipsi_rad | 0.0 | 0.3 | rad | Clearance dorsiflexion |
| vertical_grf_N | 0 | 250 | N | Minimal swing forces |
| ap_grf_N | -50 | 50 | N | Minimal swing forces |
| ml_grf_N | -30 | 30 | N | Minimal swing forces |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (step contact) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (loading) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (step contact)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (loading)

**Forward Kinematics Range Visualization:**

| Phase 0% (Step Contact) | Phase 25% (Loading) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Down Stairs Forward Kinematics Step Contact](validation/down_stairs_forward_kinematics_phase_00_range.png) | ![Down Stairs Forward Kinematics Loading](validation/down_stairs_forward_kinematics_phase_25_range.png) | ![Down Stairs Forward Kinematics Toe-Off](validation/down_stairs_forward_kinematics_phase_50_range.png) | ![Down Stairs Forward Kinematics Mid-Swing](validation/down_stairs_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Down Stairs Kinematic Filters by Phase](validation/down_stairs_kinematic_filters_by_phase.png)

### Task: run

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.8 | rad | Initial contact with forward lean |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.35 | rad | Impact absorption |
| ankle_flexion_angle_ipsi_rad | -0.25 | 0.15 | rad | Variable contact strategy |
| vertical_grf_N | 1200 | 2800 | N | High impact forces |
| ap_grf_N | -600 | 200 | N | Strong braking forces |
| ml_grf_N | -250 | 250 | N | Lateral balance |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.4 | 0.4 | rad | Hip extension for propulsion |
| knee_flexion_angle_ipsi_rad | 0.2 | 0.7 | rad | Stance flexion control |
| ankle_flexion_angle_ipsi_rad | 0.0 | 0.3 | rad | **VERIFIED: Dorsiflexion development** |
| vertical_grf_N | 800 | 2200 | N | Mid-stance loading |
| ap_grf_N | -300 | 400 | N | Transition to propulsion |
| ml_grf_N | -200 | 200 | N | Dynamic balance |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.5 | 0.2 | rad | Maximum hip extension |
| knee_flexion_angle_ipsi_rad | 0.8 | 1.3 | rad | **VERIFIED: Push-off flexion** |
| ankle_flexion_angle_ipsi_rad | -0.6 | -0.3 | rad | **VERIFIED: Strong plantarflexion** |
| vertical_grf_N | 1000 | 3000 | N | Peak propulsive forces |
| ap_grf_N | 200 | 800 | N | Maximum propulsion |
| ml_grf_N | -300 | 300 | N | Dynamic lateral forces |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.1 | 1.3 | rad | Swing hip flexion |
| knee_flexion_angle_ipsi_rad | 1.5 | 2.2 | rad | **UPDATED: Peak swing flexion** |
| ankle_flexion_angle_ipsi_rad | -0.1 | 0.35 | rad | Swing dorsiflexion |
| vertical_grf_N | 0 | 200 | N | Flight phase - minimal forces |
| ap_grf_N | -80 | 80 | N | Minimal flight forces |
| ml_grf_N | -50 | 50 | N | Minimal flight forces |

#### Phase 100% (Heel Strike - Cycle Complete)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.8 | rad | Return to initial contact with forward lean (same as 0%) |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.35 | rad | Return to impact absorption (same as 0%) |
| ankle_flexion_angle_ipsi_rad | -0.25 | 0.15 | rad | Return to variable contact strategy (same as 0%) |
| vertical_grf_N | 1200 | 2800 | N | Return to high impact forces (same as 0%) |
| ap_grf_N | -600 | 200 | N | Return to strong braking forces (same as 0%) |
| ml_grf_N | -250 | 250 | N | Return to lateral balance (same as 0%) |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)  
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Run Forward Kinematics Heel Strike](validation/run_forward_kinematics_phase_00_range.png) | ![Run Forward Kinematics Mid-Stance](validation/run_forward_kinematics_phase_25_range.png) | ![Run Forward Kinematics Toe-Off](validation/run_forward_kinematics_phase_50_range.png) | ![Run Forward Kinematics Mid-Swing](validation/run_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Run Kinematic Filters by Phase](validation/run_kinematic_filters_by_phase.png)

### Task: sit_to_stand

**Phase-Specific Range Validation (Bilateral Movement - Both Legs):**

#### Phase 0% (Seated)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 1.2 | 2.0 | rad | Initial seated position |
| hip_flexion_angle_contra_rad | 1.2 | 2.0 | rad | Bilateral seated position |
| knee_flexion_angle_ipsi_rad | 1.3 | 1.8 | rad | Seated knee position |
| knee_flexion_angle_contra_rad | 1.3 | 1.8 | rad | Bilateral knee position |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.35 | rad | Dorsiflexion for preparation |
| ankle_flexion_angle_contra_rad | 0.05 | 0.35 | rad | Bilateral preparation |
| vertical_grf_N | 400 | 800 | N | Initial weight bearing |
| ap_grf_N | -200 | 200 | N | Balance adjustment |
| ml_grf_N | -150 | 150 | N | Lateral balance |

#### Phase 25% (Initiation)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.8 | 1.6 | rad | Hip extension initiation |
| hip_flexion_angle_contra_rad | 0.8 | 1.6 | rad | Bilateral hip extension |
| knee_flexion_angle_ipsi_rad | 0.8 | 1.4 | rad | Knee extension initiation |
| knee_flexion_angle_contra_rad | 0.8 | 1.4 | rad | Bilateral knee extension |
| ankle_flexion_angle_ipsi_rad | 0.0 | 0.25 | rad | Ankle adjustment |
| ankle_flexion_angle_contra_rad | 0.0 | 0.25 | rad | Bilateral adjustment |
| vertical_grf_N | 600 | 1000 | N | Increasing weight transfer |
| ap_grf_N | -250 | 250 | N | Forward momentum |
| ml_grf_N | -180 | 180 | N | Balance control |

#### Phase 50% (Mid-Rise)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.5 | 1.2 | rad | Mid-range hip extension |
| hip_flexion_angle_contra_rad | 0.5 | 1.2 | rad | Bilateral progression |
| knee_flexion_angle_ipsi_rad | 0.4 | 1.0 | rad | Mid-range knee extension |
| knee_flexion_angle_contra_rad | 0.4 | 1.0 | rad | Bilateral progression |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.15 | rad | Neutral ankle position |
| ankle_flexion_angle_contra_rad | -0.15 | 0.15 | rad | Bilateral neutral |
| vertical_grf_N | 800 | 1200 | N | Peak vertical forces |
| ap_grf_N | -300 | 300 | N | Balance maintenance |
| ml_grf_N | -200 | 200 | N | Dynamic balance |

#### Phase 75% (Standing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.2 | 0.8 | rad | Near standing hip position |
| hip_flexion_angle_contra_rad | 0.2 | 0.8 | rad | Bilateral near standing |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.5 | rad | Near full knee extension |
| knee_flexion_angle_contra_rad | 0.0 | 0.5 | rad | Bilateral extension |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.15 | rad | Standing ankle position |
| ankle_flexion_angle_contra_rad | -0.15 | 0.15 | rad | Bilateral standing |
| vertical_grf_N | 600 | 1000 | N | Standing weight bearing |
| ap_grf_N | -200 | 200 | N | Final balance adjustment |
| ml_grf_N | -150 | 150 | N | Standing balance |

**Note:** Sit-to-stand is a bilateral symmetric movement, so both legs maintain similar ranges throughout all phases.

**Forward Kinematics Range Visualization:**

| Phase 0% (Seated) | Phase 25% (Initiation) | Phase 50% (Mid-Rise) | Phase 75% (Standing) |
|---|---|---|---|
| ![Sit To Stand Forward Kinematics Seated](validation/sit_to_stand_forward_kinematics_phase_00_range.png) | ![Sit To Stand Forward Kinematics Initiation](validation/sit_to_stand_forward_kinematics_phase_25_range.png) | ![Sit To Stand Forward Kinematics Mid-Rise](validation/sit_to_stand_forward_kinematics_phase_50_range.png) | ![Sit To Stand Forward Kinematics Standing](validation/sit_to_stand_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Sit To Stand Kinematic Filters by Phase](validation/sit_to_stand_kinematic_filters_by_phase.png)

### Task: jump

**Phase-Specific Range Validation (Bilateral Movement - Both Legs):**

#### Phase 0% (Initial)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.6 | rad | Initial standing position |
| hip_flexion_angle_contra_rad | -0.1 | 0.6 | rad | Bilateral standing |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.3 | rad | Initial knee position |
| knee_flexion_angle_contra_rad | 0.0 | 0.3 | rad | Bilateral initial position |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.15 | rad | Neutral ankle start |
| ankle_flexion_angle_contra_rad | -0.15 | 0.15 | rad | Bilateral neutral |
| vertical_grf_N | 600 | 1200 | N | Initial body weight |
| ap_grf_N | -300 | 300 | N | Balance preparation |
| ml_grf_N | -200 | 200 | N | Lateral balance |

#### Phase 25% (Countermovement)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.5 | 1.3 | rad | Countermovement hip flexion |
| hip_flexion_angle_contra_rad | 0.5 | 1.3 | rad | Bilateral countermovement |
| knee_flexion_angle_ipsi_rad | 0.7 | 1.6 | rad | **UPDATED: Deep countermovement** |
| knee_flexion_angle_contra_rad | 0.7 | 1.6 | rad | **UPDATED: Bilateral deep flexion** |
| ankle_flexion_angle_ipsi_rad | 0.1 | 0.4 | rad | **VERIFIED: Dorsiflexion preparation** |
| ankle_flexion_angle_contra_rad | 0.1 | 0.4 | rad | Bilateral preparation |
| vertical_grf_N | 200 | 800 | N | Reduced loading during descent |
| ap_grf_N | -400 | 400 | N | Dynamic balance |
| ml_grf_N | -250 | 250 | N | Balance during descent |

#### Phase 50% (Takeoff)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.3 | 0.5 | rad | Explosive hip extension |
| hip_flexion_angle_contra_rad | -0.3 | 0.5 | rad | Bilateral extension |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.6 | rad | **VERIFIED: Explosive knee extension** |
| knee_flexion_angle_contra_rad | 0.0 | 0.6 | rad | Bilateral explosion |
| ankle_flexion_angle_ipsi_rad | -0.7 | -0.3 | rad | **VERIFIED: Strong plantarflexion** |
| ankle_flexion_angle_contra_rad | -0.7 | -0.3 | rad | Bilateral plantarflexion |
| vertical_grf_N | 1500 | 4000 | N | Peak takeoff forces |
| ap_grf_N | -500 | 500 | N | Direction-dependent forces |
| ml_grf_N | -300 | 300 | N | Dynamic balance forces |

#### Phase 75% (Flight)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.2 | 1.0 | rad | Flight position |
| hip_flexion_angle_contra_rad | 0.2 | 1.0 | rad | Bilateral flight |
| knee_flexion_angle_ipsi_rad | 0.2 | 1.4 | rad | Variable flight position |
| knee_flexion_angle_contra_rad | 0.2 | 1.4 | rad | Bilateral flight position |
| ankle_flexion_angle_ipsi_rad | -0.35 | 0.35 | rad | Flight ankle position |
| ankle_flexion_angle_contra_rad | -0.35 | 0.35 | rad | Bilateral flight |
| vertical_grf_N | 0 | 100 | N | Minimal flight forces |
| ap_grf_N | -50 | 50 | N | Minimal flight forces |
| ml_grf_N | -30 | 30 | N | Minimal flight forces |

**Note:** Jumping is a bilateral symmetric movement, so both legs maintain similar ranges throughout all phases.

**Forward Kinematics Range Visualization:**

| Phase 0% (Initial) | Phase 25% (Countermovement) | Phase 50% (Takeoff) | Phase 75% (Flight) |
|---|---|---|---|
| ![Jump Forward Kinematics Initial](validation/jump_forward_kinematics_phase_00_range.png) | ![Jump Forward Kinematics Countermovement](validation/jump_forward_kinematics_phase_25_range.png) | ![Jump Forward Kinematics Takeoff](validation/jump_forward_kinematics_phase_50_range.png) | ![Jump Forward Kinematics Flight](validation/jump_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Jump Kinematic Filters by Phase](validation/jump_kinematic_filters_by_phase.png)

### Task: squats

**Phase-Specific Range Validation (Bilateral Movement - Both Legs):**

#### Phase 0% (Standing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | -0.1 | 0.3 | rad | Initial standing position |
| hip_flexion_angle_contra_rad | -0.1 | 0.3 | rad | Bilateral standing |
| knee_flexion_angle_ipsi_rad | 0.0 | 0.25 | rad | Initial knee position |
| knee_flexion_angle_contra_rad | 0.0 | 0.25 | rad | Bilateral initial |
| ankle_flexion_angle_ipsi_rad | -0.05 | 0.15 | rad | Neutral ankle start |
| ankle_flexion_angle_contra_rad | -0.05 | 0.15 | rad | Bilateral neutral |
| vertical_grf_N | 600 | 1200 | N | Initial body weight |
| ap_grf_N | -200 | 200 | N | Balance maintenance |
| ml_grf_N | -150 | 150 | N | Lateral balance |

#### Phase 25% (Descent)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.6 | 1.4 | rad | Descent hip flexion |
| hip_flexion_angle_contra_rad | 0.6 | 1.4 | rad | Bilateral descent |
| knee_flexion_angle_ipsi_rad | 0.9 | 1.8 | rad | Descent knee flexion |
| knee_flexion_angle_contra_rad | 0.9 | 1.8 | rad | Bilateral descent |
| ankle_flexion_angle_ipsi_rad | 0.15 | 0.4 | rad | **VERIFIED: Dorsiflexion for balance** |
| ankle_flexion_angle_contra_rad | 0.15 | 0.4 | rad | Bilateral dorsiflexion |
| vertical_grf_N | 400 | 1000 | N | Reduced loading during descent |
| ap_grf_N | -300 | 300 | N | Balance control |
| ml_grf_N | -180 | 180 | N | Lateral stability |

#### Phase 50% (Bottom)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 1.2 | 2.2 | rad | Maximum squat depth |
| hip_flexion_angle_contra_rad | 1.2 | 2.2 | rad | Bilateral maximum |
| knee_flexion_angle_ipsi_rad | 1.7 | 2.4 | rad | Maximum knee flexion |
| knee_flexion_angle_contra_rad | 1.7 | 2.4 | rad | Bilateral maximum |
| ankle_flexion_angle_ipsi_rad | 0.25 | 0.70 | rad | **UPDATED: Peak dorsiflexion** |
| ankle_flexion_angle_contra_rad | 0.25 | 0.70 | rad | **UPDATED: Bilateral peak** |
| vertical_grf_N | 500 | 1000 | N | Bottom position loading |
| ap_grf_N | -350 | 350 | N | Balance at depth |
| ml_grf_N | -200 | 200 | N | Lateral balance at depth |

#### Phase 75% (Ascent)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|---------|
| hip_flexion_angle_ipsi_rad | 0.4 | 1.2 | rad | Ascent hip extension |
| hip_flexion_angle_contra_rad | 0.4 | 1.2 | rad | Bilateral ascent |
| knee_flexion_angle_ipsi_rad | 0.7 | 1.6 | rad | Ascent knee extension |
| knee_flexion_angle_contra_rad | 0.7 | 1.6 | rad | Bilateral ascent |
| ankle_flexion_angle_ipsi_rad | 0.05 | 0.35 | rad | Return to neutral |
| ankle_flexion_angle_contra_rad | 0.05 | 0.35 | rad | Bilateral return |
| vertical_grf_N | 800 | 1600 | N | Ascent forces |
| ap_grf_N | -250 | 250 | N | Balance during ascent |
| ml_grf_N | -180 | 180 | N | Lateral control |

**Note:** Squats are a bilateral symmetric movement, so both legs maintain similar ranges throughout all phases.

**Forward Kinematics Range Visualization:**

| Phase 0% (Standing) | Phase 25% (Descent) | Phase 50% (Bottom) | Phase 75% (Ascent) |
|---|---|---|---|
| ![Squats Forward Kinematics Standing](validation/squats_forward_kinematics_phase_00_range.png) | ![Squats Forward Kinematics Descent](validation/squats_forward_kinematics_phase_25_range.png) | ![Squats Forward Kinematics Bottom](validation/squats_forward_kinematics_phase_50_range.png) | ![Squats Forward Kinematics Ascent](validation/squats_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Squats Kinematic Filters by Phase](validation/squats_kinematic_filters_by_phase.png)

## Joint Validation Range Summary

The filters by phase validation plots have been moved to their corresponding individual task sections above. Each task now includes both forward kinematics range visualizations and filters by phase validation plots.

**Reading the Filters by Phase Plots:**
- **X-axis**: Movement phase progression (0%, 25%, 50%, 75%)
- **Y-axis**: Joint angle values in radians (left) and degrees (right)
- **Layout**: 3 rows (hip, knee, ankle) × 2 columns (left leg, right leg)
- **Bounding Boxes**: Colored rectangles show valid range for each phase
- **Connecting Lines**: 
  - Red line with circles: Minimum acceptable values across phases
  - Blue line with circles: Maximum acceptable values across phases
- **Shaded Area**: Filled region between min/max shows complete acceptable range
- **Value Labels**: Degree values shown at min/max points for easy reference
- **Color Coding**: 
  - Red: Hip flexion angles
  - Teal: Knee flexion angles  
  - Blue: Ankle flexion angles

These plots make it easy to visualize how joint angle requirements change throughout the movement cycle and compare bilateral coordination patterns between left and right legs.

## Pattern Definitions

**Temporal Patterns:**
- `peak_at_X`: Maximum value occurs at phase X%
- `valley_at_X`: Minimum value occurs at phase X%
- `increasing`: Monotonic increase throughout phase range
- `decreasing`: Monotonic decrease throughout phase range
- `negative_to_positive`: Crosses zero from negative to positive
- `U_shaped`: Decreases then increases (valley in middle)
- `inverted_U`: Increases then decreases (peak in middle)

**Amplitude Patterns:**
- `near_zero`: Values close to zero throughout
- `predominantly_negative`: Mostly negative values
- `predominantly_positive`: Mostly positive values
- `variable`: High variability, no clear pattern
- `controlled_motion`: Smooth, controlled changes

## Parser Usage

This markdown file can be parsed programmatically using the companion parser:

```python
from validation_markdown_parser import ValidationMarkdownParser

parser = ValidationMarkdownParser()
validation_rules = parser.parse_file('validation_expectations.md')

# Get rules for specific task
level_walking_rules = validation_rules['level_walking']

# Validate data against rules
results = parser.validate_data(data, 'level_walking')
```

## Maintenance Guidelines

1. **Adding New Tasks**: Follow the exact table format
2. **Variable Names**: Must match dataset column names exactly
3. **Phase Ranges**: Use format "start-end" (e.g., "0-100", "45-55")  
4. **Patterns**: Use predefined pattern names from Pattern Definitions
5. **Units**: Must match standard specification units
6. **Tolerance**: Percentage (e.g., "15%") or absolute values

## References

These ranges are verified against:
1. Perry, J., & Burnfield, J. M. (2010). Gait Analysis: Normal and Pathological Function (2nd ed.)
2. Winter, D. A. (2009). Biomechanics and Motor Control of Human Movement (4th ed.)
3. Whittle, M. W. (2007). Gait Analysis: An Introduction (4th ed.)
4. Nordin, M., & Frankel, V. H. (2012). Basic Biomechanics of the Musculoskeletal System (4th ed.)
5. Schoenfeld, B. J. (2010). Squatting kinematics and kinetics and their application to exercise performance
6. Cook, G. (2010). Movement: Functional Movement Systems
7. Various peer-reviewed sources from 2024 literature searches

> **📋 Version History**: See [validation_expectations_changelog.md](validation_expectations_changelog.md) for complete version history and detailed change documentation.
> **🧪 Parser Testing**: See [test_validation_parser.md](test_validation_parser.md) for markdown parser unit test data.