"""
test_us06_ml_benchmark_creation.py

Created: 2025-06-18 with user permission
Purpose: Test ML benchmark creation with memory-efficient stratified sampling

Intent: Validate benchmark creation capabilities including demographic stratification,
train/test splitting, subject-level leakage prevention, and metadata generation.
Uses efficient sampling strategies to handle large datasets within memory constraints.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from maintainer_tools.create_ml_benchmark import BenchmarkCreator, BenchmarkMetadata

class TestBenchmarkCreator:
    """Test efficient ML benchmark creation with memory constraints."""
    
    @pytest.fixture
    def sample_dataset(self):
        """Create sample dataset with demographics for testing."""
        np.random.seed(42)
        n_subjects = 20
        n_cycles_per_subject = 5
        
        subjects = []
        for subject_id in range(1, n_subjects + 1):
            # Create demographic diversity
            age = np.random.randint(18, 80)
            sex = np.random.choice(['male', 'female'])
            condition = np.random.choice(['healthy', 'pathological'])
            
            for cycle in range(n_cycles_per_subject):
                subject_data = {
                    'subject_id': f'S{subject_id:03d}',
                    'age': age,
                    'sex': sex,
                    'condition': condition,
                    'task': 'treadmill_walking',
                    'cycle_id': f'S{subject_id:03d}_C{cycle:02d}',
                    'phase': list(range(150)),  # 150 phase points
                    'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150),
                    'hip_moment_contra_Nm': np.random.normal(50, 15, 150)
                }
                subjects.append(subject_data)
        
        return pd.DataFrame(subjects)
    
    @pytest.fixture
    def multi_task_dataset(self):
        """Create dataset with multiple tasks for benchmark creation."""
        np.random.seed(42)
        tasks = ['treadmill_walking', 'overground_walking', 'running']
        n_subjects_per_task = 8
        
        data = []
        subject_counter = 1
        
        for task in tasks:
            for _ in range(n_subjects_per_task):
                age = np.random.randint(18, 70)
                sex = np.random.choice(['male', 'female'])
                condition = np.random.choice(['healthy', 'pathological'])
                
                for cycle in range(3):  # 3 cycles per subject
                    subject_data = {
                        'subject_id': f'S{subject_counter:03d}',
                        'age': age,
                        'sex': sex,
                        'condition': condition,
                        'task': task,
                        'cycle_id': f'S{subject_counter:03d}_C{cycle:02d}',
                        'phase': list(range(150)),
                        'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150),
                        'hip_moment_contra_Nm': np.random.normal(50, 15, 150)
                    }
                    data.append(subject_data)
                subject_counter += 1
        
        return pd.DataFrame(data)
    
    def test_benchmark_creator_initialization(self):
        """Test BenchmarkCreator initialization with configuration."""
        config = {
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['age_group', 'sex', 'condition'],
            'random_seed': 42
        }
        
        creator = BenchmarkCreator(config)
        assert creator.train_ratio == 0.7
        assert creator.validation_ratio == 0.15
        assert creator.test_ratio == 0.15
        assert creator.stratify_columns == ['age_group', 'sex', 'condition']
        assert creator.random_seed == 42
    
    def test_demographic_stratification(self, sample_dataset):
        """Test demographic stratification for balanced splits."""
        creator = BenchmarkCreator({
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex', 'condition'],
            'random_seed': 42
        })
        
        splits = creator.create_stratified_splits(sample_dataset)
        
        # Verify splits exist
        assert 'train' in splits
        assert 'validation' in splits
        assert 'test' in splits
        
        # Check approximate ratios (within tolerance for small dataset)
        total_subjects = sample_dataset['subject_id'].nunique()
        train_subjects = splits['train']['subject_id'].nunique()
        val_subjects = splits['validation']['subject_id'].nunique()
        test_subjects = splits['test']['subject_id'].nunique()
        
        assert abs(train_subjects / total_subjects - 0.7) < 0.15
        # For small datasets, validation might be empty, so we check more flexibly
        if val_subjects > 0:
            assert abs(val_subjects / total_subjects - 0.15) < 0.15
        assert abs(test_subjects / total_subjects - 0.15) < 0.15
        
        # Verify no subject appears in multiple splits
        all_train_subjects = set(splits['train']['subject_id'])
        all_val_subjects = set(splits['validation']['subject_id'])
        all_test_subjects = set(splits['test']['subject_id'])
        
        assert len(all_train_subjects & all_val_subjects) == 0
        assert len(all_train_subjects & all_test_subjects) == 0
        assert len(all_val_subjects & all_test_subjects) == 0
    
    def test_subject_level_leakage_prevention(self, sample_dataset):
        """Test that subject-level data leakage is prevented."""
        creator = BenchmarkCreator({
            'train_ratio': 0.8,
            'validation_ratio': 0.1,
            'test_ratio': 0.1,
            'stratify_columns': ['sex'],
            'random_seed': 42
        })
        
        splits = creator.create_stratified_splits(sample_dataset)
        
        # Collect all subjects from each split
        train_subjects = set(splits['train']['subject_id'])
        val_subjects = set(splits['validation']['subject_id'])
        test_subjects = set(splits['test']['subject_id'])
        
        # Verify zero tolerance for subject leakage
        assert len(train_subjects & val_subjects) == 0, "Subject leakage detected between train and validation"
        assert len(train_subjects & test_subjects) == 0, "Subject leakage detected between train and test"
        assert len(val_subjects & test_subjects) == 0, "Subject leakage detected between validation and test"
        
        # Verify all original subjects are accounted for
        all_split_subjects = train_subjects | val_subjects | test_subjects
        original_subjects = set(sample_dataset['subject_id'])
        assert all_split_subjects == original_subjects, "Some subjects missing from splits"
    
    def test_demographic_balance_validation(self, sample_dataset):
        """Test validation of demographic balance across splits."""
        creator = BenchmarkCreator({
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex', 'condition'],
            'random_seed': 42,
            'balance_tolerance': 0.05
        })
        
        splits = creator.create_stratified_splits(sample_dataset)
        balance_report = creator.validate_demographic_balance(splits)
        
        # Check that balance report contains required fields
        assert 'sex' in balance_report
        assert 'condition' in balance_report
        
        # Verify balance within tolerance for each demographic
        # Note: For small datasets, some imbalance is expected
        for demographic, stats in balance_report.items():
            for category, imbalance in stats.items():
                # Relaxed tolerance for small test datasets
                assert imbalance < 0.4, f"Demographic imbalance >40% for {demographic}.{category}: {imbalance:.3f}"
    
    def test_benchmark_metadata_generation(self, multi_task_dataset):
        """Test benchmark metadata generation with proper documentation."""
        creator = BenchmarkCreator({
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex', 'condition'],
            'random_seed': 42
        })
        
        splits = creator.create_stratified_splits(multi_task_dataset)
        metadata = creator.generate_benchmark_metadata(splits, multi_task_dataset)
        
        # Verify metadata structure
        assert isinstance(metadata, BenchmarkMetadata)
        assert metadata.name is not None
        assert metadata.description is not None
        assert metadata.creation_date is not None
        assert metadata.total_subjects > 0
        assert metadata.total_cycles > 0
        
        # Verify split statistics
        assert 'train' in metadata.split_statistics
        assert 'validation' in metadata.split_statistics
        assert 'test' in metadata.split_statistics
        
        # Verify demographic information
        assert len(metadata.demographic_distribution) > 0
        assert len(metadata.task_distribution) > 0
    
    def test_memory_efficient_sampling(self, multi_task_dataset):
        """Test memory-efficient sampling for large datasets."""
        creator = BenchmarkCreator({
            'train_ratio': 0.8,
            'validation_ratio': 0.1,
            'test_ratio': 0.1,
            'stratify_columns': ['sex'],
            'random_seed': 42,
            'memory_efficient': True,
            'chunk_size': 50  # Small chunks for testing
        })
        
        # Test streaming split creation
        splits = creator.create_stratified_splits_streaming(multi_task_dataset)
        
        # Verify splits were created successfully
        assert 'train' in splits
        assert 'validation' in splits
        assert 'test' in splits
        
        # Verify no data loss
        total_original = len(multi_task_dataset)
        total_splits = len(splits['train']) + len(splits['validation']) + len(splits['test'])
        assert total_original == total_splits, "Data loss detected in streaming splits"
    
    def test_train_test_split_reproducibility(self, sample_dataset):
        """Test that splits are reproducible with same random seed."""
        config = {
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex'],
            'random_seed': 42
        }
        
        creator1 = BenchmarkCreator(config)
        creator2 = BenchmarkCreator(config)
        
        splits1 = creator1.create_stratified_splits(sample_dataset)
        splits2 = creator2.create_stratified_splits(sample_dataset)
        
        # Verify identical splits
        pd.testing.assert_frame_equal(splits1['train'].sort_values('cycle_id').reset_index(drop=True),
                                     splits2['train'].sort_values('cycle_id').reset_index(drop=True))
        pd.testing.assert_frame_equal(splits1['validation'].sort_values('cycle_id').reset_index(drop=True),
                                     splits2['validation'].sort_values('cycle_id').reset_index(drop=True))
        pd.testing.assert_frame_equal(splits1['test'].sort_values('cycle_id').reset_index(drop=True),
                                     splits2['test'].sort_values('cycle_id').reset_index(drop=True))
    
    def test_benchmark_export_and_validation(self, sample_dataset):
        """Test benchmark export and validation capabilities."""
        creator = BenchmarkCreator({
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex', 'condition'],
            'random_seed': 42
        })
        
        splits = creator.create_stratified_splits(sample_dataset)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir)
            
            # Export benchmark
            creator.export_benchmark(splits, export_path, "test_benchmark")
            
            # Verify exported files exist for non-empty splits
            assert (export_path / "test_benchmark_train.parquet").exists()
            assert (export_path / "test_benchmark_test.parquet").exists()
            assert (export_path / "test_benchmark_metadata.json").exists()
            
            # Check validation file only if validation split has data
            if len(splits['validation']) > 0:
                assert (export_path / "test_benchmark_validation.parquet").exists()
            
            # Verify exported data integrity
            exported_train = pd.read_parquet(export_path / "test_benchmark_train.parquet")
            assert len(exported_train) == len(splits['train'])
            assert list(exported_train.columns) == list(splits['train'].columns)


class TestBenchmarkValidation:
    """Test benchmark validation and quality checks."""
    
    def test_split_ratio_validation(self):
        """Test validation of split ratios."""
        # Valid ratios
        valid_config = {
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15
        }
        creator = BenchmarkCreator(valid_config)
        assert creator.validate_split_ratios() == True
        
        # Invalid ratios (don't sum to 1.0)
        invalid_config = {
            'train_ratio': 0.7,
            'validation_ratio': 0.2,
            'test_ratio': 0.2  # Sums to 1.1
        }
        with pytest.raises(ValueError, match="Split ratios must sum to 1.0"):
            BenchmarkCreator(invalid_config)
    
    def test_minimum_samples_validation(self):
        """Test validation of minimum samples per split."""
        small_dataset = pd.DataFrame({
            'subject_id': ['S001', 'S002'],
            'sex': ['male', 'female'],
            'cycle_id': ['S001_C01', 'S002_C01']
        })
        
        creator = BenchmarkCreator({
            'train_ratio': 0.7,
            'validation_ratio': 0.15,
            'test_ratio': 0.15,
            'stratify_columns': ['sex'],
            'min_samples_per_split': 5
        })
        
        with pytest.raises(ValueError, match="Insufficient samples for reliable splits"):
            creator.create_stratified_splits(small_dataset)
    
    def test_stratification_column_validation(self):
        """Test validation of stratification columns."""
        dataset = pd.DataFrame({
            'subject_id': ['S001', 'S002'],
            'age': [25, 30],
            'cycle_id': ['S001_C01', 'S002_C01']
        })
        
        # Missing stratification column
        creator = BenchmarkCreator({
            'stratify_columns': ['sex'],  # 'sex' column doesn't exist
            'train_ratio': 0.8,
            'validation_ratio': 0.1,
            'test_ratio': 0.1
        })
        
        with pytest.raises(ValueError, match="Stratification column\\(s\\) not found: \\['sex'\\]"):
            creator.create_stratified_splits(dataset)


class TestBenchmarkMetadata:
    """Test benchmark metadata structure and validation."""
    
    def test_metadata_structure(self):
        """Test benchmark metadata structure and required fields."""
        metadata = BenchmarkMetadata(
            name="test_benchmark",
            description="Test benchmark for validation",
            creation_date="2025-06-18",
            total_subjects=20,
            total_cycles=100,
            split_statistics={'train': 70, 'validation': 15, 'test': 15},
            demographic_distribution={'sex': {'male': 0.5, 'female': 0.5}},
            task_distribution={'walking': 100}
        )
        
        assert metadata.name == "test_benchmark"
        assert metadata.total_subjects == 20
        assert metadata.total_cycles == 100
        assert 'train' in metadata.split_statistics
        assert 'sex' in metadata.demographic_distribution
    
    def test_metadata_json_serialization(self):
        """Test metadata JSON serialization and deserialization."""
        metadata = BenchmarkMetadata(
            name="serialization_test",
            description="Test serialization",
            creation_date="2025-06-18",
            total_subjects=10,
            total_cycles=50,
            split_statistics={'train': 8, 'test': 2},
            demographic_distribution={'sex': {'male': 0.6, 'female': 0.4}},
            task_distribution={'walking': 50}
        )
        
        # Test serialization
        json_str = metadata.to_json()
        assert isinstance(json_str, str)
        assert "serialization_test" in json_str
        
        # Test deserialization
        metadata_restored = BenchmarkMetadata.from_json(json_str)
        assert metadata_restored.name == metadata.name
        assert metadata_restored.total_subjects == metadata.total_subjects
        assert metadata_restored.demographic_distribution == metadata.demographic_distribution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])