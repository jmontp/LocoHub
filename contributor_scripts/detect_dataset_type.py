#!/usr/bin/env python3
"""
detect_dataset_type.py

Created: 2025-06-18 with user permission
Purpose: CLI tool for automatic dataset type detection

Intent: Provide a simple command-line interface for detecting dataset types from filenames
and metadata. Designed for dataset curators who need to quickly identify dataset formats
without loading large files or remembering complex naming conventions.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.validation.dataset_type_detector import DatasetTypeDetector


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    import logging
    
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def detect_single_file(filepath: str, use_metadata: bool = True, verbose: bool = False) -> dict:
    """
    Detect dataset type for a single file.
    
    Args:
        filepath: Path to the dataset file
        use_metadata: Whether to analyze metadata
        verbose: Whether to include detailed evidence
        
    Returns:
        Detection result dictionary
    """
    detector = DatasetTypeDetector()
    result = detector.detect_dataset_type(filepath, use_metadata=use_metadata)
    
    if not verbose:
        # Simplify output for non-verbose mode
        return {
            'file': filepath,
            'type': result['dataset_type'],
            'confidence': result['confidence']
        }
    
    return {
        'file': filepath,
        'type': result['dataset_type'],
        'confidence': result['confidence'],
        'evidence': result['evidence']
    }


def detect_batch_files(filepaths: List[str], use_metadata: bool = True, 
                      verbose: bool = False) -> List[dict]:
    """
    Detect dataset types for multiple files.
    
    Args:
        filepaths: List of file paths
        use_metadata: Whether to analyze metadata
        verbose: Whether to include detailed evidence
        
    Returns:
        List of detection results
    """
    detector = DatasetTypeDetector()
    results = detector.detect_batch(filepaths, metadata_analysis=use_metadata)
    
    if not verbose:
        # Simplify output for non-verbose mode
        return [
            {
                'file': result['filename'],
                'type': result['dataset_type'],
                'confidence': result['confidence']
            }
            for result in results
        ]
    
    return [
        {
            'file': result['filename'],
            'type': result['dataset_type'],
            'confidence': result['confidence'],
            'evidence': result['evidence']
        }
        for result in results
    ]


def print_summary_report(results: List[dict]):
    """Print a summary report of detection results."""
    if not results:
        print("No results to summarize.")
        return
    
    # Count by type
    type_counts = {}
    confidence_by_type = {}
    
    for result in results:
        dataset_type = result['type']
        confidence = result['confidence']
        
        if dataset_type not in type_counts:
            type_counts[dataset_type] = 0
            confidence_by_type[dataset_type] = []
        
        type_counts[dataset_type] += 1
        confidence_by_type[dataset_type].append(confidence)
    
    print("\n" + "="*50)
    print("DETECTION SUMMARY")
    print("="*50)
    print(f"Total files analyzed: {len(results)}")
    print()
    
    for dataset_type, count in sorted(type_counts.items()):
        confidences = confidence_by_type[dataset_type]
        avg_conf = sum(confidences) / len(confidences)
        low_conf_count = sum(1 for c in confidences if c < 50)
        
        print(f"{dataset_type.upper()}:")
        print(f"  Count: {count}")
        print(f"  Average confidence: {avg_conf:.1f}%")
        if low_conf_count > 0:
            print(f"  Low confidence files: {low_conf_count}")
        print()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Detect dataset type from filename and metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect single file
  python detect_dataset_type.py data/addbiomech_walk_01.parquet
  
  # Detect multiple files with metadata analysis
  python detect_dataset_type.py data/*.parquet --verbose
  
  # Quick filename-only detection
  python detect_dataset_type.py data/*.parquet --no-metadata
  
  # Batch detection with summary
  python detect_dataset_type.py data/*.parquet --summary
  
  # JSON output for scripting
  python detect_dataset_type.py data/*.parquet --json
        """
    )
    
    parser.add_argument(
        'files',
        nargs='+',
        help='Dataset file(s) to analyze'
    )
    
    parser.add_argument(
        '--no-metadata',
        action='store_true',
        help='Skip metadata analysis (filename patterns only)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Include detailed evidence in output'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    
    parser.add_argument(
        '--confidence-threshold',
        type=int,
        default=50,
        help='Minimum confidence threshold for reporting (default: 50)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Expand glob patterns and validate files
    filepaths = []
    for file_pattern in args.files:
        if '*' in file_pattern or '?' in file_pattern:
            from glob import glob
            expanded = glob(file_pattern)
            if not expanded:
                print(f"Warning: No files found matching pattern '{file_pattern}'", 
                      file=sys.stderr)
            filepaths.extend(expanded)
        else:
            if not Path(file_pattern).exists():
                print(f"Error: File not found: {file_pattern}", file=sys.stderr)
                sys.exit(1)
            filepaths.append(file_pattern)
    
    if not filepaths:
        print("Error: No valid files to analyze", file=sys.stderr)
        sys.exit(1)
    
    # Detect dataset types
    use_metadata = not args.no_metadata
    
    if len(filepaths) == 1:
        result = detect_single_file(filepaths[0], use_metadata, args.verbose)
        results = [result]
    else:
        results = detect_batch_files(filepaths, use_metadata, args.verbose)
    
    # Filter by confidence threshold
    if args.confidence_threshold > 0:
        filtered_results = [r for r in results if r['confidence'] >= args.confidence_threshold]
        if len(filtered_results) < len(results):
            excluded_count = len(results) - len(filtered_results)
            print(f"Note: Excluded {excluded_count} results below confidence threshold {args.confidence_threshold}%",
                  file=sys.stderr)
        results = filtered_results
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        for result in results:
            confidence_indicator = "✓" if result['confidence'] >= 70 else "?" if result['confidence'] >= 50 else "✗"
            
            print(f"{confidence_indicator} {result['file']}")
            print(f"   Type: {result['type']}")
            print(f"   Confidence: {result['confidence']}%")
            
            if args.verbose and 'evidence' in result:
                print(f"   Evidence: {', '.join(result['evidence'])}")
            print()
    
    # Show summary if requested
    if args.summary and not args.json:
        print_summary_report(results)
    
    # Exit with error code if any files had low confidence
    low_confidence_count = sum(1 for r in results if r['confidence'] < 50)
    if low_confidence_count > 0:
        print(f"Warning: {low_confidence_count} files had low confidence detection", 
              file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()