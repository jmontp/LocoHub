---
title: Contributing to LocoHub
---

# Contributing to LocoHub

A streamlined process for converting your biomechanical data to the LocoHub standard.

## Step 1: Table Format

Your data needs to be organized in a standardized table format with specific column names and structure.

### Required Structure

Each row represents one point in the gait cycle (150 points total, 0-100% of cycle).

<div style="overflow-x: auto; border: 1px solid #ddd; margin: 20px 0;">
<table style="border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; width: 100%; min-width: 1200px;">
<thead>
<tr style="background-color: #f0f0f0; border-bottom: 2px solid #a0a0a0;">
<th style="border: 1px solid #d0d0d0; padding: 6px 4px; text-align: center; font-weight: 600; background-color: #e0e0e0; width: 40px;"></th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: left; font-weight: 600;">subject</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: left; font-weight: 600;">task</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: left; font-weight: 600;">task_id</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: left; font-weight: 600;">task_info</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: center; font-weight: 600;">step</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: right; font-weight: 600;">phase_ipsi</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: right; font-weight: 600;">hip_flexion_angle_ipsi_rad</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: right; font-weight: 600;">knee_flexion_angle_ipsi_rad</th>
<th style="border: 1px solid #d0d0d0; padding: 6px 8px; text-align: right; font-weight: 600;">ankle_dorsiflexion_angle_ipsi_rad</th>
</tr>
</thead>
<tbody>
<tr style="background-color: #ffffff;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">2</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">UM21_AB01</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking_normal</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.2,incline_deg:0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">1</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.524</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.122</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.105</td>
</tr>
<tr style="background-color: #f9f9f9;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">3</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">UM21_AB01</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking_normal</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.2,incline_deg:0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">1</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.67</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.541</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.157</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.087</td>
</tr>
<tr style="background-color: #ffffff;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">4</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">UM21_AB01</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking_normal</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.2,incline_deg:0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">1</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">1.33</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.559</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.192</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.070</td>
</tr>
<tr style="background-color: #f9f9f9;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">5</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">UM21_AB01</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking_normal</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.2,incline_deg:0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">1</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">2.0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.576</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.227</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.052</td>
</tr>
<tr style="background-color: #ffffff;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">6</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center; color: #888;" colspan="9">...</td>
</tr>
<tr style="background-color: #f9f9f9;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">151</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">UM21_AB01</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">level_walking_normal</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.2,incline_deg:0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">1</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">99.33</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.507</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.087</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.122</td>
</tr>
<tr style="background-color: #ffffff;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">152</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">GT23_AB05</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">incline_walking</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">incline_10deg</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">speed_m_s:1.0,incline_deg:10</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">3</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.698</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.209</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">-0.087</td>
</tr>
<tr style="background-color: #f9f9f9;">
<td style="border: 1px solid #d0d0d0; padding: 4px 4px; text-align: center; font-weight: 600; background-color: #e8e8e8; color: #666;">153</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">PROS_TFA03</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">stair_ascent</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">stair_ascent_17cm</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px;">step_height_m:0.17,step_width_m:0.28</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: center;">2</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.0</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.873</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.349</td>
<td style="border: 1px solid #d0d0d0; padding: 4px 8px; text-align: right;">0.052</td>
</tr>
</tbody>
</table>
</div>

### Key Requirements
- **Subject Naming**: `<DATASET>_<POPULATION><NUMBER>` (e.g., UM21_AB01)
  - Dataset code (2-4 chars)
  - Population code: AB (able-bodied), TFA (transfemoral amputee), etc.
  - Subject number (01-999)
- **Task Columns**:
  - `task`: General category (e.g., level_walking, incline_walking)
  - `task_id`: Specific variant (e.g., incline_10deg)
  - `task_info`: Metadata as key:value pairs (e.g., speed_m_s:1.2,incline_deg:10)
- **150 rows per gait cycle** (phase_ipsi: 0 to 99.33)
- **Standard variable names**: `joint_motion_side_unit`
- **Units**: Angles in radians (`_rad`), moments in Newton-meters (`_Nm`)

### Download Example Dataset

Download a complete example dataset with 1000 rows showing multiple subjects, tasks, and realistic biomechanical data:

[Download Example CSV (1000 rows)](locohub_example_data.csv){ .md-button .md-button--primary download="locohub_example_data.csv" }

This example includes 4 subjects performing various tasks (level walking, incline/decline walking, stair ascent/descent) with complete kinematic and kinetic data.

## Step 2: Validate

Your data must pass biomechanical validation to ensure it represents realistic human movement patterns.

### What Good Data Looks Like

A typical knee flexion pattern during level walking should be smooth and within expected ranges:

```
Knee Flexion Angle (rad)
  1.5 |                    oo                           
      |                  o    o                         
  1.2 |                o        o                       
      |              o            o                     
  0.9 |            o                o                   
      |          o                    o                 
  0.6 |        o                        o               
      |      o                            o             
  0.3 |    o                                o           
      |  o                                    o         
  0.0 |o                                        o       
      +------------------------------------------------
      0    20    40    60    80   100   120   140   150
                    Phase Percentage (0-100%)
```

### Validation Process: Good vs Bad Data

The validation system compares your data against expected biomechanical patterns:

```
Knee Flexion Comparison
  1.8 |                                        X        
      |              X                                  
  1.5 |                    oo            X              
      |                  o    o                         
  1.2 |                o        o   X                   
      |              o            o                     
  0.9 |            o                o                   
      |          o                    o                 
  0.6 |        o                        o               
      |      o                            o             
  0.3 |    o                                o           
      |X o                                    o         
  0.0 |o                                        o       
      |                                              X  
 -0.3 |                 X                              
      +------------------------------------------------
      0    20    40    60    80   100   120   140   150
                    Phase Percentage (0-100%)

Legend: o = Valid data points    X = Invalid outliers
```

### Validation Ranges

The system checks if data points fall within acceptable ranges at specific phases:

```
Validation Box Example (Phase 25-75%)
  1.8 |                                                 
      |           ╔═══════════════════════╗             
  1.5 |           ║         oo            ║        X    
      |           ║       o    o          ║             
  1.2 |           ║     o        o        ║             
      |           ║   o            o      ║             
  0.9 |           ║ o                o    ║             
      |           ║                    o  ║             
  0.6 |           ║                     o ║             
      |           ║                       ║             
  0.3 |     X     ╚═══════════════════════╝             
      |                                                 
  0.0 |o                                        o       
      +------------------------------------------------
      0    20    40    60    80   100   120   140   150
                    Phase Percentage (0-100%)

Box = Validation range (0.3-1.5 rad for phase 25-75%)
o = Points inside range (PASS)    X = Points outside range (FAIL)
```

### Validation Tools

Use these tools to check your data:

- **Quick check**: `python quick_validation_check.py your_data.parquet`
- **Interactive tuning**: `python interactive_validation_tuner.py`
- **Full report**: `python create_dataset_validation_report.py --dataset your_data.parquet`

## Step 3: Upload

*Content to be added*

## Step 4: Advanced Topics

*Content to be added*