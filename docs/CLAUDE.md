# CLAUDE.md - Documentation Directory

Guidance for working with project documentation.

## Directory Structure

**Key Areas**:
- `standard_spec/` - Data format specifications and validation rules
- `datasets_documentation/` - Implementation details for each dataset
- `tutorials/` - Python and MATLAB usage guides
- `development/` - Progress tracking and development notes

## Documentation Standards

**Minimal Style**:
- Essential information only
- Quick reference navigation with bullet separators
- Visual section breaks with `---`
- Action-oriented content

**File Updates Required When**:
- Adding new biomechanical variables
- Changing validation rules
- Modifying data format specifications
- Adding new datasets or task types

## Key File Patterns

**Standard Specs**: Define format, naming, validation
**Dataset Docs**: Implementation details, known issues, usage notes
**Tutorials**: Step-by-step usage with tested code examples

**Cross-References**:
- Link to conversion scripts: `../../source/conversion_scripts/<Dataset>/`
- Reference validation: `../../source/tests/validation_blueprint.py`
- Library implementations: `../../source/lib/python/locomotion_analysis.py`

## Maintenance Guidelines

- Keep dataset docs current with conversion script changes
- Update tutorials when library versions change
- Verify all code examples are tested and functional
- Maintain consistent cross-reference patterns

---

*Documentation serves as the comprehensive knowledge base for the standardization framework.*