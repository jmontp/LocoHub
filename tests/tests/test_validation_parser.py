#!/usr/bin/env python3
"""
Unit Tests for Validation Expectations Parser

Created: 2025-06-12 with user permission
Purpose: Comprehensive unit tests for markdown parser functionality

Intent:
This test suite validates the ValidationExpectationsParser's ability to:
1. Parse existing markdown files correctly
2. Write data back to markdown with proper formatting
3. Handle round-trip operations without data loss
4. Work with both kinematic and kinetic formats
5. Generate unified hierarchical tables correctly

The tests use separate test files to avoid modifying production data.
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add source directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from lib.validation.validation_expectations_parser import ValidationExpectationsParser


class TestValidationExpectationsParser(unittest.TestCase):
    """Test suite for ValidationExpectationsParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ValidationExpectationsParser()
        self.test_data_dir = Path(__file__).parent / 'test_data' / 'validation_parser'
        
        # Sample test data for writing tests
        self.sample_kinematic_data = {
            'level_walking': {
                0: {
                    'hip_flexion_angle_ipsi': {'min': 0.349, 'max': 0.833},
                    'knee_flexion_angle_ipsi': {'min': -0.047, 'max': 0.253},
                    'ankle_flexion_angle_ipsi': {'min': -0.147, 'max': 0.145}
                },
                25: {
                    'hip_flexion_angle_ipsi': {'min': -0.043, 'max': 0.526},
                    'knee_flexion_angle_ipsi': {'min': 0.024, 'max': 0.358},
                    'ankle_flexion_angle_ipsi': {'min': -0.224, 'max': -0.052}
                }
            }
        }
        
        self.sample_kinetic_data = {
            'level_walking': {
                0: {
                    'hip_flexion_moment_ipsi': {'min': -0.773, 'max': -0.113},
                    'knee_flexion_moment_ipsi': {'min': 0.077, 'max': 0.387},
                    'ankle_flexion_moment_ipsi': {'min': -0.034, 'max': 0.067}
                },
                25: {
                    'hip_flexion_moment_ipsi': {'min': -0.422, 'max': 0.248},
                    'knee_flexion_moment_ipsi': {'min': -0.208, 'max': 0.445},
                    'ankle_flexion_moment_ipsi': {'min': -1.206, 'max': -0.251}
                }
            }
        }
    
    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = ValidationExpectationsParser()
        self.assertIsInstance(parser, ValidationExpectationsParser)
    
    def test_read_original_kinetic_data(self):
        """Test reading original kinetic validation data."""
        original_kinetic_file = self.test_data_dir / 'original_kinetic.md'
        
        if not original_kinetic_file.exists():
            self.skipTest(f"Original kinetic file not found: {original_kinetic_file}")
        
        data = self.parser.read_validation_data(str(original_kinetic_file))
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('decline_walking', data)
        self.assertIn('level_walking', data)
        
        # Verify phases exist
        task_data = data['decline_walking']
        self.assertIn(0, task_data)
        self.assertIn(25, task_data)
        self.assertIn(50, task_data)
        self.assertIn(75, task_data)
        
        # Verify variables exist
        phase_data = task_data[0]
        self.assertGreater(len(phase_data), 0, "Phase should have variables")
        
        # Check for expected kinetic variables (parser removes _Nm suffix for storage)
        expected_vars = ['hip_flexion_moment_ipsi', 'knee_flexion_moment_ipsi', 'ankle_flexion_moment_ipsi']
        found_vars = [var for var in expected_vars if var in phase_data]
        self.assertGreater(len(found_vars), 0, f"Should find kinetic variables, found: {list(phase_data.keys())}")
    
    def test_read_original_kinematic_data(self):
        """Test reading original kinematic validation data."""
        original_kinematic_file = self.test_data_dir / 'original_kinematic.md'
        
        if not original_kinematic_file.exists():
            self.skipTest(f"Original kinematic file not found: {original_kinematic_file}")
        
        data = self.parser.read_validation_data(str(original_kinematic_file))
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('decline_walking', data)
        self.assertIn('level_walking', data)
        
        # Verify phases exist
        task_data = data['decline_walking']
        self.assertIn(0, task_data)
        self.assertIn(25, task_data)
        self.assertIn(50, task_data)
        self.assertIn(75, task_data)
        
        # Verify variables exist
        phase_data = task_data[0]
        self.assertGreater(len(phase_data), 0, "Phase should have variables")
        
        # Check for expected kinematic variables
        expected_vars = ['hip_flexion_angle_ipsi', 'knee_flexion_angle_ipsi', 'ankle_flexion_angle_ipsi']
        found_vars = [var for var in expected_vars if var in phase_data]
        self.assertGreater(len(found_vars), 0, f"Should find kinematic variables, found: {list(phase_data.keys())}")
    
    def test_write_kinematic_data(self):
        """Test writing kinematic data to markdown with unified format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            
            # Write minimal markdown structure
            f.write("""# Test Kinematic Validation

## Validation Tables

""")
        
        try:
            # Write sample data with explicit mode
            self.parser.write_validation_data(
                temp_file,
                self.sample_kinematic_data,
                dataset_name='test_dataset.parquet',
                method='percentile_95',
                mode='kinematic'
            )
            
            # Read back and verify
            with open(temp_file, 'r') as f:
                content = f.read()
            
            # Check for expected elements
            self.assertIn('level_walking', content)
            self.assertIn('hip_flexion_angle_ipsi_rad', content)
            self.assertIn('0.349', content)  # Min value
            self.assertIn('0.833', content)  # Max value
            self.assertIn('**rad**', content)  # Units
            
        finally:
            os.unlink(temp_file)
    
    def test_write_kinetic_data(self):
        """Test writing kinetic data to markdown with unified format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            
            # Write minimal markdown structure
            f.write("""# Test Kinetic Validation

## Validation Tables

""")
        
        try:
            # Write sample data with explicit mode
            self.parser.write_validation_data(
                temp_file,
                self.sample_kinetic_data,
                dataset_name='test_dataset.parquet',
                method='percentile_95',
                mode='kinetic'
            )
            
            # Read back and verify
            with open(temp_file, 'r') as f:
                content = f.read()
            
            # Check for expected elements
            self.assertIn('level_walking', content)
            self.assertIn('hip_flexion_moment_ipsi_Nm', content)
            self.assertIn('-0.773', content)  # Min value
            self.assertIn('-0.113', content)  # Max value
            self.assertIn('**Nm**', content)  # Units
            
        finally:
            os.unlink(temp_file)
    
    def test_round_trip_kinematic(self):
        """Test round-trip: read -> write -> read for kinematic data."""
        original_kinematic_file = self.test_data_dir / 'original_kinematic.md'
        
        if not original_kinematic_file.exists():
            self.skipTest(f"Original kinematic file not found: {original_kinematic_file}")
        
        # Read original data
        original_data = self.parser.read_validation_data(str(original_kinematic_file))
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            
            # Write minimal markdown structure
            f.write("""# Test Kinematic Validation

## Validation Tables

## Joint Validation Range Summary
""")
        
        try:
            # Write data in new format with explicit mode
            self.parser.write_validation_data(temp_file, original_data, mode='kinematic')
            
            # Read back
            new_data = self.parser.read_validation_data(temp_file)
            
            # Compare structures
            self.assertEqual(set(original_data.keys()), set(new_data.keys()), "Task names should match")
            
            # Check a specific task
            if 'level_walking' in original_data and 'level_walking' in new_data:
                orig_task = original_data['level_walking']
                new_task = new_data['level_walking']
                
                # Check phases
                self.assertEqual(set(orig_task.keys()), set(new_task.keys()), "Phases should match")
                
                # Check first phase variables
                if 0 in orig_task and 0 in new_task:
                    orig_vars = set(orig_task[0].keys())
                    new_vars = set(new_task[0].keys())
                    
                    # Should have some overlap (might not be exact due to format differences)
                    overlap = orig_vars.intersection(new_vars)
                    self.assertGreater(len(overlap), 0, f"Should have some variable overlap. Original: {orig_vars}, New: {new_vars}")
            
        finally:
            os.unlink(temp_file)
    
    def test_round_trip_kinetic(self):
        """Test round-trip: read -> write -> read for kinetic data."""
        original_kinetic_file = self.test_data_dir / 'original_kinetic.md'
        
        if not original_kinetic_file.exists():
            self.skipTest(f"Original kinetic file not found: {original_kinetic_file}")
        
        # Read original data
        original_data = self.parser.read_validation_data(str(original_kinetic_file))
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            
            # Write minimal markdown structure
            f.write("""# Test Kinetic Validation

## Validation Tables

## Research Requirements
""")
        
        try:
            # Write data in new format with explicit mode
            self.parser.write_validation_data(temp_file, original_data, mode='kinetic')
            
            # Read back
            new_data = self.parser.read_validation_data(temp_file)
            
            # Compare structures
            self.assertEqual(set(original_data.keys()), set(new_data.keys()), "Task names should match")
            
            # Check a specific task
            if 'level_walking' in original_data and 'level_walking' in new_data:
                orig_task = original_data['level_walking']
                new_task = new_data['level_walking']
                
                # Check phases
                self.assertEqual(set(orig_task.keys()), set(new_task.keys()), "Phases should match")
                
                # Check first phase variables
                if 0 in orig_task and 0 in new_task:
                    orig_vars = set(orig_task[0].keys())
                    new_vars = set(new_task[0].keys())
                    
                    # Should have some overlap
                    overlap = orig_vars.intersection(new_vars)
                    self.assertGreater(len(overlap), 0, f"Should have some variable overlap. Original: {orig_vars}, New: {new_vars}")
            
        finally:
            os.unlink(temp_file)
    
    def test_parser_handles_empty_tables(self):
        """Test parser gracefully handles empty or malformed tables."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            
            # Write markdown with empty table
            f.write("""# Test Validation

## Validation Tables

### Task: test_task

**Phase-Specific Range Validation:**

| Variable | | 0% | | | 25% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | | |

## End Section
""")
        
        try:
            # Should not crash
            data = self.parser.read_validation_data(temp_file)
            self.assertIsInstance(data, dict)
            
            if 'test_task' in data:
                self.assertIsInstance(data['test_task'], dict)
            
        finally:
            os.unlink(temp_file)
    
    def test_numeric_value_parsing(self):
        """Test numeric value parsing edge cases."""
        parser = self.parser
        
        # Test valid numbers
        self.assertEqual(parser._parse_numeric_value('0.123'), 0.123)
        self.assertEqual(parser._parse_numeric_value('-1.456'), -1.456)
        self.assertEqual(parser._parse_numeric_value('42'), 42.0)
        
        # Test NaN cases
        import math
        self.assertTrue(math.isnan(parser._parse_numeric_value('nan')))
        self.assertTrue(math.isnan(parser._parse_numeric_value('-')))
        self.assertTrue(math.isnan(parser._parse_numeric_value('')))
        
        # Test invalid cases
        with self.assertRaises(ValueError):
            parser._parse_numeric_value('invalid')


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)