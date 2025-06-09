# Test Validation Parser

**Unit Test Data for Markdown Parser Validation**

This file contains test data for validating the markdown parser functionality. It follows the same format as the real validation expectations but with simplified test data.

### Task: test_walking_parser

**Phase-Specific Range Validation (Parser Unit Test):**

#### Phase 0% (Test Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.1 (6°) | 0.5 (29°) | rad | Test hip flexion range (6-29°) |
| knee_flexion_angle_ipsi_rad | 0.0 (0°) | 0.2 (11°) | rad | Test knee range (0-11°) |
| ankle_flexion_angle_ipsi_rad | -0.1 (-6°) | 0.1 (6°) | rad | Test ankle range (-6 to 6°) |
| vertical_grf_N | 400 | 1200 | N | Test vertical forces |
| ap_grf_N | -300 | 100 | N | Test AP forces |

#### Phase 25% (Test Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.0 (0°) | 0.3 (17°) | rad | Test hip extension (0-17°) |
| knee_flexion_angle_ipsi_rad | 0.05 (3°) | 0.25 (14°) | rad | Test knee stability (3-14°) |
| ankle_flexion_angle_ipsi_rad | 0.05 (3°) | 0.2 (11°) | rad | Test dorsiflexion (3-11°) |
| vertical_grf_N | 600 | 1000 | N | Test single support |
| ap_grf_N | -200 | 200 | N | Test transition forces |

#### Phase 50% (Test Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.3 (-17°) | 0.0 (0°) | rad | Test hip extension (-17 to 0°) |
| knee_flexion_angle_ipsi_rad | 0.5 (29°) | 0.8 (46°) | rad | Test knee flexion (29-46°) |
| ankle_flexion_angle_ipsi_rad | -0.4 (-23°) | -0.2 (-11°) | rad | Test plantarflexion (-23 to -11°) |
| vertical_grf_N | 800 | 1400 | N | Test push-off forces |
| ap_grf_N | 100 | 400 | N | Test propulsive forces |

#### Phase 75% (Test Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.3 (17°) | 0.9 (52°) | rad | Test swing flexion (17-52°) |
| knee_flexion_angle_ipsi_rad | 0.8 (46°) | 1.3 (74°) | rad | Test peak swing (46-74°) |
| ankle_flexion_angle_ipsi_rad | -0.1 (-6°) | 0.2 (11°) | rad | Test swing position (-6 to 11°) |
| vertical_grf_N | 0 | 200 | N | Test minimal swing forces |
| ap_grf_N | -50 | 50 | N | Test swing forces |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Expected Parser Output:**
```json
{
  "test_walking_parser": {
    "0": {
      "hip_flexion_angle_ipsi_rad": {"min": 0.1, "max": 0.5},
      "knee_flexion_angle_ipsi_rad": {"min": 0.0, "max": 0.2},
      "ankle_flexion_angle_ipsi_rad": {"min": -0.1, "max": 0.1},
      "vertical_grf_N": {"min": 400, "max": 1200},
      "ap_grf_N": {"min": -300, "max": 100}
    },
    "25": {
      "hip_flexion_angle_ipsi_rad": {"min": 0.0, "max": 0.3},
      "knee_flexion_angle_ipsi_rad": {"min": 0.05, "max": 0.25},
      "ankle_flexion_angle_ipsi_rad": {"min": 0.05, "max": 0.2},
      "vertical_grf_N": {"min": 600, "max": 1000},
      "ap_grf_N": {"min": -200, "max": 200}
    },
    "50": {
      "hip_flexion_angle_ipsi_rad": {"min": -0.3, "max": 0.0},
      "knee_flexion_angle_ipsi_rad": {"min": 0.5, "max": 0.8},
      "ankle_flexion_angle_ipsi_rad": {"min": -0.4, "max": -0.2},
      "vertical_grf_N": {"min": 800, "max": 1400},
      "ap_grf_N": {"min": 100, "max": 400}
    },
    "75": {
      "hip_flexion_angle_ipsi_rad": {"min": 0.3, "max": 0.9},
      "knee_flexion_angle_ipsi_rad": {"min": 0.8, "max": 1.3},
      "ankle_flexion_angle_ipsi_rad": {"min": -0.1, "max": 0.2},
      "vertical_grf_N": {"min": 0, "max": 200},
      "ap_grf_N": {"min": -50, "max": 50}
    }
  }
}
```

## Test Cases for Parser Validation

1. **Task Detection**: Should extract "test_walking_parser" as task name
2. **Phase Parsing**: Should identify phases 0, 25, 50, 75
3. **Variable Extraction**: Should parse all variable names correctly
4. **Value Parsing**: Should extract min/max values as floats
5. **Unit Detection**: Should identify units (rad, N)
6. **Degree Conversion**: Should handle degree annotations like "(6°)"
7. **Negative Values**: Should correctly parse negative min/max values
8. **Range Validation**: Should validate min < max for all variables
9. **Contralateral Logic**: Should apply 50% offset when generating contra variables
10. **Error Handling**: Should gracefully handle malformed tables

## Usage

This test file should be used by the markdown parser unit tests to validate:
- Correct parsing of task names and phases
- Proper extraction of variable names and numeric values
- Handling of mixed data formats (degrees, radians, forces)
- Application of contralateral offset logic
- Error handling for malformed input