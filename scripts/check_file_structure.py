#!/usr/bin/env python3
import pandas as pd

# Check Gtech file columns
print('=== Checking Gtech Phase File ===')
df_gtech = pd.read_parquet('source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet', columns=['subject', 'task', 'phase'])
print(f'Unique subjects: {df_gtech["subject"].nunique()}')
print(f'Unique tasks: {df_gtech["task"].nunique()}')
print(f'Total rows: {len(df_gtech)}')
print('File is monolithic (single parquet file)')
print()

# Check UMich file  
print('=== Checking UMich Phase File ===')
df_umich = pd.read_parquet('source/conversion_scripts/Umich_2021/umich_2021_phase.parquet', columns=['subject_id', 'task_name', 'phase'])
print(f'Unique subjects: {df_umich["subject_id"].nunique()}')
print(f'Unique tasks: {df_umich["task_name"].nunique()}')
print(f'Total rows: {len(df_umich)}')
print('File is monolithic (single parquet file)')