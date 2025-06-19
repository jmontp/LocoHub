# 🚀 Quick Start: Your First Locomotion Analysis

**⏱️ Time:** 10 minutes | **📈 Level:** Beginner | **🎯 Goal:** Load data and create your first biomechanical plot

---

## **Progress Tracker**
**Step 1 of 4** ⏳ | **Estimated Time Remaining: 10 minutes**

✅ **What you'll accomplish:**
- Load biomechanical data in under 2 minutes
- Create a professional joint angle plot
- Understand basic data structure
- Get your first "success" moment with real data

---

## **Prerequisites Checklist**
Before starting, ensure you have:
- [ ] Python 3.7+ installed
- [ ] 5 minutes of uninterrupted time
- [ ] Basic familiarity with Python (can run simple scripts)

**❓ Not sure?** Run this quick check:
<details>
<summary>📋 <strong>Environment Verification Code</strong></summary>

```python
import sys
print(f"✅ Python version: {sys.version}")
print("✅ Ready to start!")
```

**Expected Output:** `Python version: 3.x.x` (where x.x is 7 or higher)
</details>

---

## **Step 1: Get Your Data** (2 minutes)
**🎯 Goal:** Download and verify sample data

### 📦 **Download Practice Data**
1. **Download:** [locomotion_data.csv](test_files/locomotion_data.csv) - Right-click → Save As
2. **Download:** [task_info.csv](test_files/task_info.csv) - Right-click → Save As
3. **Save both files** in your current working directory

### ✅ **Checkpoint: Data Ready?**
Verify your downloads:

<details>
<summary>📋 <strong>Data Verification Code</strong></summary>

```python
import os
import pandas as pd

# Check if files exist
files_needed = ['locomotion_data.csv', 'task_info.csv']
for file in files_needed:
    if os.path.exists(file):
        print(f"✅ Found: {file}")
    else:
        print(f"❌ Missing: {file}")
        
# Quick data peek
if all(os.path.exists(f) for f in files_needed):
    data = pd.read_csv('locomotion_data.csv')
    print(f"✅ Data loaded: {len(data)} rows, {len(data.columns)} columns")
    print("✅ Setup complete!")
```
</details>

**Expected Output:**
```
✅ Found: locomotion_data.csv
✅ Found: task_info.csv
✅ Data loaded: 10 rows, 10 columns
✅ Setup complete!
```

**❌ Troubleshooting:** If files are missing:
- Check your Downloads folder
- Ensure you're in the right directory: `print(os.getcwd())`
- Re-download if needed

---

## **Step 2: Load and Explore** (3 minutes)
**🎯 Goal:** Understand your biomechanical data

<details>
<summary>📋 <strong>Data Loading Code</strong></summary>

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the data
locomotion_data = pd.read_csv('locomotion_data.csv')
task_info = pd.read_csv('task_info.csv')

print("🔍 Data Overview:")
print(f"Locomotion data: {len(locomotion_data)} measurements")
print(f"Task info: {len(task_info)} different tasks")

# Preview the data
print("\n📊 First few rows:")
print(locomotion_data.head(3))

print("\n🏃 Available tasks:")
print(task_info[['task_name', 'walking_speed_m_s', 'ground_inclination_deg']])
```
</details>

### ✅ **Checkpoint: Data Understood?**
**What You Should See:**
- ✅ 10 measurements loaded
- ✅ 3 different tasks shown
- ✅ Columns include: `time_s`, `knee_flexion_angle_rad`, `hip_flexion_angle_rad`
- ✅ No error messages

**🤔 Understanding Your Data:**
- **`time_s`**: Time stamps of measurements
- **`knee_flexion_angle_rad`**: Knee joint angle (radians)
- **`step_id`**: Unique identifier for each gait cycle
- **`task_name`**: Type of walking (level, incline, etc.)

---

## **Step 3: Create Your First Plot** (4 minutes)
**🎯 Goal:** Visualize knee angles during walking

<details>
<summary>📋 <strong>Plotting Code</strong></summary>

```python
# Combine data to get task information
combined_data = pd.merge(locomotion_data, task_info, 
                        on=['step_id', 'task_id', 'subject_id'], 
                        how='inner')

# Focus on incline walking
incline_data = combined_data[combined_data['task_name'] == 'incline_walking']

# Create your first biomechanical plot
plt.figure(figsize=(10, 6))
plt.plot(incline_data['time_s'], 
         incline_data['knee_flexion_angle_rad'], 
         'b-o', linewidth=2, markersize=6)

plt.xlabel('Time (seconds)', fontsize=12)
plt.ylabel('Knee Flexion Angle (radians)', fontsize=12)
plt.title('Knee Angle During Incline Walking', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)

# Add context
plt.text(0.02, max(incline_data['knee_flexion_angle_rad']) * 0.9, 
         f'Speed: {incline_data["walking_speed_m_s"].iloc[0]} m/s\n'
         f'Incline: {incline_data["ground_inclination_deg"].iloc[0]}°', 
         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))

plt.tight_layout()
plt.savefig('my_first_biomechanics_plot.png', dpi=300, bbox_inches='tight')
plt.show()

print("🎉 Success! Your plot has been saved as 'my_first_biomechanics_plot.png'")
```
</details>

### ✅ **Checkpoint: Plot Created?**
**Success Criteria:**
- [ ] Plot displays without errors
- [ ] Shows knee angle over time
- [ ] Includes walking speed and incline information
- [ ] File `my_first_biomechanics_plot.png` exists in your directory

**Expected Pattern:** You should see knee angle increasing and decreasing in a cyclical pattern - this is normal gait!

**❌ Troubleshooting:**
- **No plot appears:** Try adding `plt.show()` at the end
- **File not found error:** Check that CSV files are in current directory
- **Empty plot:** Verify incline_walking data exists: `print(len(incline_data))`

---

## **Step 4: Quick Analysis** (1 minute)
**🎯 Goal:** Extract meaningful insights

<details>
<summary>📋 <strong>Analysis Code</strong></summary>

```python
# Quick biomechanical insights
print("📈 Quick Analysis Results:")
print("-" * 40)

# Range of motion
knee_angles = incline_data['knee_flexion_angle_rad']
rom = knee_angles.max() - knee_angles.min()
print(f"Knee Range of Motion: {rom:.3f} radians ({np.degrees(rom):.1f}°)")

# Peak angle
peak_angle = knee_angles.max()
print(f"Peak Knee Flexion: {peak_angle:.3f} radians ({np.degrees(peak_angle):.1f}°)")

# Walking characteristics
speed = incline_data['walking_speed_m_s'].iloc[0]
incline = incline_data['ground_inclination_deg'].iloc[0]
print(f"Walking Speed: {speed} m/s")
print(f"Ground Incline: {incline}°")

print("\n🧠 Biomechanical Insight:")
print(f"This person flexed their knee {np.degrees(rom):.1f}° during incline walking.")
print("This is typical for healthy gait patterns!")
```
</details>

### ✅ **Final Checkpoint: Analysis Complete?**
**What You Should See:**
- ✅ Range of motion calculated in both radians and degrees
- ✅ Peak knee flexion identified
- ✅ Walking parameters confirmed
- ✅ Biomechanical insight provided

---

## **🎉 Congratulations!**
**You did it!** In just 10 minutes, you've:

- ✅ **Loaded real biomechanical data** from standardized locomotion datasets
- ✅ **Created a professional joint angle plot** with proper labeling and context
- ✅ **Calculated meaningful metrics** like range of motion and peak flexion
- ✅ **Gained biomechanical insight** about healthy gait patterns

### **Your Achievement:**
You've successfully performed your first biomechanical analysis! The plot you created shows how the knee joint moves during incline walking - a fundamental measurement in gait analysis.

---

## **🚀 Next Steps**

**Ready for more?** Choose your learning path:

### **🎯 Immediate Next Steps** (Pick one):
- **[📊 Basic Analysis Tutorial](basic_analysis_interactive.md)** - Learn to compare different walking tasks (30 min)
- **[🔍 Explore Your Data](data_exploration_interactive.md)** - Dive deeper into the dataset structure (15 min)
- **[🎨 Better Plots](visualization_interactive.md)** - Create publication-ready figures (20 min)

### **🛠️ Try It Yourself Challenges:**
- **Easy:** Change the plot to show `hip_flexion_angle_rad` instead of knee
- **Medium:** Compare knee angles between level and incline walking
- **Advanced:** Plot multiple subjects on the same graph

### **📚 Learning Resources:**
- **[Biomechanics Glossary](../reference/biomechanics_glossary.md)** - Understand the terminology
- **[Data Format Guide](../reference/data_formats.md)** - Learn about the standardized format
- **[Troubleshooting Guide](troubleshooting_interactive.md)** - Solve common issues

---

## **🤝 Community & Support**

**Questions?** Join our community:
- **[GitHub Discussions](https://github.com/your-repo/discussions)** - Ask questions and share insights
- **[Example Repository](https://github.com/your-repo/examples)** - See more analysis examples
- **[Documentation](../reference/api_reference.md)** - Complete reference guide

**Share Your Success!** Tag us with your first biomechanics plot on social media!

---

### **🔖 Bookmark This Page**
Save this quick start guide for future reference. You can return here anytime to refresh the basics or help a colleague get started.

**Total Time Invested:** 10 minutes  
**Skills Gained:** Data loading, plotting, basic analysis  
**Confidence Level:** Ready for intermediate tutorials! 🚀