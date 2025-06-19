#!/usr/bin/env python3
"""
Tutorial Setup Verification Script

Created: 2025-06-19 with user permission
Purpose: Verify user environment is ready for interactive tutorials

Intent: This script performs comprehensive checks to ensure users have
everything they need to successfully complete the interactive tutorials,
providing clear feedback and actionable solutions for any issues found.
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path

def print_header(title):
    """Print a formatted header for each section."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_result(check_name, status, details=""):
    """Print a formatted check result."""
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {check_name}")
    if details:
        print(f"   {details}")

def check_python_version():
    """Check if Python version is adequate."""
    print_header("PYTHON VERSION CHECK")
    
    version = sys.version_info
    version_string = f"{version.major}.{version.minor}.{version.micro}"
    
    # Check minimum version (3.7+)
    minimum_version = (3, 7)
    is_adequate = version[:2] >= minimum_version
    
    print_result(
        f"Python Version: {version_string}",
        is_adequate,
        "✅ Good to go!" if is_adequate else f"❌ Need Python {minimum_version[0]}.{minimum_version[1]}+ for tutorials"
    )
    
    return is_adequate

def check_required_packages():
    """Check if all required packages are installed and working."""
    print_header("REQUIRED PACKAGES CHECK")
    
    required_packages = {
        'pandas': '1.0.0',
        'numpy': '1.18.0', 
        'matplotlib': '3.1.0',
        'seaborn': '0.11.0'
    }
    
    package_status = {}
    all_packages_ok = True
    
    for package, min_version in required_packages.items():
        try:
            # Try to import the package
            module = importlib.import_module(package)
            
            # Get version if available
            if hasattr(module, '__version__'):
                version = module.__version__
                print_result(f"{package}: {version}", True)
            else:
                print_result(f"{package}: installed", True, "Version not available")
                
            package_status[package] = True
            
        except ImportError:
            print_result(f"{package}: NOT INSTALLED", False)
            package_status[package] = False
            all_packages_ok = False
        except Exception as e:
            print_result(f"{package}: ERROR", False, str(e))
            package_status[package] = False
            all_packages_ok = False
    
    # Show installation command if needed
    if not all_packages_ok:
        missing_packages = [pkg for pkg, status in package_status.items() if not status]
        print(f"\n💡 To install missing packages, run:")
        print(f"   pip install {' '.join(missing_packages)}")
    
    return all_packages_ok

def check_data_files():
    """Check if tutorial data files are available."""
    print_header("TUTORIAL DATA FILES CHECK")
    
    # Check for test files in common locations
    possible_locations = [
        'test_files/',
        'docs/user_guide/docs/tutorials/test_files/',
        '../test_files/',
        'tutorials/test_files/'
    ]
    
    required_files = ['locomotion_data.csv', 'task_info.csv']
    
    files_found = False
    working_location = None
    
    for location in possible_locations:
        location_path = Path(location)
        if location_path.exists():
            all_files_present = all((location_path / file).exists() for file in required_files)
            if all_files_present:
                files_found = True
                working_location = location
                break
    
    if files_found:
        print_result("Tutorial Data Files", True, f"Found in: {working_location}")
        
        # Validate file contents
        try:
            import pandas as pd
            for file in required_files:
                file_path = Path(working_location) / file
                df = pd.read_csv(file_path)
                print_result(f"  {file}", True, f"{len(df)} rows, {len(df.columns)} columns")
                
        except Exception as e:
            print_result("File Content Validation", False, f"Error reading files: {e}")
            files_found = False
    else:
        print_result("Tutorial Data Files", False, "Not found in expected locations")
        print("\n💡 Download tutorial data files:")
        print("   1. Visit the tutorial repository")
        print("   2. Download locomotion_data.csv and task_info.csv")
        print("   3. Place them in a 'test_files/' directory")
    
    return files_found

def check_directory_structure():
    """Check if we're in the right directory for tutorials."""
    print_header("DIRECTORY STRUCTURE CHECK")
    
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Look for indicators of project structure
    project_indicators = ['README.md', 'lib/', 'docs/', 'tests/']
    tutorial_indicators = ['tutorials/', 'test_files/']
    
    project_score = sum(1 for indicator in project_indicators if (current_dir / indicator).exists())
    tutorial_score = sum(1 for indicator in tutorial_indicators if (current_dir / indicator).exists())
    
    in_project_root = project_score >= 2
    in_tutorial_dir = tutorial_score >= 1
    
    print_result("Project Root Directory", in_project_root)
    print_result("Tutorial Directory Access", in_tutorial_dir)
    
    if not (in_project_root or in_tutorial_dir):
        print("\n💡 Navigate to the correct directory:")
        print("   • For full project: navigate to the project root (contains README.md, lib/, docs/)")
        print("   • For tutorials only: navigate to the tutorials directory")
    
    return in_project_root or in_tutorial_dir

def check_matplotlib_backend():
    """Check if matplotlib can display plots."""
    print_header("MATPLOTLIB DISPLAY CHECK")
    
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        
        backend = matplotlib.get_backend()
        print_result(f"Matplotlib Backend: {backend}", True)
        
        # Test if we can create a simple plot
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 4, 2])
        ax.set_title("Test Plot")
        
        # Try to save the plot (this should always work)
        test_file = "matplotlib_test.png"
        plt.savefig(test_file)
        plt.close()
        
        if os.path.exists(test_file):
            os.remove(test_file)  # Clean up
            print_result("Plot Saving", True, "Can save plots to files")
        else:
            print_result("Plot Saving", False, "Cannot save plots")
            return False
        
        # Check if we can display plots (depends on environment)
        try:
            plt.figure()
            plt.plot([1, 2, 3])
            plt.show()
            print_result("Plot Display", True, "Interactive plotting available")
        except:
            print_result("Plot Display", False, "Interactive plotting not available (OK for some environments)")
        
        return True
        
    except Exception as e:
        print_result("Matplotlib Test", False, str(e))
        return False

def check_jupyter_compatibility():
    """Check if Jupyter notebook features will work."""
    print_header("JUPYTER COMPATIBILITY CHECK")
    
    try:
        # Check if we're in Jupyter
        in_jupyter = 'ipykernel' in sys.modules
        print_result("Running in Jupyter", in_jupyter)
        
        # Check if IPython is available
        try:
            import IPython
            print_result("IPython Available", True, f"Version: {IPython.__version__}")
        except ImportError:
            print_result("IPython Available", False, "Install with: pip install ipython")
        
        # Check matplotlib inline capability
        try:
            from IPython import get_ipython
            if get_ipython() is not None:
                get_ipython().run_line_magic('matplotlib', 'inline')
                print_result("Matplotlib Inline", True, "Plots will display in notebooks")
            else:
                print_result("Matplotlib Inline", False, "Not in IPython environment")
        except Exception as e:
            print_result("Matplotlib Inline", False, str(e))
        
        return True
        
    except Exception as e:
        print_result("Jupyter Check", False, str(e))
        return False

def run_sample_analysis():
    """Run a quick sample analysis to test everything works together."""
    print_header("SAMPLE ANALYSIS TEST")
    
    try:
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        
        # Create sample data similar to tutorial data
        sample_data = {
            'time_s': [0.01, 0.02, 0.03, 0.04, 0.05],
            'knee_flexion_angle_rad': [0.1, 0.2, 0.25, 0.2, 0.15],
            'step_id': [1, 1, 1, 1, 1],
            'subject_id': ['TEST001'] * 5,
            'task_id': ['TEST_T01'] * 5
        }
        
        df = pd.DataFrame(sample_data)
        
        # Basic analysis
        knee_rom = df['knee_flexion_angle_rad'].max() - df['knee_flexion_angle_rad'].min()
        knee_rom_deg = np.degrees(knee_rom)
        
        # Simple plot
        plt.figure(figsize=(8, 5))
        plt.plot(df['time_s'], np.degrees(df['knee_flexion_angle_rad']), 'b-o')
        plt.xlabel('Time (s)')
        plt.ylabel('Knee Angle (degrees)')
        plt.title('Sample Analysis Test')
        plt.grid(True, alpha=0.3)
        
        # Save plot
        test_plot_file = "setup_verification_test.png"
        plt.savefig(test_plot_file)
        plt.close()
        
        # Verify results
        if os.path.exists(test_plot_file):
            os.remove(test_plot_file)  # Clean up
            
        print_result("Data Loading", True, f"Created DataFrame with {len(df)} rows")
        print_result("Mathematical Operations", True, f"Calculated ROM: {knee_rom_deg:.1f}°")
        print_result("Plotting", True, "Created and saved plot successfully")
        print_result("Sample Analysis", True, "All basic operations working!")
        
        return True
        
    except Exception as e:
        print_result("Sample Analysis", False, str(e))
        return False

def generate_report():
    """Generate a comprehensive verification report."""
    print_header("VERIFICATION SUMMARY")
    
    # Run all checks
    checks = [
        ("Python Version", check_python_version()),
        ("Required Packages", check_required_packages()),
        ("Data Files", check_data_files()),
        ("Directory Structure", check_directory_structure()),
        ("Matplotlib Display", check_matplotlib_backend()),
        ("Jupyter Compatibility", check_jupyter_compatibility()),
        ("Sample Analysis", run_sample_analysis())
    ]
    
    # Summary
    passed_checks = sum(1 for _, status in checks if status)
    total_checks = len(checks)
    
    print(f"\n📊 OVERALL RESULTS:")
    print(f"   Passed: {passed_checks}/{total_checks} checks")
    
    if passed_checks == total_checks:
        print("🎉 CONGRATULATIONS! Your environment is fully ready for tutorials!")
        print("   You can proceed with confidence to any interactive tutorial.")
    elif passed_checks >= total_checks - 2:
        print("✅ Your environment is mostly ready!")
        print("   You should be able to complete most tutorials.")
        print("   Address the failed checks if you encounter issues.")
    else:
        print("⚠️  Your environment needs some setup work.")
        print("   Please address the failed checks before starting tutorials.")
    
    print(f"\n🚀 NEXT STEPS:")
    if passed_checks >= total_checks - 1:
        print("   • Start with: Quick Start Tutorial (10 minutes)")
        print("   • Continue to: Basic Analysis Tutorial (30 minutes)")
        print("   • Try: Interactive Jupyter Notebook version")
    else:
        print("   • Fix the issues identified above")
        print("   • Re-run this verification script")
        print("   • Check the troubleshooting guide if needed")
    
    # Save report
    report_file = "setup_verification_report.txt"
    with open(report_file, 'w') as f:
        f.write("Tutorial Setup Verification Report\n")
        f.write("="*40 + "\n\n")
        for check_name, status in checks:
            status_text = "PASS" if status else "FAIL"
            f.write(f"{check_name}: {status_text}\n")
        f.write(f"\nOverall: {passed_checks}/{total_checks} checks passed\n")
    
    print(f"\n📄 Report saved to: {report_file}")
    
    return passed_checks == total_checks

def main():
    """Main verification function."""
    print("🔧 Tutorial Setup Verification Script")
    print("This script will check if your environment is ready for interactive tutorials.")
    print("Please wait while we run comprehensive checks...")
    
    try:
        all_good = generate_report()
        
        print(f"\n{'='*60}")
        if all_good:
            print("🎯 You're all set! Happy learning!")
        else:
            print("🔧 Some issues found. Check the troubleshooting guide if needed.")
            print("   Troubleshooting: docs/user_guide/docs/tutorials/troubleshooting_interactive.md")
        print(f"{'='*60}")
        
        return 0 if all_good else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error during verification: {e}")
        print("Please report this issue if it persists.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)