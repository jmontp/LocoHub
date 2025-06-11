# CLAUDE.md - Source Directory

Core implementation of the locomotion data standardization framework.

## Directory Structure

**Key Components**:
- `conversion_scripts/` - Dataset-specific conversion implementations
- `lib/` - Core analysis libraries (Python and MATLAB)
- `validation/` - Centralized validation system with GIF generation
- `tests/` - Testing and demonstration framework

## Development Patterns

**Minimal Code Philosophy**:
- Dataset-specific conversion in isolated subdirectories
- Common functionality in shared libraries
- Centralized validation system with library modules
- Clean separation: library modules vs entry points

**Variable Naming**: `<joint>_<motion>_<measurement>_<side>_<unit>`
- Examples: `knee_flexion_angle_contra_rad`, `hip_moment_ipsi_Nm`

**Data Formats**:
- Time-indexed: Original sampling frequency with `time_s`
- Phase-indexed: 150 points per cycle with `phase_%`

## Integration Flow

```
Raw Data → Conversion Scripts → Standardized Parquet → Validation (includes GIFs) → Library Classes
```

**Cross-Component Dependencies**:
- All components follow specifications in `../docs/standard_spec/`
- Validation system provides centralized quality assurance and GIF generation
- Library classes integrate validation for data access
- Conversion scripts use validation for output verification

## Common Tasks

**New Dataset**: Create conversion directory, implement conversion, add validation rules, test integration
**New Variables**: Define name, update validation, extend library support, add to GIF generation
**Performance**: Profile bottlenecks, optimize 3D operations, implement chunked processing

## Quality Standards

**Testing**:
- Unit tests for individual methods
- Integration tests for cross-module workflows
- Performance tests with realistic dataset sizes
- Memory usage monitoring

**Error Handling**:
- Explicit errors over silent failures
- Informative messages with context
- Graceful degradation for missing data
- Comprehensive logging for debugging

---

*Implements the core standardization framework with minimal, tested, well-documented code.*