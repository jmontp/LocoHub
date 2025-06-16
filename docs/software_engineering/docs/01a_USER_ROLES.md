---
title: User Roles & Entry Points
tags: [user, roles, entry-points]
status: ready
---

# User Roles & Entry Points

!!! info ":busts_in_silhouette: **You are here** → User Roles & CLI Tool Reference"
    **Purpose:** Complete mapping of user types to CLI tools and workflows
    
    **Who should read this:** Product managers, developers, new contributors
    
    **Value:** Understand tool priorities and user-centric development focus
    
    **Connection:** Detailed expansion of [User Guide](01_USER_GUIDE.md) personas
    
    **:clock4: Reading time:** 12 minutes | **:busts_in_silhouette: User types:** 4 roles with tool mappings

**Complete CLI tool catalog organized by user role and priority.**

*Navigation: [← User Guide](01_USER_GUIDE.md) • [System Context →](01b_SYSTEM_CONTEXT.md)*

## 🎯 Entry Points by User Role

### **Dataset Curators - Programmers (9% of users)**
*Convert datasets and perform quality assessment*

**Tool Reference**: See [CLI Specification](04a_CLI_SPECIFICATION.md) for complete tool documentation.

**Key Tools:**
- `conversion_generate_phase_dataset.py` - Convert time-indexed to phase-indexed datasets
- `validation_dataset_report.py [--generate-gifs]` - Comprehensive validation and quality assessment

### **Dataset Curators - Biomechanical Validation (9% of users)**  
*Ensure data quality and maintain validation standards*

**Tool Reference**: See [CLI Specification](04a_CLI_SPECIFICATION.md) for complete tool documentation.

**Key Tools:**
- `validation_manual_tune_spec.py [--generate-gifs]` - Interactive editing of validation rules
- `validation_auto_tune_spec.py [--generate-gifs]` - Automatically optimize validation ranges
- `validation_compare_datasets.py` - Compare datasets from different sources
- `validation_investigate_errors.py` - Debug validation failures in detail

### **System Administrators (1% of users)**
*Manage releases and create ML benchmarks*

**Tool Reference**: See [CLI Specification](04a_CLI_SPECIFICATION.md) for complete tool documentation.

**Key Tools:**
- `create_benchmarks.py` - Create ML train/test/validation splits
- `publish_datasets.py` - Prepare datasets for public release

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

## 📊 Status Legend

- **📋 Planned** - Needs implementation from scratch
- **🚧 Refactor existing** - Existing code needs restructuring to match specifications  
- **✅ Complete** - Implemented and tested
- **🔄 In progress** - Currently being developed

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** User-Specific Tool Catalog & Entry Points"
    **⬅️ Previous:** [User Guide](01_USER_GUIDE.md) - User personas and research insights
    
    **➡️ Next:** [System Context](01b_SYSTEM_CONTEXT.md) - Technical interaction patterns
    
    **📖 Reading time:** 8 minutes
    
    **🎯 Prerequisites:** [User Guide](01_USER_GUIDE.md) - Understanding of user personas
    
    **🔄 Follow-up sections:** System context, Requirements analysis

!!! tip "**Cross-References & Related Content**"
    **🔗 User Foundation:** [User Guide - Detailed Personas](01_USER_GUIDE.md#detailed-personas) - Named personas with specific backgrounds and pain points
    
    **🔗 Interface Details:** [CLI Specification](04a_CLI_SPECIFICATION.md) - Complete technical documentation for these tools
    
    **🔗 Implementation Planning:** [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) - Development strategy for building these tools
    
    **🔗 Requirements Traceability:** [Requirements](02_REQUIREMENTS.md) - User stories implemented by these tools

---

*This reference provides quick access to all entry points. For detailed system context and workflows, see [System Context](01b_SYSTEM_CONTEXT.md).*