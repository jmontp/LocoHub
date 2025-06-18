🗂️ MkDocs Documentation Finalization Plan
(for “Dataset Standardization” project)

Goal: Shrink 36 loose Markdown files into 11 well-structured pages under docs/, ready for MkDocs Material, with no duplication and clear cross-links, while retaining all domain knowledge required to implement, test, and extend the code-base.

0  Environment prep (ONLY once)
bash
Copy
Edit
# inside the repo root
python3 -m pip install --upgrade \
    mkdocs-material \
    mkdocs-mermaid2-plugin \
    pymdown-extensions
✅ Success check: mkdocs --version prints without error.

1  Create MkDocs config & sidebar
TASK 1.1 Create mkdocs.yml
yaml
Copy
Edit
site_name: Dataset Standardization
theme:
  name: material
  palette:
    scheme: default
plugins:
  - search
  - mermaid2
markdown_extensions:
  - toc:
      permalink: true
  - pymdownx.tasklist
nav:
  - Overview: 00_OVERVIEW.md
  - User Guide: 01_USER_GUIDE.md
  - Requirements: 02_REQUIREMENTS.md
  - Architecture: 03_ARCHITECTURE.md
  - Interface Spec: 04_INTERFACE_SPEC.md
  - Implementation Guide: 05_IMPLEMENTATION_GUIDE.md
  - Test Strategy: 06_TEST_STRATEGY.md
  - Roadmap: 07_ROADMAP.md
  - Doc Standards: 08_DOC_STANDARDS.md
  - Admin Runbook: 09_ADMIN_RUNBOOK.md
  - Changelog: 99_CHANGELOG.md
✅ Success check: mkdocs build finishes clean (will warn about missing pages until TASK 2 is done).

2  Create skeleton pages with YAML front-matter
For each file in the table below, create it under docs/ with the exact H1 title and the YAML header shown.

File	H1 title	YAML header (insert at very top)
00_OVERVIEW.md	Overview	---\ntitle: Overview\ntags: [landing, intro]\nstatus: draft\n---
01_USER_GUIDE.md	User Guide	title: User Guide …
02_REQUIREMENTS.md	Requirements	…
03_ARCHITECTURE.md	Architecture	…
04_INTERFACE_SPEC.md	Interface Specification	…
05_IMPLEMENTATION_GUIDE.md	Implementation Guide	…
06_TEST_STRATEGY.md	Test Strategy	…
07_ROADMAP.md	Roadmap	…
08_DOC_STANDARDS.md	Documentation Standards	…
09_ADMIN_RUNBOOK.md	Admin Runbook	…
99_CHANGELOG.md	Changelog	…

(Front-matter keys: title, tags (list), status (draft for now).)

✅ Success check: mkdocs serve now renders empty pages without warnings.

3  Content migration & de-duplication
(Four parallel streams – run in any order)

STREAM A “User & Scope”
Move from	Keep / merge into docs/01_USER_GUIDE.md
03_personas.md	Personas section
07_journeys.md	User Journeys section
05_research_insights.md	Research Insights section

Rules

Keep only one description per persona.

For any list duplicated in another file, keep the most complete copy and insert a relative link to where the canonical copy now lives.

Max length after consolidation ≈ 400 lines.

✅ Success: 01_USER_GUIDE.md passes 400-line check and has no “TBD” placeholders.

STREAM B “Requirements & Acceptance”
Move from	Into docs/02_REQUIREMENTS.md
04_user_stories.md	User stories table.
10_requirements.md	System requirements list.

Extra actions

Prefix every user story with unique US-xx.

Immediately under each user story, insert this LLM prompt block:

html
Copy
Edit
<!--
<LLM-PROMPT>
You are Claude Code. Generate Python (+pytest) that fulfils the acceptance
criteria table below. Output ONLY the code.
</LLM-PROMPT>
-->
✅ Success: all stories uniquely numbered, every story has the prompt block.

STREAM C “Architecture & Diagrams”
Pick one context, one container, one component diagram from the 11-14_* files (choose the “future” versions if present).

Convert PlantUML (.puml) to Mermaid:

bash
Copy
Edit
python tools/diagram_convert.py --in old_diagram.puml --out docs/img/diagram.mmd
(If tools/diagram_convert.py does not exist yet, create a minimal converter that strips @startuml/@enduml and keeps ASCII boxes; manual touch-up is fine).

Embed with:

md
Copy
Edit
```mermaid
%% File: img/diagram.mmd
(paste content here)
Under each diagram, add a “See also” box linking to Interface Spec or Implementation Guide if relevant.

✅ Success: mkdocs build shows diagrams rendered; no broken img links.

STREAM D “Tests & Implementation Guide”
Source	Destination
15*_test_docs.md + 18_test_specifications.md	Consolidate prose into docs/06_TEST_STRATEGY.md
16_implementation_strategy.md	Merge into docs/05_IMPLEMENTATION_GUIDE.md

Test stub generation

Parse US-xx IDs from 02_REQUIREMENTS.md.

For each ID, create tests/us_xx/test_placeholder.py with:

python
Copy
Edit
import pytest
@pytest.mark.skip("Not implemented yet for US-xx")
def test_us_xx():
    pass
(Automate via tools/us_test_stubber.py if available.)

✅ Success: pytest -q prints all skipped, zero failures.

4  Global clean-up rules
No duplicates
Run grep -R "### .*" docs | sort | uniq -d – if anything prints, fix duplicates or disambiguate headings.

Relative links only ([text](../02_REQUIREMENTS.md#us-03)).

Line wraps: hard-wrap at 100 chars so GitHub diff is readable.

Call-outs: use Material admonitions (!!! note, !!! warning) for key implementation gotchas.

Changelog (99_CHANGELOG.md): start with

md
Copy
Edit
## [Unreleased]
### Added
- MkDocs migration skeleton (see commit <hash>).
5  Manual verification checklist (final gate)
 mkdocs build --strict completes with 0 errors, 0 warnings.

 pytest -q returns “N skipped, 0 failed”.

 Every page top shows correct title, tags, status.

 Each user story links forward to at least one test case file.

 Architecture page diagrams render in both GitHub preview and built site.

6  Post-migration TODOs (no action now, keep for backlog)
Add GitHub Actions workflows (docs.yml, ci.yml).

Enable GitHub Pages → branch gh-pages.

Replace skipped tests with real ones as code is generated.

END OF AGENT PLAN
Hand-off instructions:

Save this whole file as AGENT_TASKS.md in repo root.

Feed each numbered TASK (or STREAM) chunk to Claude Code in order, or run them in parallel workers.

Use the success checks to decide when to move on.