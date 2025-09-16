---
title: Contributor SOP
---

# Contributor Standard Operating Procedures

## High-Level Operation

```mermaid
graph LR
    A[Your Data] --> B[Standardized Format]
    B --> C[Validated Dataset]
    C --> D[Community Resource]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#c8e6c9
```

The detailed procedure reuses the same palette: blue-tinted nodes for intake decisions, orange-cream for standardization tasks, green for validation, and sage for the handoff steps.

## Low-Level Operation

```mermaid
graph TD
    A["Start:<br/>Decide to contribute"] --> B{"Do you control<br/>data sharing rights?"}
    B -->|No| Z["Pause:<br/>Resolve access or licensing"]
    Z --> B
    B -->|Yes| C["Clone repo<br/>and install tools"]
    C --> D["Review reference dataset<br/>and task_info fields"]
    D --> E["Build conversion script<br/>from template"]
    E --> F{"Does conversion<br/>run cleanly?"}
    F -->|No| E
    F -->|Yes| G["Export standardized<br/>parquet dataset"]
    G --> H["Run validation suite<br/>(quick check + tuner)"]
    H --> I{"Are validation results<br/>acceptable?"}
    I -->|No| J["Adjust conversion logic<br/>or validation ranges"]
    J --> H
    I -->|Yes| K["Fill contributor checklist<br/>(task_info, metadata, citation)"]
    K --> L["Bundle dataset, metadata,<br/>and scripts for review"]
    L --> M["Submit PR or share bundle<br/>with maintainers"]
    M --> N["End"]

    classDef intake fill:#e3f2fd,stroke:#1e88e5,color:#0d47a1
    classDef standard fill:#fff3e0,stroke:#fb8c00,color:#e65100
    classDef qa fill:#e8f5e9,stroke:#43a047,color:#1b5e20
    classDef share fill:#c8e6c9,stroke:#2e7d32,color:#1b5e20

    class A,B,Z intake
    class C,D,E,F,G standard
    class H,I,J qa
    class K,L,M,N share

    click C "https://github.com/jmontp/LocoHub" "Open the LocoHub repository" _blank
    click D "../#step-1-convert-to-a-table" "Conversion quickstart"
    click E "../#pattern-a-folder-based" "Conversion patterns"
    click G "../#step-2-validate-pythoncli" "Validation workflow"
    click H "../tool_tutorials/#quick_validation_checkpy-fast-quality-scan" "Run the quick validation check"
    click J "../tool_tutorials/#interactive_validation_tunerpy-visual-range-editing" "Tune validation ranges visually"
    click K "../#submission-checklist" "Contribution checklist"
    click L "../#package-to-share" "Packaging guidance"
    click M "https://github.com/jmontp/LocoHub/pulls" "Open pull requests on GitHub" _blank
```
