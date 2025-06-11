# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository standardizes locomotion datasets into a consistent format with both **time-indexed** and **phase-indexed** variants. The standard specification supports:

### Standard Dataset Format
- **Time-indexed**: `<dataset>_time.parquet` - Preserves original sampling frequency
- **Phase-indexed**: `<dataset>_phase.parquet` - Normalized to 150 points per gait cycle
- **Naming convention**: `<joint>_<motion>_<measurement>_<side>_<unit>`
- **Example variables**: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

### Validation System Requirements
- **Phase-based validation**: Only works with `_phase.parquet` datasets
- **150 points per cycle**: Each gait cycle normalized to exactly 150 data points
- **Required columns**: `phase_percent` (0-100%), `step` or `cycle` identifiers
- **Standard compliance**: Variable names must match standard specification exactly

### Current Dataset Status
- **Available**: Time-indexed datasets (`gtech_2023_time*.parquet`, etc.)
- **Missing**: Phase-indexed datasets (conversion needed for validation reports)
- **Validation**: Requires phase-indexed format - exits gracefully if time-indexed provided

## Common Commands

### Git Guidelines
- Never "git add -A", just add the files that you edit
- Always add co-author information when committing
- For current date information, always use Python: `python3 -c "import datetime; print(datetime.datetime.now().strftime('%Y-%m-%d'))"`

### Date and Time Information
- **Recommended Method**: Use Python to get current date
  ```python
  import datetime
  print(datetime.datetime.now().strftime('%Y-%m-%d'))
  ```

### Project Management System
**IMPORTANT**: Project management is tracked using @PM_snapshot.md as the central reference.
- Use `@PM_snapshot.md` to understand current project status and priorities
- Contains high-level overview of all project components and their current state
- Auto-generated from distributed component PM files for comprehensive tracking

### Current Project Phase and Priorities
Based on @PM_snapshot.md, the project is in **Phase 0: Validation & Quality Assurance**.

**Immediate Next Steps (Phase 0 Completion):**
- Complete validation report generation system
- Validate AddBiomechanics dataset 
- Create validation GIFs for movement visualization

**Phase 1 Goals (Upcoming):**
- Core library development (pip-installable Python package, MATLAB toolbox)
- Biomechanical rigor enhancements (ISB coordinate systems, visual diagrams)
- Documentation foundation (interactive website, tutorials)

### PM Management Commands
```bash
# Check project status and priorities
cat PM_snapshot.md                                       # View current project overview
python scripts/pm_update.py --check                      # Check all component PM files
python scripts/pm_update.py --full-update                # Update project status snapshot
```

### File Creation Guidelines
**IMPORTANT**: Always obtain explicit user permission before creating new files.

**Required for ALL new files:**
1. **User Permission**: Ask user before creating any new file
2. **Clear Intent Documentation**: Every file must include a comprehensive header describing:
   - **Purpose**: What the file accomplishes
   - **Intent**: Detailed explanation of the file's functionality and responsibilities
   - **Creation Context**: Date and permission statement (e.g., "Created: 2025-06-10 with user permission")
   - **Usage Examples**: How other developers should use the file
   - **Key Features**: Main capabilities and design decisions

**Header Template for New Files:**
```python
#!/usr/bin/env python3
"""
{File Name and Brief Description}

Created: {YYYY-MM-DD} with user permission
Purpose: {One-line summary of what this file accomplishes}

Intent:
{Detailed explanation of the file's functionality, responsibilities, and design approach.
Include what problems it solves, how it fits into the larger system, and key design decisions.}

**PRIMARY FUNCTIONS:**
1. **{Function Category}**: {Description}
2. **{Function Category}**: {Description}

Usage:
    {Realistic code examples showing how to use this file}

{Additional sections as needed: Performance notes, Dependencies, Integration points, etc.}
"""
```

**Prohibited Actions Without Permission:**
- Creating new Python modules (.py files)
- Creating new documentation files (.md files) 
- Creating new configuration files
- Creating new directories or folder structures
- Creating new test files or demo scripts

### Decision-Making Guidelines
- If you are not 100% certain on what to do, or feel like you are making a big assumption. Consult the user. 

### Coding Philosophy and Standards

**Core Principles:**
- **Minimal Code**: Write only what is necessary - less code is better code
- **Clear Intent**: Every function, class, and file must document its purpose and intent
- **Understandable**: Code should be readable by biomechanics researchers, not just programmers
- **Well-tested**: All functionality must have corresponding tests

**Implementation Guidelines:**
- **Explicit over implicit**: Raise clear errors instead of soft failures or default values
- **Single purpose**: Each function/class should do one thing well
- **Clear naming**: Variable and function names should explain intent without comments
- **Comprehensive headers**: Every file must include purpose, intent, and usage documentation

### Code Quality Standards

**Testing Requirements:**
- **Unit tests**: All functions must have corresponding tests
- **Integration tests**: Key workflows must be tested end-to-end
- **Validation tests**: Data outputs must be validated against expectations
- **Documentation tests**: Code examples in documentation must be tested

**Code Organization:**
- **Minimal codebase**: Prefer fewer, well-designed components over many small utilities
- **Clear dependencies**: Minimize external dependencies and document all requirements
- **Modular design**: Components should be independent and reusable
- **No duplication**: Eliminate redundant functionality across the codebase

### File Structure Guidelines
- Every file should include a header that describes the intent and purpose of the file
- Follow the comprehensive header template from File Creation Guidelines section

## Communication Guidelines
- Tone down the language for "publication-ready" and all of that.

## Documentation Philosophy
**Minimal yet highly effective**: All user-facing documentation should follow these principles:

### Core Principles
- **Essential information only** - Remove everything that doesn't directly help users succeed
- **Immediate actionability** - Every section should enable immediate next steps
- **Scannable structure** - Use headers, bullets, and short paragraphs for fast consumption
- **No fluff** - Eliminate introductory text, explanations of obvious concepts, and verbose descriptions

### Writing Style for User Documentation
- **Start with action** - Begin with what users can do, not what the project is
- **Use imperative voice** - "Load data" not "You can load data"
- **Concrete examples** - Show actual code/commands, not abstract descriptions
- **Minimal context** - Assume users are intelligent and want to get started quickly
- **No meta-commentary** - Remove phrases like "This guide will show you" or "As you can see"

### Structure Guidelines
- **Front-load critical paths** - Most common use cases first
- **Eliminate redundancy** - Don't repeat information across files
- **Flat navigation** - Minimize clicks to reach actionable content
- **Progressive disclosure** - Basic → advanced, with clear separation

### What to Remove from User Docs
- Long introductions or project background
- Multiple ways to do the same thing (pick the best one)
- Exhaustive feature lists (show the essential features)
- Step-by-step explanations of obvious operations
- Motivational or persuasive language
- Complex directory structure explanations

### Examples of Minimal Style
**Before**: "This comprehensive tutorial will walk you through the complete process of getting started with our locomotion analysis framework, covering everything from basic data loading concepts to advanced analytical capabilities."

**After**: "Load and analyze locomotion data."

**Before**: "As you can see from the example above, the system provides multiple flexible options for data access patterns depending on your specific analytical requirements."

**After**: "```python\ndata = LocomotionData.from_parquet('dataset.parquet')\n```"