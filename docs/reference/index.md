# Reference Documentation

**Technical specifications and standards for biomechanical data standardization**

---

## 📚 Essential References

### 🔬 [Biomechanical Standard](biomechanical_standard.md)
**Complete Technical Reference**
- Variable definitions with units & ranges
- Coordinate systems & sign conventions  
- Joint & segment angle mathematics
- Forces, moments, and GRF specifications
- Task classification hierarchy
- Validation requirements & ranges

### 📋 [Quick Reference](quick_reference.md)
**Daily Use Cheat Sheet**
- Copy-ready variable names
- Sign convention tables
- Unit conversion formulas
- Typical value ranges
- Common troubleshooting
- Print-friendly format

### 📄 [Technical Specification](standard_spec/standard_spec.md)
**File Format Details**
- Parquet structure requirements
- Required columns & metadata
- Phase vs time indexing
- Data organization patterns
- Implementation examples

---

## 🗂️ Additional Documentation

### 📊 [Dataset Documentation](datasets_documentation/)
Information about specific datasets in the standardized format:
- [Validation Reports](datasets_documentation/validation_reports/) - Quality assessment for each dataset
- Individual dataset specifications and known issues

### ✅ [Validation Specifications](standard_spec/validation_ranges.md)
Detailed validation ranges and criteria:
- Task-specific biomechanical ranges
- Phase-based validation points
- Statistical validation methods

### 🔧 [Task Definitions](standard_spec/task_definitions.md)
Complete task classification system:
- Three-level hierarchy (task/task_id/task_info)
- Standard activity definitions
- Metadata specifications

---

## 🚀 Quick Start Examples

### Loading Data
```python
from user_libs.python.locomotion_data import LocomotionData

# Load standardized dataset
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get gait cycles for analysis
cycles, features = data.get_cycles('SUB01', 'level_walking')
```

### Converting Datasets
```bash
# Run dataset-specific converter
cd contributor_tools/conversion_scripts/YourDataset/
python convert_to_parquet.py  # or MATLAB equivalent
```

### Validating Data
```bash
# Generate validation report
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet
```

---

## 📁 Directory Structure

```
docs/reference/
├── biomechanical_standard.md    # Comprehensive reference
├── quick_reference.md            # Cheat sheet
├── standard_spec/               # Technical specifications
│   ├── standard_spec.md        # File format spec
│   ├── task_definitions.md     # Task classifications
│   └── validation_ranges.md    # Validation criteria
└── datasets_documentation/      # Dataset-specific docs
    └── validation_reports/      # Quality reports
```

---

## 🔍 Finding Information

| **Looking for...** | **Go to...** |
|-------------------|--------------|
| Variable naming conventions | [Biomechanical Standard § Variable Naming](biomechanical_standard.md#variable-naming-system) |
| Sign conventions | [Quick Reference § Sign Conventions](quick_reference.md#sign-conventions) |
| Unit conversions | [Quick Reference § Unit Conversions](quick_reference.md#unit-conversions) |
| Coordinate system | [Biomechanical Standard § Coordinate System](biomechanical_standard.md#coordinate-system--conventions) |
| Task classifications | [Biomechanical Standard § Task Classification](biomechanical_standard.md#task-classification-system) |
| File format requirements | [Technical Specification](standard_spec/standard_spec.md) |
| Validation ranges | [Biomechanical Standard § Validation](biomechanical_standard.md#validation-requirements) |
| Common issues | [Quick Reference § Common Issues](quick_reference.md#common-issues) |

---

## 📝 Key Concepts

### Data Formats
- **Phase-Indexed**: 150 points per gait cycle (0-100%)
- **Time-Indexed**: Original sampling frequency preserved

### Variable Pattern
```
<joint/segment>_<motion>_<measurement>_<side>_<unit>
```
Example: `knee_flexion_angle_ipsi_rad`

### Coordinate System
- **X**: Anterior (forward) positive
- **Y**: Superior (upward) positive  
- **Z**: Right (lateral) positive

---

*For development and contribution guidelines, see the [Maintainers Guide](../maintainers/index.md)*