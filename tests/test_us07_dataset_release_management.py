#!/usr/bin/env python3
"""
US-07 Dataset Release Management Test Suite

Created: 2025-06-18 with user permission
Purpose: Memory-conscious tests for comprehensive dataset release management

Intent: Tests the complete dataset release workflow including streaming archive
creation, validation summary generation, metadata bundling, and documentation
compilation. Focuses on memory efficiency by using streaming operations and
small test data for validation.
"""

import unittest
import json
import tempfile
import os
import zipfile
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pandas as pd
import numpy as np


class TestReleaseManager(unittest.TestCase):
    """Test the memory-conscious dataset release manager."""
    
    def setUp(self):
        """Set up test environment with temporary files and mock datasets."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.temp_dir))
        
        # Create test dataset files
        self.test_datasets = self._create_test_datasets()
        
        # Create test documentation
        self.test_docs = self._create_test_documentation()
        
        # Mock ReleaseManager import (will be implemented)
        self.release_manager = None

    def _create_test_datasets(self):
        """Create small test parquet datasets for archive testing."""
        datasets = {}
        
        # Create phase dataset
        phase_data = {
            'cycle_id': [1, 1, 1, 2, 2, 2],
            'phase_pct': [0, 50, 100, 0, 50, 100],
            'hip_flexion_angle_ipsi_rad': [0.1, 0.2, 0.1, 0.15, 0.25, 0.15],
            'knee_flexion_angle_ipsi_rad': [0.3, 1.2, 0.3, 0.35, 1.25, 0.35],
            'task': ['level_walking'] * 6,
            'subject_id': ['S001'] * 6,
            'trial_id': [1] * 3 + [2] * 3
        }
        
        phase_file = os.path.join(self.temp_dir, "test_dataset_phase.parquet")
        pd.DataFrame(phase_data).to_parquet(phase_file)
        datasets['phase'] = phase_file
        
        # Create time dataset
        time_data = {
            'time_s': [0.0, 0.01, 0.02, 0.03, 0.04, 0.05],
            'hip_flexion_angle_ipsi_rad': [0.1, 0.15, 0.2, 0.18, 0.12, 0.1],
            'knee_flexion_angle_ipsi_rad': [0.3, 0.6, 1.2, 1.1, 0.7, 0.3],
            'task': ['level_walking'] * 6,
            'subject_id': ['S001'] * 6,
            'trial_id': [1] * 6
        }
        
        time_file = os.path.join(self.temp_dir, "test_dataset_time.parquet")
        pd.DataFrame(time_data).to_parquet(time_file)
        datasets['time'] = time_file
        
        return datasets

    def _create_test_documentation(self):
        """Create test documentation files."""
        docs = {}
        
        # README
        readme_content = """# Test Dataset Release

## Overview
Test dataset for release management validation.

## Citation
Test Citation (2025)

## Usage
Load with pandas: pd.read_parquet('dataset.parquet')
"""
        readme_file = os.path.join(self.temp_dir, "README.md")
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        docs['readme'] = readme_file
        
        # Validation report
        validation_content = """# Validation Report

## Summary
- Total cycles: 2
- Validation status: PASS
- Quality score: 95%

## Details
All validation checks passed successfully.
"""
        validation_file = os.path.join(self.temp_dir, "validation_report.md")
        with open(validation_file, 'w') as f:
            f.write(validation_content)
        docs['validation'] = validation_file
        
        return docs

    def test_create_dataset_metadata(self):
        """Test creation of comprehensive dataset metadata."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Test metadata creation
        metadata = manager.create_dataset_metadata(
            dataset_name="test_dataset",
            version="1.0.0",
            description="Test dataset for validation",
            citation="Test et al. 2025",
            license_type="MIT",
            dataset_files=list(self.test_datasets.values()),
            contributors=["Test Author"],
            creation_date=datetime(2025, 6, 18)
        )
        
        # Verify required metadata fields
        required_fields = [
            'name', 'version', 'description', 'citation', 'license',
            'files', 'contributors', 'creation_date', 'file_checksums'
        ]
        
        for field in required_fields:
            self.assertIn(field, metadata)
        
        # Verify data types
        self.assertIsInstance(metadata['name'], str)
        self.assertIsInstance(metadata['version'], str)
        self.assertIsInstance(metadata['files'], list)
        self.assertIsInstance(metadata['contributors'], list)
        self.assertIsInstance(metadata['file_checksums'], dict)
        
        # Verify file checksums are generated
        self.assertEqual(len(metadata['file_checksums']), len(self.test_datasets))

    def test_streaming_archive_creation(self):
        """Test memory-efficient streaming archive creation."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        archive_path = os.path.join(self.temp_dir, "test_release.zip")
        
        # Test streaming archive creation
        files_to_archive = {
            'datasets/phase.parquet': self.test_datasets['phase'],
            'datasets/time.parquet': self.test_datasets['time'],
            'docs/README.md': self.test_docs['readme'],
            'docs/validation_report.md': self.test_docs['validation']
        }
        
        manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping=files_to_archive,
            compression_level=6
        )
        
        # Verify archive was created
        self.assertTrue(os.path.exists(archive_path))
        
        # Verify archive contents
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            archive_files = zip_file.namelist()
            
            expected_files = list(files_to_archive.keys())
            for expected_file in expected_files:
                self.assertIn(expected_file, archive_files)
        
        # Verify file integrity by extracting and comparing
        extract_dir = os.path.join(self.temp_dir, "extracted")
        os.makedirs(extract_dir)
        
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            zip_file.extractall(extract_dir)
        
        # Compare original and extracted phase dataset
        original_df = pd.read_parquet(self.test_datasets['phase'])
        extracted_df = pd.read_parquet(os.path.join(extract_dir, 'datasets/phase.parquet'))
        
        pd.testing.assert_frame_equal(original_df, extracted_df)

    def test_validation_summary_generation(self):
        """Test generation of validation summaries without loading full datasets."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Mock validation results
        mock_validation_results = {
            'test_dataset_phase.parquet': {
                'status': 'PASS',
                'total_cycles': 2,
                'valid_cycles': 2,
                'quality_score': 0.95,
                'validation_issues': [],
                'file_size_mb': 0.001,
                'data_points': 6
            }
        }
        
        # Test summary generation
        summary = manager.generate_validation_summary(mock_validation_results)
        
        # Verify summary structure
        required_sections = [
            'overview', 'dataset_summary', 'quality_metrics', 
            'validation_status', 'recommendations'
        ]
        
        for section in required_sections:
            self.assertIn(section, summary)
        
        # Verify data aggregation
        self.assertEqual(summary['overview']['total_datasets'], 1)
        self.assertEqual(summary['overview']['datasets_passing'], 1)
        self.assertAlmostEqual(summary['quality_metrics']['average_quality'], 0.95, places=2)
        
        # Verify markdown formatting
        markdown_output = manager.format_validation_summary_markdown(summary)
        self.assertIn('# Validation Summary', markdown_output)
        self.assertIn('## Overview', markdown_output)
        self.assertIn('**Status:** PASS', markdown_output)

    def test_release_configuration(self):
        """Test release configuration validation and loading."""
        from internal.validation_engine.release_manager import ReleaseConfig
        
        # Create test configuration
        config_data = {
            'release_info': {
                'name': 'test_release',
                'version': '1.0.0',
                'description': 'Test release for validation'
            },
            'datasets': {
                'include_phase': True,
                'include_time': True,
                'validation_required': True
            },
            'documentation': {
                'include_readme': True,
                'include_validation_report': True,
                'include_citation': True
            },
            'archive': {
                'format': 'zip',
                'compression_level': 6,
                'include_checksums': True
            }
        }
        
        config_file = os.path.join(self.temp_dir, "release_config.json")
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Test configuration loading
        config = ReleaseConfig.from_file(config_file)
        
        # Verify configuration properties
        self.assertEqual(config.release_name, 'test_release')
        self.assertEqual(config.version, '1.0.0')
        self.assertTrue(config.include_phase_datasets)
        self.assertTrue(config.include_time_datasets)
        self.assertTrue(config.validation_required)
        self.assertEqual(config.archive_format, 'zip')

    def test_integrity_verification(self):
        """Test release archive integrity verification."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Create test archive
        archive_path = os.path.join(self.temp_dir, "test_integrity.zip")
        files_to_archive = {
            'data.parquet': self.test_datasets['phase'],
            'README.md': self.test_docs['readme']
        }
        
        # Create archive with checksums
        checksums = manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping=files_to_archive,
            include_checksums=True
        )
        
        # Test integrity verification
        integrity_result = manager.verify_archive_integrity(
            archive_path=archive_path,
            expected_checksums=checksums
        )
        
        # Verify integrity check results
        self.assertTrue(integrity_result['is_valid'])
        self.assertEqual(len(integrity_result['verified_files']), len(files_to_archive))
        self.assertEqual(len(integrity_result['checksum_mismatches']), 0)
        self.assertEqual(len(integrity_result['missing_files']), 0)

    def test_memory_efficient_processing(self):
        """Test memory efficiency with larger dataset simulation."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Create larger test dataset (but still small for CI)
        large_data = {
            'cycle_id': list(range(1, 51)) * 3,  # 50 cycles, 3 points each
            'phase_pct': [0, 50, 100] * 50,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 150),
            'task': ['level_walking'] * 150,
            'subject_id': ['S001'] * 150,
            'trial_id': list(range(1, 51)) * 3
        }
        
        large_dataset_file = os.path.join(self.temp_dir, "large_dataset.parquet")
        pd.DataFrame(large_data).to_parquet(large_dataset_file)
        
        # Test streaming processing without loading full dataset
        file_info = manager.get_dataset_info_streaming(large_dataset_file)
        
        # Verify we can get info without loading full dataset
        self.assertIn('file_size_mb', file_info)
        self.assertIn('estimated_rows', file_info)
        self.assertIn('column_count', file_info)
        self.assertIn('data_types', file_info)
        
        # Test streaming archive with larger file
        archive_path = os.path.join(self.temp_dir, "large_archive.zip")
        manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping={'large_data.parquet': large_dataset_file}
        )
        
        # Verify archive creation succeeded
        self.assertTrue(os.path.exists(archive_path))
        
        # Verify reasonable file size (compressed)
        archive_size = os.path.getsize(archive_path)
        original_size = os.path.getsize(large_dataset_file)
        compression_ratio = archive_size / original_size
        
        # Should achieve some compression
        self.assertLess(compression_ratio, 0.9)

    def test_documentation_compilation(self):
        """Test automatic documentation compilation."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Test documentation compilation
        doc_info = {
            'dataset_name': 'test_dataset',
            'version': '1.0.0',
            'description': 'Test dataset for validation',
            'citation': 'Test et al. 2025',
            'license': 'MIT',
            'total_subjects': 1,
            'total_trials': 2,
            'total_cycles': 2,
            'tasks': ['level_walking'],
            'variables': ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'],
            'quality_score': 0.95
        }
        
        compiled_readme = manager.compile_documentation(
            template_type='readme',
            doc_info=doc_info,
            custom_sections=None
        )
        
        # Verify compiled documentation
        self.assertIn('# test_dataset', compiled_readme)
        self.assertIn('**Version:** 1.0.0', compiled_readme)
        self.assertIn('Test et al. 2025', compiled_readme)
        self.assertIn('level_walking', compiled_readme)
        self.assertIn('Quality Score:** 95.0%', compiled_readme)
        
        # Test citation format compilation
        citation_info = doc_info.copy()
        citation_info['release_date'] = '2025-01-01'
        citation_doc = manager.compile_documentation(
            template_type='citation',
            doc_info=citation_info
        )
        
        self.assertIn('test_dataset', citation_doc)
        self.assertIn('v1.0.0', citation_doc)
        self.assertIn('Test et al. 2025', citation_doc)

    def test_incremental_archive_creation(self):
        """Test incremental archive creation for large releases."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        archive_path = os.path.join(self.temp_dir, "incremental_archive.zip")
        
        # Test incremental addition to archive
        with manager.create_incremental_archive(archive_path) as archive:
            # Add files in chunks
            archive.add_file('datasets/phase.parquet', self.test_datasets['phase'])
            archive.add_file('datasets/time.parquet', self.test_datasets['time'])
            
            # Add documentation
            archive.add_file('docs/README.md', self.test_docs['readme'])
            archive.add_file('docs/validation.md', self.test_docs['validation'])
            
            # Add generated metadata
            metadata = {
                'release_info': {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }
            archive.add_json('metadata.json', metadata)
        
        # Verify incremental archive
        self.assertTrue(os.path.exists(archive_path))
        
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            files = zip_file.namelist()
            self.assertIn('datasets/phase.parquet', files)
            self.assertIn('datasets/time.parquet', files)
            self.assertIn('docs/README.md', files)
            self.assertIn('metadata.json', files)

    def test_tar_archive_support(self):
        """Test support for tar.gz archive format."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        archive_path = os.path.join(self.temp_dir, "test_release.tar.gz")
        
        files_to_archive = {
            'data.parquet': self.test_datasets['phase'],
            'README.md': self.test_docs['readme']
        }
        
        # Test tar.gz creation
        manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping=files_to_archive,
            archive_format='tar.gz'
        )
        
        # Verify tar.gz archive
        self.assertTrue(os.path.exists(archive_path))
        
        with tarfile.open(archive_path, 'r:gz') as tar_file:
            names = tar_file.getnames()
            self.assertIn('data.parquet', names)
            self.assertIn('README.md', names)


class TestReleaseManagerCLI(unittest.TestCase):
    """Test CLI interface for dataset release management."""
    
    def setUp(self):
        """Set up CLI test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.temp_dir))
        
        # Create test configuration
        self.config_data = {
            'release_info': {
                'name': 'test_release',
                'version': '1.0.0',
                'description': 'Test release'
            },
            'datasets': {
                'source_directory': self.temp_dir,
                'include_phase': True,
                'include_time': True
            },
            'output': {
                'directory': self.temp_dir,
                'archive_format': 'zip'
            }
        }
        
        self.config_file = os.path.join(self.temp_dir, "release_config.json")
        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f, indent=2)

    def test_cli_command_structure(self):
        """Test CLI command structure and argument parsing."""
        # Mock CLI argument parsing
        expected_args = [
            '--config', self.config_file,
            '--output-dir', self.temp_dir,
            '--format', 'zip',
            '--compression-level', '6',
            '--with-validation',
            '--include-checksums',
            '--verbose'
        ]
        
        # Test argument structure validity
        arg_pairs = []
        for i in range(0, len(expected_args), 2):
            if i + 1 < len(expected_args) and not expected_args[i + 1].startswith('--'):
                arg_pairs.append((expected_args[i], expected_args[i + 1]))
            else:
                arg_pairs.append((expected_args[i], None))
        
        # Verify argument structure
        config_found = any(arg[0] == '--config' for arg in arg_pairs)
        output_found = any(arg[0] == '--output-dir' for arg in arg_pairs)
        format_found = any(arg[0] == '--format' for arg in arg_pairs)
        
        self.assertTrue(config_found)
        self.assertTrue(output_found)
        self.assertTrue(format_found)

    def test_configuration_validation(self):
        """Test configuration file validation."""
        from internal.validation_engine.release_manager import validate_release_config
        
        # Test valid configuration
        is_valid, errors = validate_release_config(self.config_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test invalid configuration (missing required fields)
        invalid_config = {
            'release_info': {
                'name': 'test'
                # Missing version and description
            }
        }
        
        is_valid, errors = validate_release_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_output_directory_creation(self):
        """Test automatic output directory creation."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Test directory creation
        output_dir = os.path.join(self.temp_dir, "new_output_dir")
        self.assertFalse(os.path.exists(output_dir))
        
        manager.ensure_output_directory(output_dir)
        self.assertTrue(os.path.exists(output_dir))
        self.assertTrue(os.path.isdir(output_dir))

    def test_progress_reporting(self):
        """Test progress reporting for long operations."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Mock progress callback
        progress_updates = []
        
        def progress_callback(current, total, message):
            progress_updates.append({
                'current': current,
                'total': total,
                'message': message,
                'percentage': (current / total) * 100 if total > 0 else 0
            })
        
        # Test progress reporting during archive creation
        files_to_archive = {
            'file1.txt': self.config_file,
            'file2.txt': self.config_file
        }
        
        archive_path = os.path.join(self.temp_dir, "progress_test.zip")
        
        manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping=files_to_archive,
            progress_callback=progress_callback
        )
        
        # Verify progress was reported
        self.assertGreater(len(progress_updates), 0)
        
        # Verify progress sequence
        percentages = [update['percentage'] for update in progress_updates]
        self.assertTrue(all(0 <= p <= 100 for p in percentages))
        
        # Should have start and end progress
        self.assertIn(0.0, percentages)
        self.assertIn(100.0, percentages)

    def test_error_handling(self):
        """Test comprehensive error handling."""
        from internal.validation_engine.release_manager import ReleaseManager, ReleaseError
        
        manager = ReleaseManager()
        
        # Test missing file error
        with self.assertRaises(ReleaseError) as context:
            manager.create_streaming_archive(
                archive_path=os.path.join(self.temp_dir, "error_test.zip"),
                files_mapping={'missing.txt': '/path/that/does/not/exist'}
            )
        
        self.assertIn('File not found', str(context.exception))
        
        # Test invalid archive path error
        with self.assertRaises(ReleaseError) as context:
            manager.create_streaming_archive(
                archive_path='/invalid/path/archive.zip',
                files_mapping={'file.txt': self.config_file}
            )
        
        self.assertIn('Cannot create archive directory', str(context.exception))

    def test_custom_template_support(self):
        """Test support for custom documentation templates."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Create custom template
        custom_template = """# {dataset_name} v{version}

**Description:** {description}
**Quality Score:** {quality_score:.1%}

## Custom Section
This is a custom documentation section.

## Variables
{variables_list}
"""
        
        template_file = os.path.join(self.temp_dir, "custom_template.md")
        with open(template_file, 'w') as f:
            f.write(custom_template)
        
        # Test custom template compilation
        doc_info = {
            'dataset_name': 'custom_dataset',
            'version': '2.0.0',
            'description': 'Custom dataset with template',
            'quality_score': 0.87,
            'variables': ['hip_angle', 'knee_angle']
        }
        
        compiled_doc = manager.compile_documentation(
            template_file=template_file,
            doc_info=doc_info
        )
        
        # Verify custom template was used
        self.assertIn('# custom_dataset v2.0.0', compiled_doc)
        self.assertIn('Quality Score:** 87.0%', compiled_doc)
        self.assertIn('Custom Section', compiled_doc)
        self.assertIn('hip_angle', compiled_doc)


class TestReleaseIntegration(unittest.TestCase):
    """Integration tests for complete release workflow."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.temp_dir))
        
        # Create realistic test environment
        self._setup_test_environment()

    def _setup_test_environment(self):
        """Create realistic test datasets and configuration."""
        # Create datasets directory
        datasets_dir = os.path.join(self.temp_dir, "datasets")
        os.makedirs(datasets_dir)
        
        # Create phase dataset
        phase_data = {
            'cycle_id': list(range(1, 21)) * 3,  # 20 cycles
            'phase_pct': [0, 50, 100] * 20,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 60),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 60),
            'ankle_flexion_angle_ipsi_rad': np.random.normal(-0.1, 0.2, 60),
            'task': ['level_walking'] * 60,
            'subject_id': ['S001'] * 30 + ['S002'] * 30,
            'trial_id': list(range(1, 11)) * 6
        }
        
        phase_file = os.path.join(datasets_dir, "example_dataset_phase.parquet")
        pd.DataFrame(phase_data).to_parquet(phase_file)
        
        # Create documentation
        docs_dir = os.path.join(self.temp_dir, "documentation")
        os.makedirs(docs_dir)
        
        readme_content = """# Example Dataset

## Overview
Example locomotion dataset for testing release management.

## Citation
Example Research Group (2025). Example Dataset. DOI: 10.1000/example

## Usage
```python
import pandas as pd
data = pd.read_parquet('example_dataset_phase.parquet')
```
"""
        
        with open(os.path.join(docs_dir, "README.md"), 'w') as f:
            f.write(readme_content)

    def test_complete_release_workflow(self):
        """Test complete end-to-end release creation workflow."""
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        
        # Define release configuration
        release_config = {
            'release_info': {
                'name': 'example_dataset',
                'version': '1.0.0',
                'description': 'Example dataset for testing',
                'citation': 'Example Research Group (2025)',
                'license': 'CC BY 4.0'
            },
            'datasets': {
                'source_directory': os.path.join(self.temp_dir, "datasets"),
                'include_phase': True,
                'include_time': False,
                'validation_required': True
            },
            'documentation': {
                'source_directory': os.path.join(self.temp_dir, "documentation"),
                'include_readme': True,
                'generate_citation': True,
                'include_validation_report': True
            },
            'output': {
                'directory': self.temp_dir,
                'archive_name': 'example_dataset_v1.0.0',
                'format': 'zip',
                'include_checksums': True
            }
        }
        
        # Execute complete workflow
        release_result = manager.create_complete_release(release_config)
        
        # Verify release creation
        self.assertTrue(release_result['success'])
        self.assertIn('archive_path', release_result)
        self.assertIn('metadata_path', release_result)
        self.assertIn('checksum_path', release_result)
        
        # Verify archive exists and has expected structure
        archive_path = release_result['archive_path']
        self.assertTrue(os.path.exists(archive_path))
        
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            files = zip_file.namelist()
            
            # Should contain datasets
            dataset_files = [f for f in files if f.startswith('datasets/')]
            self.assertGreater(len(dataset_files), 0)
            
            # Should contain documentation
            doc_files = [f for f in files if f.startswith('documentation/')]
            self.assertGreater(len(doc_files), 0)
            
            # Should contain metadata
            self.assertIn('metadata.json', files)
            
            # Should contain checksums if requested
            if release_config['output']['include_checksums']:
                self.assertIn('checksums.txt', files)

    def test_release_validation_integration(self):
        """Test integration with validation system during release."""
        from internal.validation_engine.release_manager import ReleaseManager
        from internal.validation_engine.dataset_validator_phase import DatasetValidator
        
        manager = ReleaseManager()
        
        # Test dataset validation before release
        phase_dataset = os.path.join(self.temp_dir, "datasets", "example_dataset_phase.parquet")
        
        # Create a simple test dataset for validation
        import pandas as pd
        import numpy as np
        
        # Create test data that matches expected structure
        test_data = pd.DataFrame({
            'subject': ['test_subject'] * 150,
            'task': ['level_walking'] * 150,
            'step': [1] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150)
        })
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(phase_dataset), exist_ok=True)
        test_data.to_parquet(phase_dataset)
        
        validator = DatasetValidator(phase_dataset, generate_plots=False)
        # Mock validation expectations for the test
        validator.kinematic_expectations = {
            'level_walking': {
                'hip_flexion_angle_ipsi_rad': {'min': -0.5, 'max': 1.5},
                'knee_flexion_angle_ipsi_rad': {'min': 0.0, 'max': 2.0}
            }
        }
        validator.kinetic_expectations = {}
        locomotion_data = validator.load_dataset()
        validation_result = validator.validate_dataset(locomotion_data)
        
        # Should pass basic validation
        self.assertIn('total_steps', validation_result)
        self.assertGreater(validation_result['total_steps'], 0)
        
        # Test integration of validation results into release
        release_summary = manager.integrate_validation_results(
            dataset_files=[phase_dataset],
            validation_results=[validation_result]
        )
        
        self.assertIn('validation_summary', release_summary)
        self.assertIn('validation_status', release_summary['validation_summary'])

    def test_memory_usage_monitoring(self):
        """Test memory usage during large release creation."""
        import psutil
        import os
        
        # Monitor memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create larger dataset for memory testing
        large_data = {
            'cycle_id': list(range(1, 101)) * 3,  # 100 cycles
            'phase_pct': [0, 50, 100] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 300),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 300),
            'task': ['level_walking'] * 300,
            'subject_id': (['S001'] * 100 + ['S002'] * 100 + ['S003'] * 100),
            'trial_id': list(range(1, 51)) * 6
        }
        
        large_dataset_file = os.path.join(self.temp_dir, "large_dataset.parquet")
        pd.DataFrame(large_data).to_parquet(large_dataset_file)
        
        # Create release with larger dataset
        from internal.validation_engine.release_manager import ReleaseManager
        
        manager = ReleaseManager()
        archive_path = os.path.join(self.temp_dir, "large_release.zip")
        
        manager.create_streaming_archive(
            archive_path=archive_path,
            files_mapping={'large_data.parquet': large_dataset_file}
        )
        
        # Check memory usage increase
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        self.assertLess(memory_increase, 100, 
                       f"Memory usage increased by {memory_increase:.1f}MB")


if __name__ == '__main__':
    unittest.main()