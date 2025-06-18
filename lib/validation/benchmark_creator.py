"""
benchmark_creator.py

Created: 2025-06-18 with user permission
Purpose: Memory-efficient ML benchmark creation with stratified sampling

Intent: Creates standardized ML benchmarks with proper train/test splits, demographic
stratification, and subject-level leakage prevention. Uses streaming processing
and efficient sampling for large datasets while maintaining statistical rigor.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import warnings
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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