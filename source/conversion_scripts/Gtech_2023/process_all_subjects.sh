#!/bin/bash
# Process all Gtech subjects one by one to manage memory usage

echo "Starting individual subject processing..."

# Get list of subjects
SUBJECTS=(AB01 AB02 AB03 AB05 AB06 AB07 AB08 AB09 AB10 AB11 AB12 AB13)

# Process each subject
for subject in "${SUBJECTS[@]}"; do
    echo "Processing $subject..."
    python3 convert_gtech_all_to_parquet.py "$subject"
    
    # Check if successful
    if [ $? -eq 0 ]; then
        echo "✓ $subject completed successfully"
    else
        echo "✗ $subject failed"
        exit 1
    fi
    
    # Show memory status
    echo "Memory status:"
    free -h | grep "^Mem"
    echo ""
done

echo "All subjects processed. Combining parquet files..."

# Create Python script to combine files
python3 - << 'EOF'
import pandas as pd
import glob
import os

# Find all individual subject parquet files
subject_files = sorted(glob.glob('gtech_2023_time_AB*.parquet'))
print(f"Found {len(subject_files)} subject files: {subject_files}")

if subject_files:
    # Read and combine all files
    dfs = []
    for file in subject_files:
        print(f"Reading {file}...")
        df = pd.read_parquet(file)
        dfs.append(df)
        print(f"  Shape: {df.shape}")
    
    # Combine all dataframes
    print("\nCombining all dataframes...")
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Combined shape: {combined_df.shape}")
    
    # Save combined file
    output_file = 'gtech_2023_time.parquet'
    combined_df.to_parquet(output_file)
    print(f"\nSaved combined data to {output_file}")
    print(f"File size: {os.path.getsize(output_file) / 1024**2:.1f} MB")
    
    # Optional: remove individual files
    # for file in subject_files:
    #     os.remove(file)
else:
    print("No subject files found!")
EOF

echo "Done!"