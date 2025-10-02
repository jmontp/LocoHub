# Documentation Structure

This directory contains the source for the public LocoHub documentation site. Pages
are authored in Markdown and rendered with MkDocs + Material.

## Build the site locally

```bash
pip install -r requirements-container.txt
mkdocs serve        # Live preview at http://127.0.0.1:8000/
mkdocs build        # Writes the static site to site/
```

Run these commands from the repository root so MkDocs can resolve paths, snippets,
and dataset metadata.

## Directory overview

- `index.md` – Homepage with dataset table, quickstart, and download links
- `datasets/` – Automatically generated dataset overviews and validation summaries
- `tutorials/` – Python and MATLAB walkthroughs using the standardized schema
- `contributing/` – Contributor workflow, tooling docs, and SOPs
- `maintainers/` – Reviewer checklists and validator guidance
- `reference/` – Schema reference, task registry notes, and variable catalog
- `api/` – Hand-authored API reference for `user_libs/python`
- `assets/`, `stylesheets/`, `javascripts/` – Shared static assets and theme tweaks

## Writing guidelines

- Keep examples runnable against files in `converted_datasets/` or
  `docs/tutorials/assets/`
- Prefer task-focused headings ("Validate a dataset") over feature lists
- Show both Python and MATLAB snippets when possible; use the tabbed fences already
  in place
- Link to the canonical task registry (`internal/config_management/task_registry.py`)
  when describing task names or suffix conventions

## Maintenance checklist

- Re-run `python contributor_tools/manage_dataset_documentation.py update-documentation`
  after adding or refreshing a dataset so tables in `index.md`, `README.md`, and
  `datasets/index.md` stay in sync
- Keep the API reference aligned with `user_libs/python/` and
  `internal/validation_engine/`
- Update screenshots or diagrams when the UI of contributor tools changes
- Use `mkdocs build --strict` before publishing to catch broken links or code blocks

## Deployment

Docs are deployed automatically from the `main` branch via the
`deploy-docs` GitHub Actions workflow. The action runs `mkdocs build` and publishes
`site/` to GitHub Pages.
