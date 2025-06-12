# Standard Specification

Data format specifications and validation rules for locomotion datasets.

**Quick Reference:** [Format Spec](standard_spec.md) • [Units & Conventions](units_and_conventions.md) • [Task Definitions](task_definitions.md)

## Core Specifications

**Data Format** - [standard_spec.md](standard_spec.md):
- Variable naming: `knee_flexion_angle_ipsi_rad`
- Time vs phase-indexed formats
- Required columns and validation rules

**Units & Conventions** - [units_and_conventions.md](units_and_conventions.md):
- OpenSim-compatible coordinate system and sign conventions
- Variable naming patterns and units
- Typical biomechanical values and ranges

**Task Definitions** - [task_definitions.md](task_definitions.md):
- Standard task vocabulary
- Metadata schema for task parameters
- Usage examples and field descriptions

---

## Validation Specifications

**Kinematic Validation** - [validation_expectations_kinematic.md](validation_expectations_kinematic.md):
- Joint angle validation ranges
- Phase-specific biomechanical expectations
- Task-specific validation rules

**Kinetic Validation** - [validation_expectations_kinetic.md](validation_expectations_kinetic.md):
- Force and moment validation ranges
- Ground reaction force expectations
- Power and energy validation criteria

---

## Templates and Tools

**Dataset Template** - [dataset_template.md](dataset_template.md):
- Standard template for documenting new datasets
- Required fields and citation format
- Implementation guidelines

**Validation Images** - [validation/](validation/):
- Phase-specific kinematic pose visualizations
- Biomechanical range validation plots
- Reference images for expected movement patterns

---

*These specifications ensure consistency and quality across all standardized datasets.*