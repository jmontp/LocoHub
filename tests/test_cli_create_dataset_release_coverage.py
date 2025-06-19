#!/usr/bin/env python3
"""
CLI Create Dataset Release Coverage Test Suite

Created: 2025-06-18 with user permission  
Purpose: 100% line coverage for create_dataset_release.py CLI script

Intent: Comprehensive test coverage for all code paths, branches, error conditions,
and CLI functionality in the dataset release creation script. Tests both
configuration-based and quick setup modes, archive creation, documentation
generation, validation integration, and error handling.
"""

import unittest
import subprocess
import sys
import os
import json
import tempfile
import zipfile
import tarfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pandas as pd
import numpy as np

# Import the CLI script functions for direct testing
cli_script_path = project_root / 'contributor_scripts' / 'create_dataset_release.py'
sys.path.append(str(cli_script_path.parent))


class TestCreateDatasetReleaseCLI(unittest.TestCase):
    """Comprehensive test suite for 100% line coverage of create_dataset_release.py CLI."""
    
    def setUp(self):
        """Set up test environment with temporary directories and mock data."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))
        
        # Create test datasets directory
        self.datasets_dir = os.path.join(self.temp_dir, "datasets")
        os.makedirs(self.datasets_dir)
        
        # Create test documentation directory
        self.docs_dir = os.path.join(self.temp_dir, "docs")
        os.makedirs(self.docs_dir)
        
        # Create test output directory
        self.output_dir = os.path.join(self.temp_dir, "releases")
        os.makedirs(self.output_dir)
        
        # Create test datasets
        self._create_test_datasets()
        
        # Create test documentation
        self._create_test_documentation()
        
        # Create test configuration file
        self._create_test_config()
        
        # Store CLI script path
        self.cli_script = str(cli_script_path)
    
    def _create_test_datasets(self):
        """Create test phase and time datasets."""
        # Phase dataset
        phase_data = {
            'subject': ['S001'] * 150 + ['S002'] * 150,
            'task': ['level_walking'] * 300,
            'step': [1] * 150 + [1] * 150,
            'phase_percent': list(np.linspace(0, 100, 150)) * 2,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 300),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 300)
        }
        
        phase_file = os.path.join(self.datasets_dir, "test_dataset_phase.parquet")
        pd.DataFrame(phase_data).to_parquet(phase_file)
        self.phase_dataset_file = phase_file
        
        # Time dataset
        time_data = {
            'subject': ['S001'] * 100,
            'time_s': np.linspace(0, 1, 100),
            'task': ['level_walking'] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 100),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 100)
        }
        
        time_file = os.path.join(self.datasets_dir, "test_dataset_time.parquet")
        pd.DataFrame(time_data).to_parquet(time_file)
        self.time_dataset_file = time_file
    
    def _create_test_documentation(self):
        """Create test documentation files."""
        readme_content = """# Test Dataset
        
## Overview
Test dataset for release management.

## Citation
Test Research Team (2025). Test Dataset.
"""
        readme_file = os.path.join(self.docs_dir, "README.md")
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        guide_content = """# Usage Guide
        
## Getting Started
Instructions for using the dataset.
"""
        guide_file = os.path.join(self.docs_dir, "usage_guide.md")
        with open(guide_file, 'w') as f:
            f.write(guide_content)
    
    def _create_test_config(self):
        """Create test configuration file."""
        self.config_data = {
            "release_info": {
                "name": "test_dataset",
                "version": "1.0.0",
                "description": "Test dataset for CLI coverage",
                "citation": "Test Team (2025). Test Dataset. DOI: test",
                "license": "MIT",
                "contributors": ["Test Author"]
            },
            "datasets": {
                "source_directory": self.datasets_dir,
                "include_phase": True,
                "include_time": False,
                "validation_required": True,
                "quality_threshold": 0.8
            },
            "documentation": {
                "source_directory": self.docs_dir,
                "include_readme": True,
                "include_validation_report": True,
                "generate_citation": True,
                "custom_template_path": None
            },
            "archive": {
                "format": "zip",
                "compression_level": 6,
                "include_checksums": True
            },
            "output": {
                "directory": self.output_dir,
                "archive_name": None
            }
        }
        
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f, indent=2)
    
    def test_create_default_config_function(self):
        """Test create_default_config function - Lines 32-71."""
        from create_dataset_release import create_default_config
        
        config_path = os.path.join(self.temp_dir, "default_config.json")
        result_path = create_default_config(config_path)
        
        self.assertEqual(result_path, config_path)
        self.assertTrue(os.path.exists(config_path))
        
        # Verify content
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.assertIn('release_info', config)
        self.assertIn('datasets', config)
        self.assertIn('documentation', config)
        self.assertIn('archive', config)
        self.assertIn('output', config)
        
        # Verify specific default values
        self.assertEqual(config['release_info']['name'], 'my_dataset')
        self.assertEqual(config['release_info']['version'], '1.0.0')
        self.assertEqual(config['datasets']['quality_threshold'], 0.8)
        self.assertEqual(config['archive']['format'], 'zip')
    
    def test_collect_dataset_files_function(self):
        """Test collect_dataset_files function - Lines 114-136."""
        from create_dataset_release import collect_dataset_files
        
        # Test include_phase=True, include_time=False (default)
        files = collect_dataset_files(self.datasets_dir, include_phase=True, include_time=False)
        self.assertEqual(len(files), 1)
        self.assertTrue(any('phase.parquet' in f for f in files))
        
        # Test include_phase=True, include_time=True
        files = collect_dataset_files(self.datasets_dir, include_phase=True, include_time=True)
        self.assertEqual(len(files), 2)
        self.assertTrue(any('phase.parquet' in f for f in files))
        self.assertTrue(any('time.parquet' in f for f in files))
        
        # Test include_phase=False, include_time=True
        files = collect_dataset_files(self.datasets_dir, include_phase=False, include_time=True)
        self.assertEqual(len(files), 1)
        self.assertTrue(any('time.parquet' in f for f in files))
    
    def test_collect_dataset_files_errors(self):
        """Test collect_dataset_files error conditions - Lines 120-134."""
        from create_dataset_release import collect_dataset_files, ReleaseError
        
        # Test non-existent directory
        with self.assertRaises(ReleaseError) as context:
            collect_dataset_files("/nonexistent/directory")
        self.assertIn("Source directory does not exist", str(context.exception))
        
        # Test empty directory
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)
        with self.assertRaises(ReleaseError) as context:
            collect_dataset_files(empty_dir)
        self.assertIn("No dataset files found", str(context.exception))
    
    def test_collect_documentation_files_function(self):
        """Test collect_documentation_files function - Lines 139-151."""
        from create_dataset_release import collect_documentation_files
        
        # Test with existing docs directory
        doc_files = collect_documentation_files(self.docs_dir)
        self.assertEqual(len(doc_files), 2)  # README.md and usage_guide.md
        
        # Test with None docs directory
        doc_files = collect_documentation_files(None)
        self.assertEqual(len(doc_files), 0)
        
        # Test with non-existent docs directory
        doc_files = collect_documentation_files("/nonexistent/docs")
        self.assertEqual(len(doc_files), 0)
    
    @patch('create_dataset_release.DatasetValidator')
    def test_validate_datasets_function_phase_success(self, mock_validator_class):
        """Test validate_datasets function with phase dataset success - Lines 74-113."""
        from create_dataset_release import validate_datasets
        
        # Mock validator
        mock_validator = MagicMock()
        mock_locomotion_data = MagicMock()
        mock_validator.load_dataset.return_value = mock_locomotion_data
        mock_validator.validate_dataset.return_value = {
            'status': 'PASS',
            'quality_score': 0.95,
            'issues': []
        }
        mock_validator_class.return_value = mock_validator
        
        # Test with phase dataset
        dataset_files = [self.phase_dataset_file]
        results = validate_datasets(dataset_files, quality_threshold=0.8)
        
        self.assertEqual(len(results), 1)
        dataset_name = os.path.basename(self.phase_dataset_file)
        self.assertIn(dataset_name, results)
        self.assertEqual(results[dataset_name]['status'], 'PASS')
        self.assertEqual(results[dataset_name]['quality_score'], 0.95)
        
        # Verify validator was created with correct arguments
        mock_validator_class.assert_called_with(self.phase_dataset_file, generate_plots=False)
    
    @patch('create_dataset_release.DatasetValidator')
    def test_validate_datasets_function_phase_low_quality(self, mock_validator_class):
        """Test validate_datasets function with low quality score - Line 93."""
        from create_dataset_release import validate_datasets
        
        # Mock validator with low quality
        mock_validator = MagicMock()
        mock_locomotion_data = MagicMock()
        mock_validator.load_dataset.return_value = mock_locomotion_data
        mock_validator.validate_dataset.return_value = {
            'status': 'PASS',
            'quality_score': 0.6,  # Below threshold
            'issues': []
        }
        mock_validator_class.return_value = mock_validator
        
        dataset_files = [self.phase_dataset_file]
        results = validate_datasets(dataset_files, quality_threshold=0.8)
        
        # Should still pass validation but be marked as warning
        dataset_name = os.path.basename(self.phase_dataset_file)
        self.assertEqual(results[dataset_name]['quality_score'], 0.6)
    
    def test_validate_datasets_function_time_dataset(self):
        """Test validate_datasets function with time dataset - Lines 96-103."""
        from create_dataset_release import validate_datasets
        
        # Test with time dataset (should be skipped)
        dataset_files = [self.time_dataset_file]
        results = validate_datasets(dataset_files)
        
        dataset_name = os.path.basename(self.time_dataset_file)
        self.assertIn(dataset_name, results)
        self.assertEqual(results[dataset_name]['status'], 'SKIPPED')
        self.assertEqual(results[dataset_name]['quality_score'], 0.9)
        self.assertIn('Time dataset validation not implemented', results[dataset_name]['message'])
    
    @patch('create_dataset_release.DatasetValidator')
    def test_validate_datasets_function_exception(self, mock_validator_class):
        """Test validate_datasets function with exception - Lines 105-111."""
        from create_dataset_release import validate_datasets
        
        # Mock validator that raises exception during initialization
        mock_validator_class.side_effect = Exception("Validation error")
        
        dataset_files = [self.phase_dataset_file]
        results = validate_datasets(dataset_files)
        
        dataset_name = os.path.basename(self.phase_dataset_file)
        self.assertIn(dataset_name, results)
        self.assertEqual(results[dataset_name]['status'], 'ERROR')
        self.assertEqual(results[dataset_name]['quality_score'], 0.0)
        self.assertIn('Validation error', results[dataset_name]['error'])
    
    def test_generate_release_summary_function(self):
        """Test generate_release_summary function - Lines 156-189."""
        from create_dataset_release import generate_release_summary
        
        # Test with successful validation
        validation_results = {
            'dataset1.parquet': {'status': 'PASS', 'quality_score': 0.95},
            'dataset2.parquet': {'status': 'PASS', 'quality_score': 0.85}
        }
        
        summary = generate_release_summary(
            validation_results=validation_results,
            total_files=5,
            archive_path="/path/to/archive.zip",
            total_size_mb=125.5
        )
        
        self.assertIn('RELEASE SUMMARY', summary)
        self.assertIn('Total datasets: 2', summary)
        self.assertIn('Passed validation: 2', summary)
        self.assertIn('Average quality: 90.0%', summary)
        self.assertIn('Total files: 5', summary)
        self.assertIn('Archive size: 125.5 MB', summary)
        self.assertIn('Release Status: COMPLETE', summary)
    
    def test_generate_release_summary_function_partial_failure(self):
        """Test generate_release_summary function with failures - Lines 185-187."""
        from create_dataset_release import generate_release_summary
        
        # Test with some failures
        validation_results = {
            'dataset1.parquet': {'status': 'PASS', 'quality_score': 0.95},
            'dataset2.parquet': {'status': 'FAIL', 'quality_score': 0.45}
        }
        
        summary = generate_release_summary(
            validation_results=validation_results,
            total_files=3,
            archive_path="/path/to/archive.zip",
            total_size_mb=50.0
        )
        
        self.assertIn('Release Status: PARTIAL', summary)
        self.assertIn('Warning: 1 datasets failed validation', summary)
    
    def test_cli_create_config_argument(self):
        """Test CLI --create-config argument - Lines 322-326."""
        config_path = os.path.join(self.temp_dir, "cli_created_config.json")
        
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--create-config', config_path
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Created default configuration", result.stdout)
        self.assertTrue(os.path.exists(config_path))
        
        # Verify the created config is valid JSON
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.assertIn('release_info', config)
    
    def test_cli_config_file_not_found(self):
        """Test CLI with non-existent config file - Lines 329-330."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--config', '/nonexistent/config.json'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("Configuration file not found", result.stdout)
    
    def test_cli_invalid_config_validation(self):
        """Test CLI with invalid configuration - Lines 338-343."""
        # Create invalid config file (missing required fields)
        invalid_config = {
            "release_info": {
                # Missing required fields: name, version, description
            }
        }
        
        invalid_config_file = os.path.join(self.temp_dir, "invalid_config.json")
        with open(invalid_config_file, 'w') as f:
            json.dump(invalid_config, f)
        
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--config', invalid_config_file
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("Configuration validation failed", result.stdout)
    
    def test_cli_quick_setup_mode(self):
        """Test CLI quick setup mode - Lines 345-375."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'quick_test',
            '--version', '2.0.0',
            '--description', 'Quick setup test',
            '--citation', 'Quick Test Citation',
            '--include-time',
            '--no-validation',
            '--format', 'tar',
            '--compression-level', '3',
            '--no-checksums',
            '--docs-dir', self.docs_dir,
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Quick setup: quick_test v2.0.0", result.stdout)
        self.assertIn("DRY RUN", result.stdout)
    
    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments - Lines 377-380."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir
            # Missing --output and --name
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("Must provide either --config or --datasets + --output + --name", result.stdout)
    
    def test_cli_successful_release_creation_direct(self):
        """Test successful CLI release creation using direct function calls - Lines 384-448."""
        # This tests the main() function directly with mocking
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--config', self.config_file,
            '--verbose',
            '--dry-run'  # Use dry-run to avoid actual release creation
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                with patch('create_dataset_release.validate_datasets') as mock_validate:
                    with patch('create_dataset_release.collect_documentation_files') as mock_collect_docs:
                        # Mock returns
                        mock_collect_files.return_value = [self.phase_dataset_file]
                        mock_validate.return_value = {
                            'test_dataset_phase.parquet': {'status': 'PASS', 'quality_score': 0.95}
                        }
                        mock_collect_docs.return_value = [os.path.join(self.docs_dir, "README.md")]
                        
                        # Test main function
                        result = create_dataset_release.main()
                        self.assertEqual(result, 0)
    
    def test_cli_release_creation_failure_direct(self):
        """Test CLI release creation failure using direct function calls - Lines 449-451."""
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--config', self.config_file
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                with patch('create_dataset_release.validate_datasets') as mock_validate:
                    with patch('create_dataset_release.collect_documentation_files') as mock_collect_docs:
                        with patch('create_dataset_release.ReleaseManager') as mock_manager_class:
                            # Mock returns
                            mock_collect_files.return_value = [self.phase_dataset_file]
                            mock_validate.return_value = {}
                            mock_collect_docs.return_value = []
                            
                            # Mock manager that fails
                            mock_manager = MagicMock()
                            mock_manager.create_complete_release.return_value = {'success': False}
                            mock_manager_class.return_value = mock_manager
                            
                            # Test main function
                            result = create_dataset_release.main()
                            self.assertEqual(result, 1)
    
    def test_cli_release_error_exception_direct(self):
        """Test CLI with ReleaseError exception using direct function calls - Lines 453-455."""
        import create_dataset_release
        from create_dataset_release import ReleaseError
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--config', self.config_file
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                mock_collect_files.side_effect = ReleaseError("Test release error")
                
                # Test main function
                result = create_dataset_release.main()
                self.assertEqual(result, 1)
    
    def test_cli_unexpected_exception_direct(self):
        """Test CLI with unexpected exception using direct function calls - Lines 456-461."""
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--config', self.config_file
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                mock_collect_files.side_effect = ValueError("Unexpected error")
                
                # Test main function
                result = create_dataset_release.main()
                self.assertEqual(result, 1)
    
    def test_cli_unexpected_exception_verbose_direct(self):
        """Test CLI with unexpected exception in verbose mode using direct function calls - Lines 458-460."""
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--config', self.config_file,
            '--verbose'
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                mock_collect_files.side_effect = ValueError("Unexpected error")
                
                # Test main function - should handle exception gracefully
                result = create_dataset_release.main()
                self.assertEqual(result, 1)
    
    def test_cli_skip_validation_mode(self):
        """Test CLI with validation skipped - Lines 395-407."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'no_validation_test',
            '--no-validation',
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Skipping dataset validation", result.stdout)
    
    @patch('create_dataset_release.validate_datasets')
    @patch('create_dataset_release.collect_dataset_files')
    def test_cli_dry_run_mode(self, mock_collect_files, mock_validate):
        """Test CLI dry run mode - Lines 415-421."""
        mock_collect_files.return_value = [self.phase_dataset_file]
        mock_validate.return_value = {}
        
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--config', self.config_file,
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("DRY RUN - Would create release with:", result.stdout)
        self.assertIn("1 dataset files", result.stdout)
        self.assertIn("Archive format: zip", result.stdout)
    
    def test_cli_all_argument_groups(self):
        """Test CLI with arguments from all groups to ensure parser coverage - Lines 219-316."""
        # Test that all argument groups are properly defined and parsed
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--help'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        
        # Verify all argument groups are present in help
        help_text = result.stdout
        self.assertIn('Configuration', help_text)
        self.assertIn('Quick Setup', help_text)
        self.assertIn('Dataset Options', help_text)
        self.assertIn('Archive Options', help_text)
        self.assertIn('Documentation Options', help_text)
        self.assertIn('Control Options', help_text)
        
        # Verify specific arguments
        expected_args = [
            '--config', '--create-config',
            '--datasets', '--output', '--name', '--version', '--description',
            '--include-phase', '--include-time', '--no-validation', '--quality-threshold',
            '--format', '--compression-level', '--no-checksums',
            '--docs-dir', '--template', '--citation',
            '--verbose', '--dry-run', '--force'
        ]
        
        for arg in expected_args:
            self.assertIn(arg, help_text)
    
    def test_cli_epilog_examples(self):
        """Test CLI epilog with examples is present - Lines 195-216."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--help'
        ], capture_output=True, text=True)
        
        help_text = result.stdout
        self.assertIn('Examples:', help_text)
        self.assertIn('Configuration format:', help_text)
        self.assertIn('--create-config release_config.json', help_text)
        self.assertIn('--config release_config.json', help_text)
    
    def test_main_entry_point(self):
        """Test main() function as entry point - Lines 462-463."""
        # Test that the script can be executed as main
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--create-config', os.path.join(self.temp_dir, "entry_test.json")
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
    
    def test_compression_level_validation(self):
        """Test compression level argument validation - Line 279."""
        # Test valid compression level
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'compression_test',
            '--compression-level', '9',
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        
        # Test invalid compression level (should be handled by argparse)
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'compression_test',
            '--compression-level', '15',  # Invalid: > 9
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertNotEqual(result.returncode, 0)
    
    def test_archive_format_choices(self):
        """Test archive format argument choices - Line 275."""
        formats = ['zip', 'tar', 'tar.gz']
        
        for fmt in formats:
            result = subprocess.run([
                sys.executable, self.cli_script,
                '--datasets', self.datasets_dir,
                '--output', self.output_dir,
                '--name', f'format_test_{fmt}',
                '--format', fmt,
                '--dry-run'
            ], capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Archive format: {fmt}", result.stdout)
    
    def test_quality_threshold_argument(self):
        """Test quality threshold argument - Line 268."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'quality_test',
            '--quality-threshold', '0.9',
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
    
    @patch('create_dataset_release.collect_dataset_files')
    @patch('create_dataset_release.collect_documentation_files')
    def test_template_and_citation_arguments(self, mock_collect_docs, mock_collect_files):
        """Test template and citation arguments - Lines 294-300."""
        mock_collect_files.return_value = [self.phase_dataset_file]
        mock_collect_docs.return_value = []
        
        # Create custom template file
        template_content = "# {dataset_name} v{version}\n\nCustom template content."
        template_file = os.path.join(self.temp_dir, "custom_template.md")
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'template_test',
            '--template', template_file,
            '--citation', 'Custom Citation (2025)',
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
    
    def test_force_argument(self):
        """Test force argument - Line 313."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,
            '--output', self.output_dir,
            '--name', 'force_test',
            '--force',
            '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)


class TestCLIEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for comprehensive coverage."""
    
    def setUp(self):
        """Set up edge case test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))
        self.cli_script = str(cli_script_path)
        
        # Create datasets directory for edge case tests
        self.datasets_dir = os.path.join(self.temp_dir, "datasets")
        os.makedirs(self.datasets_dir)
        
        # Create a minimal test dataset
        test_data = {
            'subject': ['S001'] * 150,
            'task': ['level_walking'] * 150,
            'step': [1] * 150,
            'phase_percent': list(np.linspace(0, 100, 150)),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.8, 0.3, 150)
        }
        
        phase_file = os.path.join(self.datasets_dir, "edge_test_phase.parquet")
        pd.DataFrame(test_data).to_parquet(phase_file)
    
    def test_empty_quality_scores_list(self):
        """Test generate_release_summary with empty quality scores - Line 164."""
        from create_dataset_release import generate_release_summary
        
        # Test with validation results that have no quality scores
        validation_results = {
            'dataset1.parquet': {'status': 'ERROR'}  # No quality_score field
        }
        
        summary = generate_release_summary(
            validation_results=validation_results,
            total_files=1,
            archive_path="/path/to/archive.zip",
            total_size_mb=10.0
        )
        
        # Should handle missing quality scores gracefully
        self.assertIn('Average quality: 0.0%', summary)
    
    def test_default_arguments_coverage(self):
        """Test default argument values are used - Lines 245-269."""
        # Test with minimal arguments to ensure defaults are applied
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--help'
        ], capture_output=True, text=True)
        
        help_text = result.stdout
        # Verify default values are mentioned in help
        self.assertIn('default: 1.0.0', help_text)  # version default
        self.assertIn('default: True', help_text)   # include-phase default
        self.assertIn('default: 0.8', help_text)    # quality-threshold default
        self.assertIn('default: zip', help_text)    # format default
        self.assertIn('default: 6', help_text)      # compression-level default
    
    def test_include_phase_default_behavior(self):
        """Test include-phase default behavior - Line 256."""
        result = subprocess.run([
            sys.executable, self.cli_script,
            '--datasets', self.datasets_dir,  # Use datasets_dir which has actual files
            '--output', self.temp_dir,
            '--name', 'default_test',
            '--dry-run'
        ], capture_output=True, text=True)
        
        # Should succeed with default include-phase=True even without explicit flag
        self.assertEqual(result.returncode, 0)


    def test_main_entry_point_coverage(self):
        """Test main() function entry point for coverage - Line 465."""
        # Import and test the if __name__ == '__main__' path
        import create_dataset_release
        
        # Mock sys.exit to prevent actual exit
        with patch('sys.exit') as mock_exit:
            with patch('sys.argv', [
                'create_dataset_release.py',
                '--create-config', os.path.join(self.temp_dir, "main_test.json")
            ]):
                # This tests the __main__ block execution
                exec(compile(
                    open(str(cli_script_path)).read(),
                    str(cli_script_path),
                    'exec'
                ))
                mock_exit.assert_called_once_with(0)
    
    def test_datetime_import_in_quick_setup(self):
        """Test datetime.now() usage in quick setup mode - Line 352."""
        import create_dataset_release
        from datetime import datetime
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--datasets', self.datasets_dir,
            '--output', self.temp_dir,
            '--name', 'datetime_test',
            '--dry-run'
        ]):
            with patch('create_dataset_release.datetime') as mock_datetime:
                mock_now = MagicMock()
                mock_now.year = 2025
                mock_datetime.now.return_value = mock_now
                
                result = create_dataset_release.main()
                self.assertEqual(result, 0)
                mock_datetime.now.assert_called()
    
    def test_validation_skip_path_direct(self):
        """Test validation skip path with mock results creation - Lines 403-408."""
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--datasets', self.datasets_dir,
            '--output', self.temp_dir,
            '--name', 'validation_skip_test',
            '--no-validation',
            '--dry-run'
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                with patch('create_dataset_release.collect_documentation_files') as mock_collect_docs:
                    mock_collect_files.return_value = [os.path.join(self.datasets_dir, "test.parquet")]
                    mock_collect_docs.return_value = []
                    
                    result = create_dataset_release.main()
                    self.assertEqual(result, 0)
    
    def test_quick_setup_all_options_direct(self):
        """Test quick setup mode with all options - Lines 347-375."""
        import create_dataset_release
        
        with patch('sys.argv', [
            'create_dataset_release.py',
            '--datasets', self.datasets_dir,
            '--output', self.temp_dir,
            '--name', 'full_quick_test',
            '--version', '2.1.0',
            '--description', 'Full quick setup test',
            '--citation', 'Test Citation 2025',
            '--include-time',
            '--quality-threshold', '0.9',
            '--format', 'tar.gz',
            '--compression-level', '8',
            '--no-checksums',
            '--docs-dir', self.temp_dir,
            '--template', '/nonexistent/template.md',
            '--no-validation',
            '--dry-run'
        ]):
            with patch('create_dataset_release.collect_dataset_files') as mock_collect_files:
                with patch('create_dataset_release.collect_documentation_files') as mock_collect_docs:
                    mock_collect_files.return_value = [os.path.join(self.datasets_dir, "test.parquet")]
                    mock_collect_docs.return_value = []
                    
                    result = create_dataset_release.main()
                    self.assertEqual(result, 0)


if __name__ == '__main__':
    # Run with high verbosity to see coverage details
    unittest.main(verbosity=2)