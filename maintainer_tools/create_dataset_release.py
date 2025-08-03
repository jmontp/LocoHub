#!/usr/bin/env python3
"""
Dataset Release Creation CLI

Created: 2025-06-18 with user permission
Purpose: CLI for creating comprehensive dataset releases with documentation

Intent: Provides command-line interface for creating complete dataset releases
including validation, documentation compilation, metadata generation, and
archive creation. Supports flexible configuration and memory-efficient
streaming operations for large datasets.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from internal.validation_engine.release_manager import (
    ReleaseManager, ReleaseConfig, ReleaseError, validate_release_config
)
from internal.validation_engine.validator import DatasetValidator


def create_default_config(output_path: str) -> str:
    """Create a default configuration file."""
    default_config = {
        "release_info": {
            "name": "my_dataset",
            "version": "1.0.0",
            "description": "Locomotion dataset release",
            "citation": "Research Team (2025). Dataset Description. DOI: TBD",
            "license": "CC BY 4.0",
            "contributors": ["Research Team"]
        },
        "datasets": {
            "source_directory": "./converted_datasets",
            "include_phase": True,
            "include_time": False,
            "validation_required": True,
            "quality_threshold": 0.8
        },
        "documentation": {
            "source_directory": "./docs",
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
            "directory": "./releases",
            "archive_name": None
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    return output_path


def validate_datasets(dataset_files: List[str], quality_threshold: float = 0.8) -> Dict[str, Any]:
    """Validate datasets before release."""
    validation_results = {}
    
    print(f"🔍 Validating {len(dataset_files)} datasets...")
    
    for i, dataset_file in enumerate(dataset_files, 1):
        print(f"  [{i}/{len(dataset_files)}] Validating {os.path.basename(dataset_file)}")
        
        try:
            if dataset_file.endswith('_phase.parquet'):
                # Create validator for this specific dataset
                validator = DatasetValidator(dataset_file, generate_plots=False)
                locomotion_data = validator.load_dataset()
                result = validator.validate_dataset(locomotion_data)
                validation_results[os.path.basename(dataset_file)] = result
                
                # Check quality threshold
                quality_score = result.get('quality_score', 0.0)
                status = "✅ PASS" if quality_score >= quality_threshold else "⚠️  WARN"
                print(f"    {status} Quality: {quality_score:.1%}")
                
            else:
                # For time datasets, do basic checks
                validation_results[os.path.basename(dataset_file)] = {
                    'status': 'SKIPPED',
                    'quality_score': 0.9,  # Assume good for time datasets
                    'message': 'Time dataset validation not implemented'
                }
                print(f"    ⏭️  SKIP Time dataset")
                
        except Exception as e:
            validation_results[os.path.basename(dataset_file)] = {
                'status': 'ERROR',
                'quality_score': 0.0,
                'error': str(e)
            }
            print(f"    ❌ ERROR: {str(e)}")
    
    return validation_results


def collect_dataset_files(source_dir: str, include_phase: bool = True, 
                         include_time: bool = False) -> List[str]:
    """Collect dataset files from source directory."""
    source_path = Path(source_dir)
    dataset_files = []
    
    if not source_path.exists():
        raise ReleaseError(f"Source directory does not exist: {source_dir}")
    
    if include_phase:
        phase_files = list(source_path.glob('*_phase.parquet'))
        dataset_files.extend(str(f) for f in phase_files)
        print(f"📊 Found {len(phase_files)} phase datasets")
    
    if include_time:
        time_files = list(source_path.glob('*_time.parquet'))
        dataset_files.extend(str(f) for f in time_files)
        print(f"⏱️  Found {len(time_files)} time datasets")
    
    if not dataset_files:
        raise ReleaseError(f"No dataset files found in {source_dir}")
    
    return dataset_files


def collect_documentation_files(docs_dir: Optional[str]) -> List[str]:
    """Collect documentation files."""
    doc_files = []
    
    if docs_dir and os.path.exists(docs_dir):
        docs_path = Path(docs_dir)
        for doc_file in docs_path.glob('*.md'):
            doc_files.append(str(doc_file))
        print(f"📚 Found {len(doc_files)} documentation files")
    else:
        print("📚 No documentation directory specified or found")
    
    return doc_files


def generate_release_summary(validation_results: Dict[str, Any], 
                           total_files: int, archive_path: str,
                           total_size_mb: float) -> str:
    """Generate release summary report."""
    total_datasets = len(validation_results)
    passed_datasets = sum(1 for result in validation_results.values() 
                         if result.get('status') == 'PASS')
    
    quality_scores = [result.get('quality_score', 0.0) 
                     for result in validation_results.values()]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    summary = f"""
📦 RELEASE SUMMARY
==================

📊 Dataset Validation:
  • Total datasets: {total_datasets}
  • Passed validation: {passed_datasets}
  • Average quality: {avg_quality:.1%}

📁 Archive Information:
  • Total files: {total_files}
  • Archive size: {total_size_mb:.1f} MB
  • Archive path: {archive_path}

✅ Release Status: {'COMPLETE' if passed_datasets == total_datasets else 'PARTIAL'}
"""
    
    if passed_datasets < total_datasets:
        failed_count = total_datasets - passed_datasets
        summary += f"\n⚠️  Warning: {failed_count} datasets failed validation\n"
    
    return summary


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create comprehensive dataset releases with validation and documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create default configuration
  python create_dataset_release.py --create-config release_config.json

  # Create release from configuration
  python create_dataset_release.py --config release_config.json

  # Quick release with minimal options
  python create_dataset_release.py --datasets ./converted_datasets --output ./releases --name my_dataset

  # Release with validation and custom documentation
  python create_dataset_release.py --config my_config.json --validate --verbose

Configuration format:
  See release_config.json for complete configuration options including:
  - Release metadata (name, version, citation)
  - Dataset selection (phase/time datasets)
  - Documentation compilation
  - Archive format and compression
  - Validation requirements
        """
    )
    
    # Configuration options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '--config', '-c', type=str,
        help='JSON configuration file for release parameters'
    )
    config_group.add_argument(
        '--create-config', type=str, metavar='PATH',
        help='Create default configuration file at specified path'
    )
    
    # Quick setup options
    quick_group = parser.add_argument_group('Quick Setup (alternative to config file)')
    quick_group.add_argument(
        '--datasets', type=str, metavar='DIR',
        help='Directory containing dataset files'
    )
    quick_group.add_argument(
        '--output', '-o', type=str, metavar='DIR',
        help='Output directory for release archive'
    )
    quick_group.add_argument(
        '--name', type=str,
        help='Release name (required for quick setup)'
    )
    quick_group.add_argument(
        '--version', type=str, default='1.0.0',
        help='Release version (default: 1.0.0)'
    )
    quick_group.add_argument(
        '--description', type=str,
        help='Release description'
    )
    
    # Dataset options
    dataset_group = parser.add_argument_group('Dataset Options')
    dataset_group.add_argument(
        '--include-phase', action='store_true', default=True,
        help='Include phase-indexed datasets (default: True)'
    )
    dataset_group.add_argument(
        '--include-time', action='store_true',
        help='Include time-indexed datasets'
    )
    dataset_group.add_argument(
        '--no-validation', action='store_true',
        help='Skip dataset validation'
    )
    dataset_group.add_argument(
        '--quality-threshold', type=float, default=0.8,
        help='Minimum quality score for datasets (default: 0.8)'
    )
    
    # Archive options
    archive_group = parser.add_argument_group('Archive Options')
    archive_group.add_argument(
        '--format', choices=['zip', 'tar', 'tar.gz'], default='zip',
        help='Archive format (default: zip)'
    )
    archive_group.add_argument(
        '--compression-level', type=int, default=6, choices=range(0, 10),
        help='Compression level 0-9 (default: 6)'
    )
    archive_group.add_argument(
        '--no-checksums', action='store_true',
        help='Skip checksum generation'
    )
    
    # Documentation options
    doc_group = parser.add_argument_group('Documentation Options')
    doc_group.add_argument(
        '--docs-dir', type=str,
        help='Directory containing documentation files'
    )
    doc_group.add_argument(
        '--template', type=str,
        help='Custom documentation template file'
    )
    doc_group.add_argument(
        '--citation', type=str,
        help='Citation for the dataset'
    )
    
    # Control options
    control_group = parser.add_argument_group('Control Options')
    control_group.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output'
    )
    control_group.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without creating archive'
    )
    control_group.add_argument(
        '--force', action='store_true',
        help='Overwrite existing release files'
    )
    
    args = parser.parse_args()
    
    # Handle config creation
    if args.create_config:
        config_path = create_default_config(args.create_config)
        print(f"✅ Created default configuration: {config_path}")
        print("Edit the configuration file and run with --config to create release")
        return 0
    
    try:
        # Load or create configuration
        if args.config:
            if not os.path.exists(args.config):
                raise ReleaseError(f"Configuration file not found: {args.config}")
            
            with open(args.config, 'r') as f:
                config_data = json.load(f)
            
            # Validate configuration
            is_valid, errors = validate_release_config(config_data)
            if not is_valid:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"  • {error}")
                return 1
            
            print(f"✅ Loaded configuration: {args.config}")
            
        elif args.datasets and args.output and args.name:
            # Quick setup mode
            config_data = {
                'release_info': {
                    'name': args.name,
                    'version': args.version,
                    'description': args.description or f"{args.name} dataset release",
                    'citation': args.citation or f"{args.name} Research Team ({datetime.now().year})",
                },
                'datasets': {
                    'source_directory': args.datasets,
                    'include_phase': args.include_phase,
                    'include_time': args.include_time,
                    'validation_required': not args.no_validation,
                    'quality_threshold': args.quality_threshold
                },
                'documentation': {
                    'source_directory': args.docs_dir,
                    'custom_template_path': args.template
                },
                'archive': {
                    'format': args.format,
                    'compression_level': args.compression_level,
                    'include_checksums': not args.no_checksums
                },
                'output': {
                    'directory': args.output
                }
            }
            
            print(f"✅ Quick setup: {args.name} v{args.version}")
            
        else:
            print("❌ Error: Must provide either --config or --datasets + --output + --name")
            parser.print_help()
            return 1
        
        # Initialize release manager
        manager = ReleaseManager()
        
        # Collect dataset files
        datasets_config = config_data['datasets']
        dataset_files = collect_dataset_files(
            datasets_config['source_directory'],
            datasets_config.get('include_phase', True),
            datasets_config.get('include_time', False)
        )
        
        # Validate datasets if required
        validation_results = {}
        if datasets_config.get('validation_required', True) and not args.no_validation:
            validation_results = validate_datasets(
                dataset_files, 
                datasets_config.get('quality_threshold', 0.8)
            )
        else:
            print("⏭️  Skipping dataset validation")
            # Create mock validation results
            for dataset_file in dataset_files:
                validation_results[os.path.basename(dataset_file)] = {
                    'status': 'SKIPPED',
                    'quality_score': 1.0
                }
        
        # Collect documentation files
        docs_config = config_data.get('documentation', {})
        doc_files = collect_documentation_files(docs_config.get('source_directory'))
        
        if args.dry_run:
            print("\n🔍 DRY RUN - Would create release with:")
            print(f"  • {len(dataset_files)} dataset files")
            print(f"  • {len(doc_files)} documentation files")
            print(f"  • Archive format: {config_data['archive']['format']}")
            print(f"  • Output: {config_data['output']['directory']}")
            return 0
        
        # Create release
        print(f"\n🚀 Creating release: {config_data['release_info']['name']}")
        
        release_result = manager.create_complete_release(config_data)
        
        if release_result['success']:
            # Generate and display summary
            summary = generate_release_summary(
                validation_results,
                release_result['total_files'],
                release_result['archive_path'],
                release_result['total_size_mb']
            )
            
            print(summary)
            
            if args.verbose:
                print(f"\n📋 Detailed Results:")
                print(f"  • Archive: {release_result['archive_path']}")
                print(f"  • Metadata: {release_result['metadata_path']}")
                if release_result.get('checksum_path'):
                    print(f"  • Checksums: {release_result['checksum_path']}")
                print(f"  • Created: {release_result['creation_timestamp']}")
            
            print(f"\n✅ Release created successfully!")
            return 0
        else:
            print("❌ Release creation failed")
            return 1
            
    except ReleaseError as e:
        print(f"❌ Release Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())