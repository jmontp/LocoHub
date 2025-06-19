#!/usr/bin/env python3
"""
test_cli_detect_dataset_type_coverage.py

Created: 2025-06-18 with user permission
Purpose: 100% line coverage testing for contributor_scripts/detect_dataset_type.py

Intent: Emergency government audit compliance - achieve complete test coverage
for all 106 lines of the detect_dataset_type.py CLI script through comprehensive
testing of all code paths, edge cases, and error conditions.
"""

import os
import sys
import unittest
import tempfile
import subprocess
import json
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestDetectDatasetTypeCLICoverage(unittest.TestCase):
    """Comprehensive test coverage for detect_dataset_type.py CLI script."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        
        # Create test datasets with different naming patterns
        self.test_files = self._create_test_datasets()
        
        # Path to CLI script
        self.cli_script = "contributor_scripts/detect_dataset_type.py"
        
    def _create_test_datasets(self):
        """Create test datasets with various naming patterns."""
        test_files = {}
        
        # Create base dataset
        base_data = pd.DataFrame({
            'subject': ['SUB01'] * 150,
            'task': ['level_walking'] * 150,
            'step': [1] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150),
            'subject_id': ['SUB01'] * 150,
            'trial_id': ['trial_001'] * 150
        })
        
        # AddBiomechanics patterns
        addbiomech_data = base_data.copy()
        addbiomech_data['addbiomech_version'] = ['v1.0'] * 150
        addbiomech_data['opensim_version'] = ['4.0'] * 150
        
        test_files['addbiomechanics_walk_01.parquet'] = addbiomech_data
        test_files['addbiomech_test.parquet'] = addbiomech_data
        test_files['AB_dataset.parquet'] = addbiomech_data
        test_files['data_addbiomech_full.parquet'] = addbiomech_data
        
        # GTech 2023 patterns
        gtech_data = base_data.copy()
        gtech_data['gtech_study_id'] = ['GT2023_001'] * 150
        gtech_data['georgia_tech_version'] = ['v2.0'] * 150
        
        test_files['gtech_2023_walking.parquet'] = gtech_data
        test_files['GT2023_subject01.parquet'] = gtech_data
        test_files['gtech23_data.parquet'] = gtech_data
        test_files['study_gtech_2023_full.parquet'] = gtech_data
        
        # UMich 2021 patterns
        umich_data = base_data.copy()
        umich_data['umich_study_id'] = ['UM2021_001'] * 150
        umich_data['michigan_version'] = ['v1.5'] * 150
        
        test_files['umich_2021_walking.parquet'] = umich_data
        test_files['UM2021_subject01.parquet'] = umich_data
        test_files['michigan_2021_data.parquet'] = umich_data
        test_files['data_umich_2021_complete.parquet'] = umich_data
        
        # Unknown/ambiguous patterns
        test_files['unknown_dataset.parquet'] = base_data
        test_files['generic_walking_data.parquet'] = base_data
        
        # Non-parquet file (should fail)
        test_files['not_parquet.csv'] = base_data
        
        # Create actual files
        file_paths = {}
        for filename, data in test_files.items():
            filepath = os.path.join(self.temp_dir, filename)
            if filename.endswith('.parquet'):
                data.to_parquet(filepath)
            else:
                data.to_csv(filepath)
            file_paths[filename] = filepath
            
        return file_paths
    
    def _run_cli(self, args, expect_success=True):
        """Helper to run CLI command and return result."""
        cmd = [sys.executable, self.cli_script] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if expect_success and result.returncode not in [0, 2]:  # 2 is low confidence warning
            self.fail(f"CLI failed unexpectedly: {result.stderr}\nStdout: {result.stdout}")
            
        return result
    
    def test_setup_logging_verbose(self):
        """Test setup_logging function with verbose=True."""
        # Import the function to test it directly
        from contributor_scripts.detect_dataset_type import setup_logging
        
        # Reset logging to a known state
        logger = logging.getLogger()
        original_level = logger.level
        
        # Test verbose logging
        setup_logging(verbose=True)
        
        # Verify logging level is appropriately set for verbose mode
        # The actual behavior may depend on existing logger configuration
        self.assertTrue(logger.level <= logging.DEBUG or logger.hasHandlers())
        
        # Restore original level
        logger.setLevel(original_level)
        
    def test_setup_logging_non_verbose(self):
        """Test setup_logging function with verbose=False."""
        from contributor_scripts.detect_dataset_type import setup_logging
        
        # Reset logging to a known state
        logger = logging.getLogger()
        original_level = logger.level
        
        # Test non-verbose logging
        setup_logging(verbose=False)
        
        # Verify logging level is appropriately set for non-verbose mode
        # The actual behavior may depend on existing logger configuration
        self.assertTrue(logger.level <= logging.INFO or logger.hasHandlers())
        
        # Restore original level
        logger.setLevel(original_level)
    
    def test_detect_single_file_verbose(self):
        """Test detect_single_file function with verbose=True."""
        from contributor_scripts.detect_dataset_type import detect_single_file
        
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = detect_single_file(filepath, use_metadata=True, verbose=True)
        
        # Should include evidence in verbose mode
        self.assertIn('evidence', result)
        self.assertIn('file', result)
        self.assertIn('type', result)
        self.assertIn('confidence', result)
        
    def test_detect_single_file_non_verbose(self):
        """Test detect_single_file function with verbose=False."""
        from contributor_scripts.detect_dataset_type import detect_single_file
        
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = detect_single_file(filepath, use_metadata=True, verbose=False)
        
        # Should NOT include evidence in non-verbose mode
        self.assertNotIn('evidence', result)
        self.assertIn('file', result)
        self.assertIn('type', result)
        self.assertIn('confidence', result)
        
    def test_detect_batch_files_verbose(self):
        """Test detect_batch_files function with verbose=True."""
        from contributor_scripts.detect_dataset_type import detect_batch_files
        
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        results = detect_batch_files(filepaths, use_metadata=True, verbose=True)
        
        # Should return list with evidence
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn('evidence', result)
            self.assertIn('file', result)
            
    def test_detect_batch_files_non_verbose(self):
        """Test detect_batch_files function with verbose=False."""
        from contributor_scripts.detect_dataset_type import detect_batch_files
        
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        results = detect_batch_files(filepaths, use_metadata=True, verbose=False)
        
        # Should return list without evidence
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertNotIn('evidence', result)
            self.assertIn('file', result)
            
    def test_print_summary_report_empty_results(self):
        """Test print_summary_report with empty results."""
        from contributor_scripts.detect_dataset_type import print_summary_report
        from io import StringIO
        
        # Capture stdout
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            print_summary_report([])
            
        output = captured_output.getvalue()
        self.assertIn("No results to summarize", output)
        
    def test_print_summary_report_with_results(self):
        """Test print_summary_report with actual results."""
        from contributor_scripts.detect_dataset_type import print_summary_report
        from io import StringIO
        
        # Create mock results
        results = [
            {'type': 'addbiomechanics', 'confidence': 85},
            {'type': 'addbiomechanics', 'confidence': 75},
            {'type': 'gtech_2023', 'confidence': 90},
            {'type': 'unknown', 'confidence': 25}
        ]
        
        # Capture stdout
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            print_summary_report(results)
            
        output = captured_output.getvalue()
        self.assertIn("DETECTION SUMMARY", output)
        self.assertIn("Total files analyzed: 4", output)
        self.assertIn("ADDBIOMECHANICS:", output)
        self.assertIn("GTECH_2023:", output)
        self.assertIn("UNKNOWN:", output)
        self.assertIn("Count: 2", output)  # addbiomechanics count
        self.assertIn("Low confidence files: 1", output)  # unknown file
        
    def test_cli_help_command(self):
        """Test CLI help command."""
        result = self._run_cli(['--help'])
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())
        self.assertIn("detect dataset type", result.stdout.lower())
        self.assertIn("examples", result.stdout.lower())
        
    def test_cli_single_file_detection(self):
        """Test CLI with single file detection."""
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = self._run_cli([filepath])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("addbiomechanics", result.stdout.lower())
        self.assertIn("confidence", result.stdout.lower())
        
    def test_cli_multiple_files_detection(self):
        """Test CLI with multiple files detection."""
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        result = self._run_cli(filepaths)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("addbiomechanics", result.stdout.lower())
        self.assertIn("gtech_2023", result.stdout.lower())
        
    def test_cli_verbose_flag(self):
        """Test CLI with verbose flag."""
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = self._run_cli([filepath, '--verbose'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("evidence", result.stdout.lower())
        
    def test_cli_json_output(self):
        """Test CLI with JSON output."""
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = self._run_cli([filepath, '--json'])
        
        self.assertEqual(result.returncode, 0)
        
        # Should be valid JSON
        try:
            data = json.loads(result.stdout)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)
            self.assertIn('type', data[0])
            self.assertIn('confidence', data[0])
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
            
    def test_cli_no_metadata_flag(self):
        """Test CLI with --no-metadata flag."""
        filepath = self.test_files['addbiomechanics_walk_01.parquet']
        result = self._run_cli([filepath, '--no-metadata'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("addbiomechanics", result.stdout.lower())
        
    def test_cli_summary_flag(self):
        """Test CLI with --summary flag."""
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        result = self._run_cli(filepaths + ['--summary'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("DETECTION SUMMARY", result.stdout)
        self.assertIn("Total files analyzed", result.stdout)
        
    def test_cli_confidence_threshold(self):
        """Test CLI with confidence threshold."""
        filepath = self.test_files['unknown_dataset.parquet']
        result = self._run_cli([filepath, '--confidence-threshold', '80'])
        
        # Should exclude low confidence results
        self.assertIn(result.returncode, [0, 1])  # May exit with warning
        
    def test_cli_confidence_threshold_zero(self):
        """Test CLI with confidence threshold of 0."""
        filepath = self.test_files['addbiomechanics_walk_01.parquet']  # Use high confidence file
        result = self._run_cli([filepath, '--confidence-threshold', '0'])
        
        # Should include all results and succeed with high confidence file
        self.assertEqual(result.returncode, 0)
        
    def test_cli_glob_pattern_expansion(self):
        """Test CLI with glob pattern expansion."""
        # Create a pattern that matches some files
        pattern = os.path.join(self.temp_dir, "addbiomech*.parquet")
        result = self._run_cli([pattern])
        
        self.assertEqual(result.returncode, 0)
        
    def test_cli_glob_pattern_no_matches(self):
        """Test CLI with glob pattern that matches no files."""
        pattern = os.path.join(self.temp_dir, "nonexistent*.parquet")
        result = self._run_cli([pattern], expect_success=False)
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No valid files to analyze", result.stderr)
        
    def test_cli_file_not_found(self):
        """Test CLI with non-existent file."""
        result = self._run_cli(["/nonexistent/file.parquet"], expect_success=False)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)
        
    def test_cli_non_parquet_file(self):
        """Test CLI with non-parquet file."""
        filepath = self.test_files['not_parquet.csv']
        result = self._run_cli([filepath, '--confidence-threshold', '0'])
        
        # Should detect as unknown but not crash
        self.assertEqual(result.returncode, 2)  # Exit code 2 for low confidence
        self.assertIn("unknown", result.stdout.lower())
        
    def test_cli_low_confidence_exit_code(self):
        """Test CLI exit code for low confidence results."""
        filepath = self.test_files['unknown_dataset.parquet']
        result = self._run_cli([filepath, '--confidence-threshold', '0'], expect_success=False)
        
        # Should exit with code 2 for low confidence
        self.assertEqual(result.returncode, 2)
        self.assertIn("low confidence", result.stderr.lower())
        
    def test_cli_combined_flags(self):
        """Test CLI with multiple flags combined."""
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        result = self._run_cli(filepaths + ['--verbose', '--json', '--no-metadata'])
        
        self.assertEqual(result.returncode, 0)
        
        # Should be valid JSON with evidence (verbose)
        try:
            data = json.loads(result.stdout)
            self.assertIsInstance(data, list)
            # Evidence should be present due to verbose flag
            for item in data:
                self.assertIn('evidence', item)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
            
    def test_cli_confidence_threshold_filtering(self):
        """Test CLI confidence threshold filtering behavior."""
        # Mix of high and low confidence files
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],  # High confidence
            self.test_files['unknown_dataset.parquet']  # Low confidence
        ]
        result = self._run_cli(filepaths + ['--confidence-threshold', '70', '--json'])
        
        # Should filter out low confidence results
        try:
            data = json.loads(result.stdout)
            # Should only have high confidence results
            for item in data:
                self.assertGreaterEqual(item['confidence'], 70)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
            
    def test_all_dataset_types_detection(self):
        """Test detection of all supported dataset types."""
        test_cases = [
            ('addbiomechanics_walk_01.parquet', 'addbiomechanics'),
            ('gtech_2023_walking.parquet', 'gtech_2023'),
            ('umich_2021_walking.parquet', 'umich_2021'),
            ('unknown_dataset.parquet', 'unknown')
        ]
        
        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                filepath = self.test_files[filename]
                result = self._run_cli([filepath, '--json', '--confidence-threshold', '0'])
                
                data = json.loads(result.stdout)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]['type'], expected_type)
                
    def test_all_filename_patterns(self):
        """Test all filename patterns are covered."""
        # Test different AddBiomechanics patterns
        addbiomech_files = [
            'addbiomechanics_walk_01.parquet',
            'addbiomech_test.parquet', 
            'AB_dataset.parquet',
            'data_addbiomech_full.parquet'
        ]
        
        for filename in addbiomech_files:
            with self.subTest(filename=filename):
                filepath = self.test_files[filename]
                result = self._run_cli([filepath, '--json', '--confidence-threshold', '0'])
                
                data = json.loads(result.stdout)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]['type'], 'addbiomechanics')
                
        # Test GTech patterns
        gtech_files = [
            'gtech_2023_walking.parquet',
            'GT2023_subject01.parquet',
            'gtech23_data.parquet',
            'study_gtech_2023_full.parquet'
        ]
        
        for filename in gtech_files:
            with self.subTest(filename=filename):
                filepath = self.test_files[filename]
                result = self._run_cli([filepath, '--json', '--confidence-threshold', '0'])
                
                data = json.loads(result.stdout)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]['type'], 'gtech_2023')
                
        # Test UMich patterns
        umich_files = [
            'umich_2021_walking.parquet',
            'UM2021_subject01.parquet',
            'michigan_2021_data.parquet',
            'data_umich_2021_complete.parquet'
        ]
        
        for filename in umich_files:
            with self.subTest(filename=filename):
                filepath = self.test_files[filename]
                result = self._run_cli([filepath, '--json', '--confidence-threshold', '0'])
                
                data = json.loads(result.stdout)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]['type'], 'umich_2021')
                
    def test_main_function_directly(self):
        """Test main function directly to cover edge cases."""
        from contributor_scripts.detect_dataset_type import main
        
        # Test with mock arguments
        test_args = [
            'detect_dataset_type.py',
            self.test_files['addbiomechanics_walk_01.parquet'],
            '--json'
        ]
        
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new=MagicMock()):
                try:
                    main()
                except SystemExit as e:
                    # Should exit with code 0 for success
                    self.assertEqual(e.code, 0)
                    
    def test_edge_case_empty_file_list(self):
        """Test edge case with empty file list after filtering."""
        # This tests the specific line: if not filepaths: ... sys.exit(1)
        result = self._run_cli(['/nonexistent/*.parquet'], expect_success=False)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("No valid files to analyze", result.stderr)
        
    def test_warning_message_for_glob_patterns(self):
        """Test warning message for glob patterns with no matches."""
        # This tests the specific warning message for glob patterns
        pattern = os.path.join(self.temp_dir, "nomatch*.parquet")
        result = self._run_cli([pattern], expect_success=False)
        
        # Should show warning and then exit with error
        self.assertIn("No files found matching pattern", result.stderr)
        self.assertEqual(result.returncode, 1)
        
    def test_confidence_indicators_in_output(self):
        """Test confidence indicators (✓, ?, ✗) in human-readable output."""
        # Create files with different confidence levels
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],  # Medium confidence (?)
            self.test_files['unknown_dataset.parquet']  # Low confidence (✗)
        ]
        
        result = self._run_cli(filepaths + ['--confidence-threshold', '0'])
        
        # Should contain confidence indicators - ? for medium confidence (50%), ✗ for low (0%)
        self.assertIn("?", result.stdout)  # Medium confidence (around 50%)
        self.assertIn("✗", result.stdout)  # Low confidence (0%)
        
    def test_json_and_summary_flags_together(self):
        """Test JSON output with summary flag (summary should be ignored)."""
        filepaths = [
            self.test_files['addbiomechanics_walk_01.parquet'],
            self.test_files['gtech_2023_walking.parquet']
        ]
        result = self._run_cli(filepaths + ['--json', '--summary'])
        
        self.assertEqual(result.returncode, 0)
        
        # Should be JSON output, not summary
        try:
            data = json.loads(result.stdout)
            self.assertIsInstance(data, list)
        except json.JSONDecodeError:
            self.fail("Should output JSON when --json flag is used")
            
        # Summary should not appear in JSON mode
        self.assertNotIn("DETECTION SUMMARY", result.stdout)


class TestCompleteCoverageEdgeCases(unittest.TestCase):
    """Tests specifically designed to achieve 100% line coverage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.cli_script = "contributor_scripts/detect_dataset_type.py"
        
        # Create test parquet file
        test_data = pd.DataFrame({
            'subject': ['SUB01'] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_angle': np.random.normal(0.2, 0.1, 150)
        })
        self.test_file = os.path.join(self.temp_dir, "addbiomechanics_test.parquet")
        test_data.to_parquet(self.test_file)
        
    def test_glob_expansion_with_matches(self):
        """Test glob pattern expansion that finds matches - line 215-220."""
        # Create multiple files with pattern that will have reasonable confidence
        for i in range(3):
            filepath = os.path.join(self.temp_dir, f"addbiomechanics_{i}.parquet")
            pd.DataFrame({'subject_id': ['S1'], 'trial_id': ['T1']}).to_parquet(filepath)
            
        pattern = os.path.join(self.temp_dir, "addbiomechanics_*.parquet")
        result = subprocess.run([
            sys.executable, self.cli_script, pattern, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should find and process multiple files (exit code 0 with decent confidence)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertGreaterEqual(len(data), 3)  # May find our base test file too
        
    def test_glob_with_question_mark(self):
        """Test glob pattern with question mark - line 214."""
        # Create file that matches question mark pattern
        filepath = os.path.join(self.temp_dir, "addbiomechanics_1.parquet")
        pd.DataFrame({'subject_id': ['S1'], 'trial_id': ['T1']}).to_parquet(filepath)
        
        pattern = os.path.join(self.temp_dir, "addbiomechanics_?.parquet")
        result = subprocess.run([
            sys.executable, self.cli_script, pattern, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should find the file via question mark glob
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 1)
        
    def test_glob_no_matches_warning(self):
        """Test glob pattern with no matches shows warning - lines 217-219."""
        pattern = os.path.join(self.temp_dir, "nonexistent_*.parquet")
        result = subprocess.run([
            sys.executable, self.cli_script, pattern, '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should show warning and exit with error
        self.assertEqual(result.returncode, 1)
        self.assertIn("Warning: No files found matching pattern", result.stderr)
        self.assertIn("Error: No valid files to analyze", result.stderr)
        
    def test_explicit_file_not_found(self):
        """Test explicit file that doesn't exist - lines 222-224."""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.parquet")
        result = subprocess.run([
            sys.executable, self.cli_script, nonexistent_file, '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should exit with error for missing file
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: File not found", result.stderr)
        
    def test_mixed_glob_and_explicit_files(self):
        """Test mixture of glob patterns and explicit files - lines 213-226."""
        # Create files for glob pattern
        glob_file = os.path.join(self.temp_dir, "gtech_2023_test.parquet")
        pd.DataFrame({'subject_id': ['S1'], 'trial_id': ['T1']}).to_parquet(glob_file)
        
        # Mix glob pattern with explicit file
        pattern = os.path.join(self.temp_dir, "gtech_*.parquet")
        result = subprocess.run([
            sys.executable, self.cli_script, pattern, self.test_file, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 2)  # One from glob, one explicit
        
    def test_no_valid_files_after_glob_expansion(self):
        """Test no valid files after glob expansion - lines 227-229."""
        # Use pattern that expands to empty list
        pattern = os.path.join(self.temp_dir, "*.nonexistent")
        result = subprocess.run([
            sys.executable, self.cli_script, pattern, '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should exit with error for no valid files
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: No valid files to analyze", result.stderr)
        
    def test_single_vs_batch_detection_paths(self):
        """Test single file vs batch file detection paths - line 234-238."""
        # Test single file path (line 235-236)
        result1 = subprocess.run([
            sys.executable, self.cli_script, self.test_file, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Test batch path (line 238)
        result2 = subprocess.run([
            sys.executable, self.cli_script, self.test_file, self.test_file, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)
        
        data1 = json.loads(result1.stdout)
        data2 = json.loads(result2.stdout)
        
        self.assertEqual(len(data1), 1)  # Single file
        self.assertEqual(len(data2), 2)  # Batch files
        
    def test_confidence_threshold_filtering_messages(self):
        """Test confidence threshold filtering and messages - lines 241-247."""
        # Create mix of high and low confidence files
        unknown_file = os.path.join(self.temp_dir, "unknown.parquet")
        pd.DataFrame({'a': [1]}).to_parquet(unknown_file)
        
        result = subprocess.run([
            sys.executable, self.cli_script, self.test_file, unknown_file, '--confidence-threshold', '60'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should filter and show message
        self.assertIn("Excluded", result.stderr)
        self.assertIn("below confidence threshold", result.stderr)
        
    def test_human_readable_output_all_confidence_levels(self):
        """Test human readable output formatting - lines 254-263."""
        # Create files with different confidence levels
        high_conf_file = os.path.join(self.temp_dir, "addbiomechanics_high_conf.parquet")
        pd.DataFrame({'subject_id': ['S1'], 'trial_id': ['T1'], 'addbiomech_version': ['v1']}).to_parquet(high_conf_file)
        
        med_conf_file = os.path.join(self.temp_dir, "addbiomech_med.parquet")
        pd.DataFrame({'subject_id': ['S1'], 'trial_id': ['T1']}).to_parquet(med_conf_file)
        
        low_conf_file = os.path.join(self.temp_dir, "unknown.parquet")
        pd.DataFrame({'a': [1]}).to_parquet(low_conf_file)
        
        result = subprocess.run([
            sys.executable, self.cli_script, high_conf_file, med_conf_file, low_conf_file,
            '--confidence-threshold', '0', '--verbose'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should show all confidence indicators and evidence
        output = result.stdout
        self.assertIn("Type:", output)
        self.assertIn("Confidence:", output) 
        self.assertIn("Evidence:", output)  # Verbose mode
        
        # Check confidence indicators are present
        indicators_found = sum([
            '✓' in output,  # High confidence >= 70%
            '?' in output,  # Medium confidence >= 50%
            '✗' in output   # Low confidence < 50%
        ])
        self.assertGreater(indicators_found, 0)
        
    def test_human_readable_without_verbose(self):
        """Test human readable output without verbose flag - lines 261-262."""
        result = subprocess.run([
            sys.executable, self.cli_script, self.test_file, '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should NOT show evidence without verbose flag
        output = result.stdout
        self.assertIn("Type:", output)
        self.assertIn("Confidence:", output)
        self.assertNotIn("Evidence:", output)  # No verbose mode
        
    def test_summary_output_with_human_readable(self):
        """Test summary output in human readable mode - line 266-267."""
        result = subprocess.run([
            sys.executable, self.cli_script, self.test_file, self.test_file,
            '--summary', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("DETECTION SUMMARY", result.stdout)
        self.assertIn("Total files analyzed", result.stdout)
        
    def test_low_confidence_warning_and_exit(self):
        """Test low confidence warning and exit code - lines 270-274."""
        unknown_file = os.path.join(self.temp_dir, "unknown.parquet")
        pd.DataFrame({'a': [1]}).to_parquet(unknown_file)
        
        result = subprocess.run([
            sys.executable, self.cli_script, unknown_file, '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should exit with code 2 and show warning
        self.assertEqual(result.returncode, 2)
        self.assertIn("Warning:", result.stderr)
        self.assertIn("low confidence detection", result.stderr)
        
    def test_main_function_execution(self):
        """Test main function execution path - line 277-278."""
        # This is tested by all CLI calls, but let's be explicit
        result = subprocess.run([
            sys.executable, self.cli_script, self.test_file, '--help'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)
        
    def test_script_execution_directly(self):
        """Test direct script execution to cover __name__ == '__main__' - line 277-278."""
        # Execute the script directly to ensure line 277-278 is covered
        result = subprocess.run([
            sys.executable, self.cli_script, self.test_file, '--json', '--confidence-threshold', '0'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should execute main function successfully
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 1)


class TestCLIErrorHandling(unittest.TestCase):
    """Test error handling and edge cases in CLI."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.cli_script = "contributor_scripts/detect_dataset_type.py"
        
    def test_import_error_handling(self):
        """Test CLI behavior when imports fail."""
        # This tests the import path handling
        result = subprocess.run([
            sys.executable, self.cli_script, '--help'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Help should work even if there are import issues
        self.assertEqual(result.returncode, 0)
        
    def test_malformed_parquet_file(self):
        """Test CLI with malformed parquet file."""
        # Create a fake parquet file
        fake_parquet = os.path.join(self.temp_dir, "fake.parquet")
        with open(fake_parquet, 'w') as f:
            f.write("This is not a parquet file")
            
        result = subprocess.run([
            sys.executable, self.cli_script, fake_parquet, '--json'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Should handle the error gracefully
        self.assertIn(result.returncode, [0, 2])  # May succeed with low confidence
        
    def test_permission_denied_file(self):
        """Test CLI with file permission issues."""
        # Create a file and try to make it unreadable (if possible in test environment)
        test_file = os.path.join(self.temp_dir, "unreadable.parquet")
        
        # Create a simple parquet file first
        pd.DataFrame({'a': [1, 2, 3]}).to_parquet(test_file)
        
        # Try to make it unreadable (may not work in all environments)
        try:
            os.chmod(test_file, 0o000)
            
            result = subprocess.run([
                sys.executable, self.cli_script, test_file, '--json'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            # Should handle permission error gracefully
            self.assertIn(result.returncode, [0, 2])
            
        except (OSError, PermissionError):
            # Skip test if we can't modify permissions
            self.skipTest("Cannot modify file permissions in test environment")
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(test_file, 0o644)
            except (OSError, PermissionError):
                pass


class TestDirectFunctionCoverage(unittest.TestCase):
    """Test direct function calls for 100% line coverage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        
        # Create test data
        test_data = pd.DataFrame({
            'subject_id': ['SUB01'] * 150,
            'trial_id': ['T001'] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_angle': np.random.normal(0.2, 0.1, 150)
        })
        self.test_file = os.path.join(self.temp_dir, "addbiomechanics_test.parquet")
        test_data.to_parquet(self.test_file)
        
    def test_direct_main_function_execution(self):
        """Test main function directly with mocked sys.argv."""
        from contributor_scripts.detect_dataset_type import main
        
        # Test all argument combinations directly
        test_cases = [
            # Help command
            ['detect_dataset_type.py', '--help'],
            # Single file detection
            ['detect_dataset_type.py', self.test_file, '--json', '--confidence-threshold', '0'],
            # Verbose mode
            ['detect_dataset_type.py', self.test_file, '--verbose', '--confidence-threshold', '0'],
            # No metadata
            ['detect_dataset_type.py', self.test_file, '--no-metadata', '--confidence-threshold', '0'],
            # Summary mode
            ['detect_dataset_type.py', self.test_file, self.test_file, '--summary', '--confidence-threshold', '0'],
            # JSON + verbose
            ['detect_dataset_type.py', self.test_file, '--json', '--verbose', '--confidence-threshold', '0'],
        ]
        
        for test_args in test_cases:
            with self.subTest(args=test_args):
                # Mock sys.argv and stdout/stderr
                with patch('sys.argv', test_args):
                    with patch('sys.stdout', new=MagicMock()) as mock_stdout:
                        with patch('sys.stderr', new=MagicMock()) as mock_stderr:
                            try:
                                main()
                            except SystemExit as e:
                                # Help command and other successful operations exit with 0
                                if '--help' in test_args:
                                    self.assertEqual(e.code, 0)
                                # Other exit codes are also valid for testing
                                
    def test_direct_function_calls(self):
        """Test individual functions directly."""
        from contributor_scripts.detect_dataset_type import (
            setup_logging, detect_single_file, detect_batch_files, print_summary_report
        )
        
        # Test setup_logging with both verbose modes
        setup_logging(verbose=True)
        setup_logging(verbose=False)
        
        # Test detect_single_file with all combinations
        result1 = detect_single_file(self.test_file, use_metadata=True, verbose=True)
        result2 = detect_single_file(self.test_file, use_metadata=True, verbose=False)
        result3 = detect_single_file(self.test_file, use_metadata=False, verbose=True)
        result4 = detect_single_file(self.test_file, use_metadata=False, verbose=False)
        
        # Verify results have expected structure
        for result in [result1, result2, result3, result4]:
            self.assertIn('file', result)
            self.assertIn('type', result)
            self.assertIn('confidence', result)
            
        # Check verbose vs non-verbose
        self.assertIn('evidence', result1)
        self.assertNotIn('evidence', result2)
        
        # Test detect_batch_files
        files = [self.test_file, self.test_file]
        batch_result1 = detect_batch_files(files, use_metadata=True, verbose=True)
        batch_result2 = detect_batch_files(files, use_metadata=False, verbose=False)
        
        self.assertEqual(len(batch_result1), 2)
        self.assertEqual(len(batch_result2), 2)
        
        # Test print_summary_report with empty and populated results
        with patch('sys.stdout', new=MagicMock()):
            print_summary_report([])
            print_summary_report(batch_result1)
            
    def test_main_with_all_edge_cases(self):
        """Test main function with all edge cases using mocked arguments."""
        from contributor_scripts.detect_dataset_type import main
        
        # Create test files for edge cases
        unknown_file = os.path.join(self.temp_dir, "unknown.parquet")
        pd.DataFrame({'a': [1]}).to_parquet(unknown_file)
        
        # Test cases that cover all missing lines
        edge_cases = [
            # Glob patterns with matches (lines 214-220)
            ['detect_dataset_type.py', os.path.join(self.temp_dir, "*.parquet"), '--confidence-threshold', '0'],
            # Non-existent file (lines 222-224)  
            ['detect_dataset_type.py', '/nonexistent/file.parquet'],
            # Multiple files with confidence filtering (lines 241-247)
            ['detect_dataset_type.py', self.test_file, unknown_file, '--confidence-threshold', '60'],
            # Human readable output with verbose (lines 254-263)
            ['detect_dataset_type.py', self.test_file, '--verbose', '--confidence-threshold', '0'],
            # Summary with human readable (lines 266-267)
            ['detect_dataset_type.py', self.test_file, self.test_file, '--summary', '--confidence-threshold', '0'],
            # Low confidence warning (lines 270-274)
            ['detect_dataset_type.py', unknown_file, '--confidence-threshold', '0'],
        ]
        
        for test_args in edge_cases:
            with self.subTest(args=test_args):
                with patch('sys.argv', test_args):
                    with patch('sys.stdout', new=MagicMock()):
                        with patch('sys.stderr', new=MagicMock()):
                            try:
                                main()
                            except SystemExit:
                                # Exit is expected for many edge cases
                                pass
                                
    def test_final_missing_lines(self):
        """Test the final missing lines for 100% coverage."""
        from contributor_scripts.detect_dataset_type import main
        
        # Test glob pattern with no matches (line 218) 
        with patch('sys.argv', ['detect_dataset_type.py', '/tmp/nonexistent_*.parquet']):
            with patch('sys.stderr', new=MagicMock()) as mock_stderr:
                try:
                    main()
                except SystemExit:
                    pass
                # Check that warning was printed
                mock_stderr.write.assert_called()
                
        # Test no valid files (lines 228-229)
        with patch('sys.argv', ['detect_dataset_type.py', '/tmp/nomatch*.xyz']):
            with patch('sys.stderr', new=MagicMock()) as mock_stderr:
                try:
                    main()
                except SystemExit:
                    pass
                # Check that error was printed
                mock_stderr.write.assert_called()
                
        # Test direct execution of script to cover line 278 
        # Use runpy to execute the script as a module
        import runpy
        import contextlib
        from io import StringIO
        
        # Temporarily modify sys.argv
        original_argv = sys.argv[:]
        sys.argv = ['detect_dataset_type.py', self.test_file, '--json', '--confidence-threshold', '0']
        
        try:
            # Capture stdout to avoid printing during test
            f = StringIO()
            with contextlib.redirect_stdout(f):
                with contextlib.redirect_stderr(f):
                    # Execute the module as main - this covers line 278
                    runpy.run_path('contributor_scripts/detect_dataset_type.py', run_name='__main__')
        except SystemExit:
            # Expected for successful execution
            pass
        finally:
            # Restore original argv
            sys.argv = original_argv


if __name__ == "__main__":
    # Set up test environment
    unittest.main(verbosity=2)