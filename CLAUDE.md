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

### Decision-Making Guidelines
- If you are not 100% certain on what to do, or feel like you are making a big assumption. Consult the user. 

### Coding Principles
- Do not use default values/synthetic data/soft failures, if you don't find a variable raise an explicit error that can be then debugged instead of failing softly.