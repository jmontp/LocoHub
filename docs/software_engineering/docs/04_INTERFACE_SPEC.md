---
title: Interface Specification
tags: [interface, specification]
status: ready
---

# Interface Specification

!!! info ":electric_plug: **You are here** → Interface & API Hub"
    **Purpose:** Complete interface contracts for CLI tools, APIs, and data structures
    
    **Who should read this:** Developers, API users, integration engineers, testers
    
    **Value:** Understand how to interact with system components and data contracts
    
    **Connection:** Implements [Architecture](03_ARCHITECTURE.md) design and supports [User Guide](01_USER_GUIDE.md) workflows
    
    **:clock4: Reading time:** 18 minutes | **:electric_plug: Interfaces:** CLI, data, API standards

!!! tip "**Interface Navigation**"
    **🔧 CLI Tools?** → [CLI Tools](#cli-tools) and [CLI Specification](04a_CLI_SPECIFICATION.md)
    
    **📊 Data structures?** → [Data Contracts](04b_DATA_CONTRACTS.md)
    
    **📋 API standards?** → [Interface Standards](04c_INTERFACE_STANDARDS.md)
    
    **💻 Code interfaces?** → [Core Validation Interface](#core-validation-interface)

## 🔧 Core Validation Interface

!!! abstract "**Primary Integration Point**"
    The system centers around `validation_dataset_report.py` as the main user-facing validation tool.

### PhaseValidator

**Primary Interface:** `validation_dataset_report.py [--generate-gifs]`

```python
class PhaseValidator:
    def validate_dataset(self, dataset_path: str) -> ValidationReport
    def generate_quality_report(self, dataset_path: str, include_gifs: bool = False)
    def get_validation_failures(self, dataset_path: str) -> List[ValidationFailure]
```

### ValidationSpecManager

**Interface:** Manages task/phase-specific validation ranges

```python
class ValidationSpecManager:
    def get_range(self, task: str, variable: str, phase: int) -> Range
    def update_range(self, task: str, variable: str, phase: int, min_val: float, max_val: float)
    def validate_specification(self, spec_path: str) -> bool
```

## CLI Tools

**Complete Tool Documentation**: See [CLI Specification](04a_CLI_SPECIFICATION.md) for comprehensive CLI tool documentation including usage examples, arguments, and exit codes.

**Key Tool Categories:**
- **Primary Validation Tools**: `validation_dataset_report.py`, `validation_compare_datasets.py`, `validation_investigate_errors.py`
- **Validation Management**: `validation_auto_tune_spec.py`, `validation_manual_tune_spec.py`
- **Conversion Tools**: `conversion_generate_phase_dataset.py` (legacy support)
- **Analysis Tools**: `create_benchmarks.py`, `publish_datasets.py`

## Data Contracts

### Core Result Types

- **PhaseValidationResult** - Comprehensive validation outcomes with stride-level filtering
- **QualityAssessmentResult** - Dataset quality metrics and population comparisons
- **ComparisonResult** - Multi-dataset statistical comparison analysis
- **TuningResult** - Validation range optimization results
- **BenchmarkResult** - ML benchmark creation outcomes

### Configuration Types

- **ValidationConfig** - Phase validation parameters and thresholds
- **QualityConfig** - Quality assessment criteria and scoring
- **ComparisonConfig** - Statistical comparison methods and significance levels

**→ See [Data Contracts](./04b_DATA_CONTRACTS.md) for complete interface contracts and data structures**

## Interface Standards

### CLI Patterns

- **Standard Arguments**: `--verbose`, `--quiet`, `--output-dir`, `--generate-gifs`
- **Exit Codes**: Standardized error codes (0=success, 1-7=specific error types)
- **Progress Reporting**: Consistent progress display across verbosity levels
- **Configuration**: YAML-based configuration with hierarchical loading

### Error Handling

- **Structured Messages**: Consistent error format with context and suggestions
- **Exception Hierarchy**: Typed exceptions for different failure categories
- **Recovery Patterns**: Standardized error recovery and user guidance

**→ See [Interface Standards](./04c_INTERFACE_STANDARDS.md) for complete standards documentation**

## Data Format Requirements

**Input:** Parquet files with required columns
**Output:** ValidationReport with pass/fail status and quality metrics
**Phase Data:** Exactly 150 points per gait cycle

## Future Interface Extensions

- REST API for validation services
- Python/MATLAB library interfaces for consumers
- Dataset repository access protocols

---

## 📊 Section Contents

<div class="grid cards" markdown>
-   **⚡ [CLI Specification](04a_CLI_SPECIFICATION.md)**
    
    ---
    
    Complete CLI tool documentation with examples and usage
    
    **Key Content:** Tool parameters, exit codes, usage patterns
    
    **Time:** 12 minutes
    
    **Best For:** Developers, CLI users, system integrators

-   **📋 [Data Contracts](04b_DATA_CONTRACTS.md)**
    
    ---
    
    Complete interface contracts and data structures
    
    **Key Content:** Result types, configuration types, data schemas
    
    **Time:** 10 minutes
    
    **Best For:** API developers, integration engineers

-   **📐 [Interface Standards](04c_INTERFACE_STANDARDS.md)**
    
    ---
    
    Standards documentation for CLI patterns and error handling
    
    **Key Content:** CLI patterns, error handling, configuration standards
    
    **Time:** 8 minutes
    
    **Best For:** Developers, QA engineers
</div>

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** Interface & API Contracts Hub"
    **⬅️ Previous:** [Architecture](03_ARCHITECTURE.md) - System design and C4 diagrams
    
    **➡️ Next:** [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) - Development strategy and coding standards
    
    **📖 Reading time:** 15 minutes
    
    **🎯 Prerequisites:** [Architecture](03_ARCHITECTURE.md) - System design understanding
    
    **🔄 Follow-up sections:** Implementation details, Test specifications

!!! tip "**Cross-References & Related Content**"
    **🔗 Architecture Foundation:** [Architecture - Component Architecture](03_ARCHITECTURE.md#component-architecture) - Components implementing these interfaces
    
    **🔗 User Tools:** [User Roles & Entry Points](01a_USER_ROLES.md) - User-specific tool catalog with priorities
    
    **🔗 Technical Details:** [CLI Specification](04a_CLI_SPECIFICATION.md) - Complete CLI tool documentation
    
    **🔗 Data Contracts:** [Data Contracts](04b_DATA_CONTRACTS.md) - Interface contracts and data structures
    
    **🔗 Standards:** [Interface Standards](04c_INTERFACE_STANDARDS.md) - CLI patterns and error handling standards

---

## 🔧 Interface Summary

!!! success "**Key Interface Principles**"
    ✅ **Central Tool:** `validation_dataset_report.py` serves as primary user interface
    
    ✅ **Consistent CLI:** Standardized arguments and patterns across all tools
    
    ✅ **Type Safety:** Well-defined data contracts and result types
    
    ✅ **Error Handling:** Structured error messages with context and suggestions
