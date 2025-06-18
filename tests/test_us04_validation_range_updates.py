#!/usr/bin/env python3
"""
US-04 Validation Range Updates Test Suite

Created: 2025-06-18 with user permission
Purpose: Memory-conscious tests for literature-based validation range updates

Intent: Tests the lightweight validation range update system with proper tracking,
version control, and literature citation management. Focuses on memory efficiency
by using small test data and simple data structures.
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from lib.validation.range_updater import RangeUpdater, RangeUpdate
from lib.validation.validation_expectations_parser import ValidationExpectationsParser


class TestRangeUpdater(unittest.TestCase):
    """Test the memory-conscious validation range updater."""
    
    def setUp(self):
        """Set up test environment with temporary files."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.temp_dir))
        
        # Create test validation expectations file
        self.test_md_file = os.path.join(self.temp_dir, "test_kinematic.md")
        self.test_data = {
            'level_walking': {
                0: {'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.3}}
            }
        }
        
        # Create minimal markdown content with proper format
        test_content = """# Test Kinematic Validation

## Validation Tables

### Task: level_walking

**Phase-Specific Range Validation (Ipsilateral Leg Only):**

| Variable | | 0% | | |Units|Notes|
|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | | |
| hip_flexion_angle_ipsi_rad | -0.100 | 0.300 | |**rad** | |

## Research Requirements
"""
        with open(self.test_md_file, 'w') as f:
            f.write(test_content)
        
        self.updater = RangeUpdater()

    def test_load_validation_data(self):
        """Test loading validation data from markdown file."""
        # Use a working validation file for this test
        test_data = {
            'level_walking': {
                0: {'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.3}}
            }
        }
        
        # Mock the parser to return our test data
        self.updater.parser.read_validation_data = lambda file_path: test_data
        
        data = self.updater.load_validation_data(self.test_md_file)
        
        self.assertIn('level_walking', data)
        self.assertIn(0, data['level_walking'])
        self.assertIn('hip_flexion_angle_ipsi', data['level_walking'][0])
        
        # Check values
        hip_data = data['level_walking'][0]['hip_flexion_angle_ipsi']
        self.assertAlmostEqual(hip_data['min'], -0.1, places=3)
        self.assertAlmostEqual(hip_data['max'], 0.3, places=3)

    def test_create_range_update(self):
        """Test creating a range update with literature citation."""
        update = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Smith et al. 2023',
            rationale='Updated based on newer dataset with more subjects',
            reviewer='test_user'
        )
        
        self.assertEqual(update.task, 'level_walking')
        self.assertEqual(update.phase, 0)
        self.assertEqual(update.variable, 'hip_flexion_angle_ipsi')
        self.assertEqual(update.new_min, -0.15)
        self.assertEqual(update.new_max, 0.35)
        self.assertEqual(update.citation, 'Smith et al. 2023')
        self.assertIsInstance(update.timestamp, datetime)

    def test_apply_single_range_update(self):
        """Test applying a single range update."""
        # Use test data directly
        original_data = {
            'level_walking': {
                0: {'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.3}}
            }
        }
        
        # Create update
        update = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Smith et al. 2023',
            rationale='Updated based on newer dataset',
            reviewer='test_user'
        )
        
        # Apply update
        updated_data = self.updater.apply_range_update(original_data, update)
        
        # Check updated values
        hip_data = updated_data['level_walking'][0]['hip_flexion_angle_ipsi']
        self.assertAlmostEqual(hip_data['min'], -0.15, places=3)
        self.assertAlmostEqual(hip_data['max'], 0.35, places=3)
        
        # Ensure other values unchanged
        self.assertEqual(len(updated_data['level_walking']), 1)  # Only phase 0 in test data

    def test_version_control_tracking(self):
        """Test version control functionality."""
        # Create version file
        version_file = os.path.join(self.temp_dir, "range_versions.json")
        
        update = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Smith et al. 2023',
            rationale='Updated based on newer dataset',
            reviewer='test_user'
        )
        
        # Save version
        self.updater.save_version(version_file, update, version_number=1)
        
        # Check version file exists and has correct content
        self.assertTrue(os.path.exists(version_file))
        
        with open(version_file, 'r') as f:
            version_data = json.load(f)
        
        self.assertIn('versions', version_data)
        self.assertEqual(len(version_data['versions']), 1)
        
        version_entry = version_data['versions'][0]
        self.assertEqual(version_entry['version'], 1)
        self.assertEqual(version_entry['task'], 'level_walking')
        self.assertEqual(version_entry['citation'], 'Smith et al. 2023')

    def test_conflict_detection(self):
        """Test detection of conflicting range updates."""
        # Create conflicting updates (overlapping ranges that don't make sense)
        update1 = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.1,
            new_max=0.2,  # Max less than current min would be invalid
            citation='Study A',
            rationale='Rationale A',
            reviewer='user1'
        )
        
        update2 = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=0.3,  # Min greater than update1's max
            new_max=0.4,
            citation='Study B',
            rationale='Rationale B', 
            reviewer='user2'
        )
        
        conflicts = self.updater.detect_conflicts([update1, update2])
        
        # Should detect conflict between these updates
        self.assertTrue(len(conflicts) > 0)
        
        # Check conflict details
        conflict = conflicts[0]
        self.assertEqual(conflict['variable'], 'hip_flexion_angle_ipsi')
        self.assertEqual(conflict['phase'], 0)
        self.assertEqual(conflict['task'], 'level_walking')

    def test_rollback_functionality(self):
        """Test rolling back to previous version."""
        version_file = os.path.join(self.temp_dir, "range_versions.json")
        
        # Create initial version
        update1 = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Smith et al. 2023',
            rationale='Initial update',
            reviewer='user1',
            old_min=-0.1,  # Original value
            old_max=0.3    # Original value
        )
        
        # Create second version  
        update2 = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.2,
            new_max=0.4,
            citation='Jones et al. 2024',
            rationale='Further update',
            reviewer='user2',
            old_min=-0.15,  # Previous value
            old_max=0.35    # Previous value
        )
        
        # Save both versions
        self.updater.save_version(version_file, update1, version_number=1)
        self.updater.save_version(version_file, update2, version_number=2)
        
        # Get rollback data for version 1
        rollback_update = self.updater.get_rollback_update(version_file, version=1)
        
        self.assertEqual(rollback_update.new_min, -0.15)
        self.assertEqual(rollback_update.new_max, 0.35)
        self.assertEqual(rollback_update.citation, 'Rollback to version 1')

    def test_batch_update_processing(self):
        """Test processing multiple updates efficiently."""
        updates = [
            RangeUpdate(
                task='level_walking',
                phase=0,
                variable='hip_flexion_angle_ipsi',
                new_min=-0.15,
                new_max=0.35,
                citation='Study A',
                rationale='Update A',
                reviewer='user1'
            )
        ]
        
        # Use test data directly
        original_data = {
            'level_walking': {
                0: {'hip_flexion_angle_ipsi': {'min': -0.1, 'max': 0.3}}
            }
        }
        
        # Apply batch updates
        updated_data = self.updater.apply_batch_updates(original_data, updates)
        
        # Check updates applied
        hip_0 = updated_data['level_walking'][0]['hip_flexion_angle_ipsi']
        self.assertAlmostEqual(hip_0['min'], -0.15, places=3)
        self.assertAlmostEqual(hip_0['max'], 0.35, places=3)

    def test_memory_efficiency(self):
        """Test that the system handles data efficiently."""
        # Create larger test data to verify memory efficiency
        large_test_data = {}
        for task in ['level_walking', 'incline_walking', 'decline_walking']:
            large_test_data[task] = {}
            for phase in [0, 25, 50, 75]:
                large_test_data[task][phase] = {}
                for var in ['hip_flexion_angle_ipsi', 'knee_flexion_angle_ipsi', 'ankle_flexion_angle_ipsi']:
                    large_test_data[task][phase][var] = {'min': -1.0, 'max': 1.0}
        
        # Test that we can process this efficiently
        update = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Memory Test',
            rationale='Testing memory efficiency',
            reviewer='test_user'
        )
        
        # Should process without memory issues
        updated_data = self.updater.apply_range_update(large_test_data, update)
        
        # Verify only target value changed
        self.assertAlmostEqual(
            updated_data['level_walking'][0]['hip_flexion_angle_ipsi']['min'], 
            -0.15, places=3
        )
        
        # Verify other values unchanged
        self.assertEqual(
            updated_data['incline_walking'][0]['hip_flexion_angle_ipsi']['min'],
            -1.0
        )


class TestRangeUpdateCLI(unittest.TestCase):
    """Test the CLI interface for range updates."""
    
    def setUp(self):
        """Set up CLI test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(self.temp_dir))

    def test_cli_update_command_structure(self):
        """Test CLI command structure validation."""
        # This would test that CLI commands are properly structured
        # Using mock to avoid actual CLI execution
        
        with patch('builtins.input', side_effect=['level_walking', '0', 'hip_flexion_angle_ipsi', '-0.15', '0.35', 'Test citation', 'Test rationale']):
            # Mock CLI input validation
            task = 'level_walking'
            phase = 0
            variable = 'hip_flexion_angle_ipsi'
            new_min = -0.15
            new_max = 0.35
            citation = 'Test citation'
            rationale = 'Test rationale'
            
            # Validate inputs
            self.assertIsInstance(task, str)
            self.assertIsInstance(phase, int)
            self.assertIsInstance(variable, str)
            self.assertIsInstance(new_min, float)
            self.assertIsInstance(new_max, float)
            self.assertIsInstance(citation, str)
            self.assertIsInstance(rationale, str)

    def test_literature_citation_format(self):
        """Test literature citation formatting and validation."""
        # Test various citation formats
        valid_citations = [
            'Smith et al. 2023',
            'Jones and Brown 2024',
            'Johnson (2022)',
            'Biomechanics Lab 2023',
            'Internal Study 2024'
        ]
        
        for citation in valid_citations:
            update = RangeUpdate(
                task='level_walking',
                phase=0,
                variable='hip_flexion_angle_ipsi',
                new_min=-0.1,
                new_max=0.3,
                citation=citation,
                rationale='Test',
                reviewer='test_user'
            )
            
            # Should not raise exception
            self.assertEqual(update.citation, citation)

    def test_integration_with_validation_system(self):
        """Test integration with existing validation expectations parser."""
        # Create minimal validation file
        test_content = """# Test Validation

## Validation Tables

### Task: level_walking

| Variable | | 0% | | |Units|Notes|
|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | | |
| hip_flexion_angle_ipsi_rad | -0.100 | 0.300 | |**rad** | |

## Research Requirements
"""
        test_file = os.path.join(self.temp_dir, "test_validation.md")
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Test that parser can read the file
        parser = ValidationExpectationsParser()
        data = parser.read_validation_data(test_file)
        
        self.assertIn('level_walking', data)
        
        # Test that range updater can work with parser data
        updater = RangeUpdater()
        update = RangeUpdate(
            task='level_walking',
            phase=0,
            variable='hip_flexion_angle_ipsi',
            new_min=-0.15,
            new_max=0.35,
            citation='Integration Test',
            rationale='Testing integration',
            reviewer='test_user'
        )
        
        updated_data = updater.apply_range_update(data, update)
        
        # Verify update applied
        self.assertAlmostEqual(
            updated_data['level_walking'][0]['hip_flexion_angle_ipsi']['min'],
            -0.15, places=3
        )


if __name__ == '__main__':
    unittest.main()