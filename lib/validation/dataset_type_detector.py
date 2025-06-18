"""
dataset_type_detector.py

Created: 2025-06-18 with user permission
Purpose: Memory-conscious automatic dataset type detection from filename and metadata

Intent: Efficiently identify dataset types (AddBiomechanics, GTech 2023, UMich 2021) using
lightweight pattern recognition and minimal metadata parsing. Designed for memory efficiency
with regex-based filename analysis and selective metadata sampling.
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Union, Optional
import pandas as pd


class DatasetTypeDetector:
    """
    Memory-efficient dataset type detection using filename patterns and lightweight metadata analysis.
    
    Supports detection of:
    - AddBiomechanics datasets
    - Georgia Tech 2023 datasets  
    - University of Michigan 2021 datasets
    """
    
    def __init__(self):
        """Initialize detector with filename pattern definitions."""
        self.logger = logging.getLogger(__name__)
        
        # Define filename patterns for each dataset type
        self.filename_patterns = {
            'addbiomechanics': [
                r'addbiomechanics?.*\.parquet$',
                r'addbiomech.*\.parquet$', 
                r'AB_.*\.parquet$',
                r'.*addbiomech.*\.parquet$'
            ],
            'gtech_2023': [
                r'gtech_2023.*\.parquet$',
                r'GT2023.*\.parquet$',
                r'gtech23.*\.parquet$',
                r'.*gtech.*2023.*\.parquet$'
            ],
            'umich_2021': [
                r'umich_2021.*\.parquet$',
                r'UM2021.*\.parquet$', 
                r'michigan_2021.*\.parquet$',
                r'.*umich.*2021.*\.parquet$'
            ]
        }
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for dataset_type, patterns in self.filename_patterns.items():
            self.compiled_patterns[dataset_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # Define metadata signatures for each dataset type
        self.metadata_signatures = {
            'addbiomechanics': {
                'required_columns': ['subject_id', 'trial_id'],
                'indicator_columns': ['addbiomech_version', 'opensim_version'],
                'typical_columns': ['knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm']
            },
            'gtech_2023': {
                'required_columns': ['subject_id', 'trial_id'],
                'indicator_columns': ['gtech_study_id', 'georgia_tech_version'],
                'typical_columns': ['knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm']
            },
            'umich_2021': {
                'required_columns': ['subject_id', 'trial_id'],
                'indicator_columns': ['umich_study_id', 'michigan_version'],
                'typical_columns': ['knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm']
            }
        }
    
    def detect_from_filename(self, filename: Union[str, Path]) -> Dict[str, Union[str, int, List[str]]]:
        """
        Detect dataset type from filename patterns.
        
        Args:
            filename: File path or filename to analyze
            
        Returns:
            Dict with keys: dataset_type, confidence, evidence
        """
        filename_str = str(filename).lower()
        base_filename = os.path.basename(filename_str)
        
        # Check if it's a parquet file
        if not base_filename.endswith('.parquet'):
            return {
                'dataset_type': 'unknown',
                'confidence': 0,
                'evidence': ['not_parquet_file']
            }
        
        # Score each dataset type against filename
        scores = {}
        evidence = {}
        
        for dataset_type, patterns in self.compiled_patterns.items():
            score = 0
            matched_patterns = []
            
            for pattern in patterns:
                if pattern.search(base_filename):
                    score += 30  # Base score for pattern match
                    matched_patterns.append(pattern.pattern)
                    
                    # Bonus points for specific indicators
                    if dataset_type == 'addbiomechanics':
                        if 'addbiomechanics' in base_filename:
                            score += 20
                        elif 'addbiomech' in base_filename:
                            score += 15
                        elif 'ab_' in base_filename:
                            score += 10
                    
                    elif dataset_type == 'gtech_2023':
                        if 'gtech_2023' in base_filename:
                            score += 20
                        elif '2023' in base_filename and 'gtech' in base_filename:
                            score += 15
                        elif 'gt2023' in base_filename:
                            score += 15
                    
                    elif dataset_type == 'umich_2021':
                        if 'umich_2021' in base_filename:
                            score += 20
                        elif '2021' in base_filename and ('umich' in base_filename or 'michigan' in base_filename):
                            score += 15
                        elif 'um2021' in base_filename:
                            score += 15
                    
                    break  # Only count first match per type
            
            scores[dataset_type] = min(score, 100)  # Cap at 100%
            evidence[dataset_type] = matched_patterns
        
        # Determine best match
        if not any(scores.values()):
            return {
                'dataset_type': 'unknown',
                'confidence': 0,
                'evidence': ['no_pattern_match']
            }
        
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_type]
        
        return {
            'dataset_type': best_type,
            'confidence': best_score,
            'evidence': [f'filename_pattern: {p}' for p in evidence[best_type]]
        }
    
    def detect_from_metadata(self, filepath: Union[str, Path], 
                           sample_rows: int = 100) -> Dict[str, Union[str, int, List[str]]]:
        """
        Detect dataset type from metadata using lightweight parquet sampling.
        
        Args:
            filepath: Path to parquet file
            sample_rows: Number of rows to sample for analysis (default: 100)
            
        Returns:
            Dict with keys: dataset_type, confidence, evidence
        """
        try:
            # Read only column names and a small sample for memory efficiency
            df_sample = pd.read_parquet(filepath, nrows=sample_rows)
            columns = set(col.lower() for col in df_sample.columns)
            
            scores = {}
            evidence = {}
            
            for dataset_type, signature in self.metadata_signatures.items():
                score = 0
                type_evidence = []
                
                # Check for required columns
                required_present = sum(1 for col in signature['required_columns'] 
                                     if col.lower() in columns)
                score += (required_present / len(signature['required_columns'])) * 30
                
                if required_present > 0:
                    type_evidence.append(f'required_columns: {required_present}/{len(signature["required_columns"])}')
                
                # Check for indicator columns (strong signals)
                indicator_present = sum(1 for col in signature['indicator_columns']
                                      if col.lower() in columns)
                score += indicator_present * 25  # Strong indicator
                
                if indicator_present > 0:
                    type_evidence.append(f'indicator_columns: {indicator_present}')
                
                # Check for typical columns
                typical_present = sum(1 for col in signature['typical_columns']
                                    if col.lower() in columns)
                score += (typical_present / len(signature['typical_columns'])) * 20
                
                if typical_present > 0:
                    type_evidence.append(f'typical_columns: {typical_present}/{len(signature["typical_columns"])}')
                
                scores[dataset_type] = min(score, 100)  # Cap at 100%
                evidence[dataset_type] = type_evidence
            
            # Determine best match
            if not any(scores.values()):
                return {
                    'dataset_type': 'unknown',
                    'confidence': 0,
                    'evidence': ['no_metadata_match']
                }
            
            best_type = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_type]
            
            return {
                'dataset_type': best_type,
                'confidence': int(best_score),
                'evidence': evidence[best_type]
            }
            
        except Exception as e:
            self.logger.warning(f"Error reading metadata from {filepath}: {e}")
            return {
                'dataset_type': 'unknown',
                'confidence': 0,
                'evidence': [f'metadata_error: {str(e)}']
            }
    
    def detect_dataset_type(self, filepath: Union[str, Path], 
                          use_metadata: bool = True) -> Dict[str, Union[str, int, List[str]]]:
        """
        Comprehensive dataset type detection combining filename and metadata analysis.
        
        Args:
            filepath: Path to dataset file
            use_metadata: Whether to include metadata analysis (default: True)
            
        Returns:
            Dict with keys: dataset_type, confidence, evidence
        """
        filepath = Path(filepath)
        
        # Check if file exists
        if not filepath.exists():
            return {
                'dataset_type': 'unknown',
                'confidence': 0,
                'evidence': ['file_not_found']
            }
        
        # Start with filename detection
        filename_result = self.detect_from_filename(filepath)
        
        if not use_metadata:
            return filename_result
        
        # Add metadata analysis
        try:
            metadata_result = self.detect_from_metadata(filepath)
        except Exception as e:
            # Fall back to filename detection if metadata fails
            self.logger.warning(f"Metadata analysis failed for {filepath}: {e}")
            filename_result['evidence'].append('metadata_analysis_failed')
            return filename_result
        
        # Combine results
        filename_type = filename_result['dataset_type']
        metadata_type = metadata_result['dataset_type']
        
        # If both agree, increase confidence
        if filename_type == metadata_type and filename_type != 'unknown':
            combined_confidence = min(
                int((filename_result['confidence'] + metadata_result['confidence']) * 0.6), 
                100
            )
            combined_evidence = (filename_result['evidence'] + 
                               ['metadata_analysis'] + 
                               metadata_result['evidence'])
            
            return {
                'dataset_type': filename_type,
                'confidence': combined_confidence,
                'evidence': combined_evidence
            }
        
        # If they conflict, report uncertainty
        elif filename_type != metadata_type and filename_type != 'unknown' and metadata_type != 'unknown':
            return {
                'dataset_type': 'unknown',
                'confidence': 25,  # Low confidence due to conflict
                'evidence': [
                    'conflicting_signals',
                    f'filename_suggests: {filename_type}',
                    f'metadata_suggests: {metadata_type}'
                ]
            }
        
        # If one is unknown, use the other
        elif filename_type != 'unknown':
            return filename_result
        elif metadata_type != 'unknown':
            return metadata_result
        
        # Both unknown
        else:
            return {
                'dataset_type': 'unknown',
                'confidence': 0,
                'evidence': filename_result['evidence'] + metadata_result['evidence']
            }
    
    def detect_batch(self, filepaths: List[Union[str, Path]], 
                    metadata_analysis: bool = True) -> List[Dict]:
        """
        Efficiently detect dataset types for multiple files.
        
        Args:
            filepaths: List of file paths to analyze
            metadata_analysis: Whether to include metadata analysis
            
        Returns:
            List of detection results, one per file
        """
        results = []
        
        for filepath in filepaths:
            result = self.detect_dataset_type(filepath, use_metadata=metadata_analysis)
            result['filename'] = str(filepath)
            results.append(result)
        
        return results
    
    def get_summary_report(self, detection_results: List[Dict]) -> Dict:
        """
        Generate summary report from batch detection results.
        
        Args:
            detection_results: List of detection results from detect_batch()
            
        Returns:
            Summary statistics and recommendations
        """
        if not detection_results:
            return {'error': 'No detection results provided'}
        
        # Count by dataset type
        type_counts = {}
        confidence_stats = {}
        
        for result in detection_results:
            dataset_type = result['dataset_type']
            confidence = result['confidence']
            
            if dataset_type not in type_counts:
                type_counts[dataset_type] = 0
                confidence_stats[dataset_type] = []
            
            type_counts[dataset_type] += 1
            confidence_stats[dataset_type].append(confidence)
        
        # Calculate confidence statistics
        summary = {
            'total_files': len(detection_results),
            'type_distribution': type_counts,
            'confidence_summary': {}
        }
        
        for dataset_type, confidences in confidence_stats.items():
            if confidences:
                summary['confidence_summary'][dataset_type] = {
                    'mean_confidence': sum(confidences) / len(confidences),
                    'min_confidence': min(confidences),
                    'max_confidence': max(confidences),
                    'low_confidence_count': sum(1 for c in confidences if c < 50)
                }
        
        return summary


# Convenience function for simple detection
def detect_dataset_type(filepath: Union[str, Path]) -> str:
    """
    Simple function to detect dataset type and return type name.
    
    Args:
        filepath: Path to dataset file
        
    Returns:
        Dataset type name ('addbiomechanics', 'gtech_2023', 'umich_2021', 'unknown')
    """
    detector = DatasetTypeDetector()
    result = detector.detect_dataset_type(filepath)
    return result['dataset_type']