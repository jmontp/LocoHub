---
title: Overview
tags: [landing, intro]
status: ready
---

# Dataset Standardization - Software Engineering Documentation

!!! info "🎯 **You are here** → Project Overview & Navigation Hub"
    This is your starting point for understanding the locomotion data standardization project. Choose your path based on your role and needs.
    
    **:clock4: Reading time:** 10 minutes | **:books: Pages:** 19 total docs

## 🚀 Project at a Glance

!!! quote "Mission Statement"
    Standardize locomotion datasets across research institutions for reproducible biomechanical research.

!!! quote "Vision Statement"  
    Become the definitive source for standardized locomotion datasets, empowering global biomechanics research with high-quality, interoperable data.

!!! abstract ":zap: TL;DR - Quick Summary"
    - **What:** Standardize biomechanical locomotion datasets from multiple research institutions
    - **Why:** Enable reproducible research with quality-assured, interoperable data  
    - **How:** Validation-first approach with Phase 1 tools for contributors, Phase 2 for consumers
    - **Status:** Phase 1 active - building validation infrastructure for dataset contributors

!!! tip "**Quick Start by Role**"
    === "Dataset Contributors (9%)"
        **You convert and validate datasets** → Start with [User Guide](01_USER_GUIDE.md) to understand your workflows
        
    === "System Administrators (1%)"
        **You manage infrastructure** → Jump to [Architecture](03_ARCHITECTURE.md) for system design
        
    === "Developers & Maintainers"
        **You build the system** → Check [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) for development strategy

## 🏗️ System Architecture Overview

**Data Formats:**
- `dataset_time.parquet` - Original sampling frequency
- `dataset_phase.parquet` - 150 points per gait cycle  
- Variables: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

**Validation:** Phase-indexed data only, requires exact 150 points per cycle.

!!! success "**Current Focus: Quality-First Foundation**"
    Phase 1 targets dataset contributors (9%) + administrators (1%) to establish validation infrastructure before building consumer tools for researchers (90%).

## 🎯 User Population Strategy

<div class="grid cards" markdown>
-   **📊 Dataset Consumers (90%)**
    
    Graduate students, clinical researchers, biomechanics engineers, sports scientists
    
    *Future Phase 2 focus*

-   **🔧 Dataset Contributors (9%)**
    
    Dataset curators (programmers + biomechanical validation)
    
    *Current Phase 1 focus*

-   **⚙️ System Administrators (1%)**
    
    Release managers, infrastructure maintainers
    
    *Current Phase 1 focus*
</div>

## 📈 Development Progress

!!! tip ":chart_with_upwards_trend: **Development Progress Tracker**"
    ```
    Phase 1: Validation Infrastructure (Current) ████████░░ 80%
    Phase 2: Consumer Tools (Future)            ░░░░░░░░░░  0%
    ```
    
    **Current Focus:** Quality-first foundation with validation tools

!!! abstract "**Phase 1:** Validation Infrastructure (Current)"
    === "Completed :white_check_mark:"
        - **Core validation architecture** - ValidationExpectationsParser, PhaseValidator
        - **Dataset validation reporting** - Comprehensive quality assessment
        - **Biomechanical visualization** - Kinematic/kinetic plotting with GIF animation
    
    === "In Progress :construction:"
        - **Specification management** - Auto/manual tuning tools
        - **Conversion scaffolding** - Dataset contributor examples
        - **Error investigation** - Debugging and analysis tools
    
    === "Planned :memo:"
        - **Documentation completion** - Tutorial integration
        - **Testing framework** - Comprehensive validation testing
    
    **Target:** Enable high-quality dataset contribution and validation

!!! note "**Phase 2:** Consumer Tools (Future)"
    === "Research Tools :microscope:"
        - **Data repository** - Standardized access portal
        - **Python/MATLAB libraries** - Analysis and manipulation tools
        - **Educational tutorials** - Getting started guides
    
    === "ML/AI Tools :robot:"
        - **Benchmark datasets** - Train/test splits with proper subject separation
        - **Quality metrics** - Automated assessment for ML workflows
    
    **Target:** Serve 90% of users with quality-assured datasets

## 🧭 Documentation Navigation

### 📚 **Essential Reading Path**

<div class="grid cards" markdown>
-   **1️⃣ [User Guide](01_USER_GUIDE.md)**
    
    ---
    
    **Who:** All users
    
    **Why:** Understand user personas, journeys, and research insights
    
    **Time:** 15 minutes
    
    **Next:** Requirements

-   **2️⃣ [Requirements](02_REQUIREMENTS.md)**
    
    ---
    
    **Who:** Developers, stakeholders
    
    **Why:** User stories and system requirements
    
    **Time:** 10 minutes
    
    **Next:** Architecture

-   **3️⃣ [Architecture](03_ARCHITECTURE.md)**
    
    ---
    
    **Who:** Developers, architects
    
    **Why:** System design and C4 diagrams
    
    **Time:** 20 minutes
    
    **Next:** Interface Spec

-   **4️⃣ [Interface Spec](04_INTERFACE_SPEC.md)**
    
    ---
    
    **Who:** Developers, API users
    
    **Why:** API and tool interfaces
    
    **Time:** 15 minutes
    
    **Next:** Implementation Guide
</div>

### 🔧 **Implementation & Operations**

<div class="grid cards" markdown>
-   **[Implementation Guide](05_IMPLEMENTATION_GUIDE.md)**
    
    ---
    
    Development strategy and coding standards
    
    **Audience:** Developers
    
    **Time:** 10 minutes

-   **[Test Strategy](06_TEST_STRATEGY.md)**
    
    ---
    
    Testing approach and specifications
    
    **Audience:** QA, Developers
    
    **Time:** 8 minutes

-   **[Admin Runbook](09_ADMIN_RUNBOOK.md)**
    
    ---
    
    Operations procedures and troubleshooting
    
    **Audience:** System Administrators
    
    **Time:** 10 minutes
</div>

### 📋 **Reference & Planning**

<div class="grid cards" markdown>
-   **[Roadmap](07_ROADMAP.md)**
    
    ---
    
    Future development plans and milestones
    
    **Audience:** All stakeholders
    
    **Time:** 5 minutes

-   **[Doc Standards](08_DOC_STANDARDS.md)**
    
    ---
    
    Documentation guidelines and best practices
    
    **Audience:** Documentation contributors
    
    **Time:** 5 minutes

-   **[Changelog](99_CHANGELOG.md)**
    
    ---
    
    Version history and release notes
    
    **Audience:** All users
    
    **Time:** 2 minutes
</div>

---

## 📄 Project Charter

**Mission:** Standardize locomotion datasets across research institutions for reproducible biomechanical research.

**Key Goals**: See [Project Charter](00a_PROJECT_CHARTER.md) for complete mission, vision, success metrics, and stakeholder analysis.

---

!!! success ":rocket: **Ready to Dive In?**"
    <div class="grid cards" markdown>
    -   :student: **New to the project?**
        
        ---
        
        Start with [User Guide](01_USER_GUIDE.md) to understand the user landscape
        
    -   :gear: **Need technical details?**
        
        ---
        
        Jump to [Architecture](03_ARCHITECTURE.md) for system design
        
    -   :hammer_and_wrench: **Want to contribute?**
        
        ---
        
        Check [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) for development workflow
    </div>

---

## :information_source: Documentation Meta

!!! info "Documentation Information"
    === "Status & Metrics"
        - **Total pages:** 19 comprehensive documents
        - **Last updated:** {{ "now" | date("Y-m-d") }}
        - **Documentation status:** Ready for Phase 1 development
        - **Maintenance:** Active - updated with each major release
        
    === "Quick Reference"
        - **Primary tool:** `validation_dataset_report.py`
        - **Main format:** Phase-indexed parquet (150 points/cycle)
        - **Target users:** Dataset contributors (9%) + administrators (1%)
        - **Architecture:** C4 model with validation-centric design
        
    === "Support"
        - **Issues:** Report documentation issues via GitHub
        - **Updates:** Documentation updated with each feature release
        - **Feedback:** Suggestions welcome from all user types

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** Overview & Navigation Hub"
    **⬅️ Previous:** *(Start of documentation)*
    
    **➡️ Next:** [User Guide](01_USER_GUIDE.md) - Understanding users and workflows
    
    **📖 Reading time:** 15 minutes
    
    **🎯 Prerequisites:** None - this is your starting point
    
    **🔄 Follow-up sections:** All documentation paths begin here

!!! tip "**Recommended Reading Paths**"
    **📚 Complete Linear Path (60 minutes):**
    Overview → [User Guide](01_USER_GUIDE.md) → [Requirements](02_REQUIREMENTS.md) → [Architecture](03_ARCHITECTURE.md) → [Interface Spec](04_INTERFACE_SPEC.md) → [Implementation Guide](05_IMPLEMENTATION_GUIDE.md)
    
    **⚡ Quick Technical Path (30 minutes):**
    Overview → [Architecture](03_ARCHITECTURE.md) → [Interface Spec](04_INTERFACE_SPEC.md) → [Implementation Guide](05_IMPLEMENTATION_GUIDE.md)
    
    **🎯 Role-Specific Paths:**
    - **Product Managers:** Overview → [User Guide](01_USER_GUIDE.md) → [Requirements](02_REQUIREMENTS.md) → [Roadmap](07_ROADMAP.md)
    - **Developers:** Overview → [Architecture](03_ARCHITECTURE.md) → [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) → [Test Strategy](06_TEST_STRATEGY.md)
    - **System Administrators:** Overview → [Architecture](03_ARCHITECTURE.md) → [Admin Runbook](09_ADMIN_RUNBOOK.md)
