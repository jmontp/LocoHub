#!/usr/bin/env python3
"""
Dataset Release Management

Created: 2025-06-18 with user permission
Purpose: Memory-efficient dataset release creation with streaming archives

Intent: Provides comprehensive dataset release management including streaming
archive creation, validation summary generation, metadata bundling, and
documentation compilation. Optimized for memory efficiency by avoiding
loading large datasets into memory during archive operations.
"""

import os
import json
import zipfile
import tarfile
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import pandas as pd


class ReleaseError(Exception):
    """Custom exception for release management errors."""
    pass


@dataclass
class ReleaseConfig:
    """Configuration for dataset release creation."""
    release_name: str
    version: str
    description: str
    citation: str
    license_type: str = "MIT"
    include_phase_datasets: bool = True
    include_time_datasets: bool = False
    validation_required: bool = True
    archive_format: str = "zip"
    compression_level: int = 6
    include_checksums: bool = True
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ReleaseConfig':
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Extract nested configuration
        release_info = config_data.get('release_info', {})
        datasets = config_data.get('datasets', {})
        archive = config_data.get('archive', {})
        
        return cls(
            release_name=release_info.get('name', 'unnamed_release'),
            version=release_info.get('version', '1.0.0'),
            description=release_info.get('description', ''),
            citation=release_info.get('citation', ''),
            license_type=release_info.get('license', 'MIT'),
            include_phase_datasets=datasets.get('include_phase', True),
            include_time_datasets=datasets.get('include_time', False),
            validation_required=datasets.get('validation_required', True),
            archive_format=archive.get('format', 'zip'),
            compression_level=archive.get('compression_level', 6),
            include_checksums=archive.get('include_checksums', True)
        )


class IncrementalArchive:
    """Context manager for incremental archive creation."""
    
    def __init__(self, archive_path: str, archive_format: str = "zip", 
                 compression_level: int = 6):
        self.archive_path = archive_path
        self.archive_format = archive_format.lower()
        self.compression_level = compression_level
        self.archive_handle = None
        
    def __enter__(self):
        """Open archive for writing."""
        if self.archive_format == "zip":
            self.archive_handle = zipfile.ZipFile(
                self.archive_path, 'w', 
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=self.compression_level
            )
        elif self.archive_format in ["tar", "tar.gz", "tgz"]:
            mode = "w:gz" if self.archive_format in ["tar.gz", "tgz"] else "w"
            self.archive_handle = tarfile.open(self.archive_path, mode)
        else:
            raise ReleaseError(f"Unsupported archive format: {self.archive_format}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close archive."""
        if self.archive_handle:
            self.archive_handle.close()
    
    def add_file(self, archive_name: str, file_path: str):
        """Add file to archive without loading into memory."""
        if not os.path.exists(file_path):
            raise ReleaseError(f"File not found: {file_path}")
        
        if isinstance(self.archive_handle, zipfile.ZipFile):
            self.archive_handle.write(file_path, archive_name)
        elif isinstance(self.archive_handle, tarfile.TarFile):
            self.archive_handle.add(file_path, arcname=archive_name)
    
    def add_json(self, archive_name: str, data: Dict[str, Any]):
        """Add JSON data to archive."""
        json_content = json.dumps(data, indent=2, default=str)
        
        if isinstance(self.archive_handle, zipfile.ZipFile):
            self.archive_handle.writestr(archive_name, json_content)
        elif isinstance(self.archive_handle, tarfile.TarFile):
            import io
            tarinfo = tarfile.TarInfo(name=archive_name)
            tarinfo.size = len(json_content.encode('utf-8'))
            tarinfo.mtime = int(datetime.now().timestamp())
            self.archive_handle.addfile(
                tarinfo, io.BytesIO(json_content.encode('utf-8'))
            )
    
    def add_string(self, archive_name: str, content: str):
        """Add string content to archive."""
        if isinstance(self.archive_handle, zipfile.ZipFile):
            self.archive_handle.writestr(archive_name, content)
        elif isinstance(self.archive_handle, tarfile.TarFile):
            import io
            tarinfo = tarfile.TarInfo(name=archive_name)
            tarinfo.size = len(content.encode('utf-8'))
            tarinfo.mtime = int(datetime.now().timestamp())
            self.archive_handle.addfile(
                tarinfo, io.BytesIO(content.encode('utf-8'))
            )


class ReleaseManager:
    """Memory-efficient dataset release manager."""
    
    def __init__(self):
        """Initialize release manager."""
        self.validation_summaries = {}
        self.file_checksums = {}
    
    def create_dataset_metadata(self, dataset_name: str, version: str,
                              description: str, citation: str, license_type: str,
                              dataset_files: List[str], contributors: List[str],
                              creation_date: datetime = None,
                              additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create comprehensive dataset metadata."""
        if creation_date is None:
            creation_date = datetime.now()
        
        # Generate file checksums without loading files
        file_checksums = {}
        file_sizes = {}
        
        for file_path in dataset_files:
            if os.path.exists(file_path):
                # Calculate checksum streaming
                checksum = self._calculate_file_checksum(file_path)
                file_checksums[os.path.basename(file_path)] = checksum
                file_sizes[os.path.basename(file_path)] = os.path.getsize(file_path)
        
        metadata = {
            'name': dataset_name,
            'version': version,
            'description': description,
            'citation': citation,
            'license': license_type,
            'creation_date': creation_date.isoformat(),
            'contributors': contributors,
            'files': [os.path.basename(f) for f in dataset_files],
            'file_checksums': file_checksums,
            'file_sizes_bytes': file_sizes,
            'total_size_bytes': sum(file_sizes.values()),
            'metadata_version': '1.0',
            'generator': 'locomotion-data-standardization-release-manager'
        }
        
        if additional_info:
            metadata.update(additional_info)
        
        return metadata
    
    def _calculate_file_checksum(self, file_path: str, 
                                algorithm: str = 'sha256') -> str:
        """Calculate file checksum without loading entire file into memory."""
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            # Read in chunks to avoid memory issues
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def create_streaming_archive(self, archive_path: str, 
                               files_mapping: Dict[str, str],
                               archive_format: str = None,
                               compression_level: int = 6,
                               include_checksums: bool = False,
                               progress_callback: Callable = None) -> Dict[str, str]:
        """Create archive using streaming operations to minimize memory usage."""
        if archive_format is None:
            # Infer format from file extension
            if archive_path.endswith('.zip'):
                archive_format = 'zip'
            elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
                archive_format = 'tar.gz'
            elif archive_path.endswith('.tar'):
                archive_format = 'tar'
            else:
                archive_format = 'zip'
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        
        checksums = {}
        total_files = len(files_mapping)
        
        try:
            with IncrementalArchive(
                archive_path, archive_format, compression_level
            ) as archive:
                
                for i, (archive_name, file_path) in enumerate(files_mapping.items()):
                    if progress_callback:
                        progress_callback(
                            i, total_files, 
                            f"Adding {os.path.basename(file_path)}"
                        )
                    
                    if not os.path.exists(file_path):
                        raise ReleaseError(f"File not found: {file_path}")
                    
                    # Add file to archive
                    archive.add_file(archive_name, file_path)
                    
                    # Calculate checksum if requested
                    if include_checksums:
                        checksums[archive_name] = self._calculate_file_checksum(file_path)
                
                # Add checksums file if requested
                if include_checksums and checksums:
                    checksum_content = self._format_checksums(checksums)
                    archive.add_string('checksums.txt', checksum_content)
                
                if progress_callback:
                    progress_callback(
                        total_files, total_files, 
                        "Archive creation complete"
                    )
        
        except Exception as e:
            # Clean up partial archive on error
            if os.path.exists(archive_path):
                os.remove(archive_path)
            raise ReleaseError(f"Cannot create archive: {str(e)}")
        
        return checksums
    
    def _format_checksums(self, checksums: Dict[str, str]) -> str:
        """Format checksums in standard format."""
        lines = []
        for filename, checksum in sorted(checksums.items()):
            lines.append(f"{checksum}  {filename}")
        return '\n'.join(lines)
    
    @contextmanager
    def create_incremental_archive(self, archive_path: str, 
                                  archive_format: str = "zip",
                                  compression_level: int = 6):
        """Context manager for incremental archive creation."""
        archive = IncrementalArchive(archive_path, archive_format, compression_level)
        with archive:
            yield archive
    
    def get_dataset_info_streaming(self, dataset_path: str) -> Dict[str, Any]:
        """Get dataset information without loading full dataset into memory."""
        if not os.path.exists(dataset_path):
            raise ReleaseError(f"Dataset file not found: {dataset_path}")
        
        file_size_mb = os.path.getsize(dataset_path) / (1024 * 1024)
        
        try:
            # Use pandas parquet metadata without loading data
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(dataset_path)
            
            schema = parquet_file.schema
            metadata = parquet_file.metadata
            
            info = {
                'file_size_mb': round(file_size_mb, 3),
                'estimated_rows': metadata.num_rows,
                'column_count': len(schema),
                'data_types': {
                    field.name: str(field.type) 
                    for field in schema
                },
                'parquet_version': metadata.format_version,
                'compression': str(metadata.row_group(0).column(0).compression) if metadata.num_row_groups > 0 else 'unknown'
            }
            
        except ImportError:
            # Fallback if pyarrow not available - use pandas but sample only
            try:
                # Read only first few rows to get basic info
                sample_df = pd.read_parquet(dataset_path, nrows=10)
                
                info = {
                    'file_size_mb': round(file_size_mb, 3),
                    'estimated_rows': 'unknown',
                    'column_count': len(sample_df.columns),
                    'data_types': {
                        col: str(dtype) 
                        for col, dtype in sample_df.dtypes.items()
                    }
                }
            except Exception as e:
                info = {
                    'file_size_mb': round(file_size_mb, 3),
                    'error': f"Could not read dataset: {str(e)}"
                }
        
        return info
    
    def generate_validation_summary(self, validation_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate validation summary from individual dataset results."""
        if not validation_results:
            return {
                'overview': {'total_datasets': 0, 'datasets_passing': 0},
                'quality_metrics': {'average_quality': 0.0},
                'validation_status': 'NO_DATA',
                'recommendations': ['No datasets provided for validation']
            }
        
        total_datasets = len(validation_results)
        datasets_passing = sum(
            1 for result in validation_results.values() 
            if result.get('status') == 'PASS'
        )
        
        quality_scores = [
            result.get('quality_score', 0.0) 
            for result in validation_results.values()
            if 'quality_score' in result
        ]
        
        average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Aggregate data points and cycles
        total_cycles = sum(
            result.get('total_cycles', 0) 
            for result in validation_results.values()
        )
        
        total_data_points = sum(
            result.get('data_points', 0) 
            for result in validation_results.values()
        )
        
        # Collect all validation issues
        all_issues = []
        for dataset_name, result in validation_results.items():
            issues = result.get('validation_issues', [])
            for issue in issues:
                all_issues.append({
                    'dataset': dataset_name,
                    'issue': issue
                })
        
        # Generate recommendations
        recommendations = []
        if datasets_passing < total_datasets:
            recommendations.append(
                f"{total_datasets - datasets_passing} datasets failed validation"
            )
        if average_quality < 0.8:
            recommendations.append("Consider reviewing data quality")
        if total_cycles < 50:
            recommendations.append("Limited data available for robust analysis")
        if not recommendations:
            recommendations.append("All validation checks passed successfully")
        
        summary = {
            'overview': {
                'total_datasets': total_datasets,
                'datasets_passing': datasets_passing,
                'pass_rate': datasets_passing / total_datasets if total_datasets > 0 else 0.0
            },
            'dataset_summary': {
                'total_cycles': total_cycles,
                'total_data_points': total_data_points,
                'average_cycles_per_dataset': total_cycles / total_datasets if total_datasets > 0 else 0
            },
            'quality_metrics': {
                'average_quality': average_quality,
                'quality_distribution': {
                    'excellent': len([q for q in quality_scores if q >= 0.9]),
                    'good': len([q for q in quality_scores if 0.8 <= q < 0.9]),
                    'fair': len([q for q in quality_scores if 0.6 <= q < 0.8]),
                    'poor': len([q for q in quality_scores if q < 0.6])
                }
            },
            'validation_status': 'PASS' if datasets_passing == total_datasets else 'PARTIAL' if datasets_passing > 0 else 'FAIL',
            'validation_issues': all_issues,
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }
        
        return summary
    
    def format_validation_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format validation summary as markdown document."""
        overview = summary['overview']
        quality = summary['quality_metrics']
        dataset_summary = summary['dataset_summary']
        
        status_emoji = {
            'PASS': '✅',
            'PARTIAL': '⚠️',
            'FAIL': '❌',
            'NO_DATA': '📋'
        }.get(summary['validation_status'], '❓')
        
        markdown = f"""# Validation Summary

## Overview
{status_emoji} **Status:** {summary['validation_status']}

- **Total Datasets:** {overview['total_datasets']}
- **Datasets Passing:** {overview['datasets_passing']}
- **Pass Rate:** {overview['pass_rate']:.1%}

## Dataset Summary
- **Total Cycles:** {dataset_summary['total_cycles']:,}
- **Total Data Points:** {dataset_summary['total_data_points']:,}
- **Average Cycles per Dataset:** {dataset_summary['average_cycles_per_dataset']:.1f}

## Quality Metrics
- **Average Quality Score:** {quality['average_quality']:.1%}

### Quality Distribution
- **Excellent (≥90%):** {quality['quality_distribution']['excellent']} datasets
- **Good (80-89%):** {quality['quality_distribution']['good']} datasets
- **Fair (60-79%):** {quality['quality_distribution']['fair']} datasets
- **Poor (<60%):** {quality['quality_distribution']['poor']} datasets

## Recommendations
"""
        
        for i, rec in enumerate(summary['recommendations'], 1):
            markdown += f"{i}. {rec}\n"
        
        if summary['validation_issues']:
            markdown += "\n## Validation Issues\n"
            for issue in summary['validation_issues']:
                markdown += f"- **{issue['dataset']}:** {issue['issue']}\n"
        
        markdown += f"\n---\n*Generated on {summary['generated_at']}*\n"
        
        return markdown
    
    def verify_archive_integrity(self, archive_path: str, 
                               expected_checksums: Dict[str, str] = None) -> Dict[str, Any]:
        """Verify archive integrity and contents."""
        if not os.path.exists(archive_path):
            return {
                'is_valid': False,
                'error': 'Archive file not found',
                'verified_files': [],
                'checksum_mismatches': [],
                'missing_files': []
            }
        
        try:
            verified_files = []
            checksum_mismatches = []
            missing_files = []
            
            # Extract to temporary directory for verification
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract archive
                if archive_path.endswith('.zip'):
                    with zipfile.ZipFile(archive_path, 'r') as zip_file:
                        zip_file.extractall(temp_dir)
                        archive_files = zip_file.namelist()
                elif archive_path.endswith(('.tar.gz', '.tgz', '.tar')):
                    with tarfile.open(archive_path, 'r:*') as tar_file:
                        tar_file.extractall(temp_dir)
                        archive_files = tar_file.getnames()
                
                # Verify checksums if provided
                if expected_checksums:
                    for archive_name, expected_checksum in expected_checksums.items():
                        file_path = os.path.join(temp_dir, archive_name)
                        
                        if os.path.exists(file_path):
                            actual_checksum = self._calculate_file_checksum(file_path)
                            if actual_checksum == expected_checksum:
                                verified_files.append(archive_name)
                            else:
                                checksum_mismatches.append({
                                    'file': archive_name,
                                    'expected': expected_checksum,
                                    'actual': actual_checksum
                                })
                        else:
                            missing_files.append(archive_name)
                else:
                    # Just verify files exist in archive
                    verified_files = archive_files
            
            is_valid = (len(checksum_mismatches) == 0 and len(missing_files) == 0)
            
            return {
                'is_valid': is_valid,
                'verified_files': verified_files,
                'checksum_mismatches': checksum_mismatches,
                'missing_files': missing_files,
                'total_files': len(archive_files)
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'verified_files': [],
                'checksum_mismatches': [],
                'missing_files': []
            }
    
    def ensure_output_directory(self, output_dir: str):
        """Ensure output directory exists."""
        os.makedirs(output_dir, exist_ok=True)
    
    def compile_documentation(self, template_type: str = None, 
                            template_file: str = None,
                            doc_info: Dict[str, Any] = None,
                            custom_sections: Dict[str, str] = None) -> str:
        """Compile documentation from templates and data."""
        if doc_info is None:
            doc_info = {}
        
        if template_file and os.path.exists(template_file):
            # Use custom template file
            with open(template_file, 'r') as f:
                template = f.read()
        else:
            # Use built-in templates
            template = self._get_builtin_template(template_type or 'readme')
        
        # Format template with doc_info
        try:
            # Handle variables list formatting
            if 'variables' in doc_info and isinstance(doc_info['variables'], list):
                doc_info['variables_list'] = '\n'.join(f"- {var}" for var in doc_info['variables'])
            
            # Format quality score as percentage
            if 'quality_score' in doc_info:
                doc_info['quality_score_pct'] = f"{doc_info['quality_score']:.1%}"
            
            formatted_doc = template.format(**doc_info)
            
            # Add custom sections if provided
            if custom_sections:
                for section_title, section_content in custom_sections.items():
                    formatted_doc += f"\n\n## {section_title}\n{section_content}"
            
            return formatted_doc
            
        except KeyError as e:
            raise ReleaseError(f"Missing template variable: {e}")
    
    def _get_builtin_template(self, template_type: str) -> str:
        """Get built-in documentation template."""
        templates = {
            'readme': """# {dataset_name}

## Overview
{description}

**Version:** {version}
**Quality Score:** {quality_score_pct}

## Citation
{citation}

## Data Summary
- **Total Subjects:** {total_subjects}
- **Total Trials:** {total_trials}  
- **Total Cycles:** {total_cycles}
- **Tasks:** {tasks}

## Variables
{variables_list}

## Usage
```python
import pandas as pd

# Load phase-indexed data
data = pd.read_parquet('{dataset_name}_phase.parquet')

# Basic analysis
print(data.groupby('task').describe())
```

## License
This dataset is released under the {license} license.
""",
            
            'citation': """{dataset_name} v{version}

{citation}

Dataset DOI: [To be assigned]
Repository: https://github.com/locomotion-data-standardization

Released: {release_date}
""",
            
            'changelog': """# Changelog - {dataset_name}

## Version {version}
Released: {release_date}

### Changes
- Initial release
- {total_cycles} gait cycles from {total_subjects} subjects
- Quality score: {quality_score_pct}

### Validation
- All biomechanical validation checks passed
- Data quality verified according to standardization protocol
"""
        }
        
        return templates.get(template_type, templates['readme'])
    
    def integrate_validation_results(self, dataset_files: List[str], 
                                   validation_results: List[Dict]) -> Dict[str, Any]:
        """Integrate validation results into release summary."""
        # Map results to files
        results_mapping = {}
        for i, file_path in enumerate(dataset_files):
            filename = os.path.basename(file_path)
            if i < len(validation_results):
                results_mapping[filename] = validation_results[i]
        
        # Generate comprehensive summary
        validation_summary = self.generate_validation_summary(results_mapping)
        
        return {
            'validation_summary': validation_summary,
            'individual_results': results_mapping,
            'dataset_files': dataset_files,
            'integration_timestamp': datetime.now().isoformat()
        }
    
    def create_complete_release(self, release_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete dataset release with all components."""
        # Extract configuration
        release_info = release_config['release_info']
        datasets_config = release_config['datasets']
        docs_config = release_config.get('documentation', {})
        output_config = release_config['output']
        
        # Prepare file collections
        dataset_files = []
        documentation_files = []
        
        # Collect dataset files
        source_dir = datasets_config.get('source_directory', '.')
        if datasets_config.get('include_phase', True):
            phase_files = Path(source_dir).glob('*_phase.parquet')
            dataset_files.extend(str(f) for f in phase_files)
        
        if datasets_config.get('include_time', False):
            time_files = Path(source_dir).glob('*_time.parquet')
            dataset_files.extend(str(f) for f in time_files)
        
        # Collect documentation files
        docs_dir = docs_config.get('source_directory')
        if docs_dir and os.path.exists(docs_dir):
            for doc_file in Path(docs_dir).glob('*.md'):
                documentation_files.append(str(doc_file))
        
        # Create release directory
        output_dir = output_config['directory']
        self.ensure_output_directory(output_dir)
        
        # Generate metadata
        metadata = self.create_dataset_metadata(
            dataset_name=release_info['name'],
            version=release_info['version'],
            description=release_info['description'],
            citation=release_info['citation'],
            license_type=release_info.get('license', 'MIT'),
            dataset_files=dataset_files,
            contributors=release_info.get('contributors', [])
        )
        
        # Create archive
        archive_name = output_config.get('archive_name', f"{release_info['name']}_v{release_info['version']}")
        archive_format = output_config.get('format', 'zip')
        archive_path = os.path.join(output_dir, f"{archive_name}.{archive_format}")
        
        # Prepare files for archive
        files_mapping = {}
        
        # Add datasets
        for dataset_file in dataset_files:
            filename = os.path.basename(dataset_file)
            files_mapping[f"datasets/{filename}"] = dataset_file
        
        # Add documentation
        for doc_file in documentation_files:
            filename = os.path.basename(doc_file)
            files_mapping[f"documentation/{filename}"] = doc_file
        
        # Create archive with metadata and progress tracking
        def progress_callback(current, total, message):
            if current % 5 == 0 or current == total:  # Report every 5 files
                print(f"Progress: {current}/{total} - {message}")
        
        # Use incremental archive to add metadata
        with self.create_incremental_archive(archive_path, archive_format, 
                                           output_config.get('compression_level', 6)) as archive:
            # Add datasets
            for dataset_file in dataset_files:
                filename = os.path.basename(dataset_file)
                archive.add_file(f"datasets/{filename}", dataset_file)
            
            # Add documentation
            for doc_file in documentation_files:
                filename = os.path.basename(doc_file)
                archive.add_file(f"documentation/{filename}", doc_file)
            
            # Add metadata as JSON
            archive.add_json('metadata.json', metadata)
            
            # Add checksums if requested
            if output_config.get('include_checksums', True):
                checksums = {}
                for dataset_file in dataset_files + documentation_files:
                    checksums[os.path.basename(dataset_file)] = self._calculate_file_checksum(dataset_file)
                checksum_content = self._format_checksums(checksums)
                archive.add_string('checksums.txt', checksum_content)
        
        checksums = {}
        
        # Save metadata
        metadata_path = os.path.join(output_dir, f"{archive_name}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Save checksums separately if requested
        checksum_path = None
        if checksums and output_config.get('include_checksums', True):
            checksum_path = os.path.join(output_dir, f"{archive_name}_checksums.txt")
            with open(checksum_path, 'w') as f:
                f.write(self._format_checksums(checksums))
        
        # Calculate total files in archive (datasets + docs + metadata + checksums)
        total_files_in_archive = len(dataset_files) + len(documentation_files) + 1  # +1 for metadata
        if output_config.get('include_checksums', True):
            total_files_in_archive += 1  # +1 for checksums
        
        return {
            'success': True,
            'archive_path': archive_path,
            'metadata_path': metadata_path,
            'checksum_path': checksum_path,
            'total_files': total_files_in_archive,
            'total_size_mb': sum(
                os.path.getsize(f) for f in dataset_files + documentation_files
            ) / (1024 * 1024),
            'creation_timestamp': datetime.now().isoformat()
        }


def validate_release_config(config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate release configuration data."""
    errors = []
    
    # Check required sections
    required_sections = ['release_info']
    for section in required_sections:
        if section not in config_data:
            errors.append(f"Missing required section: {section}")
            continue
    
    # Check release_info fields
    release_info = config_data.get('release_info', {})
    required_release_fields = ['name', 'version', 'description']
    
    for field in required_release_fields:
        if field not in release_info:
            errors.append(f"Missing required field in release_info: {field}")
        elif not release_info[field]:
            errors.append(f"Empty value for required field: {field}")
    
    # Validate version format (basic check)
    version = release_info.get('version', '')
    if version and not any(char.isdigit() for char in version):
        errors.append("Version should contain at least one digit")
    
    # Check datasets configuration if present
    datasets = config_data.get('datasets', {})
    if 'source_directory' in datasets:
        source_dir = datasets['source_directory']
        if not os.path.exists(source_dir):
            errors.append(f"Source directory does not exist: {source_dir}")
    
    # Check output configuration if present
    output = config_data.get('output', {})
    if 'directory' in output:
        output_dir = output['directory']
        parent_dir = os.path.dirname(output_dir)
        if parent_dir and not os.path.exists(parent_dir):
            errors.append(f"Output directory parent does not exist: {parent_dir}")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Example usage
    manager = ReleaseManager()
    
    # Example configuration
    example_config = {
        'release_info': {
            'name': 'example_dataset',
            'version': '1.0.0',
            'description': 'Example locomotion dataset',
            'citation': 'Example Research Group (2025)'
        },
        'datasets': {
            'source_directory': './converted_datasets',
            'include_phase': True,
            'include_time': False
        },
        'output': {
            'directory': './releases',
            'format': 'zip'
        }
    }
    
    print("Release Manager initialized successfully")
    print("Example configuration validated:", validate_release_config(example_config))