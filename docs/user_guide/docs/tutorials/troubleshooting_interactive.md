# 🔧 Interactive Troubleshooting Guide

**🎯 Goal:** Quickly resolve common issues and get back to learning

---

## **Quick Problem Solver**

**Select your issue category:**

### 📁 [Data Loading Problems](#data-loading-problems)
- File not found errors
- Import/export issues
- Data format problems

### 🐍 [Python Environment Issues](#python-environment-issues)
- Package installation
- Import errors
- Version conflicts

### 📊 [Plotting & Visualization](#plotting-visualization-issues)
- Plots not displaying
- Formatting problems
- Save/export issues

### 🔢 [Analysis & Calculations](#analysis-calculation-issues)
- Unexpected results
- Mathematical errors
- Performance problems

### 💻 [System & Setup](#system-setup-issues)
- Directory problems
- Path issues
- Permission errors

---

## **Data Loading Problems**

### ❌ **"File not found" Error**

**Problem:** `FileNotFoundError: [Errno 2] No such file or directory: 'locomotion_data.csv'`

<details>
<summary>🔍 <strong>Diagnostic Steps</strong></summary>

```python
import os
from pathlib import Path

# Check current directory
print("Current directory:", os.getcwd())
print("Files in current directory:")
for file in os.listdir('.'):
    print(f"  - {file}")

# Check if specific files exist
required_files = ['locomotion_data.csv', 'task_info.csv']
for file in required_files:
    exists = os.path.exists(file)
    print(f"{file}: {'✅ Found' if exists else '❌ Missing'}")
```
</details>

**Solutions (try in order):**

1. **Download files again:**
   - [locomotion_data.csv](test_files/locomotion_data.csv)
   - [task_info.csv](test_files/task_info.csv)
   - Save in your current working directory

2. **Check directory location:**
   ```python
   # Navigate to correct directory
   import os
   os.chdir('path/to/your/tutorial/files')
   print("New directory:", os.getcwd())
   ```

3. **Use absolute paths:**
   ```python
   import pandas as pd
   # Replace with your actual file paths
   df = pd.read_csv('/full/path/to/locomotion_data.csv')
   ```

### ❌ **"Empty DataFrame" or "No Data Loaded"**

**Problem:** Data loads but appears empty or has unexpected structure

<details>
<summary>🔍 <strong>Data Validation Code</strong></summary>

```python
import pandas as pd

# Load and inspect data
df = pd.read_csv('locomotion_data.csv')

print("Data shape:", df.shape)
print("Column names:", list(df.columns))
print("Data types:")
print(df.dtypes)
print("\nFirst few rows:")
print(df.head())
print("\nData summary:")
print(df.describe())
```
</details>

**Solutions:**

1. **Check file encoding:**
   ```python
   df = pd.read_csv('locomotion_data.csv', encoding='utf-8')
   # Try different encodings: 'latin-1', 'ascii', 'utf-16'
   ```

2. **Verify delimiter:**
   ```python
   df = pd.read_csv('locomotion_data.csv', sep=',')  # or sep=';' or sep='\t'
   ```

3. **Handle missing values:**
   ```python
   df = pd.read_csv('locomotion_data.csv', na_values=['', 'NA', 'NULL', 'NaN'])
   print("Missing values per column:")
   print(df.isnull().sum())
   ```

---

## **Python Environment Issues**

### ❌ **"ModuleNotFoundError" for Required Packages**

**Problem:** `ModuleNotFoundError: No module named 'pandas'`

**Solutions:**

1. **Install missing packages:**
   ```bash
   pip install pandas numpy matplotlib seaborn
   ```

2. **For Jupyter notebooks:**
   ```python
   import sys
   !{sys.executable} -m pip install pandas numpy matplotlib seaborn
   ```

3. **Check installation:**
   ```python
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   print("✅ All packages imported successfully!")
   print(f"Pandas version: {pd.__version__}")
   print(f"NumPy version: {np.__version__}")
   ```

### ❌ **Import Errors for Custom Libraries**

**Problem:** Cannot import `LocomotionData` or other custom classes

<details>
<summary>🔍 <strong>Path Diagnostic Code</strong></summary>

```python
import sys
import os
from pathlib import Path

print("Python path:")
for p in sys.path:
    print(f"  - {p}")

# Check for library files
lib_path = Path.cwd() / "lib" / "core"
print(f"\nLooking for library at: {lib_path}")
print(f"Library exists: {lib_path.exists()}")

if lib_path.exists():
    print("Files in library:")
    for file in lib_path.glob("*.py"):
        print(f"  - {file.name}")
```
</details>

**Solutions:**

1. **Add library to path:**
   ```python
   import sys
   from pathlib import Path
   
   # Add library path
   lib_path = Path.cwd() / "lib" / "core"
   if lib_path.exists():
       sys.path.append(str(lib_path))
       print(f"✅ Added to path: {lib_path}")
   ```

2. **Navigate to project root:**
   ```python
   import os
   # Change to project root directory
   os.chdir('path/to/project/root')
   # Project root should contain: README.md, lib/, docs/, etc.
   ```

---

## **Plotting & Visualization Issues**

### ❌ **Plots Not Displaying**

**Problem:** Code runs without errors but no plots appear

**Solutions:**

1. **Add explicit show command:**
   ```python
   import matplotlib.pyplot as plt
   
   # Your plotting code here
   plt.figure(figsize=(10, 6))
   plt.plot([1, 2, 3], [1, 4, 2])
   
   # Add this line
   plt.show()
   ```

2. **For Jupyter notebooks:**
   ```python
   %matplotlib inline
   import matplotlib.pyplot as plt
   ```

3. **Check backend:**
   ```python
   import matplotlib
   print("Current backend:", matplotlib.get_backend())
   
   # Try different backend if needed
   matplotlib.use('Agg')  # For saving files only
   # or
   matplotlib.use('TkAgg')  # For interactive display
   ```

### ❌ **Plot Formatting Issues**

**Problem:** Plots look unprofessional or have layout issues

<details>
<summary>🎨 <strong>Professional Formatting Code</strong></summary>

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Set professional style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Configure matplotlib for high quality
plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 12,
    'figure.titlesize': 18,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

# Example well-formatted plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot([1, 2, 3], [1, 4, 2], linewidth=2)
ax.set_xlabel('X Label')
ax.set_ylabel('Y Label')
ax.set_title('Professional Plot Title')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```
</details>

---

## **Analysis & Calculation Issues**

### ❌ **Unexpected or Incorrect Results**

**Problem:** Calculations produce unrealistic values

<details>
<summary>🔍 <strong>Data Quality Check Code</strong></summary>

```python
import pandas as pd
import numpy as np

def validate_biomechanical_data(df):
    """Comprehensive data validation for biomechanical datasets."""
    
    print("🔍 Data Quality Report:")
    print("=" * 40)
    
    # Check for missing values
    missing = df.isnull().sum()
    print("Missing values:")
    for col, count in missing.items():
        if count > 0:
            print(f"  ❌ {col}: {count} missing ({count/len(df)*100:.1f}%)")
    
    # Check joint angle ranges (convert to degrees for easier interpretation)
    angle_cols = [col for col in df.columns if 'angle_rad' in col]
    
    for col in angle_cols:
        if col in df.columns:
            angles_deg = np.degrees(df[col])
            print(f"\n{col}:")
            print(f"  Range: {angles_deg.min():.1f}° to {angles_deg.max():.1f}°")
            
            # Check for realistic ranges
            joint = col.split('_')[0]
            if joint == 'knee':
                if angles_deg.min() < -20 or angles_deg.max() > 120:
                    print(f"  ⚠️  Warning: Knee angles outside typical range (-20° to 120°)")
            elif joint == 'hip':
                if angles_deg.min() < -40 or angles_deg.max() > 80:
                    print(f"  ⚠️  Warning: Hip angles outside typical range (-40° to 80°)")
    
    # Check for duplicate entries
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        print(f"\n❌ Found {duplicates} duplicate rows")
    
    # Check time progression
    if 'time_s' in df.columns:
        time_diff = df['time_s'].diff().dropna()
        if (time_diff <= 0).any():
            print(f"❌ Warning: Non-monotonic time progression detected")
    
    print("\n✅ Data validation complete")

# Run validation
validate_biomechanical_data(your_dataframe)
```
</details>

**Solutions:**

1. **Check units and conversions:**
   ```python
   # Ensure angles are in radians for calculations
   import numpy as np
   
   # Convert degrees to radians if needed
   df['angle_rad'] = np.radians(df['angle_deg'])
   
   # Convert radians to degrees for display
   df['angle_deg'] = np.degrees(df['angle_rad'])
   ```

2. **Validate calculation logic:**
   ```python
   # Example: Range of Motion calculation
   def calculate_rom_with_validation(angles):
       """Calculate ROM with validation checks."""
       if len(angles) == 0:
           print("❌ Error: No data for ROM calculation")
           return np.nan
       
       rom = np.max(angles) - np.min(angles)
       rom_deg = np.degrees(rom)
       
       # Validation
       if rom_deg > 180:
           print(f"⚠️  Warning: ROM > 180° ({rom_deg:.1f}°) - check data")
       elif rom_deg < 5:
           print(f"⚠️  Warning: Very small ROM ({rom_deg:.1f}°) - check data")
       
       return rom
   ```

### ❌ **Performance Issues / Slow Calculations**

**Problem:** Code runs very slowly or uses too much memory

<details>
<summary>⚡ <strong>Performance Optimization Code</strong></summary>

```python
import time
import numpy as np
import pandas as pd

def optimize_data_processing(df):
    """Optimize data processing for large datasets."""
    
    print("⚡ Performance Optimization:")
    print("-" * 30)
    
    # Check data size
    memory_usage = df.memory_usage(deep=True).sum() / 1024**2  # MB
    print(f"Dataset size: {len(df)} rows, {memory_usage:.1f} MB")
    
    # Optimize data types
    original_memory = df.memory_usage(deep=True).sum()
    
    # Convert to more efficient types
    for col in df.columns:
        if df[col].dtype == 'object':
            # Try to convert to category if low cardinality
            if df[col].nunique() / len(df) < 0.5:
                df[col] = df[col].astype('category')
        elif df[col].dtype == 'int64':
            # Use smaller int types if possible
            if df[col].min() >= -32768 and df[col].max() <= 32767:
                df[col] = df[col].astype('int16')
        elif df[col].dtype == 'float64':
            # Use float32 if precision allows
            df[col] = pd.to_numeric(df[col], downcast='float')
    
    new_memory = df.memory_usage(deep=True).sum()
    savings = (original_memory - new_memory) / original_memory * 100
    
    print(f"✅ Memory optimized: {savings:.1f}% reduction")
    
    return df

# Efficient processing for large datasets
def efficient_groupby_analysis(df, group_cols, value_cols):
    """Fast groupby operations for biomechanical analysis."""
    
    start_time = time.time()
    
    # Use categorical data for grouping
    for col in group_cols:
        if df[col].dtype != 'category':
            df[col] = df[col].astype('category')
    
    # Vectorized operations
    results = df.groupby(group_cols)[value_cols].agg(['mean', 'std', 'min', 'max'])
    
    elapsed = time.time() - start_time
    print(f"⚡ Groupby completed in {elapsed:.3f} seconds")
    
    return results
```
</details>

---

## **System & Setup Issues**

### ❌ **Directory and Path Problems**

**Problem:** Cannot find files or directories

<details>
<summary>📁 <strong>Directory Navigation Code</strong></summary>

```python
import os
from pathlib import Path

def diagnose_directory_structure():
    """Diagnose and fix directory structure issues."""
    
    print("📁 Directory Diagnosis:")
    print("=" * 30)
    
    # Current location
    current = Path.cwd()
    print(f"Current directory: {current}")
    
    # List current directory contents
    print("\nCurrent directory contents:")
    for item in current.iterdir():
        item_type = "📁" if item.is_dir() else "📄"
        print(f"  {item_type} {item.name}")
    
    # Look for project structure
    expected_dirs = ['lib', 'docs', 'tests', 'scripts']
    expected_files = ['README.md', 'LICENSE']
    
    print("\nProject structure check:")
    for dirname in expected_dirs:
        path = current / dirname
        status = "✅" if path.exists() else "❌"
        print(f"  {status} {dirname}/")
    
    for filename in expected_files:
        path = current / filename
        status = "✅" if path.exists() else "❌"
        print(f"  {status} {filename}")
    
    # Suggest navigation
    if not any((current / d).exists() for d in expected_dirs):
        print("\n💡 Suggestion: Navigate to project root directory")
        print("   The project root should contain lib/, docs/, README.md, etc.")
        
        # Look for project root in parent directories
        parent = current.parent
        for i in range(3):  # Check up to 3 levels up
            if any((parent / d).exists() for d in expected_dirs):
                print(f"   Found project structure at: {parent}")
                print(f"   Use: os.chdir(r'{parent}')")
                break
            parent = parent.parent

# Run diagnosis
diagnose_directory_structure()
```
</details>

**Solutions:**

1. **Navigate to correct directory:**
   ```python
   import os
   
   # Method 1: Use absolute path
   os.chdir('/full/path/to/your/project')
   
   # Method 2: Navigate step by step
   os.chdir('..')  # Go up one level
   os.chdir('locomotion-data-standardization')  # Enter project
   
   # Verify location
   print("Current directory:", os.getcwd())
   ```

2. **Set up proper project structure:**
   ```python
   import os
   from pathlib import Path
   
   # Create necessary directories if missing
   required_dirs = ['data', 'results', 'plots']
   for dirname in required_dirs:
       Path(dirname).mkdir(exist_ok=True)
       print(f"✅ Created/verified: {dirname}/")
   ```

---

## **Emergency Reset Solutions**

### 🚨 **"Nothing Works" - Complete Reset**

If multiple issues persist, try this complete reset:

<details>
<summary>🔄 <strong>Complete Environment Reset</strong></summary>

```python
# 1. Clean import and restart
import importlib
import sys

# Clear cached modules
modules_to_reload = [mod for mod in sys.modules.keys() if 'locomotion' in mod.lower()]
for mod in modules_to_reload:
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])

# 2. Re-import everything fresh
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

# 3. Reset matplotlib
plt.close('all')
plt.rcdefaults()

# 4. Verify basic functionality
print("🔄 Environment Reset Complete")
print("Testing basic functionality:")

# Test data loading
try:
    df = pd.DataFrame({'test': [1, 2, 3]})
    print("✅ Pandas working")
except Exception as e:
    print(f"❌ Pandas issue: {e}")

# Test plotting
try:
    plt.figure()
    plt.plot([1, 2, 3])
    plt.close()
    print("✅ Matplotlib working")
except Exception as e:
    print(f"❌ Matplotlib issue: {e}")

# Test file system
try:
    print(f"✅ Current directory: {os.getcwd()}")
    print(f"✅ Directory accessible: {os.access('.', os.R_OK)}")
except Exception as e:
    print(f"❌ File system issue: {e}")

print("✅ Reset complete - try your analysis again")
```
</details>

---

## **Getting Additional Help**

### 🆘 **When to Seek Help**

If you've tried the solutions above and still have issues:

1. **Check if it's a known issue:**
   - Look through [GitHub Issues](https://github.com/your-repo/issues)
   - Search recent discussions

2. **Prepare a good question:**
   ```python
   # Include this information when asking for help:
   import sys
   import pandas as pd
   import numpy as np
   import matplotlib
   
   print("System Information:")
   print(f"Python version: {sys.version}")
   print(f"Pandas version: {pd.__version__}")
   print(f"NumPy version: {np.__version__}")
   print(f"Matplotlib version: {matplotlib.__version__}")
   print(f"Operating system: {sys.platform}")
   print(f"Current directory: {os.getcwd()}")
   ```

3. **Create a minimal example:**
   ```python
   # Minimal code that reproduces your issue
   import pandas as pd
   
   # This fails:
   df = pd.read_csv('my_file.csv')
   print(df.head())
   
   # Error message: [paste exact error here]
   ```

### 📞 **Support Channels**

- **[GitHub Discussions](https://github.com/your-repo/discussions)** - Community support
- **[GitHub Issues](https://github.com/your-repo/issues)** - Bug reports
- **[Documentation](../reference/api_reference.md)** - Complete reference
- **[FAQ](faq.md)** - Frequently asked questions

---

### **📋 Quick Reference Checklist**

Before asking for help, verify:

- [ ] Files are in the correct directory
- [ ] All required packages are installed
- [ ] Python version is 3.7 or higher
- [ ] Using the correct file paths
- [ ] No typos in variable names or function calls
- [ ] Data files are not corrupted or empty
- [ ] Have tried restarting Python/Jupyter kernel

**Remember:** Most issues are common and have simple solutions. Don't hesitate to ask for help, but including the diagnostic information above will help you get faster, more accurate assistance!

---

**🔗 Return to:** [Quick Start](quick_start_interactive.md) | [Basic Analysis](basic_analysis_interactive.md) | [Tutorial Index](README.md)