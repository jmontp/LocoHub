#!/usr/bin/env python3
"""
Add step_number column to phase-indexed datasets.

This script adds a step_number column that increments for each gait cycle
within a subject-task combination. This enables efficient reshaping of data
without using groupby operations.
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path


def add_step_numbers(df, subject_col='subject', task_col='task', phase_col='phase', points_per_cycle=150):
    """
    Add step_number column to phase-indexed data.
    
    Args:
        df: DataFrame with phase-indexed data
        subject_col: Name of subject column
        task_col: Name of task column  
        phase_col: Name of phase column
        points_per_cycle: Number of points per gait cycle (default 150)
        
    Returns:
        DataFrame with added step_number column
    """
    # Create a copy to avoid modifying original
    df_with_steps = df.copy()
    
    # Initialize step_number column
    df_with_steps['step_number'] = -1
    
    # Process each subject-task combination
    for subject in df[subject_col].unique():
        for task in df[df[subject_col] == subject][task_col].unique():
            # Get mask for this subject-task
            mask = (df_with_steps[subject_col] == subject) & (df_with_steps[task_col] == task)
            subset_indices = df_with_steps[mask].index
            
            # Calculate number of complete cycles
            n_points = len(subset_indices)
            if n_points % points_per_cycle != 0:
                print(f"Warning: {subject} - {task} has {n_points} points, not divisible by {points_per_cycle}")
                continue
                
            n_cycles = n_points // points_per_cycle
            
            # Create step numbers (0, 0, ..., 1, 1, ..., 2, 2, ...)
            step_numbers = np.repeat(np.arange(n_cycles), points_per_cycle)
            
            # Assign step numbers
            df_with_steps.loc[subset_indices, 'step_number'] = step_numbers
    
    # Verify no unassigned step numbers
    unassigned = df_with_steps['step_number'] == -1
    if unassigned.any():
        print(f"Warning: {unassigned.sum()} rows have unassigned step numbers")
    
    return df_with_steps


def main():
    parser = argparse.ArgumentParser(description='Add step numbers to phase-indexed parquet files')
    parser.add_argument('input_file', type=str, help='Input parquet file path')
    parser.add_argument('--output', type=str, help='Output parquet file path (default: overwrites input)')
    parser.add_argument('--subject-col', type=str, default='subject', help='Subject column name')
    parser.add_argument('--task-col', type=str, default='task', help='Task column name')
    parser.add_argument('--phase-col', type=str, default='phase', help='Phase column name')
    parser.add_argument('--points-per-cycle', type=int, default=150, help='Points per gait cycle')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading {args.input_file}...")
    df = pd.read_parquet(args.input_file)
    print(f"Loaded {len(df)} rows with {len(df.columns)} columns")
    
    # Check if step_number already exists
    if 'step_number' in df.columns:
        print("Warning: step_number column already exists. It will be overwritten.")
    
    # Add step numbers
    print("Adding step numbers...")
    df_with_steps = add_step_numbers(
        df, 
        subject_col=args.subject_col,
        task_col=args.task_col,
        phase_col=args.phase_col,
        points_per_cycle=args.points_per_cycle
    )
    
    # Save output
    output_file = args.output if args.output else args.input_file
    print(f"Saving to {output_file}...")
    df_with_steps.to_parquet(output_file, index=False)
    print("Done!")
    
    # Print summary statistics
    print("\nSummary:")
    print(f"Total subjects: {df_with_steps[args.subject_col].nunique()}")
    print(f"Total tasks: {df_with_steps[args.task_col].nunique()}")
    print(f"Total steps: {df_with_steps['step_number'].max() + 1}")
    
    # Show example
    print("\nExample data (first subject-task):")
    first_subject = df_with_steps[args.subject_col].iloc[0]
    first_task = df_with_steps[args.task_col].iloc[0]
    example = df_with_steps[
        (df_with_steps[args.subject_col] == first_subject) & 
        (df_with_steps[args.task_col] == first_task)
    ][[args.subject_col, args.task_col, args.phase_col, 'step_number']].head(10)
    print(example)


if __name__ == '__main__':
    main()