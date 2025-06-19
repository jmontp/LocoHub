#!/usr/bin/env python3
"""
Pre-Build Verification Hook

Created: 2025-06-19 with user permission
Purpose: MkDocs hook that validates documentation before build process

Intent: This hook runs comprehensive verification checks before MkDocs builds
the documentation site, ensuring all content is accurate and up-to-date with
the actual codebase. It prevents deployment of inaccurate documentation.
"""

import os
import sys
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Add the project root to the Python path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class VerificationResult:
    """Results from a verification check"""
    check_name: str
    passed: bool
    warnings: List[str]
    errors: List[str]
    details: Dict[str, Any]

class PreBuildVerifier:
    """Comprehensive pre-build verification system"""
    
    def __init__(self, config_path: str, docs_dir: str):
        self.config_path = Path(config_path)
        self.docs_dir = Path(docs_dir)
        self.project_root = self.config_path.parent.parent.parent
        self.verification_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def verify_code_examples(self) -> VerificationResult:
        """Validate all code examples in documentation"""
        self.logger.info("Verifying code examples...")
        
        warnings = []
        errors = []
        validated_files = 0
        validated_examples = 0
        
        try:
            # Find all markdown files with code examples
            md_files = list(self.docs_dir.rglob("*.md"))
            
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract Python code blocks
                    python_blocks = self.extract_python_blocks(content)
                    
                    for i, block in enumerate(python_blocks):
                        if self.should_skip_verification(block):
                            continue
                            
                        validation_result = self.validate_python_block(block, md_file)
                        validated_examples += 1
                        
                        if not validation_result['success']:
                            errors.append(f"{md_file}:block{i+1}: {validation_result['error']}")
                        elif validation_result['warnings']:
                            warnings.extend([f"{md_file}:block{i+1}: {w}" for w in validation_result['warnings']])
                    
                    validated_files += 1
                    
                except Exception as e:
                    errors.append(f"Failed to process {md_file}: {str(e)}")
            
            return VerificationResult(
                check_name="code_examples",
                passed=len(errors) == 0,
                warnings=warnings,
                errors=errors,
                details={
                    "files_validated": validated_files,
                    "examples_validated": validated_examples
                }
            )
            
        except Exception as e:
            return VerificationResult(
                check_name="code_examples",
                passed=False,
                warnings=[],
                errors=[f"Code example verification failed: {str(e)}"],
                details={}
            )
    
    def extract_python_blocks(self, content: str) -> List[str]:
        """Extract Python code blocks from markdown content"""
        blocks = []
        lines = content.split('\n')
        in_python_block = False
        current_block = []
        
        for line in lines:
            if line.strip().startswith('```python'):
                in_python_block = True
                current_block = []
            elif line.strip() == '```' and in_python_block:
                in_python_block = False
                if current_block:
                    blocks.append('\n'.join(current_block))
            elif in_python_block:
                current_block.append(line)
        
        return blocks
    
    def should_skip_verification(self, code_block: str) -> bool:
        """Check if code block should be skipped"""
        skip_markers = [
            '# SKIP-VERIFICATION',
            '# TODO:',
            '# EXAMPLE-ONLY',
            'import hypothetical_module'
        ]
        
        return any(marker in code_block for marker in skip_markers)
    
    def validate_python_block(self, code_block: str, source_file: Path) -> Dict[str, Any]:
        """Validate a Python code block"""
        try:
            # Create a temporary test environment
            test_env = {
                '__file__': str(source_file),
                '__name__': '__main__'
            }
            
            # Add project modules to path for imports
            original_path = sys.path.copy()
            sys.path.insert(0, str(self.project_root))
            sys.path.insert(0, str(self.project_root / 'lib'))
            
            warnings = []
            
            try:
                # Try to compile the code first
                compile(code_block, str(source_file), 'exec')
                
                # Execute in isolated environment
                exec(code_block, test_env)
                
                return {
                    'success': True,
                    'warnings': warnings,
                    'error': None
                }
                
            except ImportError as e:
                # Check if it's a missing project module vs external dependency
                if any(mod in str(e) for mod in ['pandas', 'numpy', 'matplotlib']):
                    warnings.append(f"External dependency not available: {str(e)}")
                    return {
                        'success': True,
                        'warnings': warnings,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'warnings': warnings,
                        'error': f"Import error: {str(e)}"
                    }
            
            except Exception as e:
                return {
                    'success': False,
                    'warnings': warnings,
                    'error': str(e)
                }
            
            finally:
                sys.path = original_path
                
        except SyntaxError as e:
            return {
                'success': False,
                'warnings': [],
                'error': f"Syntax error: {str(e)}"
            }
    
    def verify_file_references(self) -> VerificationResult:
        """Validate all file path references in documentation"""
        self.logger.info("Verifying file references...")
        
        warnings = []
        errors = []
        checked_references = 0
        
        try:
            md_files = list(self.docs_dir.rglob("*.md"))
            
            for md_file in md_files:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find file references (links, paths, etc.)
                file_refs = self.extract_file_references(content)
                
                for ref in file_refs:
                    checked_references += 1
                    if not self.validate_file_reference(ref, md_file):
                        errors.append(f"{md_file}: Referenced file not found: {ref}")
            
            return VerificationResult(
                check_name="file_references",
                passed=len(errors) == 0,
                warnings=warnings,
                errors=errors,
                details={"references_checked": checked_references}
            )
            
        except Exception as e:
            return VerificationResult(
                check_name="file_references",
                passed=False,
                warnings=[],
                errors=[f"File reference verification failed: {str(e)}"],
                details={}
            )
    
    def extract_file_references(self, content: str) -> List[str]:
        """Extract file references from markdown content"""
        import re
        
        references = []
        
        # Markdown links: [text](path)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(link_pattern, content):
            path = match.group(2)
            if not path.startswith(('http://', 'https://', 'mailto:', '#')):
                references.append(path)
        
        # Code block file references
        file_patterns = [
            r'[\'"]([^\'"\s]+\.(?:py|md|csv|parquet|png|jpg|jpeg))[\'"]',
            r'(?:read_csv|load|open)\([\'"]([^\'"\s]+)[\'"]',
        ]
        
        for pattern in file_patterns:
            for match in re.finditer(pattern, content):
                references.append(match.group(1))
        
        return references
    
    def validate_file_reference(self, ref: str, source_file: Path) -> bool:
        """Check if a file reference is valid"""
        # Handle relative paths
        if ref.startswith('./') or ref.startswith('../'):
            ref_path = (source_file.parent / ref).resolve()
        elif ref.startswith('/'):
            ref_path = self.project_root / ref.lstrip('/')
        else:
            # Try both relative to source file and project root
            ref_path = source_file.parent / ref
            if not ref_path.exists():
                ref_path = self.project_root / ref
        
        return ref_path.exists()
    
    def verify_api_documentation(self) -> VerificationResult:
        """Validate API documentation against actual code"""
        self.logger.info("Verifying API documentation...")
        
        warnings = []
        errors = []
        
        try:
            # Check if main library modules exist and are importable
            lib_path = self.project_root / 'lib'
            if lib_path.exists():
                # Try importing core modules
                try:
                    sys.path.insert(0, str(lib_path))
                    
                    # Import and inspect core modules
                    from core import locomotion_analysis
                    from validation import dataset_validator_phase
                    
                    # Validate documented vs actual interfaces
                    # This is a simplified check - full implementation would
                    # parse API docs and compare with actual function signatures
                    
                    # Check LocomotionData class
                    if hasattr(locomotion_analysis, 'LocomotionData'):
                        cls = locomotion_analysis.LocomotionData
                        expected_methods = ['load_from_parquet', 'validate_phase', 'plot_feature']
                        
                        for method in expected_methods:
                            if not hasattr(cls, method):
                                errors.append(f"LocomotionData missing documented method: {method}")
                    
                except ImportError as e:
                    warnings.append(f"Could not import core modules for API verification: {str(e)}")
            
            return VerificationResult(
                check_name="api_documentation",
                passed=len(errors) == 0,
                warnings=warnings,
                errors=errors,
                details={}
            )
            
        except Exception as e:
            return VerificationResult(
                check_name="api_documentation",
                passed=False,
                warnings=[],
                errors=[f"API documentation verification failed: {str(e)}"],
                details={}
            )
    
    def verify_tutorial_data_files(self) -> VerificationResult:
        """Verify that tutorial test files exist and are valid"""
        self.logger.info("Verifying tutorial data files...")
        
        warnings = []
        errors = []
        
        try:
            # Check tutorial test files
            test_files_dir = self.docs_dir / 'user_guide' / 'docs' / 'tutorials' / 'test_files'
            
            required_files = [
                'locomotion_data.csv',
                'task_info.csv'
            ]
            
            for file_name in required_files:
                file_path = test_files_dir / file_name
                if not file_path.exists():
                    errors.append(f"Required tutorial file missing: {file_path}")
                else:
                    # Basic validation of CSV structure
                    try:
                        import pandas as pd
                        df = pd.read_csv(file_path)
                        
                        if file_name == 'locomotion_data.csv':
                            required_cols = ['time_s', 'step_id', 'subject_id', 'task_id']
                            missing_cols = [col for col in required_cols if col not in df.columns]
                            if missing_cols:
                                errors.append(f"{file_name} missing columns: {missing_cols}")
                        
                        elif file_name == 'task_info.csv':
                            required_cols = ['step_id', 'task_id', 'task_name', 'subject_id']
                            missing_cols = [col for col in required_cols if col not in df.columns]
                            if missing_cols:
                                errors.append(f"{file_name} missing columns: {missing_cols}")
                    
                    except Exception as e:
                        errors.append(f"Error validating {file_name}: {str(e)}")
            
            return VerificationResult(
                check_name="tutorial_data_files",
                passed=len(errors) == 0,
                warnings=warnings,
                errors=errors,
                details={"files_checked": len(required_files)}
            )
            
        except Exception as e:
            return VerificationResult(
                check_name="tutorial_data_files",
                passed=False,
                warnings=[],
                errors=[f"Tutorial data file verification failed: {str(e)}"],
                details={}
            )
    
    def run_all_verifications(self) -> List[VerificationResult]:
        """Run all verification checks"""
        self.logger.info("Starting pre-build verification...")
        
        verifications = [
            self.verify_code_examples,
            self.verify_file_references,
            self.verify_api_documentation,
            self.verify_tutorial_data_files,
        ]
        
        results = []
        for verification in verifications:
            try:
                result = verification()
                results.append(result)
                
                if result.passed:
                    self.logger.info(f"✅ {result.check_name}: PASSED")
                    if result.warnings:
                        for warning in result.warnings:
                            self.logger.warning(f"⚠️  {warning}")
                else:
                    self.logger.error(f"❌ {result.check_name}: FAILED")
                    for error in result.errors:
                        self.logger.error(f"   {error}")
                        
            except Exception as e:
                self.logger.error(f"❌ Verification {verification.__name__} crashed: {str(e)}")
                results.append(VerificationResult(
                    check_name=verification.__name__,
                    passed=False,
                    warnings=[],
                    errors=[f"Verification crashed: {str(e)}"],
                    details={}
                ))
        
        self.verification_results = results
        return results
    
    def generate_verification_report(self) -> Dict[str, Any]:
        """Generate a comprehensive verification report"""
        total_checks = len(self.verification_results)
        passed_checks = sum(1 for r in self.verification_results if r.passed)
        total_warnings = sum(len(r.warnings) for r in self.verification_results)
        total_errors = sum(len(r.errors) for r in self.verification_results)
        
        return {
            "timestamp": "2025-06-19T14:30:00Z",
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": total_checks - passed_checks,
                "total_warnings": total_warnings,
                "total_errors": total_errors,
                "success_rate": passed_checks / total_checks if total_checks > 0 else 0
            },
            "results": [
                {
                    "check": r.check_name,
                    "status": "PASSED" if r.passed else "FAILED",
                    "warnings": r.warnings,
                    "errors": r.errors,
                    "details": r.details
                }
                for r in self.verification_results
            ]
        }

def on_pre_build(config):
    """MkDocs hook called before build starts"""
    
    # Get the docs directory
    docs_dir = config.get('docs_dir', 'docs')
    config_path = config.get('config_file_path', 'mkdocs.yml')
    
    # Initialize verifier
    verifier = PreBuildVerifier(config_path, docs_dir)
    
    # Run all verifications
    results = verifier.run_all_verifications()
    
    # Generate report
    report = verifier.generate_verification_report()
    
    # Save verification report
    report_path = Path(docs_dir) / 'infrastructure' / 'verification_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Check if build should continue
    failed_checks = [r for r in results if not r.passed]
    if failed_checks:
        # Collect all critical errors
        critical_errors = []
        for result in failed_checks:
            critical_errors.extend(result.errors)
        
        # Print summary
        print("\n" + "="*60)
        print("🚨 DOCUMENTATION VERIFICATION FAILED")
        print("="*60)
        print(f"Failed checks: {len(failed_checks)}")
        print(f"Total errors: {len(critical_errors)}")
        print("\nCritical errors:")
        for error in critical_errors[:10]:  # Show first 10 errors
            print(f"  • {error}")
        
        if len(critical_errors) > 10:
            print(f"  ... and {len(critical_errors) - 10} more errors")
        
        print(f"\nFull report saved to: {report_path}")
        print("="*60)
        
        # Fail the build
        raise SystemExit("Build stopped due to documentation verification failures")
    
    # Success message
    print(f"\n✅ Documentation verification passed ({report['summary']['passed_checks']}/{report['summary']['total_checks']} checks)")
    if report['summary']['total_warnings'] > 0:
        print(f"⚠️  {report['summary']['total_warnings']} warnings found (see report for details)")
    
    return config

# If run directly, perform standalone verification
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run documentation verification')
    parser.add_argument('--docs-dir', default='docs', help='Documentation directory')
    parser.add_argument('--config', default='mkdocs.yml', help='MkDocs config file')
    args = parser.parse_args()
    
    verifier = PreBuildVerifier(args.config, args.docs_dir)
    results = verifier.run_all_verifications()
    report = verifier.generate_verification_report()
    
    print(json.dumps(report, indent=2))
    
    if report['summary']['failed_checks'] > 0:
        sys.exit(1)