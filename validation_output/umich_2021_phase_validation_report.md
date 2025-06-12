# Dataset Validation Report

**Generated**: 2025-06-11 17:24:01
**Dataset**: `converted_datasets/umich_2021_phase.parquet`

## Validation Summary

- **Total Steps Validated**: 8305
- **Valid Steps**: 0
- **Failed Steps**: 8305
- **Success Rate**: 0.0%
- **Tasks Validated**: decline_walking, incline_walking, level_walking

## ⚠️ Detailed Failure Analysis (150576 total)

### Kinematic Failures (150576)

#### Task: Decline Walking

**Variable: hip_flexion_angle_contra** (8999 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | -0.775 | -0.400 to 0.100 | Value -0.775 outside range [-0.400, 0.100] at phase 0% |
| 25.0% | -1.121 | 0.100 to 0.700 | Value -1.121 outside range [0.100, 0.700] at phase 25% |
| 75.0% | -0.429 | -0.300 to 0.200 | Value -0.429 outside range [-0.300, 0.200] at phase 75% |
| 0.0% | -0.669 | -0.400 to 0.100 | Value -0.669 outside range [-0.400, 0.100] at phase 0% |
| 25.0% | -1.193 | 0.100 to 0.700 | Value -1.193 outside range [0.100, 0.700] at phase 25% |
| 75.0% | -0.416 | -0.300 to 0.200 | Value -0.416 outside range [-0.300, 0.200] at phase 75% |
| 0.0% | -0.642 | -0.400 to 0.100 | Value -0.642 outside range [-0.400, 0.100] at phase 0% |
| 25.0% | -1.187 | 0.100 to 0.700 | Value -1.187 outside range [0.100, 0.700] at phase 25% |
| 75.0% | -0.463 | -0.300 to 0.200 | Value -0.463 outside range [-0.300, 0.200] at phase 75% |
| 0.0% | -0.686 | -0.400 to 0.100 | Value -0.686 outside range [-0.400, 0.100] at phase 0% |

*... and 8989 more failures*

**Variable: knee_flexion_angle_ipsi** (11007 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.295 | 0.000 to 0.200 | Value 0.295 outside range [0.000, 0.200] at phase 0% |
| 50.0% | 0.052 | 0.400 to 0.700 | Value 0.052 outside range [0.400, 0.700] at phase 50% |
| 75.0% | 0.119 | 0.700 to 1.200 | Value 0.119 outside range [0.700, 1.200] at phase 75% |
| 0.0% | 0.319 | 0.000 to 0.200 | Value 0.319 outside range [0.000, 0.200] at phase 0% |
| 50.0% | 0.071 | 0.400 to 0.700 | Value 0.071 outside range [0.400, 0.700] at phase 50% |
| 75.0% | 0.120 | 0.700 to 1.200 | Value 0.120 outside range [0.700, 1.200] at phase 75% |
| 0.0% | 0.345 | 0.000 to 0.200 | Value 0.345 outside range [0.000, 0.200] at phase 0% |
| 50.0% | 0.105 | 0.400 to 0.700 | Value 0.105 outside range [0.400, 0.700] at phase 50% |
| 75.0% | 0.128 | 0.700 to 1.200 | Value 0.128 outside range [0.700, 1.200] at phase 75% |
| 0.0% | 0.325 | 0.000 to 0.200 | Value 0.325 outside range [0.000, 0.200] at phase 0% |

*... and 10997 more failures*

**Variable: ankle_flexion_angle_contra** (7921 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.052 | -0.450 to -0.250 | Value 0.052 outside range [-0.450, -0.250] at phase 0% |
| 50.0% | 0.319 | -0.150 to 0.000 | Value 0.319 outside range [-0.150, 0.000] at phase 50% |
| 0.0% | 0.071 | -0.450 to -0.250 | Value 0.071 outside range [-0.450, -0.250] at phase 0% |
| 50.0% | 0.345 | -0.150 to 0.000 | Value 0.345 outside range [-0.150, 0.000] at phase 50% |
| 0.0% | 0.105 | -0.450 to -0.250 | Value 0.105 outside range [-0.450, -0.250] at phase 0% |
| 50.0% | 0.325 | -0.150 to 0.000 | Value 0.325 outside range [-0.150, 0.000] at phase 50% |
| 0.0% | 0.080 | -0.450 to -0.250 | Value 0.080 outside range [-0.450, -0.250] at phase 0% |
| 50.0% | 0.315 | -0.150 to 0.000 | Value 0.315 outside range [-0.150, 0.000] at phase 50% |
| 75.0% | -0.058 | -0.050 to 0.150 | Value -0.058 outside range [-0.050, 0.150] at phase 75% |
| 0.0% | 0.091 | -0.450 to -0.250 | Value 0.091 outside range [-0.450, -0.250] at phase 0% |

*... and 7911 more failures*

**Variable: hip_flexion_angle_ipsi** (8585 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | 0.618 | -0.300 to 0.200 | Value 0.618 outside range [-0.300, 0.200] at phase 25% |
| 50.0% | 0.424 | -0.400 to 0.100 | Value 0.424 outside range [-0.400, 0.100] at phase 50% |
| 25.0% | 0.565 | -0.300 to 0.200 | Value 0.565 outside range [-0.300, 0.200] at phase 25% |
| 50.0% | 0.424 | -0.400 to 0.100 | Value 0.424 outside range [-0.400, 0.100] at phase 50% |
| 25.0% | 0.571 | -0.300 to 0.200 | Value 0.571 outside range [-0.300, 0.200] at phase 25% |
| 50.0% | 0.451 | -0.400 to 0.100 | Value 0.451 outside range [-0.400, 0.100] at phase 50% |
| 25.0% | 0.580 | -0.300 to 0.200 | Value 0.580 outside range [-0.300, 0.200] at phase 25% |
| 50.0% | 0.443 | -0.400 to 0.100 | Value 0.443 outside range [-0.400, 0.100] at phase 50% |
| 25.0% | 0.497 | -0.300 to 0.200 | Value 0.497 outside range [-0.300, 0.200] at phase 25% |
| 50.0% | 0.422 | -0.400 to 0.100 | Value 0.422 outside range [-0.400, 0.100] at phase 50% |

*... and 8575 more failures*

**Variable: knee_flexion_angle_contra** (9806 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | 0.302 | 0.700 to 1.200 | Value 0.302 outside range [0.700, 1.200] at phase 25% |
| 50.0% | 0.222 | 0.000 to 0.200 | Value 0.222 outside range [0.000, 0.200] at phase 50% |
| 75.0% | 0.565 | 0.000 to 0.300 | Value 0.565 outside range [0.000, 0.300] at phase 75% |
| 25.0% | 0.286 | 0.700 to 1.200 | Value 0.286 outside range [0.700, 1.200] at phase 25% |
| 75.0% | 0.571 | 0.000 to 0.300 | Value 0.571 outside range [0.000, 0.300] at phase 75% |
| 25.0% | 0.342 | 0.700 to 1.200 | Value 0.342 outside range [0.700, 1.200] at phase 25% |
| 50.0% | 0.240 | 0.000 to 0.200 | Value 0.240 outside range [0.000, 0.200] at phase 50% |
| 75.0% | 0.580 | 0.000 to 0.300 | Value 0.580 outside range [0.000, 0.300] at phase 75% |
| 25.0% | 0.324 | 0.700 to 1.200 | Value 0.324 outside range [0.700, 1.200] at phase 25% |
| 75.0% | 0.497 | 0.000 to 0.300 | Value 0.497 outside range [0.000, 0.300] at phase 75% |

*... and 9796 more failures*

**Variable: ankle_flexion_angle_ipsi** (10155 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | -0.429 | -0.050 to 0.150 | Value -0.429 outside range [-0.050, 0.150] at phase 25% |
| 50.0% | -0.669 | -0.450 to -0.250 | Value -0.669 outside range [-0.450, -0.250] at phase 50% |
| 75.0% | -1.193 | -0.100 to 0.200 | Value -1.193 outside range [-0.100, 0.200] at phase 75% |
| 25.0% | -0.416 | -0.050 to 0.150 | Value -0.416 outside range [-0.050, 0.150] at phase 25% |
| 50.0% | -0.642 | -0.450 to -0.250 | Value -0.642 outside range [-0.450, -0.250] at phase 50% |
| 75.0% | -1.187 | -0.100 to 0.200 | Value -1.187 outside range [-0.100, 0.200] at phase 75% |
| 25.0% | -0.463 | -0.050 to 0.150 | Value -0.463 outside range [-0.050, 0.150] at phase 25% |
| 50.0% | -0.686 | -0.450 to -0.250 | Value -0.686 outside range [-0.450, -0.250] at phase 50% |
| 75.0% | -1.173 | -0.100 to 0.200 | Value -1.173 outside range [-0.100, 0.200] at phase 75% |
| 25.0% | -0.438 | -0.050 to 0.150 | Value -0.438 outside range [-0.050, 0.150] at phase 25% |

*... and 10145 more failures*

#### Task: Incline Walking

**Variable: hip_flexion_angle_ipsi** (9452 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.043 | 0.250 to 0.800 | Value 0.043 outside range [0.250, 0.800] at phase 0% |
| 25.0% | 0.605 | 0.000 to 0.500 | Value 0.605 outside range [0.000, 0.500] at phase 25% |
| 50.0% | 0.961 | -0.200 to 0.300 | Value 0.961 outside range [-0.200, 0.300] at phase 50% |
| 0.0% | 0.091 | 0.250 to 0.800 | Value 0.091 outside range [0.250, 0.800] at phase 0% |
| 25.0% | 0.623 | 0.000 to 0.500 | Value 0.623 outside range [0.000, 0.500] at phase 25% |
| 50.0% | 0.862 | -0.200 to 0.300 | Value 0.862 outside range [-0.200, 0.300] at phase 50% |
| 0.0% | 0.067 | 0.250 to 0.800 | Value 0.067 outside range [0.250, 0.800] at phase 0% |
| 25.0% | 0.629 | 0.000 to 0.500 | Value 0.629 outside range [0.000, 0.500] at phase 25% |
| 50.0% | 0.954 | -0.200 to 0.300 | Value 0.954 outside range [-0.200, 0.300] at phase 50% |
| 0.0% | 0.095 | 0.250 to 0.800 | Value 0.095 outside range [0.250, 0.800] at phase 0% |

*... and 9442 more failures*

**Variable: knee_flexion_angle_ipsi** (11610 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.350 | 0.000 to 0.250 | Value 0.350 outside range [0.000, 0.250] at phase 0% |
| 25.0% | 0.005 | 0.100 to 0.400 | Value 0.005 outside range [0.100, 0.400] at phase 25% |
| 50.0% | 0.239 | 0.600 to 0.900 | Value 0.239 outside range [0.600, 0.900] at phase 50% |
| 75.0% | 0.432 | 0.900 to 1.500 | Value 0.432 outside range [0.900, 1.500] at phase 75% |
| 0.0% | 0.413 | 0.000 to 0.250 | Value 0.413 outside range [0.000, 0.250] at phase 0% |
| 25.0% | 0.014 | 0.100 to 0.400 | Value 0.014 outside range [0.100, 0.400] at phase 25% |
| 50.0% | 0.253 | 0.600 to 0.900 | Value 0.253 outside range [0.600, 0.900] at phase 50% |
| 75.0% | 0.447 | 0.900 to 1.500 | Value 0.447 outside range [0.900, 1.500] at phase 75% |
| 0.0% | 0.392 | 0.000 to 0.250 | Value 0.392 outside range [0.000, 0.250] at phase 0% |
| 25.0% | -0.011 | 0.100 to 0.400 | Value -0.011 outside range [0.100, 0.400] at phase 25% |

*... and 11600 more failures*

**Variable: knee_flexion_angle_contra** (10172 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.961 | 0.600 to 0.900 | Value 0.961 outside range [0.600, 0.900] at phase 0% |
| 25.0% | 0.553 | 0.900 to 1.500 | Value 0.553 outside range [0.900, 1.500] at phase 25% |
| 75.0% | 0.623 | 0.100 to 0.400 | Value 0.623 outside range [0.100, 0.400] at phase 75% |
| 25.0% | 0.475 | 0.900 to 1.500 | Value 0.475 outside range [0.900, 1.500] at phase 25% |
| 75.0% | 0.629 | 0.100 to 0.400 | Value 0.629 outside range [0.100, 0.400] at phase 75% |
| 0.0% | 0.954 | 0.600 to 0.900 | Value 0.954 outside range [0.600, 0.900] at phase 0% |
| 25.0% | 0.546 | 0.900 to 1.500 | Value 0.546 outside range [0.900, 1.500] at phase 25% |
| 75.0% | 0.661 | 0.100 to 0.400 | Value 0.661 outside range [0.100, 0.400] at phase 75% |
| 0.0% | 0.907 | 0.600 to 0.900 | Value 0.907 outside range [0.600, 0.900] at phase 0% |
| 25.0% | 0.518 | 0.900 to 1.500 | Value 0.518 outside range [0.900, 1.500] at phase 25% |

*... and 10162 more failures*

**Variable: ankle_flexion_angle_ipsi** (11305 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | -0.464 | 0.050 to 0.250 | Value -0.464 outside range [0.050, 0.250] at phase 0% |
| 25.0% | -0.495 | 0.100 to 0.300 | Value -0.495 outside range [0.100, 0.300] at phase 25% |
| 50.0% | -0.076 | -0.300 to -0.100 | Value -0.076 outside range [-0.300, -0.100] at phase 50% |
| 75.0% | -1.178 | 0.000 to 0.350 | Value -1.178 outside range [0.000, 0.350] at phase 75% |
| 0.0% | -0.499 | 0.050 to 0.250 | Value -0.499 outside range [0.050, 0.250] at phase 0% |
| 25.0% | -0.445 | 0.100 to 0.300 | Value -0.445 outside range [0.100, 0.300] at phase 25% |
| 50.0% | -0.099 | -0.300 to -0.100 | Value -0.099 outside range [-0.300, -0.100] at phase 50% |
| 75.0% | -1.170 | 0.000 to 0.350 | Value -1.170 outside range [0.000, 0.350] at phase 75% |
| 0.0% | -0.556 | 0.050 to 0.250 | Value -0.556 outside range [0.050, 0.250] at phase 0% |
| 25.0% | -0.462 | 0.100 to 0.300 | Value -0.462 outside range [0.100, 0.300] at phase 25% |

*... and 11295 more failures*

**Variable: ankle_flexion_angle_contra** (9475 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.239 | -0.300 to -0.100 | Value 0.239 outside range [-0.300, -0.100] at phase 0% |
| 25.0% | 0.432 | 0.000 to 0.350 | Value 0.432 outside range [0.000, 0.350] at phase 25% |
| 50.0% | 0.413 | 0.050 to 0.250 | Value 0.413 outside range [0.050, 0.250] at phase 50% |
| 75.0% | 0.014 | 0.100 to 0.300 | Value 0.014 outside range [0.100, 0.300] at phase 75% |
| 0.0% | 0.253 | -0.300 to -0.100 | Value 0.253 outside range [-0.300, -0.100] at phase 0% |
| 25.0% | 0.447 | 0.000 to 0.350 | Value 0.447 outside range [0.000, 0.350] at phase 25% |
| 50.0% | 0.392 | 0.050 to 0.250 | Value 0.392 outside range [0.050, 0.250] at phase 50% |
| 75.0% | -0.011 | 0.100 to 0.300 | Value -0.011 outside range [0.100, 0.300] at phase 75% |
| 0.0% | 0.256 | -0.300 to -0.100 | Value 0.256 outside range [-0.300, -0.100] at phase 0% |
| 25.0% | 0.442 | 0.000 to 0.350 | Value 0.442 outside range [0.000, 0.350] at phase 25% |

*... and 9465 more failures*

**Variable: hip_flexion_angle_contra** (10020 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | -1.148 | 0.400 to 1.000 | Value -1.148 outside range [0.400, 1.000] at phase 25% |
| 50.0% | -0.464 | 0.250 to 0.800 | Value -0.464 outside range [0.250, 0.800] at phase 50% |
| 75.0% | -0.495 | 0.000 to 0.500 | Value -0.495 outside range [0.000, 0.500] at phase 75% |
| 25.0% | -1.178 | 0.400 to 1.000 | Value -1.178 outside range [0.400, 1.000] at phase 25% |
| 50.0% | -0.499 | 0.250 to 0.800 | Value -0.499 outside range [0.250, 0.800] at phase 50% |
| 75.0% | -0.445 | 0.000 to 0.500 | Value -0.445 outside range [0.000, 0.500] at phase 75% |
| 25.0% | -1.170 | 0.400 to 1.000 | Value -1.170 outside range [0.400, 1.000] at phase 25% |
| 50.0% | -0.556 | 0.250 to 0.800 | Value -0.556 outside range [0.250, 0.800] at phase 50% |
| 75.0% | -0.462 | 0.000 to 0.500 | Value -0.462 outside range [0.000, 0.500] at phase 75% |
| 25.0% | -1.173 | 0.400 to 1.000 | Value -1.173 outside range [0.400, 1.000] at phase 25% |

*... and 10010 more failures*

#### Task: Level Walking

**Variable: hip_flexion_angle_ipsi** (5596 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | -0.036 | 0.150 to 0.600 | Value -0.036 outside range [0.150, 0.600] at phase 0% |
| 25.0% | 0.473 | -0.050 to 0.350 | Value 0.473 outside range [-0.050, 0.350] at phase 25% |
| 50.0% | 0.573 | -0.350 to 0.000 | Value 0.573 outside range [-0.350, 0.000] at phase 50% |
| 75.0% | 0.249 | 0.300 to 0.900 | Value 0.249 outside range [0.300, 0.900] at phase 75% |
| 0.0% | 0.010 | 0.150 to 0.600 | Value 0.010 outside range [0.150, 0.600] at phase 0% |
| 25.0% | 0.522 | -0.050 to 0.350 | Value 0.522 outside range [-0.050, 0.350] at phase 25% |
| 50.0% | 0.571 | -0.350 to 0.000 | Value 0.571 outside range [-0.350, 0.000] at phase 50% |
| 75.0% | 0.233 | 0.300 to 0.900 | Value 0.233 outside range [0.300, 0.900] at phase 75% |
| 0.0% | 0.017 | 0.150 to 0.600 | Value 0.017 outside range [0.150, 0.600] at phase 0% |
| 25.0% | 0.491 | -0.050 to 0.350 | Value 0.491 outside range [-0.050, 0.350] at phase 25% |

*... and 5586 more failures*

**Variable: knee_flexion_angle_ipsi** (6271 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.246 | 0.000 to 0.150 | Value 0.246 outside range [0.000, 0.150] at phase 0% |
| 25.0% | -0.055 | 0.050 to 0.250 | Value -0.055 outside range [0.050, 0.250] at phase 25% |
| 50.0% | 0.123 | 0.500 to 0.800 | Value 0.123 outside range [0.500, 0.800] at phase 50% |
| 75.0% | 0.192 | 0.800 to 1.300 | Value 0.192 outside range [0.800, 1.300] at phase 75% |
| 0.0% | 0.232 | 0.000 to 0.150 | Value 0.232 outside range [0.000, 0.150] at phase 0% |
| 25.0% | -0.077 | 0.050 to 0.250 | Value -0.077 outside range [0.050, 0.250] at phase 25% |
| 50.0% | 0.040 | 0.500 to 0.800 | Value 0.040 outside range [0.500, 0.800] at phase 50% |
| 75.0% | 0.175 | 0.800 to 1.300 | Value 0.175 outside range [0.800, 1.300] at phase 75% |
| 0.0% | 0.248 | 0.000 to 0.150 | Value 0.248 outside range [0.000, 0.150] at phase 0% |
| 25.0% | -0.102 | 0.050 to 0.250 | Value -0.102 outside range [0.050, 0.250] at phase 25% |

*... and 6261 more failures*

**Variable: ankle_flexion_angle_ipsi** (5623 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | -0.152 | -0.050 to 0.050 | Value -0.152 outside range [-0.050, 0.050] at phase 0% |
| 25.0% | -0.228 | 0.050 to 0.250 | Value -0.228 outside range [0.050, 0.250] at phase 25% |
| 75.0% | -1.094 | -0.100 to 0.200 | Value -1.094 outside range [-0.100, 0.200] at phase 75% |
| 0.0% | -0.089 | -0.050 to 0.050 | Value -0.089 outside range [-0.050, 0.050] at phase 0% |
| 25.0% | -0.219 | 0.050 to 0.250 | Value -0.219 outside range [0.050, 0.250] at phase 25% |
| 50.0% | -0.198 | -0.400 to -0.200 | Value -0.198 outside range [-0.400, -0.200] at phase 50% |
| 75.0% | -1.103 | -0.100 to 0.200 | Value -1.103 outside range [-0.100, 0.200] at phase 75% |
| 0.0% | -0.118 | -0.050 to 0.050 | Value -0.118 outside range [-0.050, 0.050] at phase 0% |
| 25.0% | -0.228 | 0.050 to 0.250 | Value -0.228 outside range [0.050, 0.250] at phase 25% |
| 50.0% | -0.165 | -0.400 to -0.200 | Value -0.165 outside range [-0.400, -0.200] at phase 50% |

*... and 5613 more failures*

**Variable: ankle_flexion_angle_contra** (4836 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 0.0% | 0.123 | -0.400 to -0.200 | Value 0.123 outside range [-0.400, -0.200] at phase 0% |
| 50.0% | 0.232 | -0.050 to 0.050 | Value 0.232 outside range [-0.050, 0.050] at phase 50% |
| 75.0% | -0.077 | 0.050 to 0.250 | Value -0.077 outside range [0.050, 0.250] at phase 75% |
| 0.0% | 0.040 | -0.400 to -0.200 | Value 0.040 outside range [-0.400, -0.200] at phase 0% |
| 50.0% | 0.248 | -0.050 to 0.050 | Value 0.248 outside range [-0.050, 0.050] at phase 50% |
| 75.0% | -0.102 | 0.050 to 0.250 | Value -0.102 outside range [0.050, 0.250] at phase 75% |
| 0.0% | 0.134 | -0.400 to -0.200 | Value 0.134 outside range [-0.400, -0.200] at phase 0% |
| 50.0% | 0.255 | -0.050 to 0.050 | Value 0.255 outside range [-0.050, 0.050] at phase 50% |
| 75.0% | -0.101 | 0.050 to 0.250 | Value -0.101 outside range [0.050, 0.250] at phase 75% |
| 0.0% | 0.050 | -0.400 to -0.200 | Value 0.050 outside range [-0.400, -0.200] at phase 0% |

*... and 4826 more failures*

**Variable: hip_flexion_angle_contra** (4832 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | -1.152 | 0.300 to 0.900 | Value -1.152 outside range [0.300, 0.900] at phase 25% |
| 50.0% | -0.152 | 0.150 to 0.600 | Value -0.152 outside range [0.150, 0.600] at phase 50% |
| 75.0% | -0.228 | -0.050 to 0.350 | Value -0.228 outside range [-0.050, 0.350] at phase 75% |
| 25.0% | -1.094 | 0.300 to 0.900 | Value -1.094 outside range [0.300, 0.900] at phase 25% |
| 50.0% | -0.089 | 0.150 to 0.600 | Value -0.089 outside range [0.150, 0.600] at phase 50% |
| 75.0% | -0.219 | -0.050 to 0.350 | Value -0.219 outside range [-0.050, 0.350] at phase 75% |
| 25.0% | -1.103 | 0.300 to 0.900 | Value -1.103 outside range [0.300, 0.900] at phase 25% |
| 50.0% | -0.118 | 0.150 to 0.600 | Value -0.118 outside range [0.150, 0.600] at phase 50% |
| 75.0% | -0.228 | -0.050 to 0.350 | Value -0.228 outside range [-0.050, 0.350] at phase 75% |
| 25.0% | -1.144 | 0.300 to 0.900 | Value -1.144 outside range [0.300, 0.900] at phase 25% |

*... and 4822 more failures*

**Variable: knee_flexion_angle_contra** (4911 failures)

| Phase | Value | Expected Range | Failure Reason |
|-------|-------|----------------|----------------|
| 25.0% | 0.249 | 0.800 to 1.300 | Value 0.249 outside range [0.800, 1.300] at phase 25% |
| 75.0% | 0.522 | 0.050 to 0.250 | Value 0.522 outside range [0.050, 0.250] at phase 75% |
| 25.0% | 0.233 | 0.800 to 1.300 | Value 0.233 outside range [0.800, 1.300] at phase 25% |
| 75.0% | 0.491 | 0.050 to 0.250 | Value 0.491 outside range [0.050, 0.250] at phase 75% |
| 25.0% | 0.290 | 0.800 to 1.300 | Value 0.290 outside range [0.800, 1.300] at phase 25% |
| 75.0% | 0.477 | 0.050 to 0.250 | Value 0.477 outside range [0.050, 0.250] at phase 75% |
| 25.0% | 0.221 | 0.800 to 1.300 | Value 0.221 outside range [0.800, 1.300] at phase 25% |
| 50.0% | -0.014 | 0.000 to 0.150 | Value -0.014 outside range [0.000, 0.150] at phase 50% |
| 75.0% | 0.540 | 0.050 to 0.250 | Value 0.540 outside range [0.050, 0.250] at phase 75% |
| 25.0% | 0.260 | 0.800 to 1.300 | Value 0.260 outside range [0.800, 1.300] at phase 25% |

*... and 4901 more failures*


## Recommendations

1. Review data collection protocols for tasks with high failure rates
2. Check sensor calibration for variables consistently out of range
3. Verify subject instructions and movement quality
4. Consider if validation ranges need updating for your population
