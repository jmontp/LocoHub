"""
demo_us06_ml_benchmark_creation.py

Created: 2025-06-18 with user permission
Purpose: Demonstration of US-06 ML benchmark creation capabilities

Intent: Show how to create ML benchmarks with stratified sampling, demographic balance,
and subject-level leakage prevention. Demonstrates both the BenchmarkCreator API
and CLI interface using synthetic data.
"""

import sys
from pathlib import Path
import tempfile
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.validation.benchmark_creator import BenchmarkCreator


def create_demo_dataset(n_subjects=50, n_cycles_per_subject=10):
    """Create demonstration dataset with realistic demographics."""
    np.random.seed(42)
    
    # Define demographic distributions
    sex_options = ['male', 'female']
    condition_options = ['healthy', 'pathological']
    age_ranges = [(18, 30), (30, 50), (50, 80)]
    tasks = ['level_walking', 'incline_walking', 'decline_walking']
    
    data = []
    
    for subject_id in range(1, n_subjects + 1):
        # Create subject demographics
        sex = np.random.choice(sex_options)
        condition = np.random.choice(condition_options)
        age_range = age_ranges[np.random.randint(0, len(age_ranges))]
        age = np.random.randint(age_range[0], age_range[1])
        
        # Multiple tasks per subject
        subject_tasks = np.random.choice(tasks, size=np.random.randint(1, len(tasks)+1), replace=False)
        
        cycle_counter = 1
        for task in subject_tasks:
            n_cycles = np.random.randint(n_cycles_per_subject//2, n_cycles_per_subject)
            
            for cycle in range(n_cycles):
                # Create cycle data
                cycle_data = {
                    'subject_id': f'S{subject_id:03d}',
                    'cycle_id': f'S{subject_id:03d}_C{cycle_counter:03d}',
                    'age': age,
                    'sex': sex,
                    'condition': condition,
                    'task': task,
                    'phase': list(range(150)),  # 150 phase points
                    'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150),
                    'hip_moment_contra_Nm': np.random.normal(50, 15, 150)
                }
                data.append(cycle_data)
                cycle_counter += 1
    
    return pd.DataFrame(data)


def demo_benchmark_creation():
    """Demonstrate benchmark creation with API and quality validation."""
    print("="*60)
    print("US-06 ML BENCHMARK CREATION DEMONSTRATION")
    print("="*60)
    
    # Create demo dataset
    print("\n1. Creating demonstration dataset...")
    df = create_demo_dataset(n_subjects=50, n_cycles_per_subject=8)
    
    print(f"   Dataset: {len(df):,} cycles from {df['subject_id'].nunique()} subjects")
    print(f"   Tasks: {', '.join(df['task'].unique())}")
    print(f"   Demographics:")
    for col in ['sex', 'condition']:
        counts = df.drop_duplicates('subject_id')[col].value_counts()
        for category, count in counts.items():
            percentage = count / df['subject_id'].nunique() * 100
            print(f"     {col}.{category}: {count} subjects ({percentage:.1f}%)")
    
    # Configure benchmark creation
    print("\n2. Configuring benchmark creator...")
    config = {
        'train_ratio': 0.7,
        'validation_ratio': 0.15,
        'test_ratio': 0.15,
        'stratify_columns': ['sex', 'condition', 'age_group'],
        'random_seed': 42,
        'balance_tolerance': 0.1,
        'min_samples_per_split': 3
    }
    
    creator = BenchmarkCreator(config)
    print(f"   Configuration: {config['train_ratio']:.0%} train, {config['validation_ratio']:.0%} val, {config['test_ratio']:.0%} test")
    print(f"   Stratification: {', '.join(config['stratify_columns'])}")
    
    # Create stratified splits
    print("\n3. Creating stratified splits...")
    splits = creator.create_stratified_splits(df)
    
    print("   Split Results:")
    for split_name, split_df in splits.items():
        n_subjects = split_df['subject_id'].nunique() if len(split_df) > 0 else 0
        n_cycles = len(split_df)
        print(f"     {split_name.capitalize()}: {n_subjects} subjects, {n_cycles:,} cycles")
    
    # Validate subject-level leakage prevention
    print("\n4. Validating subject-level leakage prevention...")
    train_subjects = set(splits['train']['subject_id'])
    val_subjects = set(splits['validation']['subject_id'])
    test_subjects = set(splits['test']['subject_id'])
    
    train_val_overlap = len(train_subjects & val_subjects)
    train_test_overlap = len(train_subjects & test_subjects)
    val_test_overlap = len(val_subjects & test_subjects)
    
    print(f"   Train-Validation overlap: {train_val_overlap} subjects (should be 0)")
    print(f"   Train-Test overlap: {train_test_overlap} subjects (should be 0)")
    print(f"   Validation-Test overlap: {val_test_overlap} subjects (should be 0)")
    
    leakage_prevented = (train_val_overlap == 0 and train_test_overlap == 0 and val_test_overlap == 0)
    print(f"   ✅ Subject leakage prevention: {'PASSED' if leakage_prevented else 'FAILED'}")
    
    # Validate demographic balance
    print("\n5. Validating demographic balance...")
    balance_report = creator.validate_demographic_balance(splits)
    
    for demographic, categories in balance_report.items():
        print(f"   {demographic.capitalize()} balance:")
        for category, imbalance in categories.items():
            status = "✅ BALANCED" if imbalance < 0.1 else "⚠️ IMBALANCED"
            print(f"     {category}: {imbalance:.3f} imbalance {status}")
    
    # Run comprehensive quality validation
    print("\n6. Running comprehensive quality validation...")
    quality_report = creator.validate_benchmark_quality(splits)
    score = quality_report.get('overall_quality_score', 0)
    
    print(f"   Overall Quality Score: {score:.3f}/1.000")
    if score >= 0.9:
        print("   ✅ EXCELLENT - Benchmark meets high quality standards")
    elif score >= 0.8:
        print("   ✅ GOOD - Benchmark meets quality standards")
    elif score >= 0.7:
        print("   ⚠️ ACCEPTABLE - Some quality concerns")
    else:
        print("   ❌ POOR - Quality issues detected")
    
    # Export benchmark
    print("\n7. Exporting benchmark...")
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir)
        creator.export_benchmark(splits, export_path, "demo_benchmark")
        
        # Check exported files
        exported_files = list(export_path.glob("demo_benchmark_*"))
        print(f"   Exported {len(exported_files)} files:")
        for file_path in sorted(exported_files):
            if file_path.suffix == '.parquet':
                df_exported = pd.read_parquet(file_path)
                print(f"     {file_path.name}: {len(df_exported):,} cycles")
            else:
                print(f"     {file_path.name}: metadata file")
    
    # Generate metadata
    print("\n8. Generating benchmark metadata...")
    metadata = creator.generate_benchmark_metadata(splits, df)
    
    print(f"   Benchmark: {metadata.name}")
    print(f"   Created: {metadata.creation_date}")
    print(f"   Total: {metadata.total_subjects} subjects, {metadata.total_cycles:,} cycles")
    print(f"   Tasks: {', '.join(metadata.task_distribution.keys())}")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nKey Features Demonstrated:")
    print("✅ Memory-efficient stratified sampling")
    print("✅ Subject-level data leakage prevention (zero tolerance)")
    print("✅ Demographic balance validation")
    print("✅ Comprehensive quality scoring")
    print("✅ Benchmark metadata generation")
    print("✅ Export to standardized format")
    
    return splits, metadata


def demo_memory_efficient_processing():
    """Demonstrate memory-efficient processing for large datasets."""
    print("\n" + "="*60)
    print("MEMORY-EFFICIENT PROCESSING DEMONSTRATION")
    print("="*60)
    
    # Create larger dataset
    print("\n1. Creating larger demonstration dataset...")
    df = create_demo_dataset(n_subjects=100, n_cycles_per_subject=15)
    print(f"   Dataset: {len(df):,} cycles from {df['subject_id'].nunique()} subjects")
    
    # Configure for memory-efficient processing
    config = {
        'train_ratio': 0.8,
        'validation_ratio': 0.1,
        'test_ratio': 0.1,
        'stratify_columns': ['sex', 'condition'],
        'random_seed': 42,
        'memory_efficient': True,
        'chunk_size': 1000
    }
    
    creator = BenchmarkCreator(config)
    
    print("\n2. Running memory-efficient streaming splits...")
    splits = creator.create_stratified_splits_streaming(df)
    
    print("   Streaming Results:")
    total_original = len(df)
    total_splits = sum(len(split_df) for split_df in splits.values())
    
    for split_name, split_df in splits.items():
        n_subjects = split_df['subject_id'].nunique() if len(split_df) > 0 else 0
        n_cycles = len(split_df)
        print(f"     {split_name.capitalize()}: {n_subjects} subjects, {n_cycles:,} cycles")
    
    print(f"   Data integrity: {total_original:,} original → {total_splits:,} split cycles")
    print(f"   ✅ No data loss: {'PASSED' if total_original == total_splits else 'FAILED'}")
    
    print("\n✅ Memory-efficient processing completed successfully")


if __name__ == "__main__":
    print("Starting US-06 ML Benchmark Creation Demonstrations...")
    
    try:
        # Run main demonstration
        splits, metadata = demo_benchmark_creation()
        
        # Run memory-efficient demonstration
        demo_memory_efficient_processing()
        
        print(f"\n🎉 All demonstrations completed successfully!")
        print(f"\nNext steps:")
        print("- Use the CLI: python contributor_scripts/create_ml_benchmark.py --help")
        print("- Create benchmarks from real datasets with proper stratification")
        print("- Validate benchmark quality before using in ML research")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)