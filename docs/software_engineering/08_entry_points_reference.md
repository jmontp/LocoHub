# Entry Points Reference

**Complete CLI tool catalog organized by user role and priority.**

*What tools exist and their implementation status for each user type.*

## 🎯 Entry Points by User Role

### **Dataset Curators - Programmers (9% of users)**
*Convert datasets and perform quality assessment*

| Priority | Tool | Purpose | Status |
|----------|------|---------|--------|
| **Critical** | `conversion_generate_phase_dataset.py` | Convert time-indexed to phase-indexed datasets | 📋 Planned |
| **Critical** | `validation_dataset_report.py [--generate-gifs]` | Comprehensive validation and quality assessment | 🚧 Refactor existing |

### **Dataset Curators - Biomechanical Validation (9% of users)**  
*Ensure data quality and maintain validation standards*

| Priority | Tool | Purpose | Status |
|----------|------|---------|--------|
| **High** | `validation_manual_tune_spec.py [--generate-gifs]` | Interactive editing of validation rules | 🚧 Refactor existing |
| **High** | `validation_auto_tune_spec.py [--generate-gifs]` | Automatically optimize validation ranges | 🚧 Refactor existing |
| **High** | `validation_compare_datasets.py` | Compare datasets from different sources | 📋 Planned |
| **Medium** | `validation_investigate_errors.py` | Debug validation failures in detail | 📋 Planned |

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
python conversion_generate_phase_dataset.py # Enable phase dataset creation
python validation_dataset_report.py         # Core validation and quality assessment
python create_benchmarks.py                 # Enable ML research community
```

### **Phase 2: Quality Tools (3-4 weeks)**
```bash
# High-priority quality assurance tools
python validation_manual_tune_spec.py  # Literature-based range updates
python validation_auto_tune_spec.py    # Statistical range optimization
python validation_compare_datasets.py  # Multi-dataset consistency
```

### **Phase 3: Advanced Features (2-3 weeks)**
```bash
# Advanced debugging and investigation
python validation_investigate_errors.py # Complex failure debugging
```

### **Phase 4: Release Management (1-2 weeks)**
```bash
# Public release and version management
python publish_datasets.py    # Public dataset releases
python manage_releases.py     # Version and lifecycle management
```

---

## 📋 Common Usage Patterns

### **Dataset Curator Workflow**
```bash
# 1. Generate phase-indexed dataset from time data
python conversion_generate_phase_dataset.py time_dataset.parquet

# 2. Comprehensive validation and quality assessment
python validation_dataset_report.py dataset_phase.parquet

# 3. Generate visual verification with animations (optional)
python validation_dataset_report.py dataset_phase.parquet --generate-gifs
```

### **Validation Specialist Workflow**
```bash
# 1. Update validation ranges based on literature
python validation_manual_tune_spec.py --edit kinematic

# 2. Optimize ranges using statistical analysis
python validation_auto_tune_spec.py --dataset combined_data.parquet --method percentile_95

# 3. Compare datasets from different sources
python validation_compare_datasets.py dataset1.parquet dataset2.parquet

# 4. Debug specific validation failures
python validation_investigate_errors.py dataset_phase.parquet --variable knee_flexion_angle
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