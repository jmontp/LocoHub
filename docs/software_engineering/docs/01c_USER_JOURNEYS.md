---
title: User Journeys
tags: [user, journeys, workflows]
status: ready
---

# User Journeys

!!! info "🛤️ **You are here** → User Journey Workflows Hub"
    **Purpose:** Detailed workflow maps showing how users interact with the system
    
    **Who should read this:** Product managers, UX designers, developers, user researchers
    
    **Value:** Deep workflow insights enable better tool design and user experience optimization
    
    **Connection:** Detailed implementation of personas from [User Personas](01_USER_GUIDE.md), feeds into [Requirements](02_REQUIREMENTS.md)
    
    **:clock4: Reading time:** 12 minutes | **:footprints: Journey types:** 3 contributor workflows + 1 future consumer

!!! abstract "**TL;DR - User Journey Overview**"
    **Current Focus:** Dataset contributor workflows (Phase 1)
    
    - **Journey 1:** Technical dataset conversion by programmer
    - **Journey 2:** Validation specification updates by domain expert  
    - **Journey 3:** Collaborative dataset contribution (programmer + validator)
    - **Future:** Simplified consumer experience (Phase 2)
    
    **Key Insight:** Quality-first approach requires sophisticated contributor tools before simple consumer interfaces.

## User Journey Maps

### Current Focus: Dataset Contributor Journeys

#### Journey 1: Dataset Curator (Programmer) Converts Lab Dataset

**Workflow:** Discovery → Development → Quality Assessment → Resolution

**Discovery Phase:**
- Find conversion requirements (satisfaction: 3/5)
- Access validation scaffolding (satisfaction: 4/5)
- Review example scripts (satisfaction: 5/5)
- Understand standard specification (satisfaction: 3/5)

**Development Phase:**
- Analyze raw dataset structure (satisfaction: 4/5)
- Map variables to standard names (satisfaction: 2/5)
- Create time-indexed parquet (satisfaction: 4/5)
- Generate phase dataset with tool (satisfaction: 5/5)
- Handle missing data patterns (satisfaction: 2/5)

**Quality Assessment Phase:**
- Generate comprehensive dataset report (satisfaction: 5/5)
- Review validation and quality results (satisfaction: 3/5)
- Debug biomechanical failures (satisfaction: 1/5)
- Consult biomechanics expert (satisfaction: 3/5)
- Fix conversion issues (satisfaction: 3/5)
- Document conversion decisions (satisfaction: 2/5)
- Prepare contribution materials (satisfaction: 3/5)

**Pain Points:**
- Complex biomechanical conventions and coordinate systems
- Variable naming inconsistencies across source datasets
- Ensuring vertical ground reaction force data is properly formatted for phase generation
- Debugging validation failures requires domain expertise
- Time-consuming iteration between conversion and validation

**Emotional Journey:**
- **Discovery**: Confidence with clear examples and scaffolding
- **Development**: Frustration with biomechanical complexity
- **Quality Assessment**: Relief with unified validation and quality reporting
- **Resolution**: Satisfaction when comprehensive report shows dataset quality

#### Journey 2: Dataset Curator (Biomechanical Validation) Updates Validation Ranges

**Workflow:** Research → Analysis → Implementation → Verification

**Research Phase:**
- Review recent literature (satisfaction: 4/5)
- Identify range updates needed (satisfaction: 3/5)
- Analyze population differences (satisfaction: 3/5)
- Document evidence sources (satisfaction: 2/5)

**Analysis Phase:**
- Run statistical range analysis (satisfaction: 4/5)
- Compare literature vs data (satisfaction: 3/5)
- Assess impact on existing datasets (satisfaction: 2/5)
- Preview validation changes (satisfaction: 4/5)

**Implementation Phase:**
- Update validation specifications (satisfaction: 3/5)
- Test against known datasets (satisfaction: 4/5)
- Document rationale for changes (satisfaction: 2/5)
- Communicate updates to team (satisfaction: 3/5)

**Verification Phase:**
- Monitor validation pass rates (satisfaction: 4/5)
- Investigate unexpected failures (satisfaction: 2/5)
- Refine ranges based on feedback (satisfaction: 3/5)
- Maintain change documentation (satisfaction: 2/5)

**Pain Points:**
- Balancing strict standards with real-world data variability
- Explaining biomechanical rationale to programming colleagues
- Manual investigation of outliers and edge cases
- Tracking change rationale across multiple updates

**Emotional Journey:**
- **Research**: Professional satisfaction with evidence-based decisions
- **Analysis**: Analytical engagement with statistical tools
- **Implementation**: Confidence in systematic change management
- **Verification**: Responsibility for community data quality

#### Journey 3: Collaborative Dataset Contribution

**Workflow:** Planning → Development → Quality Review → Documentation

**Planning Phase:**
- Define dataset contribution goals (satisfaction: 5/5)
- Assign programmer and validator roles (satisfaction: 4/5)
- Review existing similar datasets (satisfaction: 3/5)
- Plan conversion approach (satisfaction: 4/5)

**Development Phase:**
- Programmer creates conversion script (satisfaction: 3/5)
- Validator reviews biomechanical accuracy (satisfaction: 4/5)
- Iterate on validation failures (satisfaction: 2/5)
- Document conversion decisions (satisfaction: 3/5)

**Quality Review Phase:**
- Run comprehensive validation (satisfaction: 4/5)
- Generate quality assessment report (satisfaction: 4/5)
- Compare against population norms (satisfaction: 3/5)
- Approve dataset for contribution (satisfaction: 5/5)

**Documentation Phase:**
- Create dataset documentation (satisfaction: 3/5)
- Document biomechanical considerations (satisfaction: 4/5)
- Prepare contribution materials (satisfaction: 3/5)
- Submit to community repository (satisfaction: 5/5)

**Pain Points:**
- Communication gaps between programming and biomechanics expertise
- Iterative debugging cycle requires both skill sets
- Documentation must serve both technical and domain audiences
- Quality standards require consensus between roles

**Emotional Journey:**
- **Planning**: Excitement about contributing to community
- **Development**: Collaborative problem-solving satisfaction
- **Quality Review**: Shared responsibility for data integrity
- **Documentation**: Pride in professional contribution

### Future: Consumer Journey Preview *(90% of users - Phase 2)*

**Simplified Consumer Experience:**
- Discovery: Find standardized repository → Browse quality-assured datasets → Review population demographics → Download parquet files
- Analysis: Load data with Python library → Apply domain-specific analysis → Trust data quality implicitly → Focus on research questions

**Design Goal:** Consumer confidence through behind-the-scenes validation quality.

## Journey Insights

### Contributor Success Factors
1. **Clear Scaffolding**: Examples and guidelines reduce development friction
2. **Automated Phase Generation**: `generate_phase_dataset.py` handles complex gait cycle detection
3. **Domain Expertise Integration**: Biomechanics knowledge accessible to programmers
4. **Iterative Feedback**: Validation tools enable continuous improvement
5. **Comprehensive Documentation**: Technical and domain perspectives both covered

### Collaboration Patterns
- **Programmer Focus**: Technical implementation, data processing, tool usage
- **Validator Focus**: Biomechanical accuracy, standard evolution, quality oversight
- **Shared Responsibility**: Dataset quality, documentation, community contribution

### Pain Point Mitigation
- **Technical Complexity**: Scaffolding and examples reduce learning curve
- **Domain Knowledge Gaps**: Validation tools provide biomechanical guidance
- **Quality Uncertainty**: Comprehensive reporting builds confidence
- **Collaboration Friction**: Clear role definitions and shared tools

### Emotional Design Principles
- **Confidence Through Examples**: Proven patterns reduce uncertainty
- **Satisfaction Through Quality**: Comprehensive tools enable thorough work
- **Pride Through Contribution**: Community impact motivates quality standards
- **Support Through Collaboration**: Shared expertise reduces individual burden

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** User Journey Workflows Hub"
    **⬅️ Previous:** [User Guide](01_USER_GUIDE.md) - User personas and population analysis
    
    **➡️ Next:** [Requirements](02_REQUIREMENTS.md) - User stories derived from journey insights
    
    **📖 Reading time:** 12 minutes
    
    **🎯 Prerequisites:** [User Guide](01_USER_GUIDE.md) - Understanding of user personas
    
    **🔄 Follow-up sections:** Requirements, Architecture design decisions

!!! tip "**Cross-References & Related Content**"
    **🔗 User Context:** [User Guide](01_USER_GUIDE.md) - Complete persona profiles and user population analysis
    
    **🔗 Technical Tools:** [User Roles & Entry Points](01a_USER_ROLES.md) - CLI tool catalog by user role
    
    **🔗 System Interactions:** [System Context](01b_SYSTEM_CONTEXT.md) - Architecture diagrams and interaction patterns
    
    **🔗 Requirements Traceability:** [Requirements](02_REQUIREMENTS.md) - User stories derived from these journey insights

---

!!! success "**Key Journey Takeaways**"
    ✅ **Collaborative Workflows:** Contributors work in programmer + domain expert pairs
    
    ✅ **Quality Gates:** Multiple validation checkpoints ensure data integrity
    
    ✅ **Tool Integration:** Comprehensive reporting reduces debugging friction
    
    ✅ **Emotional Design:** Confidence through examples, satisfaction through quality tools