# Reality-Based Information Architecture

**Created: 2025-06-19 with user permission**  
**Purpose: Design IA structure based on actual implemented features**  

**Intent:** Create navigation and content organization that matches what users can actually accomplish with current tools, while planning for future capabilities.

## Information Architecture Strategy

### Core IA Principles

1. **Implementation-Driven Organization**: Structure content around working tools and verified capabilities
2. **Clear Capability Boundaries**: Distinguish between "available now" and "planned" features
3. **Workflow-Centric Navigation**: Organize by actual user workflows, not idealized processes
4. **Tool-First Approach**: Lead with functional CLI tools rather than conceptual frameworks
5. **Quality-Centered Design**: Reflect the validation-centric architecture in content organization

### Primary Navigation Structure

**Based on Actual System Analysis:**

```
LOCOMOTION DATA STANDARDIZATION
├── 🚀 Getting Started
│   ├── Installation & Setup                    # ✅ WORKING
│   ├── Your First Dataset Validation           # ✅ WORKING - validate_phase_dataset.py
│   └── Understanding Data Quality               # ✅ WORKING - based on actual validation
│
├── 🔧 Tools & Workflows 
│   ├── Dataset Validation                      # ✅ WORKING - validate_phase_dataset.py
│   ├── Dataset Type Detection                  # ✅ WORKING - detect_dataset_type.py  
│   ├── Validation Range Management             # ✅ WORKING - update/optimize scripts
│   ├── ML Benchmark Creation                   # ✅ WORKING - create_ml_benchmark.py
│   └── Dataset Release Management              # ✅ WORKING - create_dataset_release.py
│
├── 📚 Libraries & APIs
│   ├── LocomotionData Python Library           # ✅ WORKING - comprehensive
│   ├── Validation System Integration           # ✅ WORKING - DatasetValidator
│   ├── MATLAB Library (Limited)                # ⚠️ EXISTS - needs more testing
│   └── Feature Constants & Standards           # ✅ WORKING - single source
│
├── 📊 Available Datasets
│   ├── GTech 2023 Dataset                      # ✅ REAL DATA
│   ├── UMich 2021 Dataset                      # ✅ REAL DATA  
│   ├── Dataset Documentation                   # ✅ WORKING
│   └── Validation Reports                      # ✅ GENERATED
│
├── 📖 References
│   ├── Standard Specification                  # ✅ COMPREHENSIVE
│   ├── Variable Naming Convention              # ✅ ENFORCED
│   ├── Validation Expectations                 # ✅ ACTIVE
│   └── CLI Command Reference                   # ✅ WORKING
│
└── 🔮 Future Features
    ├── Consumer Python Library                 # ❌ PLANNED
    ├── Web Data Portal                          # ❌ PLANNED
    ├── Educational Tutorials                   # ❌ PARTIALLY MISSING
    └── Community Submission Portal             # ❌ PLANNED
```

## Detailed IA Design

### 1. Getting Started (Reality-Based)

**Path 1: For Dataset Contributors (Primary Users)**
```
Getting Started → Installation → Validate First Dataset → Understand Quality Reports
```

**Key Content (All Verified Working):**
- Environment setup (conda/pip requirements verified)
- First validation run with `validate_phase_dataset.py`
- Understanding validation reports and plots
- Common validation failures and solutions

**Path 2: For Data Consumers (Limited Options)**
```
Getting Started → Browse Available Datasets → Load with pandas/MATLAB → Understand Format
```

**Honest Limitations:**
- No consumer library (coming in Phase 2)
- Direct parquet loading required
- Limited tutorial infrastructure

### 2. Tools & Workflows (Implementation-Driven)

**Organized by Actual CLI Scripts:**

**Dataset Validation Workflow:**
```
1. validate_phase_dataset.py --help
2. Understanding validation reports  
3. Interpreting phase plots
4. Troubleshooting common issues
```

**Validation Management Workflow:**
```
1. detect_dataset_type.py (determine format)
2. optimize_validation_ranges.py (auto-tune)
3. update_validation_ranges.py (manual tune)
4. Validation specification management
```

**Release Management Workflow:**
```
1. create_ml_benchmark.py (prepare datasets)
2. create_dataset_release.py (package release)
3. Documentation compilation
4. Quality reporting
```

### 3. Libraries & APIs (Verified Capabilities)

**LocomotionData Library (Comprehensive):**
- Data loading (parquet/CSV auto-detection)
- 3D array operations (n_cycles × 150 × n_features)
- Statistical analysis (means, ROM, correlations)
- Biomechanical validation
- Visualization tools

**Integration Points (Working):**
- DatasetValidator for quality assessment
- StepClassifier for biomechanical constraints
- Feature constants for naming standards
- Validation expectations parser

**Code Examples (All Tested):**
```python
# Reality-based examples that actually work
from lib.core.locomotion_analysis import LocomotionData
loco = LocomotionData('umich_2021_phase.parquet')
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
```

### 4. Content Organization Strategy

**Primary Information Types:**

**Immediate Value (Working Now):**
- CLI tool documentation with actual examples
- Library API documentation with verified code
- Dataset documentation for available data
- Quality assessment and validation guidance

**Near-Term Value (Partially Working):**
- Conversion workflows for new datasets
- Validation tuning and range management
- Release management procedures
- Integration examples

**Future Value (Planned):**
- Consumer tutorials (when library exists)
- Web portal access (when implemented)
- Community contribution (when portal ready)
- Educational materials (when infrastructure complete)

## Navigation User Experience

### Entry Points by User Type

**Dataset Contributors (90% of current users):**
```
Landing → Tools Overview → Validation Workflow → Quality Assessment → Release
```

**Data Analysts (Current workaround users):**
```
Landing → Available Datasets → Direct Loading Guide → Format Documentation
```

**System Administrators:**
```
Landing → Tools Reference → Release Management → Infrastructure Documentation
```

**Future Users (Phase 2):**
```
Landing → Consumer Library → Tutorial → Analysis Examples → Community
```

### Content Prioritization

**Tier 1 (High Priority - Working Tools):**
- Dataset validation documentation
- CLI tool reference with examples
- LocomotionData library guide
- Available dataset documentation
- Quality standards and expectations

**Tier 2 (Medium Priority - Partially Working):**
- Advanced validation management
- Custom dataset conversion
- ML benchmark preparation
- Release workflow documentation

**Tier 3 (Lower Priority - Future Features):**
- Consumer library tutorials
- Web portal documentation
- Community features
- Educational content

## Search and Discovery Strategy

**Primary Discoverability:**
1. **Tool-Based Search**: Find by CLI script name or function
2. **Workflow-Based Search**: Find by task (validate, convert, analyze)
3. **Dataset-Based Search**: Find by available data
4. **Problem-Based Search**: Find solutions to validation issues

**Search Categories (Based on Actual Content):**
- CLI Commands and Tools
- Python Library Functions  
- Available Datasets
- Validation Standards
- Quality Assessment
- Error Resolution

## Information Architecture Validation

**IA Success Metrics:**
1. **Tool Discovery**: Users can find relevant CLI scripts quickly
2. **Workflow Completion**: Users can complete end-to-end processes
3. **Error Resolution**: Users can solve validation problems
4. **API Adoption**: Library usage increases with clear documentation

**Reality Check Questions:**
- ✅ Can users validate a dataset after reading docs?
- ✅ Can users understand validation failures?
- ✅ Can users load and analyze available datasets?
- ❌ Can users complete consumer tutorials? (Not yet - planned)
- ❌ Can users submit datasets via web portal? (Not yet - planned)

## Content Migration Strategy

**Phase 1 (Immediate - Match Reality):**
1. Reorganize existing content around working tools
2. Create clear "working now" vs "planned" sections
3. Add reality-based getting started guides
4. Document actual CLI workflows

**Phase 2 (Near-term - Fill Gaps):**
1. Create missing tutorial content
2. Expand library documentation with examples
3. Add troubleshooting guides based on real issues
4. Improve dataset documentation

**Phase 3 (Future - Consumer Focus):**
1. Add consumer library documentation when ready
2. Create web portal IA when implemented
3. Expand educational content
4. Build community features

---

**Key Insight:** This IA design prioritizes what users can actually accomplish today while providing clear paths to future capabilities. Navigation reflects the tool-centric, validation-focused architecture that actually exists.