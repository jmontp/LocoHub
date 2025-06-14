# Entry Points Reference

**Complete CLI tool catalog organized by user role and priority.**

*What tools exist and their implementation status for each user type.*

## 🎯 Entry Points by User Role

### **Dataset Curators (9% of users)**
*Convert and initially validate new datasets*

| Priority | Tool | Purpose | Status |
|----------|------|---------|--------|
| **Critical** | `convert_dataset.py` | Convert raw datasets to standardized parquet | 📋 Planned |
| **Critical** | `validate_phase_data.py` | Validate phase-indexed datasets | 🚧 Refactor existing |
| **Critical** | `validate_time_data.py` | Validate time-indexed datasets | 🚧 Refactor existing |
| **High** | `generate_validation_plots.py` | Create static validation plots | 🚧 Refactor existing |
| **Medium** | `generate_validation_gifs.py` | Create animated validation GIFs | 🚧 Refactor existing |

### **Validation Specialists (9% of users)**  
*Ensure data quality and maintain standards*

| Priority | Tool | Purpose | Status |
|----------|------|---------|--------|
| **High** | `assess_quality.py` | Generate comprehensive quality reports | 📋 Planned |
| **High** | `manage_validation_specs.py` | Interactive editing of validation rules | 🚧 Refactor existing |
| **High** | `auto_tune_ranges.py` | Automatically optimize validation ranges | 🚧 Refactor existing |
| **High** | `compare_datasets.py` | Compare datasets from different sources | 📋 Planned |
| **Medium** | `investigate_errors.py` | Debug validation failures in detail | 📋 Planned |

### **System Administrators (1% of users)**
*Manage releases and create ML benchmarks*

| Priority | Tool | Purpose | Status |
|----------|------|---------|--------|
| **Critical** | `create_benchmarks.py` | Create ML train/test/validation splits | 📋 Planned |
| **Medium** | `publish_datasets.py` | Prepare datasets for public release | 📋 Planned |
| **Medium** | `manage_releases.py` | Manage dataset versions and releases | 📋 Planned |

---

## 🚀 Implementation Priority Matrix

### **Phase 1: Core Infrastructure (4-6 weeks)**
```bash
# Critical tools needed for basic functionality
python convert_dataset.py         # Enable new dataset addition
python validate_phase_data.py     # Core validation workflow
python validate_time_data.py      # Core validation workflow  
python create_benchmarks.py       # Enable ML research community
```

### **Phase 2: Quality Tools (3-4 weeks)**
```bash
# High-priority quality assurance tools
python assess_quality.py          # Quality oversight
python manage_validation_specs.py # Standards evolution
python auto_tune_ranges.py        # Data-driven improvements
```

### **Phase 3: Analysis & Visualization (2-3 weeks)**
```bash
# Analysis and visualization tools
python generate_validation_plots.py # Visual verification
python compare_datasets.py          # Multi-dataset analysis
```

### **Phase 4: Advanced Features (2-3 weeks)**
```bash
# Advanced debugging and visualization
python generate_validation_gifs.py # Animation visualization
python investigate_errors.py       # Complex debugging
```

### **Phase 5: Release Management (1-2 weeks)**
```bash
# Public release and version management
python publish_datasets.py    # Public dataset releases
python manage_releases.py     # Version and lifecycle management
```

---

## 📋 Common Usage Patterns

### **Dataset Curator Workflow**
```bash
# 1. Convert new dataset
python convert_dataset.py raw_data.mat ./output/

# 2. Validate converted data
python validate_phase_data.py output/dataset_phase.parquet

# 3. Generate visual verification
python generate_validation_plots.py output/dataset_phase.parquet
```

### **Validation Specialist Workflow**
```bash
# 1. Assess overall quality
python assess_quality.py dataset_phase.parquet

# 2. Tune validation ranges if needed
python auto_tune_ranges.py --dataset dataset_phase.parquet --method percentile_95

# 3. Compare with other datasets
python compare_datasets.py dataset1.parquet dataset2.parquet
```

### **System Administrator Workflow**
```bash
# 1. Create ML benchmarks
python create_benchmarks.py validated_datasets/*.parquet ./ml_benchmarks/

# 2. Prepare for public release
python publish_datasets.py ./ml_benchmarks/ ./public_release/

# 3. Manage release versions
python manage_releases.py --version 1.2.0 --changelog changes.md
```

---

## 🔗 Cross-References

**Detailed Documentation**:
- **User Stories**: [`04_user_stories_acceptance_criteria.md`](04_user_stories_acceptance_criteria.md)
- **Technical Specs**: [`09_c4_detailed_component_specs.md`](09_c4_detailed_component_specs.md)  
- **Interface Standards**: [`13_interface_standards.md`](13_interface_standards.md)
- **Test Specifications**: [`12_test_specifications.md`](12_test_specifications.md)

**Architecture Context**:
- **Future CLI Architecture**: [`08_c4_component_future_cli.md`](08_c4_component_future_cli.md)
- **User Journey Maps**: [`03_user_journey_maps.md`](03_user_journey_maps.md)
- **Class Design**: [`10_uml_class_design.md`](10_uml_class_design.md)

---

## 📊 Status Legend

- **📋 Planned** - Needs implementation from scratch
- **🚧 Refactor existing** - Existing code needs restructuring to match specifications  
- **✅ Complete** - Implemented and tested
- **🔄 In progress** - Currently being developed

---

*This reference provides quick access to all entry points. For detailed user stories, acceptance criteria, and technical specifications, see the cross-referenced documentation.*