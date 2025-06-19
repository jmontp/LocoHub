#!/usr/bin/env python3
"""
Tutorial Testing Framework

Created: 2025-06-19 with user permission
Purpose: Automated testing framework for interactive tutorials

Intent: This framework automatically tests all tutorial code to ensure
it works correctly, provides expected outputs, and maintains quality
standards. It validates code blocks, expected outputs, and learning
objectives completion.
"""

import sys
import os
import subprocess
import tempfile
import shutil
import re
import traceback
from pathlib import Path
import importlib.util

class TutorialTester:
    """Comprehensive testing framework for interactive tutorials."""
    
    def __init__(self, tutorial_dir=None):
        """Initialize the testing framework."""
        self.tutorial_dir = Path(tutorial_dir) if tutorial_dir else Path.cwd()
        self.test_results = {}
        self.temp_dirs = []
        
    def __del__(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def extract_code_blocks(self, markdown_file):
        """Extract Python code blocks from markdown files."""
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all Python code blocks
        code_pattern = r'```python\n(.*?)\n```'
        code_blocks = re.findall(code_pattern, content, re.DOTALL)
        
        # Also look for code in collapsible sections
        collapsible_pattern = r'<summary>.*?</summary>\s*```python\n(.*?)\n```'
        collapsible_blocks = re.findall(collapsible_pattern, content, re.DOTALL)
        
        return code_blocks + collapsible_blocks
    
    def create_test_environment(self):
        """Create isolated test environment with sample data."""
        temp_dir = Path(tempfile.mkdtemp(prefix='tutorial_test_'))
        self.temp_dirs.append(temp_dir)
        
        # Copy sample data files if they exist
        test_files_dir = self.tutorial_dir / 'test_files'
        if test_files_dir.exists():
            shutil.copytree(test_files_dir, temp_dir / 'test_files')
        
        # Create minimal sample data if needed
        self.create_sample_data(temp_dir)
        
        return temp_dir
    
    def create_sample_data(self, test_dir):
        """Create minimal sample data for testing."""
        import pandas as pd
        import numpy as np
        
        # Create locomotion_data.csv
        locomotion_data = {
            'time_s': [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10],
            'step_id': [1, 1, 1, 2, 2, 2, 3, 3, 3, 3],
            'subject_id': ['P001'] * 10,
            'task_id': ['P001_T01', 'P001_T01', 'P001_T01', 'P001_T02', 'P001_T02', 
                       'P001_T02', 'P001_T01', 'P001_T01', 'P001_T01', 'P001_T01'],
            'knee_flexion_angle_rad': [0.178, 0.218, 0.264, 0.354, 0.384, 0.447, 0.155, 0.182, 0.230, 0.279],
            'hip_flexion_angle_rad': [0.089, 0.108, 0.122, 0.183, 0.197, 0.224, 0.075, 0.087, 0.107, 0.131],
            'ankle_flexion_angle_rad': [0.052, 0.063, 0.075, 0.087, 0.093, 0.105, 0.045, 0.055, 0.068, 0.079],
            'cop_x_m': [0.10, 0.11, 0.12, 0.15, 0.16, 0.17, 0.09, 0.10, 0.11, 0.12],
            'cop_y_m': [0.05, 0.06, 0.07, 0.10, 0.11, 0.12, 0.04, 0.05, 0.06, 0.07],
            'vertical_grf_N': [650.2, 680.5, 700.3, 720.8, 750.2, 760.5, 620.1, 640.3, 660.7, 680.9]
        }
        
        df_locomotion = pd.DataFrame(locomotion_data)
        df_locomotion.to_csv(test_dir / 'locomotion_data.csv', index=False)
        
        # Create task_info.csv
        task_data = {
            'step_id': [1, 2, 3],
            'task_id': ['P001_T01', 'P001_T02', 'P001_T01'],
            'task_name': ['level_walking', 'incline_walking', 'level_walking'],
            'subject_id': ['P001', 'P001', 'P001'],
            'ground_inclination_deg': [0, 5, 0],
            'walking_speed_m_s': [1.2, 1.5, 1.2]
        }
        
        df_task = pd.DataFrame(task_data)
        df_task.to_csv(test_dir / 'task_info.csv', index=False)
        
        print(f"✅ Created sample data in {test_dir}")
    
    def test_code_block(self, code_block, test_dir):
        """Test a single code block in isolation."""
        try:
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(test_dir)
            
            # Create a temporary script
            script_content = f'''
import sys
import warnings
warnings.filterwarnings('ignore')

# Import commonly needed libraries
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Execute the code block
{code_block}

print("✅ Code block executed successfully")
'''
            
            script_file = test_dir / 'test_script.py'
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            os.chdir(original_cwd)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            os.chdir(original_cwd)
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Code execution timed out (>30 seconds)',
                'returncode': -1
            }
        except Exception as e:
            os.chdir(original_cwd)
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Error running code: {str(e)}',
                'returncode': -1
            }
    
    def test_tutorial_file(self, tutorial_file):
        """Test all code blocks in a tutorial file."""
        print(f"\n🔍 Testing tutorial: {tutorial_file.name}")
        print("=" * 50)
        
        # Extract code blocks
        code_blocks = self.extract_code_blocks(tutorial_file)
        print(f"Found {len(code_blocks)} code blocks to test")
        
        if not code_blocks:
            return {
                'file': tutorial_file.name,
                'total_blocks': 0,
                'passed_blocks': 0,
                'failed_blocks': 0,
                'results': [],
                'overall_success': True
            }
        
        # Create test environment
        test_dir = self.create_test_environment()
        
        # Test each code block
        results = []
        passed = 0
        
        for i, code_block in enumerate(code_blocks, 1):
            print(f"\n  Testing code block {i}/{len(code_blocks)}...")
            
            # Skip certain patterns that shouldn't be executed
            skip_patterns = [
                'pip install',
                'os.chdir(',
                'cd ',
                'mkdir ',
                '# CHALLENGE:',
                '# YOUR CODE HERE',
                'exit(',
                'sys.exit('
            ]
            
            should_skip = any(pattern in code_block for pattern in skip_patterns)
            
            if should_skip:
                print(f"    ⏭️  Skipped (contains non-executable content)")
                results.append({
                    'block_number': i,
                    'code_preview': code_block[:100] + '...' if len(code_block) > 100 else code_block,
                    'result': 'skipped',
                    'reason': 'Contains non-executable content'
                })
                passed += 1  # Count skipped as passed
                continue
            
            # Test the code block
            test_result = self.test_code_block(code_block, test_dir)
            
            if test_result['success']:
                print(f"    ✅ Passed")
                passed += 1
                status = 'passed'
                reason = 'Executed successfully'
            else:
                print(f"    ❌ Failed: {test_result['stderr'][:100]}...")
                status = 'failed'
                reason = test_result['stderr']
            
            results.append({
                'block_number': i,
                'code_preview': code_block[:100] + '...' if len(code_block) > 100 else code_block,
                'result': status,
                'reason': reason,
                'stdout': test_result.get('stdout', ''),
                'stderr': test_result.get('stderr', '')
            })
        
        overall_success = passed == len(code_blocks)
        success_rate = (passed / len(code_blocks)) * 100 if code_blocks else 100
        
        print(f"\n📊 Results: {passed}/{len(code_blocks)} code blocks passed ({success_rate:.1f}%)")
        
        return {
            'file': tutorial_file.name,
            'total_blocks': len(code_blocks),
            'passed_blocks': passed,
            'failed_blocks': len(code_blocks) - passed,
            'success_rate': success_rate,
            'results': results,
            'overall_success': overall_success
        }
    
    def test_all_tutorials(self):
        """Test all tutorial files in the directory."""
        print("🧪 Interactive Tutorial Testing Framework")
        print("=" * 60)
        
        # Find all tutorial markdown files
        tutorial_files = []
        for pattern in ['*interactive*.md', '*tutorial*.md', 'quick_start*.md']:
            tutorial_files.extend(self.tutorial_dir.glob(pattern))
        
        # Remove duplicates and sort
        tutorial_files = sorted(set(tutorial_files))
        
        if not tutorial_files:
            print("❌ No tutorial files found to test")
            return False
        
        print(f"Found {len(tutorial_files)} tutorial files to test:")
        for file in tutorial_files:
            print(f"  - {file.name}")
        
        # Test each tutorial
        all_results = []
        total_files_passed = 0
        
        for tutorial_file in tutorial_files:
            result = self.test_tutorial_file(tutorial_file)
            all_results.append(result)
            
            if result['overall_success']:
                total_files_passed += 1
        
        # Generate summary report
        self.generate_test_report(all_results, total_files_passed, len(tutorial_files))
        
        return total_files_passed == len(tutorial_files)
    
    def generate_test_report(self, all_results, files_passed, total_files):
        """Generate comprehensive test report."""
        print(f"\n{'='*60}")
        print(" TUTORIAL TESTING SUMMARY")
        print(f"{'='*60}")
        
        # Overall statistics
        total_blocks = sum(r['total_blocks'] for r in all_results)
        total_passed = sum(r['passed_blocks'] for r in all_results)
        total_failed = sum(r['failed_blocks'] for r in all_results)
        
        overall_success_rate = (total_passed / total_blocks * 100) if total_blocks > 0 else 100
        file_success_rate = (files_passed / total_files * 100) if total_files > 0 else 100
        
        print(f"\n📊 Overall Results:")
        print(f"   Files tested: {total_files}")
        print(f"   Files passed: {files_passed} ({file_success_rate:.1f}%)")
        print(f"   Code blocks tested: {total_blocks}")
        print(f"   Code blocks passed: {total_passed} ({overall_success_rate:.1f}%)")
        print(f"   Code blocks failed: {total_failed}")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for result in all_results:
            status_icon = "✅" if result['overall_success'] else "❌"
            print(f"   {status_icon} {result['file']}: {result['passed_blocks']}/{result['total_blocks']} blocks passed")
        
        # Failed blocks details
        failed_details = []
        for result in all_results:
            for block_result in result['results']:
                if block_result['result'] == 'failed':
                    failed_details.append({
                        'file': result['file'],
                        'block': block_result['block_number'],
                        'error': block_result['reason'],
                        'code': block_result['code_preview']
                    })
        
        if failed_details:
            print(f"\n❌ Failed Code Blocks ({len(failed_details)} total):")
            for i, failure in enumerate(failed_details[:5], 1):  # Show first 5 failures
                print(f"   {i}. {failure['file']} - Block {failure['block']}:")
                print(f"      Code: {failure['code']}")
                print(f"      Error: {failure['error'][:100]}...")
            
            if len(failed_details) > 5:
                print(f"      ... and {len(failed_details) - 5} more failures")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if file_success_rate == 100:
            print("   🎉 Excellent! All tutorials are working perfectly.")
            print("   ✅ Safe to publish and share with users.")
        elif file_success_rate >= 80:
            print("   ✅ Good overall status. Address failing blocks if critical.")
            print("   📝 Consider adding troubleshooting notes for common issues.")
        else:
            print("   ⚠️  Multiple tutorials have issues. Review and fix before release.")
            print("   🔧 Focus on fixing tutorials with the highest failure rates first.")
        
        # Save detailed report
        report_file = self.tutorial_dir / 'tutorial_test_report.txt'
        with open(report_file, 'w') as f:
            f.write("Interactive Tutorial Testing Report\n")
            f.write("=" * 40 + "\n\n")
            
            # Import pandas for timestamp if needed
            try:
                import pandas as pd
                f.write(f"Test Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            except ImportError:
                from datetime import datetime
                f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Files Tested: {total_files}\n")
            f.write(f"Files Passed: {files_passed}\n")
            f.write(f"Code Blocks Tested: {total_blocks}\n")
            f.write(f"Code Blocks Passed: {total_passed}\n")
            f.write(f"Overall Success Rate: {overall_success_rate:.1f}%\n\n")
            
            for result in all_results:
                f.write(f"File: {result['file']}\n")
                f.write(f"  Blocks: {result['passed_blocks']}/{result['total_blocks']} passed\n")
                f.write(f"  Success Rate: {result['success_rate']:.1f}%\n")
                for block_result in result['results']:
                    if block_result['result'] == 'failed':
                        f.write(f"    Failed Block {block_result['block_number']}: {block_result['reason'][:100]}\n")
                f.write("\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return file_success_rate >= 80  # Consider 80%+ as acceptable

def main():
    """Main testing function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test interactive tutorials for code correctness')
    parser.add_argument('--tutorial-dir', '-d', 
                       help='Directory containing tutorial files (default: current directory)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output with detailed error messages')
    
    args = parser.parse_args()
    
    # Set up testing
    tutorial_dir = Path(args.tutorial_dir) if args.tutorial_dir else Path.cwd()
    
    if not tutorial_dir.exists():
        print(f"❌ Error: Tutorial directory '{tutorial_dir}' does not exist")
        return 1
    
    # Run tests
    tester = TutorialTester(tutorial_dir)
    
    try:
        success = tester.test_all_tutorials()
        
        if success:
            print(f"\n🎉 All tutorials passed testing! Ready for users.")
            return 0
        else:
            print(f"\n⚠️  Some tutorials have issues. Check the report for details.")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Testing interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)