# Validation Failure Analysis Report

**Generated**: 2025-06-10 08:23:19
**Dataset**: converted_datasets/umich_2021_phase.parquet

## 🚨 Validation Failures Summary

**Total Failures**: 2361258

### Task: Decline Walking

**Failures in this task**: 981837

#### Variable: hip_flexion_angle_contra

**Failures**: 258397

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 0 | N/A | 0.0% | 0.271 | -0.400 | 0.100 | Above max |
| 0 | N/A | 0.7% | 0.272 | -0.400 | 0.100 | Above max |
| 0 | N/A | 1.3% | 0.274 | -0.400 | 0.100 | Above max |
| 0 | N/A | 2.0% | 0.277 | -0.400 | 0.100 | Above max |
| 0 | N/A | 2.7% | 0.282 | -0.400 | 0.100 | Above max |
| 0 | N/A | 3.3% | 0.288 | -0.400 | 0.100 | Above max |
| 0 | N/A | 4.0% | 0.296 | -0.400 | 0.100 | Above max |
| 0 | N/A | 4.7% | 0.305 | -0.400 | 0.100 | Above max |
| 0 | N/A | 5.3% | 0.317 | -0.400 | 0.100 | Above max |
| 0 | N/A | 6.0% | 0.329 | -0.400 | 0.100 | Above max |

*... and 258387 more failures*

#### Variable: knee_flexion_angle_contra

**Failures**: 442332

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 0 | N/A | 0.0% | -0.775 | 0.400 | 0.700 | Below min |
| 0 | N/A | 0.7% | -0.792 | 0.400 | 0.700 | Below min |
| 0 | N/A | 1.3% | -0.811 | 0.400 | 0.700 | Below min |
| 0 | N/A | 2.0% | -0.830 | 0.400 | 0.700 | Below min |
| 0 | N/A | 2.7% | -0.852 | 0.400 | 0.700 | Below min |
| 0 | N/A | 3.3% | -0.876 | 0.400 | 0.700 | Below min |
| 0 | N/A | 4.0% | -0.900 | 0.400 | 0.700 | Below min |
| 0 | N/A | 4.7% | -0.927 | 0.400 | 0.700 | Below min |
| 0 | N/A | 5.3% | -0.955 | 0.400 | 0.700 | Below min |
| 0 | N/A | 6.0% | -0.984 | 0.400 | 0.700 | Below min |

*... and 442322 more failures*

#### Variable: ankle_flexion_angle_contra

**Failures**: 281108

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 0 | N/A | 0.0% | 0.295 | -0.450 | -0.250 | Above max |
| 0 | N/A | 0.7% | 0.288 | -0.450 | -0.250 | Above max |
| 0 | N/A | 1.3% | 0.279 | -0.450 | -0.250 | Above max |
| 0 | N/A | 2.0% | 0.268 | -0.450 | -0.250 | Above max |
| 0 | N/A | 2.7% | 0.253 | -0.450 | -0.250 | Above max |
| 0 | N/A | 3.3% | 0.235 | -0.450 | -0.250 | Above max |
| 0 | N/A | 4.0% | 0.214 | -0.450 | -0.250 | Above max |
| 0 | N/A | 4.7% | 0.190 | -0.450 | -0.250 | Above max |
| 0 | N/A | 5.3% | 0.161 | -0.450 | -0.250 | Above max |
| 0 | N/A | 6.0% | 0.130 | -0.450 | -0.250 | Above max |

*... and 281098 more failures*

### Task: Level Walking

**Failures in this task**: 419760

#### Variable: hip_flexion_angle_contra

**Failures**: 91473

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 99 | N/A | 10.7% | 0.015 | -0.350 | 0.000 | Above max |
| 99 | N/A | 11.3% | 0.034 | -0.350 | 0.000 | Above max |
| 99 | N/A | 12.0% | 0.054 | -0.350 | 0.000 | Above max |
| 99 | N/A | 12.7% | 0.077 | 0.300 | 0.900 | Below min |
| 99 | N/A | 13.3% | 0.101 | 0.300 | 0.900 | Below min |
| 99 | N/A | 14.0% | 0.126 | 0.300 | 0.900 | Below min |
| 99 | N/A | 14.7% | 0.151 | 0.300 | 0.900 | Below min |
| 99 | N/A | 15.3% | 0.176 | 0.300 | 0.900 | Below min |
| 99 | N/A | 16.0% | 0.200 | 0.300 | 0.900 | Below min |
| 99 | N/A | 16.7% | 0.224 | 0.300 | 0.900 | Below min |

*... and 91463 more failures*

#### Variable: knee_flexion_angle_contra

**Failures**: 209969

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 99 | N/A | 0.0% | -0.165 | 0.500 | 0.800 | Below min |
| 99 | N/A | 0.7% | -0.176 | 0.500 | 0.800 | Below min |
| 99 | N/A | 1.3% | -0.187 | 0.500 | 0.800 | Below min |
| 99 | N/A | 2.0% | -0.199 | 0.500 | 0.800 | Below min |
| 99 | N/A | 2.7% | -0.212 | 0.500 | 0.800 | Below min |
| 99 | N/A | 3.3% | -0.226 | 0.500 | 0.800 | Below min |
| 99 | N/A | 4.0% | -0.241 | 0.500 | 0.800 | Below min |
| 99 | N/A | 4.7% | -0.258 | 0.500 | 0.800 | Below min |
| 99 | N/A | 5.3% | -0.276 | 0.500 | 0.800 | Below min |
| 99 | N/A | 6.0% | -0.296 | 0.500 | 0.800 | Below min |

*... and 209959 more failures*

#### Variable: ankle_flexion_angle_contra

**Failures**: 118318

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 99 | N/A | 0.0% | 0.246 | -0.400 | -0.200 | Above max |
| 99 | N/A | 0.7% | 0.246 | -0.400 | -0.200 | Above max |
| 99 | N/A | 1.3% | 0.245 | -0.400 | -0.200 | Above max |
| 99 | N/A | 2.0% | 0.243 | -0.400 | -0.200 | Above max |
| 99 | N/A | 2.7% | 0.240 | -0.400 | -0.200 | Above max |
| 99 | N/A | 3.3% | 0.235 | -0.400 | -0.200 | Above max |
| 99 | N/A | 4.0% | 0.229 | -0.400 | -0.200 | Above max |
| 99 | N/A | 4.7% | 0.221 | -0.400 | -0.200 | Above max |
| 99 | N/A | 5.3% | 0.211 | -0.400 | -0.200 | Above max |
| 99 | N/A | 6.0% | 0.199 | -0.400 | -0.200 | Above max |

*... and 118308 more failures*

### Task: Incline Walking

**Failures in this task**: 959661

#### Variable: hip_flexion_angle_contra

**Failures**: 210645

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 142 | N/A | 12.7% | 0.097 | 0.400 | 1.000 | Below min |
| 142 | N/A | 13.3% | 0.119 | 0.400 | 1.000 | Below min |
| 142 | N/A | 14.0% | 0.143 | 0.400 | 1.000 | Below min |
| 142 | N/A | 14.7% | 0.169 | 0.400 | 1.000 | Below min |
| 142 | N/A | 15.3% | 0.195 | 0.400 | 1.000 | Below min |
| 142 | N/A | 16.0% | 0.223 | 0.400 | 1.000 | Below min |
| 142 | N/A | 16.7% | 0.252 | 0.400 | 1.000 | Below min |
| 142 | N/A | 17.3% | 0.282 | 0.400 | 1.000 | Below min |
| 142 | N/A | 18.0% | 0.312 | 0.400 | 1.000 | Below min |
| 142 | N/A | 18.7% | 0.342 | 0.400 | 1.000 | Below min |

*... and 210635 more failures*

#### Variable: knee_flexion_angle_contra

**Failures**: 470163

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 142 | N/A | 0.0% | -0.090 | 0.600 | 0.900 | Below min |
| 142 | N/A | 0.7% | -0.099 | 0.600 | 0.900 | Below min |
| 142 | N/A | 1.3% | -0.109 | 0.600 | 0.900 | Below min |
| 142 | N/A | 2.0% | -0.119 | 0.600 | 0.900 | Below min |
| 142 | N/A | 2.7% | -0.130 | 0.600 | 0.900 | Below min |
| 142 | N/A | 3.3% | -0.141 | 0.600 | 0.900 | Below min |
| 142 | N/A | 4.0% | -0.154 | 0.600 | 0.900 | Below min |
| 142 | N/A | 4.7% | -0.167 | 0.600 | 0.900 | Below min |
| 142 | N/A | 5.3% | -0.182 | 0.600 | 0.900 | Below min |
| 142 | N/A | 6.0% | -0.198 | 0.600 | 0.900 | Below min |

*... and 470153 more failures*

#### Variable: ankle_flexion_angle_contra

**Failures**: 278853

| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |
|---------|-------|-------|-------|--------------|--------------|-------|
| 142 | N/A | 0.0% | 0.350 | -0.300 | -0.100 | Above max |
| 142 | N/A | 0.7% | 0.342 | -0.300 | -0.100 | Above max |
| 142 | N/A | 1.3% | 0.333 | -0.300 | -0.100 | Above max |
| 142 | N/A | 2.0% | 0.324 | -0.300 | -0.100 | Above max |
| 142 | N/A | 2.7% | 0.313 | -0.300 | -0.100 | Above max |
| 142 | N/A | 3.3% | 0.300 | -0.300 | -0.100 | Above max |
| 142 | N/A | 4.0% | 0.287 | -0.300 | -0.100 | Above max |
| 142 | N/A | 4.7% | 0.272 | -0.300 | -0.100 | Above max |
| 142 | N/A | 5.3% | 0.256 | -0.300 | -0.100 | Above max |
| 142 | N/A | 6.0% | 0.238 | -0.300 | -0.100 | Above max |

*... and 278843 more failures*


## 🔧 Debugging Recommendations

1. **Check data collection protocols** for tasks with high failure rates
2. **Verify sensor calibration** for variables consistently out of range
3. **Review subject instructions** for tasks with biomechanical implausibilities
4. **Consider updating validation ranges** if failures represent normal variation
