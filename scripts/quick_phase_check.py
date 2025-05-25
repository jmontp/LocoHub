#!/usr/bin/env python3
"""Quick phase data compliance check"""

import pandas as pd
import pyarrow.parquet as pq
import os

def check_phase_compliance(filepath):
    """Quick check for 150-point compliance"""
    
    print(f"\nChecking: {os.path.basename(filepath)}")
    
    # Get metadata
    pf = pq.ParquetFile(filepath)
    print(f"Total rows: {pf.metadata.num_rows:,}")
    
    # Get column names
    columns = pf.schema.names
    
    # Find subject/task columns
    subject_col = 'subject' if 'subject' in columns else 'subject_id'
    task_col = 'task' if 'task' in columns else 'task_name'
    
    # Load just subject and task columns
    df = pd.read_parquet(filepath, columns=[subject_col, task_col])
    
    # Get unique combinations
    unique_combos = df.groupby([subject_col, task_col]).size().reset_index(name='count')
    
    print(f"Unique subject-task combinations: {len(unique_combos)}")
    
    # Check compliance
    compliant = unique_combos[unique_combos['count'] % 150 == 0]
    non_compliant = unique_combos[unique_combos['count'] % 150 != 0]
    
    print(f"Compliant: {len(compliant)}")
    print(f"Non-compliant: {len(non_compliant)}")
    
    if len(non_compliant) > 0:
        print("\nFirst 10 non-compliant combinations:")
        for _, row in non_compliant.head(10).iterrows():
            cycles = row['count'] / 150
            print(f"  ❌ {row[subject_col]} - {row[task_col]}: {row['count']} points ({cycles:.2f} cycles)")
    else:
        print("✅ All combinations comply with 150-point standard!")
    
    # Show distribution of cycle counts
    unique_combos['cycles'] = unique_combos['count'] / 150
    cycle_dist = unique_combos['cycles'].value_counts().sort_index()
    print(f"\nCycle count distribution:")
    for cycles, count in cycle_dist.head(10).items():
        print(f"  {cycles:.1f} cycles: {count} subject-task combinations")

# Test on both datasets
datasets = [
    "/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization/source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet",
    "/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization/source/conversion_scripts/Umich_2021/umich_2021_phase.parquet"
]

for filepath in datasets:
    if os.path.exists(filepath):
        check_phase_compliance(filepath)
    else:
        print(f"File not found: {filepath}")
    print("-" * 60)