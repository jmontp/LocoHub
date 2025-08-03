#!/usr/bin/env python3
"""
ML Benchmark Creation Tool

Creates stratified train/test splits for machine learning benchmarks.
Combines CLI and benchmark creation logic in one self-contained file.

Created: 2025-06-18 with user permission
Purpose: Creates ML benchmarks with proper train/test splits, demographic
stratification, and subject-level leakage prevention.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import logging
from typing import List, Dict, Optional, Tuple, Any
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import warnings
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# LIBRARY SECTION - Benchmark Creation Classes and Functions
# ============================================================================

def train_test_split(X, test_size=0.25, stratify=None, random_state=None):
    """
    Simple train-test split implementation to avoid sklearn dependency.
    
    Args:
        X: DataFrame to split
        test_size: Proportion for test set
        stratify: Series for stratification (optional)
        random_state: Random seed
        
    Returns:
        X_train, X_test
    """
    if random_state is not None:
        np.random.seed(random_state)
    
    indices = np.arange(len(X))
    
    if stratify is not None:
        # Simple stratified sampling
        unique_strats = stratify.unique()
        train_indices = []
        test_indices = []
        
        for strat_value in unique_strats:
            strat_mask = stratify == strat_value
            strat_indices = indices[strat_mask]
            
            n_test = max(1, int(len(strat_indices) * test_size))
            shuffled = np.random.permutation(strat_indices)
            
            test_indices.extend(shuffled[:n_test])
            train_indices.extend(shuffled[n_test:])
        
        train_indices = np.array(train_indices)
        test_indices = np.array(test_indices)
    else:
        # Simple random sampling
        shuffled = np.random.permutation(indices)
        n_test = int(len(X) * test_size)
        test_indices = shuffled[:n_test]
        train_indices = shuffled[n_test:]
    
    X_train = X.iloc[train_indices].reset_index(drop=True)
    X_test = X.iloc[test_indices].reset_index(drop=True)
    
    return X_train, X_test


@dataclass
class BenchmarkMetadata:
    """Metadata structure for ML benchmarks."""
    name: str
    description: str
    creation_date: str
    total_subjects: int
    total_cycles: int
    split_statistics: Dict[str, int]
    demographic_distribution: Dict[str, Dict[str, float]]
    task_distribution: Dict[str, int]
    stratification_columns: List[str] = None
    random_seed: int = None
    balance_tolerance: float = 0.05
    
    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BenchmarkMetadata':
        """Create metadata from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class BenchmarkCreator:
    """Memory-efficient ML benchmark creator with stratified sampling."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize benchmark creator with configuration.
        
        Args:
            config: Configuration dictionary with split ratios, stratification options, etc.
        """
        self.train_ratio = config.get('train_ratio', 0.7)
        self.validation_ratio = config.get('validation_ratio', 0.15)
        self.test_ratio = config.get('test_ratio', 0.15)
        self.stratify_columns = config.get('stratify_columns', [])
        self.random_seed = config.get('random_seed', 42)
        self.balance_tolerance = config.get('balance_tolerance', 0.05)
        self.min_samples_per_split = config.get('min_samples_per_split', 3)
        self.memory_efficient = config.get('memory_efficient', False)
        self.chunk_size = config.get('chunk_size', 1000)
        
        # Validate configuration
        self.validate_split_ratios()
        
        # Set random seed for reproducibility
        np.random.seed(self.random_seed)
    
    def validate_split_ratios(self) -> bool:
        """Validate that split ratios sum to 1.0."""
        total_ratio = self.train_ratio + self.validation_ratio + self.test_ratio
        if not np.isclose(total_ratio, 1.0, atol=1e-6):
            raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio:.6f}")
        return True
    
    def _add_age_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add age group stratification if age column exists."""
        if 'age' in df.columns:
            df = df.copy()
            df['age_group'] = pd.cut(df['age'], 
                                   bins=[0, 30, 50, 100], 
                                   labels=['young', 'middle', 'older'],
                                   include_lowest=True)
        return df
    
    def _validate_stratification_columns(self, df: pd.DataFrame) -> None:
        """Validate that stratification columns exist in dataset."""
        missing_cols = [col for col in self.stratify_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Stratification column(s) not found: {missing_cols}")
    
    def _get_subject_demographics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique subject demographics for stratification."""
        # Add age groups if needed
        df = self._add_age_groups(df)
        
        # Validate columns exist
        self._validate_stratification_columns(df)
        
        # Get unique subjects with their demographics
        subject_cols = ['subject_id'] + self.stratify_columns
        subject_demographics = df[subject_cols].drop_duplicates()
        
        return subject_demographics
    
    def _create_stratification_key(self, subject_demographics: pd.DataFrame) -> pd.Series:
        """Create stratification key by combining demographic columns."""
        if not self.stratify_columns:
            return pd.Series(['all'] * len(subject_demographics), index=subject_demographics.index)
        
        # Combine stratification columns
        strat_key = subject_demographics[self.stratify_columns[0]].astype(str)
        for col in self.stratify_columns[1:]:
            strat_key = strat_key + '_' + subject_demographics[col].astype(str)
        
        return strat_key
    
    def create_stratified_splits(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Create stratified train/validation/test splits at subject level.
        
        Args:
            df: Input dataset with subject_id and demographic columns
            
        Returns:
            Dictionary with 'train', 'validation', 'test' DataFrames
        """
        # Get subject demographics
        subject_demographics = self._get_subject_demographics(df)
        
        # Check minimum samples
        n_subjects = len(subject_demographics)
        min_total_samples = self.min_samples_per_split * 3  # For 3 splits
        if n_subjects < min_total_samples:
            raise ValueError(f"Insufficient samples for reliable splits. "
                           f"Need at least {min_total_samples}, got {n_subjects}")
        
        # Create stratification key
        strat_key = self._create_stratification_key(subject_demographics)
        
        # Split subjects into train and temp (validation + test)
        temp_size = self.validation_ratio + self.test_ratio
        train_subjects, temp_subjects = train_test_split(
            subject_demographics,
            test_size=temp_size,
            stratify=strat_key,
            random_state=self.random_seed
        )
        
        # Split temp into validation and test
        if self.validation_ratio > 0 and len(temp_subjects) > 1:
            # Calculate relative test size within temp set
            temp_test_ratio = self.test_ratio / temp_size
            
            # Get stratification for temp subjects
            temp_strat_key = self._create_stratification_key(temp_subjects)
            
            # Only stratify if we have enough samples per group
            if len(temp_subjects) >= 4:  # At least 2 per split
                val_subjects, test_subjects = train_test_split(
                    temp_subjects,
                    test_size=temp_test_ratio,
                    stratify=temp_strat_key,
                    random_state=self.random_seed + 1
                )
            else:
                # Simple split without stratification for very small datasets
                val_subjects, test_subjects = train_test_split(
                    temp_subjects,
                    test_size=temp_test_ratio,
                    random_state=self.random_seed + 1
                )
        else:
            val_subjects = pd.DataFrame(columns=subject_demographics.columns)
            test_subjects = temp_subjects
        
        # Map subjects back to full dataset
        train_subject_ids = set(train_subjects['subject_id'])
        val_subject_ids = set(val_subjects['subject_id'])
        test_subject_ids = set(test_subjects['subject_id'])
        
        splits = {
            'train': df[df['subject_id'].isin(train_subject_ids)].copy(),
            'validation': df[df['subject_id'].isin(val_subject_ids)].copy(),
            'test': df[df['subject_id'].isin(test_subject_ids)].copy()
        }
        
        logger.info(f"Created splits: Train={len(train_subject_ids)} subjects, "
                   f"Val={len(val_subject_ids)} subjects, "
                   f"Test={len(test_subject_ids)} subjects")
        
        return splits
    
    def create_stratified_splits_streaming(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Memory-efficient streaming split creation for large datasets.
        
        Args:
            df: Input dataset
            
        Returns:
            Dictionary with split DataFrames
        """
        logger.info("Creating memory-efficient streaming splits")
        
        # First pass: collect unique subjects and demographics (memory efficient)
        subject_demographics = self._get_subject_demographics(df)
        
        # Create splits at subject level (small memory footprint)
        strat_key = self._create_stratification_key(subject_demographics)
        train_subjects, temp_subjects = train_test_split(
            subject_demographics,
            test_size=(self.validation_ratio + self.test_ratio),
            stratify=strat_key,
            random_state=self.random_seed
        )
        
        # Split validation and test
        if self.validation_ratio > 0:
            temp_test_ratio = self.test_ratio / (self.validation_ratio + self.test_ratio)
            temp_strat_key = self._create_stratification_key(temp_subjects)
            val_subjects, test_subjects = train_test_split(
                temp_subjects,
                test_size=temp_test_ratio,
                stratify=temp_strat_key,
                random_state=self.random_seed + 1
            )
        else:
            val_subjects = pd.DataFrame(columns=subject_demographics.columns)
            test_subjects = temp_subjects
        
        # Create subject ID sets
        train_ids = set(train_subjects['subject_id'])
        val_ids = set(val_subjects['subject_id'])
        test_ids = set(test_subjects['subject_id'])
        
        # Stream data in chunks and assign to splits
        splits = {'train': [], 'validation': [], 'test': []}
        
        for chunk_start in range(0, len(df), self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, len(df))
            chunk = df.iloc[chunk_start:chunk_end]
            
            # Assign chunk rows to appropriate splits
            train_mask = chunk['subject_id'].isin(train_ids)
            val_mask = chunk['subject_id'].isin(val_ids)
            test_mask = chunk['subject_id'].isin(test_ids)
            
            splits['train'].append(chunk[train_mask])
            splits['validation'].append(chunk[val_mask])
            splits['test'].append(chunk[test_mask])
        
        # Concatenate chunks for each split
        final_splits = {}
        for split_name, chunks in splits.items():
            if chunks:
                final_splits[split_name] = pd.concat(chunks, ignore_index=True)
            else:
                final_splits[split_name] = pd.DataFrame(columns=df.columns)
        
        logger.info("Streaming splits created successfully")
        return final_splits
    
    def validate_demographic_balance(self, splits: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        Validate demographic balance across splits.
        
        Args:
            splits: Dictionary of split DataFrames
            
        Returns:
            Dictionary of imbalance metrics per demographic category
        """
        balance_report = {}
        
        for demographic in self.stratify_columns:
            if demographic not in splits['train'].columns:
                continue
                
            balance_report[demographic] = {}
            
            # Calculate proportions for each split
            split_proportions = {}
            for split_name, split_df in splits.items():
                if len(split_df) > 0:
                    # Get unique subjects to avoid counting cycles multiple times
                    unique_subjects = split_df.drop_duplicates('subject_id')
                    if len(unique_subjects) > 0:
                        proportions = unique_subjects[demographic].value_counts(normalize=True)
                        split_proportions[split_name] = proportions
            
            # Calculate imbalance for each category
            if 'train' in split_proportions:
                train_props = split_proportions['train']
                
                for category in train_props.index:
                    max_imbalance = 0
                    
                    # Check imbalance against other splits
                    for split_name, props in split_proportions.items():
                        if split_name != 'train' and len(props) > 0 and category in props.index:
                            imbalance = abs(train_props[category] - props[category])
                            max_imbalance = max(max_imbalance, imbalance)
                    
                    balance_report[demographic][category] = max_imbalance
        
        return balance_report
    
    def generate_benchmark_metadata(self, splits: Dict[str, pd.DataFrame], 
                                   original_df: pd.DataFrame) -> BenchmarkMetadata:
        """
        Generate comprehensive benchmark metadata.
        
        Args:
            splits: Dictionary of split DataFrames
            original_df: Original dataset
            
        Returns:
            BenchmarkMetadata object
        """
        # Calculate basic statistics
        total_subjects = original_df['subject_id'].nunique()
        total_cycles = len(original_df)
        
        # Split statistics
        split_stats = {}
        for split_name, split_df in splits.items():
            split_stats[split_name] = {
                'subjects': split_df['subject_id'].nunique(),
                'cycles': len(split_df)
            }
        
        # Demographic distribution (from unique subjects)
        unique_subjects = original_df.drop_duplicates('subject_id')
        demo_dist = {}
        for col in self.stratify_columns:
            if col in unique_subjects.columns:
                proportions = unique_subjects[col].value_counts(normalize=True)
                demo_dist[col] = proportions.to_dict()
        
        # Task distribution
        task_dist = {}
        if 'task' in original_df.columns:
            task_counts = original_df['task'].value_counts()
            task_dist = task_counts.to_dict()
        
        metadata = BenchmarkMetadata(
            name=f"ml_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Stratified ML benchmark with subject-level splits",
            creation_date=datetime.now().isoformat(),
            total_subjects=total_subjects,
            total_cycles=total_cycles,
            split_statistics=split_stats,
            demographic_distribution=demo_dist,
            task_distribution=task_dist,
            stratification_columns=self.stratify_columns,
            random_seed=self.random_seed,
            balance_tolerance=self.balance_tolerance
        )
        
        return metadata
    
    def export_benchmark(self, splits: Dict[str, pd.DataFrame], 
                        export_path: Path, benchmark_name: str) -> None:
        """
        Export benchmark splits and metadata to files.
        
        Args:
            splits: Dictionary of split DataFrames
            export_path: Directory to export files
            benchmark_name: Name for the benchmark files
        """
        export_path = Path(export_path)
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Export split parquet files
        for split_name, split_df in splits.items():
            if len(split_df) > 0:
                file_path = export_path / f"{benchmark_name}_{split_name}.parquet"
                split_df.to_parquet(file_path, index=False)
                logger.info(f"Exported {split_name} split: {len(split_df)} samples -> {file_path}")
            else:
                logger.info(f"Skipped {split_name} split: empty dataset")
        
        # Generate and export metadata
        # Combine all splits to get original dataset approximation
        all_data = pd.concat(splits.values(), ignore_index=True)
        metadata = self.generate_benchmark_metadata(splits, all_data)
        
        metadata_path = export_path / f"{benchmark_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            f.write(metadata.to_json())
        
        logger.info(f"Exported metadata -> {metadata_path}")
        logger.info(f"Benchmark '{benchmark_name}' exported successfully to {export_path}")
    
    def validate_benchmark_quality(self, splits: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Comprehensive benchmark quality validation.
        
        Args:
            splits: Dictionary of split DataFrames
            
        Returns:
            Quality report dictionary
        """
        quality_report = {
            'subject_leakage': self._check_subject_leakage(splits),
            'demographic_balance': self.validate_demographic_balance(splits),
            'split_sizes': self._validate_split_sizes(splits),
            'data_integrity': self._check_data_integrity(splits)
        }
        
        # Overall quality score
        quality_score = self._calculate_quality_score(quality_report)
        quality_report['overall_quality_score'] = quality_score
        
        return quality_report
    
    def _check_subject_leakage(self, splits: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """Check for subject-level data leakage between splits."""
        split_subjects = {}
        for split_name, split_df in splits.items():
            split_subjects[split_name] = set(split_df['subject_id'])
        
        leakage_results = {}
        split_names = list(split_subjects.keys())
        
        for i in range(len(split_names)):
            for j in range(i + 1, len(split_names)):
                split1, split2 = split_names[i], split_names[j]
                overlap = split_subjects[split1] & split_subjects[split2]
                leakage_results[f"{split1}_{split2}_overlap"] = len(overlap) == 0
        
        return leakage_results
    
    def _validate_split_sizes(self, splits: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate that split sizes meet minimum requirements."""
        size_validation = {}
        total_subjects = sum(df['subject_id'].nunique() for df in splits.values())
        
        for split_name, split_df in splits.items():
            n_subjects = split_df['subject_id'].nunique()
            size_validation[f"{split_name}_subjects"] = n_subjects
            size_validation[f"{split_name}_meets_minimum"] = n_subjects >= self.min_samples_per_split
            size_validation[f"{split_name}_proportion"] = n_subjects / total_subjects if total_subjects > 0 else 0
        
        return size_validation
    
    def _check_data_integrity(self, splits: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Check data integrity across splits."""
        integrity_results = {}
        
        for split_name, split_df in splits.items():
            integrity_results[f"{split_name}_has_data"] = len(split_df) > 0
            integrity_results[f"{split_name}_no_nulls_in_ids"] = split_df['subject_id'].notna().all()
            
            # Check for required columns
            required_cols = ['subject_id', 'cycle_id'] + self.stratify_columns
            missing_cols = [col for col in required_cols if col not in split_df.columns]
            integrity_results[f"{split_name}_has_required_columns"] = len(missing_cols) == 0
        
        return integrity_results
    
    def _calculate_quality_score(self, quality_report: Dict[str, Any]) -> float:
        """Calculate overall quality score (0-1 scale)."""
        score_components = []
        
        # Subject leakage score (critical)
        leakage_results = quality_report['subject_leakage']
        leakage_score = sum(leakage_results.values()) / len(leakage_results) if leakage_results else 1.0
        score_components.append(leakage_score * 0.4)  # 40% weight
        
        # Demographic balance score
        balance_results = quality_report['demographic_balance']
        if balance_results:
            balance_scores = []
            for demo_dict in balance_results.values():
                demo_score = sum(1.0 - min(imbalance / self.balance_tolerance, 1.0) 
                               for imbalance in demo_dict.values())
                demo_score /= len(demo_dict) if demo_dict else 1
                balance_scores.append(demo_score)
            balance_score = np.mean(balance_scores) if balance_scores else 1.0
        else:
            balance_score = 1.0
        score_components.append(balance_score * 0.3)  # 30% weight
        
        # Split size score
        size_results = quality_report['split_sizes']
        min_keys = [k for k in size_results.keys() if k.endswith('_meets_minimum')]
        size_score = sum(size_results[k] for k in min_keys) / len(min_keys) if min_keys else 1.0
        score_components.append(size_score * 0.2)  # 20% weight
        
        # Data integrity score
        integrity_results = quality_report['data_integrity']
        integrity_score = sum(integrity_results.values()) / len(integrity_results) if integrity_results else 1.0
        score_components.append(integrity_score * 0.1)  # 10% weight
        
        return sum(score_components)


# ============================================================================
# CLI HELPER FUNCTIONS
# ============================================================================

def load_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load dataset from parquet file with validation."""
    try:
        df = pd.read_parquet(dataset_path)
        logger.info(f"Loaded dataset: {len(df)} cycles, {df['subject_id'].nunique()} subjects")
        return df
    except Exception as e:
        logger.error(f"Failed to load dataset {dataset_path}: {e}")
        raise


def combine_datasets(dataset_paths: List[Path], dataset_names: Optional[List[str]] = None) -> pd.DataFrame:
    """Combine multiple datasets with source tracking."""
    if dataset_names and len(dataset_names) != len(dataset_paths):
        raise ValueError("Number of dataset names must match number of dataset paths")
    
    combined_data = []
    
    for i, path in enumerate(dataset_paths):
        df = load_dataset(path)
        
        # Add dataset source
        source_name = dataset_names[i] if dataset_names else f"dataset_{i+1}"
        df['dataset_source'] = source_name
        
        combined_data.append(df)
        logger.info(f"Added {source_name}: {len(df)} cycles")
    
    combined_df = pd.concat(combined_data, ignore_index=True)
    logger.info(f"Combined dataset: {len(combined_df)} total cycles, "
               f"{combined_df['subject_id'].nunique()} total subjects")
    
    return combined_df


def validate_dataset_requirements(df: pd.DataFrame, stratify_columns: List[str]) -> None:
    """Validate dataset meets benchmark creation requirements."""
    required_columns = ['subject_id', 'cycle_id']
    missing_required = [col for col in required_columns if col not in df.columns]
    
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")
    
    missing_stratify = [col for col in stratify_columns if col not in df.columns]
    if missing_stratify:
        raise ValueError(f"Missing stratification columns: {missing_stratify}")
    
    # Check for reasonable number of subjects
    n_subjects = df['subject_id'].nunique()
    if n_subjects < 10:
        logger.warning(f"Small number of subjects ({n_subjects}) may lead to unreliable splits")
    
    # Check for missing values in key columns
    key_columns = ['subject_id'] + stratify_columns
    for col in key_columns:
        if df[col].isna().any():
            logger.warning(f"Missing values detected in {col}")


def print_dataset_summary(df: pd.DataFrame, stratify_columns: List[str]) -> None:
    """Print comprehensive dataset summary."""
    print("\n" + "="*50)
    print("DATASET SUMMARY")
    print("="*50)
    
    print(f"Total cycles: {len(df):,}")
    print(f"Total subjects: {df['subject_id'].nunique():,}")
    
    if 'task' in df.columns:
        print(f"Tasks: {', '.join(df['task'].unique())}")
    
    if 'dataset_source' in df.columns:
        print("\nDataset sources:")
        source_counts = df.groupby('dataset_source')['subject_id'].nunique()
        for source, count in source_counts.items():
            print(f"  {source}: {count} subjects")
    
    print("\nDemographic distribution:")
    for col in stratify_columns:
        if col in df.columns:
            unique_subjects = df.drop_duplicates('subject_id')
            counts = unique_subjects[col].value_counts()
            print(f"  {col}:")
            for category, count in counts.items():
                percentage = count / len(unique_subjects) * 100
                print(f"    {category}: {count} subjects ({percentage:.1f}%)")


def print_quality_report(quality_report: Dict) -> None:
    """Print benchmark quality report."""
    print("\n" + "="*50)
    print("BENCHMARK QUALITY REPORT")
    print("="*50)
    
    # Overall quality score
    score = quality_report.get('overall_quality_score', 0)
    print(f"Overall Quality Score: {score:.3f}/1.000")
    
    if score >= 0.9:
        print("✅ EXCELLENT - Benchmark meets high quality standards")
    elif score >= 0.8:
        print("✅ GOOD - Benchmark meets quality standards")
    elif score >= 0.7:
        print("⚠️  ACCEPTABLE - Some quality concerns, review recommended")
    else:
        print("❌ POOR - Quality issues detected, improvement needed")
    
    # Subject leakage check
    print("\nSubject Leakage Check:")
    leakage = quality_report.get('subject_leakage', {})
    for check, passed in leakage.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check}: {status}")
    
    # Demographic balance
    print("\nDemographic Balance:")
    balance = quality_report.get('demographic_balance', {})
    for demo, categories in balance.items():
        print(f"  {demo}:")
        for category, imbalance in categories.items():
            if imbalance < 0.05:
                status = "✅ BALANCED"
            elif imbalance < 0.1:
                status = "⚠️  SLIGHT IMBALANCE"
            else:
                status = "❌ IMBALANCED"
            print(f"    {category}: {imbalance:.3f} {status}")
    
    # Split sizes
    print("\nSplit Sizes:")
    sizes = quality_report.get('split_sizes', {})
    for key, value in sizes.items():
        if key.endswith('_subjects'):
            split_name = key.replace('_subjects', '')
            print(f"  {split_name}: {value} subjects")


def create_benchmark_config(args) -> Dict:
    """Create benchmark configuration from CLI arguments."""
    config = {
        'train_ratio': args.train_ratio,
        'validation_ratio': args.validation_ratio,
        'test_ratio': args.test_ratio,
        'stratify_columns': args.stratify_columns,
        'random_seed': args.random_seed,
        'balance_tolerance': args.balance_tolerance,
        'min_samples_per_split': args.min_samples_per_split,
        'memory_efficient': args.memory_efficient,
        'chunk_size': args.chunk_size
    }
    return config


# ============================================================================
# MAIN CLI ENTRY POINT
# ============================================================================

def main():
    """Main CLI function for benchmark creation."""
    parser = argparse.ArgumentParser(
        description="Create ML benchmarks from locomotion datasets with stratified sampling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single dataset benchmark
  python create_ml_benchmark.py data/gtech_2023_phase.parquet --output benchmarks/

  # Multi-dataset benchmark
  python create_ml_benchmark.py data/gtech_2023_phase.parquet data/umich_2021_phase.parquet \\
    --dataset-names "GTech2023" "UMich2021" --output benchmarks/

  # Custom stratification
  python create_ml_benchmark.py data/dataset.parquet --stratify-columns age_group sex condition \\
    --train-ratio 0.8 --test-ratio 0.2 --validation-ratio 0.0

  # Memory-efficient processing
  python create_ml_benchmark.py large_dataset.parquet --memory-efficient --chunk-size 500
        """
    )
    
    # Dataset arguments
    parser.add_argument('datasets', nargs='+', type=Path,
                       help='Paths to input datasets (parquet files)')
    parser.add_argument('--dataset-names', nargs='+',
                       help='Names for datasets (must match number of datasets)')
    
    # Output arguments
    parser.add_argument('--output', '-o', type=Path, required=True,
                       help='Output directory for benchmark files')
    parser.add_argument('--benchmark-name', default='ml_benchmark',
                       help='Name for the benchmark (default: ml_benchmark)')
    
    # Split configuration
    parser.add_argument('--train-ratio', type=float, default=0.7,
                       help='Training set ratio (default: 0.7)')
    parser.add_argument('--validation-ratio', type=float, default=0.15,
                       help='Validation set ratio (default: 0.15)')
    parser.add_argument('--test-ratio', type=float, default=0.15,
                       help='Test set ratio (default: 0.15)')
    
    # Stratification options
    parser.add_argument('--stratify-columns', nargs='+', 
                       default=['sex', 'age_group'],
                       help='Columns for demographic stratification (default: sex age_group)')
    parser.add_argument('--balance-tolerance', type=float, default=0.05,
                       help='Maximum allowed demographic imbalance (default: 0.05)')
    
    # Quality controls
    parser.add_argument('--min-samples-per-split', type=int, default=3,
                       help='Minimum subjects per split (default: 3)')
    parser.add_argument('--random-seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    
    # Memory efficiency
    parser.add_argument('--memory-efficient', action='store_true',
                       help='Use memory-efficient streaming processing')
    parser.add_argument('--chunk-size', type=int, default=1000,
                       help='Chunk size for streaming processing (default: 1000)')
    
    # Analysis options
    parser.add_argument('--skip-quality-check', action='store_true',
                       help='Skip detailed quality validation')
    parser.add_argument('--export-metadata-only', action='store_true',
                       help='Export only metadata without split files')
    
    args = parser.parse_args()
    
    try:
        # Validate inputs
        for dataset_path in args.datasets:
            if not dataset_path.exists():
                raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        # Create output directory
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Load and combine datasets
        if len(args.datasets) == 1:
            df = load_dataset(args.datasets[0])
        else:
            df = combine_datasets(args.datasets, args.dataset_names)
        
        # Validate dataset requirements
        validate_dataset_requirements(df, args.stratify_columns)
        
        # Print dataset summary
        print_dataset_summary(df, args.stratify_columns)
        
        # Create benchmark configuration
        config = create_benchmark_config(args)
        
        # Create benchmark
        creator = BenchmarkCreator(config)
        
        # Create splits
        if args.memory_efficient:
            logger.info("Creating memory-efficient stratified splits...")
            splits = creator.create_stratified_splits_streaming(df)
        else:
            logger.info("Creating stratified splits...")
            splits = creator.create_stratified_splits(df)
        
        # Print split summary
        print("\n" + "="*50)
        print("SPLIT SUMMARY")
        print("="*50)
        for split_name, split_df in splits.items():
            n_subjects = split_df['subject_id'].nunique() if len(split_df) > 0 else 0
            n_cycles = len(split_df)
            print(f"{split_name.title()}: {n_subjects} subjects, {n_cycles} cycles")
        
        # Quality validation
        if not args.skip_quality_check:
            logger.info("Validating benchmark quality...")
            quality_report = creator.validate_benchmark_quality(splits)
            print_quality_report(quality_report)
        
        # Export benchmark
        if not args.export_metadata_only:
            logger.info("Exporting benchmark files...")
            creator.export_benchmark(splits, args.output, args.benchmark_name)
        else:
            logger.info("Exporting metadata only...")
            all_data = pd.concat(splits.values(), ignore_index=True)
            metadata = creator.generate_benchmark_metadata(splits, all_data)
            metadata_path = args.output / f"{args.benchmark_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                f.write(metadata.to_json())
            logger.info(f"Metadata exported to {metadata_path}")
        
        print(f"\n✅ Benchmark creation completed successfully!")
        print(f"📁 Output directory: {args.output}")
        
    except Exception as e:
        logger.error(f"Benchmark creation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()