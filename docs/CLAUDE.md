# CLAUDE.md - Documentation Directory

This file provides Claude Code guidance for working with the documentation in this directory.

## Directory Overview

The `docs/` directory contains all project documentation, specifications, tutorials, and dataset information for the Locomotion Data Standardization project.

## Directory Structure

```
docs/
├── README.md                     # Documentation overview and navigation
├── datasets_documentation/       # Dataset-specific implementation details
├── development/                  # Development status and progress tracking
├── standard_spec/               # Format specifications and standards
├── tutorials/                   # Step-by-step usage guides
└── goal.txt                     # Project objectives and scope
```

## Key Documentation Areas

### 1. Standard Specifications (`standard_spec/`)
**Primary Purpose**: Define the standardized data format, naming conventions, and validation rules

**Key Files**:
- `standard_spec.md` - Main format specification with schema definitions
- `sign_conventions.md` - Joint angle sign definitions and coordinate systems
- `units_and_conventions.md` - Units, measurement standards, and coordinate frames
- `phase_calculation.md` - Phase normalization methodology (150 points/cycle)
- `task_definitions.md` - Standardized task vocabulary and naming
- `dataset_template.md` - Template for documenting new datasets

**When to Update**: 
- Adding new biomechanical variables
- Changing validation rules
- Modifying data format specifications
- Adding new task types

### 2. Dataset Documentation (`datasets_documentation/`)
**Primary Purpose**: Implementation details, known issues, and usage notes for each dataset

**Key Files**:
- `datasets_glossary.md` - Overview of all supported datasets
- `dataset_addbiomechanics.md` - AddBiomechanics dataset implementation
- `dataset_gtech_2023.md` - Georgia Tech 2023 dataset implementation  
- `dataset_umich_2021.md` - University of Michigan 2021 dataset implementation

**Content Structure for Each Dataset**:
- Data source and citation information
- Input data format and structure
- Conversion script locations and usage
- Known limitations and missing data
- Validation considerations
- Example usage and outputs

### 3. Tutorials (`tutorials/`)
**Primary Purpose**: Step-by-step guides for using the standardized data and libraries

**Python Tutorials** (`tutorials/python/`):
- `getting_started_python.md` - Basic usage with LocomotionData class
- `library_tutorial_python.md` - Advanced features and 3D array operations
- `efficient_reshape_guide.md` - Performance optimization techniques
- Test scripts and example code

**MATLAB Tutorials** (`tutorials/matlab/`):
- `getting_started_matlab.md` - Basic usage with LocomotionData class
- `library_tutorial_matlab.md` - Advanced features and analysis
- Test scripts and validation code

**Test Files** (`tutorials/test_files/`):
- Sample data files for tutorial validation
- Reference plots for comparison
- Expected output files

### 4. Development Documentation (`development/`)
**Primary Purpose**: Track project progress, naming convention changes, and development status

**Key Files**:
- `PROGRESS_TRACKING.md` - Project milestones and current status
- `NAMING_CONVENTION_UPDATE_SUMMARY.md` - Evolution of variable naming standards

## Documentation Standards

### Writing Guidelines
- Use clear, descriptive headers and subheadings
- Include code examples with expected outputs
- Reference specific file paths using backticks: `source/lib/python/locomotion_analysis.py`
- Cross-reference related documentation sections
- Include troubleshooting sections for common issues

### File Naming Conventions
- Use lowercase with underscores: `dataset_name.md`
- Prefix dataset docs with `dataset_`: `dataset_addbiomechanics.md`
- Use descriptive names that match the content purpose

### Cross-References and Links
- Link to conversion script READMEs: `../../source/conversion_scripts/DatasetName/README.md`
- Reference validation code: `../../source/tests/validation_blueprint.py`
- Link to library implementations: `../../source/lib/python/locomotion_analysis.py`

## Common Documentation Tasks

### Adding Documentation for a New Dataset
1. Create `datasets_documentation/dataset_<name>.md` following the template
2. Update `datasets_documentation/datasets_glossary.md` with new entry
3. Add entry to main project README.md
4. Create tutorial examples if needed
5. Update validation documentation if new rules are required

### Updating Format Specifications
1. Modify relevant files in `standard_spec/`
2. Update validation rules in `../../source/tests/validation_blueprint.py`
3. Update library implementations to support changes
4. Update tutorials and examples to reflect changes
5. Update dataset documentation if format changes affect existing datasets

### Creating New Tutorials
1. Create tutorial file in appropriate language directory (`python/` or `matlab/`)
2. Include step-by-step instructions with code examples
3. Add test data to `tutorials/test_files/` if needed
4. Test tutorial on clean environment to ensure reproducibility
5. Update `tutorials/README.md` with new tutorial information

## Documentation Maintenance

### Regular Updates Needed
- Keep dataset documentation current with conversion script changes
- Update progress tracking as milestones are reached
- Verify tutorial code examples still work with current library versions
- Update validation documentation when new rules are added

### Quality Checks
- Ensure all code examples are tested and functional
- Verify all cross-references point to correct files
- Check that file paths are accurate and up-to-date
- Validate that documentation matches actual implementation

## Relationship to Other Directories

### Links to Source Code
- Specifications drive implementation in `../../source/lib/`
- Dataset docs reference conversion scripts in `../../source/conversion_scripts/`
- Tutorials use library code from `../../source/lib/`

### Links to Scripts
- Validation documentation references `../../scripts/validate_all_datasets.sh`
- Performance guides reference benchmark scripts in `../../scripts/`

### Integration with Main Documentation
- This directory provides detailed documentation referenced by main README.md
- Supports the main CLAUDE.md file with implementation specifics
- Provides the foundation for user-facing documentation

## Best Practices for Claude Code

### When Working with Documentation
1. **Always check existing docs first** - Look for relevant documentation before creating new content
2. **Maintain consistency** - Follow existing formatting and cross-reference patterns
3. **Update related files** - When changing one doc, check if others need updates
4. **Verify examples** - Ensure code examples are tested and functional
5. **Cross-reference appropriately** - Link to related implementation files and other docs

### Common File Locations to Reference
- Main specs: `standard_spec/standard_spec.md`
- Validation rules: `../../source/tests/validation_blueprint.py` 
- Python library: `../../source/lib/python/locomotion_analysis.py`
- MATLAB library: `../../source/lib/matlab/LocomotionData.m`
- Conversion scripts: `../../source/conversion_scripts/<Dataset>/`

This documentation directory serves as the comprehensive knowledge base for the project, providing both technical specifications and user guidance for the locomotion data standardization framework.