"""
test_us02_dataset_type_detection.py

Created: 2025-06-18 with user permission
Purpose: Memory-conscious tests for automatic dataset type detection

Intent: Test filename pattern recognition and metadata analysis without loading large datasets.
Uses mock data and small samples to keep memory usage minimal.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import tempfile
import os
from pathlib import Path


class TestDatasetTypeDetection(unittest.TestCase):
    """Memory-conscious tests for dataset type detection functionality."""
    
    def setUp(self):
        """Set up test fixtures with minimal memory footprint."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Sample filename patterns for each dataset type
        self.addbiomechanics_files = [
            "addbiomechanics_subject_01_walking_time.parquet",
            "addbiomechanics_subject_02_running_phase.parquet", 
            "AB_study_01_participant_05_time.parquet",
            "addbiomech_walk_01_phase.parquet"
        ]
        
        self.gtech_files = [
            "gtech_2023_subject_01_walking_time.parquet",
            "gtech_2023_subject_02_running_phase.parquet",
            "GT2023_walk_01_time.parquet",
            "gtech23_run_phase.parquet"
        ]
        
        self.umich_files = [
            "umich_2021_subject_01_walking_time.parquet", 
            "umich_2021_subject_02_running_phase.parquet",
            "UM2021_walk_01_time.parquet",
            "michigan_2021_run_phase.parquet"
        ]
        
        self.unknown_files = [
            "random_dataset_walking_time.parquet",
            "study_xyz_subject_01_phase.parquet",
            "experiment_data.parquet"
        ]
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_filename_pattern_recognition(self):
        """Test that filename patterns are correctly identified."""
        # Import the detector module (will be created in Phase 2)
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        
        detector = DatasetTypeDetector()
        
        # Test AddBiomechanics patterns
        for filename in self.addbiomechanics_files:
            result = detector.detect_from_filename(filename)
            self.assertEqual(result['dataset_type'], 'addbiomechanics')
            self.assertGreaterEqual(result['confidence'], 30)
        
        # Test GTech patterns  
        for filename in self.gtech_files:
            result = detector.detect_from_filename(filename)
            self.assertEqual(result['dataset_type'], 'gtech_2023')
            self.assertGreaterEqual(result['confidence'], 30)
        
        # Test UMich patterns
        for filename in self.umich_files:
            result = detector.detect_from_filename(filename)
            self.assertEqual(result['dataset_type'], 'umich_2021')
            self.assertGreaterEqual(result['confidence'], 30)
        
        # Test unknown patterns
        for filename in self.unknown_files:
            result = detector.detect_from_filename(filename)
            self.assertEqual(result['dataset_type'], 'unknown')
            self.assertLess(result['confidence'], 50)
    
    def test_confidence_scoring(self):
        """Test confidence scoring algorithm."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        
        detector = DatasetTypeDetector()
        
        # High confidence cases
        high_conf = detector.detect_from_filename("addbiomechanics_subject_01_walking_time.parquet")
        self.assertGreaterEqual(high_conf['confidence'], 50)
        
        # Medium confidence cases  
        med_conf = detector.detect_from_filename("AB_walk_01_time.parquet")
        self.assertGreaterEqual(med_conf['confidence'], 30)
        self.assertLess(med_conf['confidence'], 60)
        
        # Low confidence cases
        low_conf = detector.detect_from_filename("random_data.parquet")
        self.assertLess(low_conf['confidence'], 50)
    
    @patch('lib.validation.dataset_type_detector.pd.read_parquet')
    def test_metadata_analysis_mock(self, mock_read_parquet):
        """Test metadata analysis using mocked parquet reading to avoid memory usage."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        
        detector = DatasetTypeDetector()
        
        # Mock AddBiomechanics metadata
        addbiomech_columns = ['time', 'knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm', 
                             'subject_id', 'trial_id', 'addbiomech_version']
        mock_df = Mock()
        mock_df.columns = addbiomech_columns
        mock_df.shape = (1000, len(addbiomech_columns))
        mock_read_parquet.return_value = mock_df
        
        test_file = os.path.join(self.temp_dir, "test_addbiomech.parquet")
        result = detector.detect_from_metadata(test_file)
        
        self.assertEqual(result['dataset_type'], 'addbiomechanics')
        self.assertGreater(result['confidence'], 50)
        
        # Mock GTech metadata
        gtech_columns = ['time', 'knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm',
                        'subject_id', 'trial_id', 'gtech_study_id']
        mock_df.columns = gtech_columns
        mock_df.shape = (1500, len(gtech_columns))
        
        result = detector.detect_from_metadata(test_file)
        self.assertEqual(result['dataset_type'], 'gtech_2023')
        self.assertGreater(result['confidence'], 50)
    
    def test_combined_detection(self):
        """Test combined filename and metadata detection."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        import tempfile
        
        detector = DatasetTypeDetector()
        
        # Create a temporary file that exists
        with tempfile.NamedTemporaryFile(suffix='_addbiomechanics_subject_01_walking_time.parquet', delete=False) as tmp:
            test_file = tmp.name
        
        try:
            # Mock metadata that confirms filename detection
            with patch.object(detector, 'detect_from_metadata') as mock_metadata:
                mock_metadata.return_value = {
                    'dataset_type': 'addbiomechanics',
                    'confidence': 85,
                    'evidence': ['addbiomech_version column present']
                }
                
                result = detector.detect_dataset_type(test_file)
                
                self.assertEqual(result['dataset_type'], 'addbiomechanics')
                self.assertGreater(result['confidence'], 50)
                self.assertTrue(any('filename_pattern' in ev for ev in result['evidence']))
        finally:
            import os
            os.unlink(test_file)
    
    def test_conflicting_detection(self):
        """Test handling of conflicting filename and metadata signals."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        import tempfile
        
        detector = DatasetTypeDetector()
        
        # Create a temporary file that exists
        with tempfile.NamedTemporaryFile(suffix='_addbiomechanics_subject_01_walking_time.parquet', delete=False) as tmp:
            test_file = tmp.name
        
        try:
            # Filename suggests AddBiomechanics but metadata suggests GTech
            with patch.object(detector, 'detect_from_metadata') as mock_metadata:
                mock_metadata.return_value = {
                    'dataset_type': 'gtech_2023',
                    'confidence': 80,
                    'evidence': ['gtech_study_id column present']
                }
                
                result = detector.detect_dataset_type(test_file)
                
                # Should indicate uncertainty when signals conflict
                self.assertLess(result['confidence'], 70)
                self.assertIn('conflicting_signals', result['evidence'])
        finally:
            import os
            os.unlink(test_file)
    
    def test_memory_efficiency(self):
        """Test that detection process has minimal memory footprint."""
        try:
            import psutil
            import os
            
            from lib.validation.dataset_type_detector import DatasetTypeDetector
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            detector = DatasetTypeDetector()
            
            # Run multiple detections
            test_files = self.addbiomechanics_files + self.gtech_files + self.umich_files
            for filename in test_files:
                detector.detect_from_filename(filename)
            
            # Check memory usage didn't increase significantly
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Should use less than 10MB additional memory
            self.assertLess(memory_increase, 10)
        except ImportError:
            # Skip test if psutil not available
            self.skipTest("psutil not available - memory test skipped")
    
    def test_batch_detection_efficiency(self):
        """Test efficient batch processing of multiple files."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        
        detector = DatasetTypeDetector()
        
        # Create list of test filenames
        test_files = (self.addbiomechanics_files + self.gtech_files + 
                     self.umich_files + self.unknown_files)
        
        # Test batch detection
        results = detector.detect_batch(test_files, metadata_analysis=False)
        
        self.assertEqual(len(results), len(test_files))
        
        # Verify each result has required fields
        for result in results:
            self.assertIn('filename', result)
            self.assertIn('dataset_type', result)
            self.assertIn('confidence', result)
            self.assertIn('evidence', result)
    
    def test_error_handling(self):
        """Test graceful error handling for problematic files."""
        from lib.validation.dataset_type_detector import DatasetTypeDetector
        
        detector = DatasetTypeDetector()
        
        # Test non-existent file
        result = detector.detect_dataset_type("/nonexistent/file.parquet")
        self.assertEqual(result['dataset_type'], 'unknown')
        self.assertEqual(result['confidence'], 0)
        self.assertIn('file_not_found', result['evidence'])
        
        # Test invalid filename
        result = detector.detect_from_filename("not_a_parquet_file.txt")
        self.assertEqual(result['dataset_type'], 'unknown')
        self.assertLess(result['confidence'], 50)


if __name__ == '__main__':
    unittest.main()