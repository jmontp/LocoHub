# User Journey Maps

**User workflows with emotional context and pain points.**

## Current Focus: Dataset Contributor Journeys

### Journey 1: Dataset Curator (Programmer) Converts Lab Dataset

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Dataset Curator (Programmer): Converting Lab Dataset to Standard Format
    section Discovery
      Find conversion requirements: 3: Programmer
      Access validation scaffolding: 4: Programmer
      Review example scripts: 5: Programmer
      Understand standard specification: 3: Programmer
    section Development
      Analyze raw dataset structure: 4: Programmer
      Map variables to standard names: 2: Programmer
      Create time-indexed parquet: 4: Programmer
      Generate phase dataset with tool: 5: Programmer
      Handle missing data patterns: 2: Programmer
    section Quality Assessment
      Generate comprehensive dataset report: 5: Programmer
      Review validation and quality results: 3: Programmer
      Debug biomechanical failures: 1: Programmer
      Consult biomechanics expert: 3: Programmer
      Fix conversion issues: 3: Programmer
      Document conversion decisions: 2: Programmer
      Prepare contribution materials: 3: Programmer
```

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

---

### Journey 2: Dataset Curator (Biomechanical Validation) Updates Validation Ranges

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Biomechanical Validator: Updating Validation Standards
    section Research
      Review recent literature: 4: Validator
      Identify range updates needed: 3: Validator
      Analyze population differences: 3: Validator
      Document evidence sources: 2: Validator
    section Analysis
      Run statistical range analysis: 4: Validator
      Compare literature vs data: 3: Validator
      Assess impact on existing datasets: 2: Validator
      Preview validation changes: 4: Validator
    section Implementation
      Update validation specifications: 3: Validator
      Test against known datasets: 4: Validator
      Document rationale for changes: 2: Validator
      Communicate updates to team: 3: Validator
    section Verification
      Monitor validation pass rates: 4: Validator
      Investigate unexpected failures: 2: Validator
      Refine ranges based on feedback: 3: Validator
      Maintain change documentation: 2: Validator
```

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

---

### Journey 3: Collaborative Dataset Contribution

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Collaborative Team: Adding New Dataset to Collection
    section Planning
      Define dataset contribution goals: 5: Team
      Assign programmer and validator roles: 4: Team
      Review existing similar datasets: 3: Team
      Plan conversion approach: 4: Team
    section Development
      Programmer creates conversion script: 3: Programmer
      Validator reviews biomechanical accuracy: 4: Validator
      Iterate on validation failures: 2: Both
      Document conversion decisions: 3: Programmer
    section Quality Review
      Run comprehensive validation: 4: Validator
      Generate quality assessment report: 4: Both
      Compare against population norms: 3: Validator
      Approve dataset for contribution: 5: Both
    section Documentation
      Create dataset documentation: 3: Programmer
      Document biomechanical considerations: 4: Validator
      Prepare contribution materials: 3: Both
      Submit to community repository: 5: Both
```

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

---

## Future: Consumer Journey Preview *(90% of users - Phase 2)*

### Simplified Consumer Experience

```mermaid
%%{init: {'theme': 'dark'}}%%
journey
    title Future Consumer: Using Validated Dataset
    section Discovery
      Find standardized repository: 5: Consumer
      Browse quality-assured datasets: 5: Consumer
      Review population demographics: 4: Consumer
      Download parquet files: 5: Consumer
    section Analysis
      Load data with Python library: 5: Consumer
      Apply domain-specific analysis: 5: Consumer
      Trust data quality implicitly: 5: Consumer
      Focus on research questions: 5: Consumer
```

**Design Goal:** Consumer confidence through behind-the-scenes validation quality.

---

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