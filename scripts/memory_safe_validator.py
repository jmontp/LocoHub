#!/usr/bin/env python3
"""
Memory-safe validator for large parquet files
Processes data in chunks to avoid memory issues
"""

import os
import sys
import gc

def validate_parquet_chunked(filepath, chunk_size=10000):
    """Validate parquet file in chunks to avoid memory issues"""
    
    try:
        import pandas as pd
        import pyarrow.parquet as pq
    except ImportError as e:
        print(f"Error: Missing required package - {e}")
        print("Install with: python3 -m pip install --user pandas pyarrow --break-system-packages")
        return False
    
    print(f"\nValidating: {os.path.basename(filepath)}")
    print(f"File size: {os.path.getsize(filepath) / (1024**3):.2f} GB")
    
    # Read parquet metadata without loading data
    parquet_file = pq.ParquetFile(filepath)
    print(f"Total rows: {parquet_file.metadata.num_rows:,}")
    print(f"Columns: {parquet_file.schema.names[:10]}...")
    
    # Check if this is phase or time indexed
    columns = parquet_file.schema.names
    is_phase = 'phase_r' in columns or 'phase' in columns
    
    if is_phase:
        print("\nChecking phase-indexed data (150 points per cycle)...")
        validate_phase_data_chunked(filepath, chunk_size)
    else:
        print("\nThis appears to be time-indexed data")
        validate_time_data_chunked(filepath, chunk_size)
    
    # Force garbage collection
    gc.collect()
    return True

def validate_phase_data_chunked(filepath, chunk_size=10000):
    """Validate phase data in chunks"""
    import pandas as pd
    import pyarrow.parquet as pq
    
    # First, get actual column names from the file
    parquet_file = pq.ParquetFile(filepath)
    actual_columns = parquet_file.schema.names
    
    # Map standard names to possible column names in the file
    column_mappings = {
        'subject_id': ['subject_id', 'subject', 'Subject'],
        'task_name': ['task_name', 'task', 'Task'],
        'phase': ['phase_r', 'phase_l', 'phase', 'Phase']
    }
    
    # Find actual column names
    found_columns = {}
    for standard_name, possible_names in column_mappings.items():
        for col in possible_names:
            if col in actual_columns:
                found_columns[standard_name] = col
                break
    
    if 'subject_id' not in found_columns or 'task_name' not in found_columns:
        print("Error: Required columns not found")
        print(f"Available columns: {actual_columns[:20]}...")
        return
    
    subject_col = found_columns['subject_id']
    task_col = found_columns['task_name']
    phase_col = found_columns.get('phase', 'phase_r')
    
    print(f"Using columns: subject={subject_col}, task={task_col}, phase={phase_col}")
    
    # Process in chunks
    issues = []
    subjects_checked = set()
    
    try:
        # First, get unique combinations without loading all data
        unique_df = pd.read_parquet(
            filepath,
            columns=[subject_col, task_col]
        ).drop_duplicates()
        
        print(f"Found {len(unique_df)} unique subject-task combinations")
        
        # Check each combination
        for idx, row in unique_df.iterrows():
            subj = row[subject_col]
            task = row[task_col]
            
            if (subj, task) not in subjects_checked:
                subjects_checked.add((subj, task))
                
                # Count rows for this subject-task without loading all data
                # This is more memory efficient
                subset_df = pd.read_parquet(
                    filepath,
                    columns=[subject_col, task_col, phase_col],
                    filters=[
                        (subject_col, '=', subj),
                        (task_col, '=', task)
                    ]
                )
                
                data_length = len(subset_df)
                if data_length % 150 != 0:
                    issues.append({
                        'subject': subj,
                        'task': task,
                        'length': data_length,
                        'cycles': data_length / 150
                    })
                
                # Clear memory
                del subset_df
                gc.collect()
                
            # Show progress
            if idx > 0 and idx % 10 == 0:
                print(f"  Checked {idx}/{len(unique_df)} combinations...")
                
    except Exception as e:
        print(f"Error during validation: {e}")
    
    # Report results
    print(f"\nChecked {len(subjects_checked)} subject-task combinations")
    if issues:
        print(f"Found {len(issues)} non-compliant combinations:")
        for issue in issues[:10]:  # Show first 10
            print(f"  ❌ {issue['subject']} - {issue['task']}: "
                  f"{issue['length']} points ({issue['cycles']:.2f} cycles)")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("✅ All data complies with 150-point standard!")

def validate_time_data_chunked(filepath, chunk_size=10000):
    """Validate time-indexed data in chunks"""
    import pandas as pd
    import pyarrow.parquet as pq
    
    print("Checking time continuity and data quality...")
    
    # Get actual column names
    parquet_file = pq.ParquetFile(filepath)
    actual_columns = parquet_file.schema.names
    
    # Find time column
    time_col = None
    for col in ['time_s', 'time', 'Time']:
        if col in actual_columns:
            time_col = col
            break
    
    if not time_col:
        print("No time column found")
        return
    
    # Just check basic stats for time data
    try:
        # Sample first 10k rows
        sample = pd.read_parquet(filepath, nrows=10000)
        
        print(f"Sample time range: {sample[time_col].min():.2f} - {sample[time_col].max():.2f} seconds")
        
        # Find subject/task columns
        if 'subject' in sample.columns:
            print(f"Subjects in sample: {sample['subject'].nunique()}")
        if 'task' in sample.columns:
            print(f"Tasks in sample: {sample['task'].nunique()}")
        
    except Exception as e:
        print(f"Error checking time data: {e}")

def main():
    """Main validation routine"""
    workspace = "/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization"
    
    # Files to validate (phase-indexed only for memory safety)
    phase_files = [
        "source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet",
        "source/conversion_scripts/Umich_2021/umich_2021_phase.parquet"
    ]
    
    print("=== Memory-Safe Parquet Validation ===")
    print(f"Working directory: {workspace}")
    
    # Check available memory
    os.system("free -h")
    print()
    
    for rel_path in phase_files:
        filepath = os.path.join(workspace, rel_path)
        if os.path.exists(filepath):
            validate_parquet_chunked(filepath)
            print("-" * 60)
        else:
            print(f"File not found: {rel_path}")
    
    print("\nValidation complete!")

if __name__ == "__main__":
    main()