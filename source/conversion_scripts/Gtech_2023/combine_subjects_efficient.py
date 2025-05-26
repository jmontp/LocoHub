#!/usr/bin/env python3
"""
Memory-efficient script to combine individual subject parquet files.
Uses chunked reading and writing to avoid loading everything into memory at once.
"""

import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import glob
import os
import gc

def combine_parquet_files_efficient():
    # Find all individual subject parquet files
    subject_files = sorted(glob.glob('gtech_2023_time_AB*.parquet'))
    print(f"Found {len(subject_files)} subject files to combine")
    
    if not subject_files:
        print("No subject files found!")
        return
    
    output_file = 'gtech_2023_time.parquet'
    
    # Initialize the parquet writer
    writer = None
    total_rows = 0
    
    try:
        for i, file in enumerate(subject_files):
            print(f"\nProcessing {file} ({i+1}/{len(subject_files)})...")
            
            # Read the parquet file
            df = pd.read_parquet(file)
            print(f"  Loaded {len(df)} rows")
            
            # Convert to PyArrow table
            table = pa.Table.from_pandas(df)
            
            # Initialize writer with schema from first file
            if writer is None:
                writer = pq.ParquetWriter(output_file, table.schema)
            
            # Write the table
            writer.write_table(table)
            total_rows += len(df)
            
            # Clear memory
            del df
            del table
            gc.collect()
            
            print(f"  Written. Total rows so far: {total_rows}")
            
    finally:
        if writer:
            writer.close()
    
    print(f"\nSuccessfully combined all files into {output_file}")
    print(f"Total rows: {total_rows}")
    
    # Verify the output
    file_size = os.path.getsize(output_file) / 1024**2
    print(f"Output file size: {file_size:.1f} MB")
    
    # Quick verification - just check we can read metadata
    metadata = pq.read_metadata(output_file)
    print(f"Verified: {metadata.num_rows} rows in {metadata.num_row_groups} row groups")

if __name__ == "__main__":
    combine_parquet_files_efficient()