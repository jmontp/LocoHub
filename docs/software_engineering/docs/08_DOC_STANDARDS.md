---
title: Documentation Standards
tags: [documentation, standards]
status: ready
---

# Documentation Standards

!!! info ":memo: **You are here** → Documentation Guidelines & Best Practices"
    **Purpose:** Writing style, formatting standards, and quality guidelines for all documentation
    
    **Who should read this:** Documentation contributors, developers, technical writers
    
    **Value:** Consistent, high-quality documentation across all project materials
    
    **Connection:** Applied throughout all documentation in this suite
    
    **:clock4: Reading time:** 8 minutes | **:memo: Standards:** Content, technical, visual

!!! abstract ":zap: TL;DR - Documentation Principles"
    - **One Concept Per Section** - Avoid mixing topics, use progressive disclosure
    - **Action-Oriented Writing** - Start with verbs, avoid meta-commentary
    - **Technical Precision** - Consistent terminology, specific references
    - **Visual Consistency** - MkDocs Material admonitions, consistent formatting

## Content Structure

### **One Concept Per Section**
- Avoid mixing different topics
- Progressive disclosure - overview first, then details
- Clear section hierarchy (##, ###)
- Visual breaks with `---` between major sections

### **Writing Style**
- **Action-oriented** - Start with verbs ("Validate", "Generate", "Manage")
- **Concrete specifics** - "150 points per cycle" not "appropriate number of points"
- **Avoid meta-commentary** - No "This section will cover..." or "As mentioned above..."
- **Essential information only** - Remove explanatory text that doesn't drive decisions

## Technical Precision

### **Consistent Terminology**
- "strides" not mixed with "steps"
- "phase-indexed" not "phase data"
- Specific file references with line numbers: `file.py:125`
- Exact interface names: `validate_dataset()` not "validation method"

### **Priority Indicators**
- Use ⭐ for critical components
- Clear priority levels (High/Medium/Low)
- Status indicators: ✅ 🚧 📋

## File Organization

### **Structure Principles**
- Single responsibility per file
- Sequential prefixes (00_, 01_) for reading order
- Logical naming conventions
- Cross-references without circular dependencies

### **YAML Front-Matter**
```yaml
---
title: Page Title
tags: [tag1, tag2]
status: ready|review|final
---
```

## Mermaid Diagrams

### **Standards**
- Always use `%%{init: {'theme': 'default'}}%%` for light theme compatibility
- Clear node labels with type and description
- Consistent color coding across diagrams
- Readable styling and layout

## Documentation Maintenance

### **Update Triggers**
- Code interface changes
- New validation rules
- Architecture modifications
- User research insights

### **Quality Checks**
- All code examples tested
- Cross-references validated
- YAML front-matter consistent
- Line length <400 per file (recommended)

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** Documentation Guidelines & Standards Hub"
    **⬅️ Previous:** [Roadmap](07_ROADMAP.md) - Future development plans and milestones
    
    **➡️ Next:** [Admin Runbook](09_ADMIN_RUNBOOK.md) - Operations procedures and troubleshooting
    
    **📖 Reading time:** 5 minutes
    
    **🎯 Prerequisites:** None - Reference material for documentation contributors
    
    **🔄 Follow-up sections:** Admin procedures, Project maintenance

!!! tip "**Cross-References & Related Content**"
    **🔗 Project Overview:** [Overview](00_OVERVIEW.md) - Mission and vision informing documentation style
    
    **🔗 Implementation Quality:** [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) - Code quality standards alignment
    
    **🔗 Test Documentation:** [Test Strategy](06_TEST_STRATEGY.md) - Documentation testing requirements
    
    **🔗 System Administration:** [Admin Runbook](09_ADMIN_RUNBOOK.md) - MkDocs management and operations
    
    **🔗 All Documentation:** *(This page sets standards for every page in this documentation set)*
