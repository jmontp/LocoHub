# CLAUDE.md - Software Engineering Directory

**Essential guidance for locomotion data standardization architecture.**

## Software Engineering Philosophy

**Follow best software engineering practices throughout development.** 

**Claude Code Role**: Guide user through software engineering best practices. While Claude Code is an expert in software engineering, the user is still learning. The user owns the vision and makes final decisions, but Claude Code should proactively suggest improvements whenever they would build a better project.

**Collaboration Approach**:
- User defines project vision and requirements
- Claude Code can suggest improvements to vision, mission, and strategic direction
- Claude Code suggests architectural improvements, design patterns, and engineering practices
- Focus on maintainable, testable, and scalable code
- Prioritize code quality, documentation, and proper abstractions

---

## Key Documents

**Critical**: `09_c4_code.md` - Interface specifications • `08_c4_component.md` - Component architecture  
**Important**: `04_user_stories_acceptance_criteria.md` - Requirements • `10_test_specifications.md` - Test cases

---

## Critical Components

**PhaseValidator** ⭐ - Validates datasets with stride-level filtering using ValidationSpecManager  
**ValidationSpecManager** ⭐ - Manages task/phase-specific ranges (task → variable → phase → {min,max})  
**External Reality**: No standard conversion interfaces - validate parquet outputs only

---

## Validation Essentials

**Three Core Goals**: Sign convention adherence • Outlier detection • Phase segmentation (150 points/cycle)  
**Stride Filtering**: Keep valid strides, delete invalid strides, report pass rates  
**Task-Specific**: walking/incline_walking/decline_walking with phase-specific ranges (0%, 25%, 50%, 75%)

---

## Documentation Style Guidelines

### **Content Structure**
- **One concept per section** - Avoid mixing different topics
- **Progressive disclosure** - Start with overview, then drill down to details
- **Clear section hierarchy** - Use consistent heading levels (##, ###)
- **Visual breaks** - Use `---` between major sections

### **Writing Style**
- **Action-oriented** - Start with verbs ("Validate", "Generate", "Manage")
- **Concrete specifics** - "150 points per cycle" not "appropriate number of points"
- **Avoid meta-commentary** - No "This section will cover..." or "As mentioned above..."
- **Essential information only** - Remove explanatory text that doesn't drive decisions

### **Technical Precision**
- **Consistent terminology** - "strides" not mixed with "steps", "phase-indexed" not "phase data"
- **Specific file references** - Include line numbers when referencing code: `file.py:125`
- **Exact interface names** - Use actual method names: `validate_dataset()` not "validation method"
- **Priority indicators** - Use ⭐ for critical, clear priority levels

### **File Organization**
- **Single responsibility** - Each file covers one architecture level or concern
- **Logical naming** - Sequential prefixes (00_, 01_) for reading order
- **Cross-references** - Link to related files but avoid circular dependencies

### **Mermaid Diagrams**
- **Consistent themes** - Always use `%%{init: {'theme': 'dark'}}%%`
- **Clear node labels** - Include type and brief description
- **Readable styling** - Use consistent color coding across diagrams

### **Documentation Approach**
- **Minimize Content** - Each file should capture essential aspects with minimal text
- **Manageable Context** - Split large files for focused development and easier review
- **Essential Only** - Remove redundant information, focus on critical implementation details