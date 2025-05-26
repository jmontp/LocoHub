# Conversion Scripts Consolidation Plan

## Overview
This document outlines the proposed consolidation of conversion scripts to reduce redundancy and improve maintainability.

## GTech 2023 Consolidation

### Scripts to Keep:
1. **convert_gtech_all_to_parquet.py** - Main time-indexed converter
   - Already supports single subject conversion via command line
   - Well-documented and actively used
   
2. **convert_gtech_phase_to_parquet.m** - Phase-indexed converter
   - Essential for phase-normalized data
   
3. **combine_subjects_efficient.py** - Subject combination utility
   - Memory-efficient for large datasets

### Scripts to Remove:
1. **convert_gtech_time_to_parquet.py**
   - Redundant with convert_gtech_all_to_parquet.py
   - Appears to be an older version with similar functionality
   
2. **Gtechalltoparquet.ipynb**
   - Notebook version likely used for development
   - Functionality covered by Python scripts

### Scripts to Move to Utilities Folder:
Create `source/conversion_scripts/Gtech_2023/utilities/`:
1. **benchmark_processing.m** - Performance testing
2. **plot_leg_alignment.m** - Visualization tool
3. **test_parquet_conversion.m** - Testing script
4. **verify_gtech_data.ipynb** - Data verification
5. **convert_gtech_rotm_to_eul_csv.m** - Specialized conversion

## UMich 2021 Consolidation

### Scripts to Keep:
All current scripts are essential:
1. **convert_umich_time_to_parquet.m** - Time-indexed converter
2. **convert_umich_phase_to_parquet.m** - Phase-indexed converter
3. **verify_umich_data.ipynb** - Data verification

The UMich folder is already well-organized with minimal scripts.

## Benefits of Consolidation

1. **Reduced Confusion**: Clear which scripts are the main entry points
2. **Easier Maintenance**: Fewer scripts to update when making changes
3. **Better Organization**: Utilities separated from main converters
4. **Consistent Structure**: Both datasets follow similar organization

## Implementation Steps

1. Create utilities folders for auxiliary scripts
2. Move/delete redundant scripts as identified
3. Update README files to reflect new structure
4. Test that main conversion workflows still function

## Notes

- Before removing any scripts, verify they don't contain unique functionality
- Consider keeping notebooks in a separate 'notebooks' folder for reference
- Ensure all file paths in scripts are updated after reorganization