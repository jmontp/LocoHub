#!/usr/bin/env python3
"""
Manage Dataset Documentation

A tool for contributors to prepare and reset dataset documentation including
overview pages, validation reports, metadata, and plots.

Usage:
    python contributor_tools/manage_dataset_documentation.py add-dataset \
        --dataset converted_datasets/your_dataset_phase.parquet \
        [--metadata-file docs/datasets/_metadata/your_dataset.yaml] \
        [--ranges-file contributor_tools/validation_ranges/custom.yaml] \
        [--replace-existing] \
        [--overwrite]

The tool will:
1. Collect dataset metadata (interactively or from --metadata-file)
2. Run validation and generate reports
3. Create standardized documentation
4. Package everything for PR submission
5. Show a checklist of files to include
"""

import sys
import argparse
import yaml
import json
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import os
from collections import OrderedDict
from pandas import isna

# Add parent directories to path for imports
current_dir = Path(__file__).parent
repo_root = current_dir.parent
sys.path.insert(0, str(repo_root))

from user_libs.python.locomotion_data import LocomotionData

SITE_DATASET_BASE_URL = "https://jmontp.github.io/LocoHub/datasets"
DATASET_TABLE_FILES = [
    repo_root / "README.md",
    repo_root / "docs" / "index.md",
    repo_root / "docs" / "datasets" / "index.md",
]
TABLE_MARKER_START = "<!-- DATASET_TABLE_START -->"
TABLE_MARKER_END = "<!-- DATASET_TABLE_END -->"

DEFAULT_RANGES_CANDIDATES = [
    repo_root / "contributor_tools" / "validation_ranges" / "default_ranges_v3.yaml",
    repo_root / "contributor_tools" / "validation_ranges" / "default_ranges.yaml",
]


def _resolve_default_ranges_file() -> Path:
    for candidate in DEFAULT_RANGES_CANDIDATES:
        if candidate.exists():
            return candidate
    # Return first candidate even if missing to preserve prior behaviour
    return DEFAULT_RANGES_CANDIDATES[0]

# Import validation modules
try:
    from internal.validation_engine.validator import Validator
except ImportError as e:
    print(f"❌ Error importing validation modules: {e}")
    print("Make sure you're running from the repository root directory")
    sys.exit(1)


def check_existing_short_codes() -> Dict[str, str]:
    """
    Check for existing short codes in documentation.
    
    Returns:
        Dictionary mapping short codes to dataset names
    """
    codes = {}
    docs_dir = repo_root / "docs" / "datasets"
    
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            try:
                with open(doc_file, 'r') as f:
                    content = f.read()
                    # Look for short code in frontmatter or metadata
                    match = re.search(r'short_code:\s*([A-Z0-9]+)', content)
                    if match:
                        codes[match.group(1)] = doc_file.stem
            except Exception:
                continue
    
    return codes


def _relative_path(path: Path) -> str:
    """Return repo-relative path if possible, else name."""
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return path.name


def _display_path(path: Path) -> str:
    """Return repo-relative path if possible, else full path string."""
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_metadata_file(path: Path) -> Dict:
    """Load metadata from a YAML or JSON file."""

    try:
        with open(path, "r") as f:
            if path.suffix.lower() in {".yml", ".yaml"}:
                data = yaml.safe_load(f)
            elif path.suffix.lower() == ".json":
                data = json.load(f)
            else:
                # Try YAML first, then JSON as fallback
                try:
                    data = yaml.safe_load(f)
                except yaml.YAMLError:
                    f.seek(0)
                    data = json.load(f)
    except Exception as exc:
        raise ValueError(f"Unable to load metadata file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Metadata file must contain a mapping of keys to values")

    return data


def _normalize_tasks(value) -> List[str]:
    """Normalize tasks input to a list of strings."""

    if not value:
        return []

    if isinstance(value, str):
        return [task.strip() for task in value.split(",") if task.strip()]

    if isinstance(value, (list, tuple)):
        return [str(task).strip() for task in value if str(task).strip()]

    return []


def _format_task_name(task: str) -> str:
    return task.replace("_", " ").title()


def _slugify_short_code(short_code: str) -> str:
    return short_code.lower()


def _canonical_cell_value(value) -> str:
    """Return a stripped string representation, preserving blanks for hierarchy."""

    if isna(value):
        return ''
    return str(value).strip()


def _extract_task_catalog(locomotion_data: LocomotionData) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    """Return sorted task list and hierarchical rows (task, task_id, task_info)."""

    detected_tasks = [task for task in locomotion_data.get_tasks() if task]
    required_cols = {'task', 'task_id', 'task_info'}
    if not required_cols.issubset(locomotion_data.df.columns):
        return detected_tasks, []

    subset = locomotion_data.df[['task', 'task_id', 'task_info']].drop_duplicates().copy()
    for column in ['task', 'task_id', 'task_info']:
        subset[column] = subset[column].apply(_canonical_cell_value)

    subset = subset.sort_values(['task', 'task_id', 'task_info'])
    rows = list(subset[['task', 'task_id', 'task_info']].itertuples(index=False, name=None))
    return detected_tasks, rows


def _build_task_table(rows: List[Tuple[str, str, str]]) -> str:
    """Build hierarchical markdown table from task rows."""

    if not rows:
        return ''

    lines = [
        "| Task | Task ID | Task Info |",
        "|------|---------|-----------|",
    ]
    prev_task: Optional[str] = None
    prev_task_id: Optional[str] = None

    for task, task_id, task_info in rows:
        task_value = task if task else '—'
        task_id_value = task_id if task_id else '—'
        task_info_value = task_info if task_info else '—'

        if prev_task is not None and task == prev_task:
            task_cell = ' '
        else:
            task_cell = task_value

        if task != prev_task:
            prev_task_id = None

        if prev_task_id is not None and task_id == prev_task_id and task == prev_task:
            task_id_cell = ' '
        else:
            task_id_cell = task_id_value

        lines.append(f"| {task_cell} | {task_id_cell} | {task_info_value} |")

        prev_task = task
        prev_task_id = task_id

    return "\n".join(lines)


def write_metadata_file(metadata: Dict) -> None:
    dataset_name = metadata['dataset_name']
    meta_dir = repo_root / "docs" / "datasets" / "_metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta_path = meta_dir / f"{dataset_name}.yaml"

    fields = OrderedDict()
    fields['display_name'] = metadata['display_name']
    fields['short_code'] = metadata['short_code']
    fields['description'] = metadata['description']
    fields['year'] = str(metadata['year'])
    fields['institution'] = metadata['institution']
    fields['subjects'] = str(metadata['subjects'])
    fields['tasks'] = metadata['tasks']
    if metadata.get('download_url'):
        fields['download_url'] = metadata['download_url']
    if metadata.get('citation'):
        fields['citation'] = metadata['citation']
    if metadata.get('protocol'):
        fields['protocol'] = metadata['protocol']
    if metadata.get('notes'):
        fields['notes'] = metadata['notes']
    fields['date_added'] = metadata.get('date_added')
    fields['validation_status'] = metadata.get('validation_status')
    if metadata.get('validation_pass_rate') is not None:
        fields['validation_pass_rate'] = round(float(metadata['validation_pass_rate']), 1)
    fields['total_strides'] = metadata.get('validation_total_strides')
    fields['passing_strides'] = metadata.get('validation_passing_strides')
    fields['quality_display'] = metadata.get('quality_display')
    fields['doc_url'] = metadata.get('doc_url')
    fields['doc_path'] = metadata.get('doc_path')
    if metadata.get('validation_doc_url'):
        fields['validation_doc_url'] = metadata.get('validation_doc_url')
    if metadata.get('validation_doc_path'):
        fields['validation_doc_path'] = metadata.get('validation_doc_path')
    fields['validation_summary'] = metadata.get('validation_summary')
    if metadata.get('validation_ranges_file'):
        fields['validation_ranges_file'] = metadata.get('validation_ranges_file')

    with open(meta_path, 'w') as fh:
        yaml.safe_dump(dict(fields), fh, sort_keys=False)


def _relative_link(path_value: Optional[str], table_file: Path) -> Optional[str]:
    if not path_value:
        return None
    target = Path(path_value)
    if not target.is_absolute():
        target = (repo_root / target).resolve()
    if target.suffix != '.md':
        target = target.with_suffix('.md')
    try:
        docs_root = repo_root / "docs"
        target_rel = target.relative_to(docs_root)
    except ValueError:
        # Path outside docs; return as-is
        return target.as_posix()

    table_rel = table_file.relative_to(docs_root)
    rel_path = PurePosixPath(
        os.path.relpath(target_rel.as_posix(), start=table_rel.parent.as_posix())
    )
    return rel_path.as_posix()


def _resolve_dataset_link(data: Dict, table_file: Path, absolute: bool) -> str:
    if absolute:
        return data.get('doc_url') or f"{SITE_DATASET_BASE_URL}/{data['dataset_name']}/"
    relative = _relative_link(data.get('doc_path'), table_file)
    if relative:
        return relative
    fallback = repo_root / "docs" / "datasets" / f"{data['dataset_name']}.md"
    rel_path = _relative_link(str(fallback), table_file)
    return rel_path or f"{data['dataset_name']}.md"


def _resolve_validation_link(data: Dict, table_file: Path, absolute: bool) -> Optional[str]:
    if absolute:
        return data.get('validation_doc_url') or f"{SITE_DATASET_BASE_URL}/{data['dataset_name']}_validation/"
    relative = _relative_link(data.get('validation_doc_path'), table_file)
    if relative:
        return relative
    fallback = repo_root / "docs" / "datasets" / f"{data['dataset_name']}_validation.md"
    return _relative_link(str(fallback), table_file)


def _build_dataset_table(metadata_entries: List[Dict], table_file: Path, absolute_links: bool) -> str:
    rows = []
    header = "| Dataset | Tasks | Quality | Validation | Download |"
    separator = "|---------|-------|---------|------------|----------|"

    for data in sorted(metadata_entries, key=lambda d: d.get('display_name', '').lower()):
        doc_url = _resolve_dataset_link(data, table_file, absolute_links)
        validation_url = _resolve_validation_link(data, table_file, absolute_links)
        display_name = data.get('display_name') or data['dataset_name']
        dataset_cell = f"[{display_name}]({doc_url})"
        tasks_list = data.get('tasks', []) or []
        tasks_cell = ', '.join(_format_task_name(task) for task in tasks_list) if tasks_list else '—'
        quality = data.get('quality_display') or data.get('validation_status') or '—'
        validation_cell = f"[Report]({validation_url})" if validation_url else '—'
        download_url = data.get('download_url')
        download_cell = f"[Download]({download_url})" if download_url else 'Coming Soon'
        rows.append(f"| {dataset_cell} | {tasks_cell} | {quality} | {validation_cell} | {download_cell} |")

    return "\n".join([header, separator] + rows)


def replace_between_markers(path: Path, content: str) -> None:
    text = path.read_text()
    if TABLE_MARKER_START not in text or TABLE_MARKER_END not in text:
        return
    new_text = re.sub(
        rf"{re.escape(TABLE_MARKER_START)}.*?{re.escape(TABLE_MARKER_END)}",
        f"{TABLE_MARKER_START}\n{content}\n{TABLE_MARKER_END}",
        text,
        flags=re.DOTALL,
    )
    path.write_text(new_text)


def update_dataset_tables() -> None:
    meta_dir = repo_root / "docs" / "datasets" / "_metadata"
    if not meta_dir.exists():
        return

    metadata_entries = []
    for meta_file in sorted(meta_dir.glob('*.yaml')):
        data = load_metadata_file(meta_file)
        data['dataset_name'] = meta_file.stem
        metadata_entries.append(data)

    if not metadata_entries:
        return

    for table_file in DATASET_TABLE_FILES:
        if table_file.exists():
            use_absolute = table_file.name.lower() == 'readme.md'
            table = _build_dataset_table(metadata_entries, table_file, use_absolute)
            replace_between_markers(table_file, table)


def _remove_path(path: Path, removed: List[str]) -> None:
    """Delete files or directories that exist and track what changed."""

    if not path.exists() and not path.is_symlink():
        return

    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path.relative_to(repo_root)))
    except Exception as exc:
        removed.append(f"FAILED:{path.relative_to(repo_root)} ({exc})")


def reset_dataset_assets(dataset_slug: str, include_parquet: bool = False) -> List[str]:
    """Remove generated assets for a dataset so it can be rebuilt."""

    removed: List[str] = []

    docs_dir = repo_root / "docs" / "datasets"
    metadata_dir = docs_dir / "_metadata"
    plots_dir = docs_dir / "validation_plots"

    _remove_path(docs_dir / f"{dataset_slug}.md", removed)
    _remove_path(docs_dir / f"{dataset_slug}_validation.md", removed)
    _remove_path(metadata_dir / f"{dataset_slug}.yaml", removed)
    _remove_path(plots_dir / dataset_slug, removed)

    if plots_dir.exists():
        for file_path in plots_dir.glob(f"*{dataset_slug}*.png"):
            _remove_path(file_path, removed)

    checklist_path = repo_root / f"submission_checklist_{dataset_slug}.txt"
    _remove_path(checklist_path, removed)

    if include_parquet:
        for parquet_path in repo_root.glob(f"converted_datasets/{dataset_slug}*.parquet"):
            _remove_path(parquet_path, removed)

    update_dataset_tables()

    return removed


def _remove_dataset_for_slug(dataset_slug: str, include_parquet: bool = False) -> List[str]:
    """Wrapper to remove dataset assets and display summary."""

    removed_paths = reset_dataset_assets(dataset_slug, include_parquet=include_parquet)
    if removed_paths:
        print(f"♻️ Removed existing dataset assets for '{dataset_slug}':")
        for path in removed_paths:
            print(f"  - {path}")
    else:
        print(f"ℹ️ No existing assets found for '{dataset_slug}'.")
    return removed_paths


def _generate_validation_plots(dataset_path: Path, output_dir: Path, ranges_file: Optional[Path] = None) -> None:
    script_path = repo_root / 'contributor_tools' / 'quick_validation_check.py'
    if not script_path.exists():
        return
    cmd = [
        sys.executable,
        str(script_path),
        str(dataset_path),
        '--plot',
        '--output-dir',
        str(output_dir)
    ]
    if ranges_file:
        cmd.extend(['--ranges', str(ranges_file)])
    subprocess.run(cmd, check=True, cwd=repo_root)


def update_validation_gallery(doc_path: Path, dataset_name: str) -> None:
    plots_dir = repo_root / 'docs' / 'datasets' / 'validation_plots' / dataset_name
    if not plots_dir.exists():
        return
    images = sorted(plots_dir.glob('*.png'))
    if not images:
        return

    gallery_lines = []
    for image_path in images:
        name = image_path.stem
        task_segment = name
        if '_phase_' in name and '_all_features' in name:
            task_segment = name.split('_phase_')[1].split('_all_features')[0]
        task_segment = task_segment.replace('filtered_', '').replace('raw_', '')
        task_title = _format_task_name(task_segment)
        rel_path = Path('validation_plots') / dataset_name / image_path.name
        gallery_lines.append(f"![{task_title}](./{rel_path.as_posix()})")
        gallery_lines.append("")

    gallery = "\n".join(gallery_lines).strip() or "(Generate plots with quick_validation_check.py --plot)"
    content = doc_path.read_text()
    if '<!-- VALIDATION_GALLERY -->' in content:
        content = content.replace('<!-- VALIDATION_GALLERY -->', f"{gallery}\n")
    else:
        content = content + "\n" + gallery + "\n"
    doc_path.write_text(content)

def generate_dataset_page(dataset_path: Path, metadata: Dict, validation_doc_filename: str) -> Path:
    """Generate the dataset overview markdown page."""
    dataset_rel = _relative_path(dataset_path)
    date_added = metadata.get('date_added') or datetime.now().strftime('%Y-%m-%d')
    tasks_display = ', '.join(_format_task_name(task) for task in metadata['tasks'])
    task_catalog_section = ''
    task_table = metadata.get('task_table')
    if task_table:
        task_catalog_section = f"#### Task Catalog\n\n{task_table}\n\n"

    status_label = metadata.get('quality_display') or metadata.get('validation_status') or 'Validation pending'
    pass_rate = metadata.get('validation_pass_rate')
    pass_display = f"{float(pass_rate):.1f}%" if pass_rate is not None else '—'

    validation_link = f"./{validation_doc_filename}"

    doc_content = f"""---
title: {metadata['display_name']}
short_code: {metadata['short_code']}
date_added: {date_added}
---

# {metadata['display_name']}

## Overview

**Short Code**: {metadata['short_code']}  
**Year**: {metadata['year']}  
**Institution**: {metadata['institution']}  

{metadata['description']}

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: {metadata['subjects']}
- **Tasks Included**: {tasks_display}

{task_catalog_section}### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: {status_label}
- **Stride Pass Rate**: {pass_display}
- **Validation Ranges**: {metadata.get('validation_ranges_file', '—')}
- **Detailed Report**: [View validation report]({validation_link})

## Data Access

### Download
{metadata.get('download_url', 'Contact the authors for data access.')}

### Citation
{metadata.get('citation', 'Please cite appropriately when using this dataset.')}

## Collection Details

### Protocol
{metadata.get('protocol', 'Standard motion capture protocol was used.')}

### Processing Notes
{metadata.get('notes', 'No additional notes.')}

## Files Included

- `{dataset_rel}` — Phase-normalized dataset
- [Validation report]({validation_link})
- [Validation plots](./validation_plots/{metadata['dataset_name']}/index.md)
- Conversion script in `contributor_tools/conversion_scripts/{metadata['dataset_name']}/`

---

*Generated by Dataset Submission Tool on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    doc_dir = repo_root / "docs" / "datasets"
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_path = doc_dir / f"{metadata['dataset_name']}.md"
    doc_path.write_text(doc_content)
    return doc_path


def generate_validation_page(
    dataset_path: Path,
    metadata: Dict,
    validation_summary: str,
    validation_stats: Optional[Dict],
    validation_ranges: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
    validation_doc_path: Path,
) -> Path:
    """Generate the per-dataset validation markdown page."""

    ranges_payload = {}
    for task in sorted(validation_ranges.keys()):
        phase_payload = {}
        for phase in sorted(validation_ranges[task].keys()):
            phase_payload[int(phase)] = validation_ranges[task][phase]
        if phase_payload:
            ranges_payload[task] = phase_payload

    if ranges_payload:
        ranges_yaml = yaml.safe_dump({'tasks': ranges_payload}, sort_keys=False, width=120)
    else:
        ranges_yaml = 'tasks: {}'

    pass_rate = metadata.get('validation_pass_rate')
    pass_display = f"{float(pass_rate):.1f}%" if pass_rate is not None else '—'
    total_strides = metadata.get('validation_total_strides') or '—'
    passing_strides = metadata.get('validation_passing_strides') or '—'

    stats_lines = [
        "| Metric | Value |",
        "|--------|-------|",
        f"| Stride Pass Rate | {pass_display} |",
        f"| Total Strides | {total_strides} |",
        f"| Passing Strides | {passing_strides} |",
        f"| Ranges File | {metadata.get('validation_ranges_file', '—')} |",
    ]

    validation_doc_path.parent.mkdir(parents=True, exist_ok=True)
    stats_table = "\n".join(stats_lines)
    validation_content = f"""---
title: {metadata['display_name']} Validation Report
short_code: {metadata['short_code']}
generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

# Validation Report — {metadata['display_name']}

## Status Summary

{stats_table}

{validation_summary}

## Validation Ranges

```yaml
{ranges_yaml.strip()}
```

## Validation Plots

<!-- VALIDATION_GALLERY -->

---

*Generated from `{_relative_path(dataset_path)}` on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    validation_doc_path.write_text(validation_content)

    return validation_doc_path



def run_validation(dataset_path: Path, ranges_path: Optional[Path] = None) -> Tuple[Dict, str, Optional[Dict], Dict[str, Dict[int, Dict[str, Dict[str, float]]]]]:
    """
    Run validation on the dataset.
    
    Args:
        dataset_path: Path to the dataset parquet file
        
    Returns:
        Tuple of (validation_result, summary_text, stats_dict, ranges_dict)
    """
    print(f"🔍 Running validation...")
    
    if ranges_path is not None:
        ranges_file = Path(ranges_path)
        if not ranges_file.is_absolute():
            ranges_file = (repo_root / ranges_file).resolve()
    else:
        ranges_file = _resolve_default_ranges_file()

    if not ranges_file.exists():
        print(f"⚠️  Validation ranges file not found: {ranges_file}")
        return {}, "Validation not run (ranges file missing)", None, {}

    ranges_display = _display_path(ranges_file)

    if ranges_path is not None:
        print(f"🔧 Using validation ranges from {ranges_display}")

    try:
        validator = Validator(config_path=ranges_file)
        validation_result = validator.validate(str(dataset_path))

        summary_data = validation_result.get('summary') or {}
        stats_block = validation_result.get('stats') or {}

        if not summary_data and stats_block:
            total = stats_block.get('total_strides', 0)
            failing = stats_block.get('total_failing_strides', 0)
            passed = total - failing
        elif summary_data:
            total = summary_data.get('total_strides', 0)
            passed = summary_data.get('passing_strides', 0)
        else:
            dataset_hint = _relative_path(dataset_path)
            fallback = (
                "⚠️ Validation summary unavailable from automated run.\n"
                f"Run `python contributor_tools/quick_validation_check.py {dataset_hint}` "
                "and paste the results here."
            )
            return validation_result, fallback, None, {}

        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Generate summary text
        status = "✅ PASSED" if pass_rate >= 95 else "⚠️ PARTIAL" if pass_rate >= 80 else "❌ NEEDS REVIEW"
        
        # Compute per-task stride pass rates using validator helper
        locomotion_data = LocomotionData(str(dataset_path), phase_col='phase_ipsi')
        task_stats = {}
        summary_rows = []
        for task in locomotion_data.get_tasks():
            task_data = locomotion_data.df[locomotion_data.df['task'] == task]
            total_cycles = len(task_data) // 150 if len(task_data) else 0
            failing = validator._validate_task_with_failing_features(locomotion_data, task, None)
            failing_strides = len(failing)
            task_pass_rate = 100.0 * (1 - failing_strides / total_cycles) if total_cycles else 0.0
            if task_pass_rate >= 90:
                task_status = "✅"
            elif task_pass_rate >= 70:
                task_status = "⚠️"
            else:
                task_status = "❌"
            task_stats[task] = {
                'pass_rate': task_pass_rate,
                'status': task_status,
                'total_strides': total_cycles,
                'failing_strides': failing_strides,
            }
            summary_rows.append(f"| {_format_task_name(task)} | {task_pass_rate:.1f}% | {task_status} |")

        summary = f"""### Summary

**Status**: {status} ({pass_rate:.1f}% valid)  
**Total Strides**: {total}  
**Passing Strides**: {passed}  

### Task Breakdown

| Task | Pass Rate | Status |
|------|-----------|--------|
""" + "\n".join(summary_rows) + "\n"

        summary += f"\n_Validation ranges file: {ranges_display}_\n"

        if pass_rate < 80:
            summary += "\n⚠️ **Note**: Low pass rates may indicate special populations or non-standard protocols. "
            summary += "Consider documenting these differences or creating custom validation ranges.\n"

        stats = {
            'total_strides': total,
            'passing_strides': passed,
            'pass_rate': pass_rate,
            'status': status,
            'tasks': task_stats,
            'ranges_path': str(ranges_file),
            'ranges_display': ranges_display,
        }

        # Capture validation ranges for tasks present in the dataset
        ranges_snapshot: Dict[str, Dict[int, Dict[str, Dict[str, float]]]] = {}
        for task in locomotion_data.get_tasks():
            task_ranges = validator.config_manager.get_task_data(task)
            if not task_ranges:
                continue
            organized: Dict[int, Dict[str, Dict[str, float]]] = {}
            for phase in sorted(task_ranges.keys()):
                phase_ranges = {}
                for var_name, bounds in task_ranges[phase].items():
                    if not isinstance(bounds, dict):
                        continue
                    phase_ranges[var_name] = {
                        'min': float(bounds.get('min')) if bounds.get('min') is not None else None,
                        'max': float(bounds.get('max')) if bounds.get('max') is not None else None,
                    }
                if phase_ranges:
                    organized[int(phase)] = phase_ranges
            if organized:
                ranges_snapshot[task] = organized

        return validation_result, summary, stats, ranges_snapshot

    except Exception as e:
        print(f"⚠️  Validation failed: {e}")
        return {}, f"⚠️ Validation could not be completed: {str(e)}", None, {}


def generate_submission_checklist(dataset_slug: str, dataset_file: Path, doc_path: Path, validation_doc_path: Path) -> str:
    """
    Generate a checklist for the PR submission.
    
    Args:
        dataset_slug: Slugified dataset identifier
        dataset_file: Path to dataset parquet file
        doc_path: Path to documentation file
        validation_doc_path: Path to validation report file
        
    Returns:
        Formatted checklist string
    """
    dataset_file_rel = _relative_path(dataset_file)
    conversion_hint = f"contributor_tools/conversion_scripts/{dataset_slug}/"
    plots_hint = f"docs/datasets/validation_plots/{dataset_slug}/"

    checklist = f"""
📋 SUBMISSION CHECKLIST
{'='*60}

Your dataset submission is ready! Please include the following in your PR:

REQUIRED FILES:
□ Dataset file: {dataset_file_rel}
□ Documentation: {doc_path.relative_to(repo_root)}
□ Validation report: {validation_doc_path.relative_to(repo_root)}
□ Conversion script: {conversion_hint}

OPTIONAL FILES:
□ Validation plots: {plots_hint}
□ Custom validation ranges (if applicable)
□ README with additional details

PR DESCRIPTION TEMPLATE:
------------------------
## New Dataset: {dataset_slug}

### Summary
[Brief description of the dataset]

### Validation Results
[Copy validation summary from above]

### Files Included
- Dataset parquet file
- Documentation
- Conversion script
- [Any additional files]

### Testing
- [ ] Validation passes with >80% rate
- [ ] Documentation is complete
- [ ] Conversion script is reproducible

### Notes
[Any special considerations or deviations from standard]
------------------------

NEXT STEPS:
1. Create a new branch for your changes
2. Add all files listed above
3. Commit with descriptive message
4. Push and create PR
5. Tag maintainers for review

Need help? Check the contributor guide or ask in discussions!
"""
    return checklist


def handle_add_dataset(args):
    """Handle the add-dataset command."""
    dataset_path = Path(args.dataset)

    # Validate dataset file
    if not dataset_path.exists():
        print(f"❌ Dataset file not found: {dataset_path}")
        return 1

    dataset_path = dataset_path.resolve()

    custom_ranges_path: Optional[Path] = None
    if getattr(args, 'ranges_file', None):
        custom_ranges_path = Path(args.ranges_file)
        if not custom_ranges_path.is_absolute():
            custom_ranges_path = (repo_root / custom_ranges_path).resolve()
    
    if not dataset_path.suffix == '.parquet':
        print(f"❌ Dataset must be a parquet file, got: {dataset_path.suffix}")
        return 1
    
    # Derive a fallback name from the parquet filename
    dataset_filename_stem = dataset_path.stem.replace("_phase", "").replace("_time", "")
    display_name = dataset_filename_stem.replace("_", " ").title()

    print(f"📦 Preparing submission for: {display_name}")
    print(f"{'='*60}")

    metadata_source: Optional[Dict] = None
    if getattr(args, 'metadata_file', None):
        metadata_path = Path(args.metadata_file)
        if not metadata_path.exists():
            print(f"❌ Metadata file not found: {metadata_path}")
            return 1

        try:
            metadata_source = load_metadata_file(metadata_path)
        except ValueError as exc:
            print(f"❌ {exc}")
            return 1

    try:
        locomotion_data = LocomotionData(str(dataset_path), phase_col='phase_ipsi')
    except Exception as exc:
        print(f"❌ Unable to load dataset for task extraction: {exc}")
        return 1

    detected_tasks, task_rows = _extract_task_catalog(locomotion_data)
    task_table = _build_task_table(task_rows)
    subject_count = len(locomotion_data.get_subjects())
    subjects_value = str(subject_count)

    non_interactive = metadata_source is not None

    print(f"\n📝 Dataset Metadata")
    if non_interactive:
        print("(loaded from metadata file)")
    else:
        print(f"{'='*40}")
        print("Please provide information about your dataset:\n")

    # Collect metadata (either from file or interactively)
    date_added = None
    short_code: Optional[str] = None
    dataset_slug: Optional[str] = None
    tasks: List[str] = detected_tasks.copy()
    if non_interactive:
        existing_codes = check_existing_short_codes()
        display_name = metadata_source.get('display_name', display_name)
        short_code = metadata_source.get('short_code')
        if not short_code:
            print("❌ Metadata file must include 'short_code'")
            return 1
        short_code = short_code.upper()

        if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
            print("❌ Short code must be 2 letters + 2 digits (optional trailing letter, e.g., UM21 or UM21F)")
            return 1

        candidate_slug = _slugify_short_code(short_code)
        existing_slug = existing_codes.get(short_code)
        if existing_slug:
            if existing_slug != candidate_slug:
                if getattr(args, 'replace_existing', False):
                    _remove_dataset_for_slug(existing_slug)
                    existing_codes.pop(short_code, None)
                else:
                    print(f"❌ Short code '{short_code}' already used by {existing_slug}. Re-run with --replace-existing to remove it, or choose a different code.")
                    return 1
            else:
                if getattr(args, 'overwrite', False) or getattr(args, 'replace_existing', False):
                    _remove_dataset_for_slug(existing_slug)
                    existing_codes.pop(short_code, None)
                else:
                    print(f"❌ Short code '{short_code}' already exists for dataset '{existing_slug}'. Use --overwrite or --replace-existing to regenerate it.")
                    return 1
        dataset_slug = candidate_slug

        description = metadata_source.get('description', f"Biomechanical dataset from {display_name}")
        year = str(metadata_source.get('year', datetime.now().year))
        institution = metadata_source.get('institution', "[Please add institution name]")
        metadata_subjects = metadata_source.get('subjects')
        if metadata_subjects and str(metadata_subjects).strip() != subjects_value:
            print("ℹ️ Detected subject count differs from metadata file; using dataset-derived count.")
        metadata_tasks = _normalize_tasks(metadata_source.get('tasks'))
        if tasks:
            if metadata_tasks and metadata_tasks != tasks:
                print("ℹ️ Detected dataset tasks differ from metadata file; using dataset-derived list.")
        else:
            tasks = metadata_tasks
        if not tasks:
            tasks = ["[Please list tasks]"]

        download_url = metadata_source.get('download_url')
        citation = metadata_source.get('citation')
        protocol = metadata_source.get('protocol')
        notes = metadata_source.get('notes')
        date_added = metadata_source.get('date_added')
    else:
        try:
            # Short code validation
            existing_codes = check_existing_short_codes()
            default_stub = (display_name[:2].upper() or dataset_filename_stem[:2].upper() or "DS")
            while True:
                suggested_code = f"{default_stub}{str(datetime.now().year)[2:]}"
                short_code_input = input(f"Short code (AA00 or AA00F) [{suggested_code}]: ").strip().upper()
                short_code = short_code_input or suggested_code

                if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
                    print("❌ Short code must be 2 letters + 2 digits (optional trailing letter, e.g., UM21 or UM21F)")
                    continue

                candidate_slug = _slugify_short_code(short_code)
                existing_slug = existing_codes.get(short_code)
                if existing_slug:
                    auto_replace = getattr(args, 'replace_existing', False)
                    allow_same = getattr(args, 'overwrite', False) or auto_replace
                    if existing_slug != candidate_slug:
                        if auto_replace:
                            _remove_dataset_for_slug(existing_slug)
                            existing_codes.pop(short_code, None)
                        else:
                            response = input(f"⚠️ Short code '{short_code}' is already used by dataset '{existing_slug}'. Remove it? [y/N]: ").strip().lower()
                            if response == 'y':
                                _remove_dataset_for_slug(existing_slug)
                                existing_codes.pop(short_code, None)
                            else:
                                print("➡️ Choose a different short code.")
                                continue
                    else:
                        if allow_same:
                            _remove_dataset_for_slug(existing_slug)
                            existing_codes.pop(short_code, None)
                        else:
                            response = input(f"⚠️ Dataset '{existing_slug}' already uses this short code. Regenerate it? [y/N]: ").strip().lower()
                            if response == 'y':
                                _remove_dataset_for_slug(existing_slug)
                                existing_codes.pop(short_code, None)
                            else:
                                continue

                print(f"✅ Short code '{short_code}' accepted")
                dataset_slug = candidate_slug
                break

            # Basic metadata
            display_name = input(f"Display name [{display_name}]: ").strip() or display_name

            # Dataset details
            print("\nDataset Details:")
            description = input("Brief description (1-2 sentences): ").strip()
            if not description:
                description = f"Biomechanical dataset from {display_name}"

            year = input(f"Collection year [{datetime.now().year}]: ").strip()
            year = year or str(datetime.now().year)

            institution = input("Institution/Lab name: ").strip()
            if not institution:
                institution = "[Please add institution name]"

            print(f"\nDetected {subject_count} unique subjects in the dataset.")

            if tasks:
                print("\nDetected tasks from dataset:")
                for task_name in tasks:
                    print(f"  - {task_name}")
                if task_table:
                    print("\nDetected task catalog:")
                    print(task_table)
            else:
                print("\nTasks included (comma-separated):")
                print("  Common: level_walking, incline_walking, stair_ascent, stair_descent")
                tasks_input = input("Tasks: ").strip()
                tasks = [t.strip() for t in tasks_input.split(",")] if tasks_input else ["[Please list tasks]"]

            # Optional information
            print("\nOptional Information (press Enter to skip):")
            download_url = input("Download URL: ").strip()
            citation = input("Citation: ").strip()
            protocol = input("Collection protocol notes: ").strip()
            notes = input("Additional notes: ").strip()

            date_added = datetime.now().strftime('%Y-%m-%d')

        except KeyboardInterrupt:
            print("\n\n🛑 Submission preparation cancelled")
            return 1

    if not short_code:
        print("❌ Short code was not provided")
        return 1

    if not dataset_slug:
        dataset_slug = _slugify_short_code(short_code)

    tasks = [task for task in tasks if task] or ["[Please list tasks]"]

    # Prepare metadata dictionary
    dataset_name = dataset_slug

    doc_path = repo_root / "docs" / "datasets" / f"{dataset_name}.md"
    validation_doc_filename = f"{dataset_name}_validation.md"

    if doc_path.exists():
        if args.overwrite:
            print(f"⚠️  Documentation already exists: {doc_path} (will overwrite)")
            _remove_dataset_for_slug(dataset_slug)
        else:
            if metadata_source:
                print("❌ Documentation already exists. Re-run with --overwrite to replace it.")
                return 1
            print(f"⚠️  Documentation already exists: {doc_path}")
            overwrite = input("Overwrite? [y/N]: ").strip().lower()
            if overwrite != 'y':
                print("🛑 Cancelled")
                return 0
            _remove_dataset_for_slug(dataset_slug)

    metadata = {
        'dataset_name': dataset_name,
        'display_name': display_name,
        'short_code': short_code,
        'description': description,
        'year': year,
        'institution': institution,
        'subjects': subjects_value,
        'tasks': tasks,
        'download_url': download_url if download_url else None,
        'citation': citation if citation else None,
        'protocol': protocol if protocol else None,
        'notes': notes if notes else None,
        'date_added': date_added or datetime.now().strftime('%Y-%m-%d'),
        'task_table': task_table,
    }
    
    # Run validation
    print(f"\n🔍 Validating dataset...")
    _, validation_summary, validation_stats, validation_ranges = run_validation(dataset_path, custom_ranges_path)
    metadata['validation_summary'] = validation_summary
    metadata['doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_name}/"
    metadata['doc_path'] = f"docs/datasets/{dataset_name}.md"
    metadata['validation_doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_name}_validation/"
    metadata['validation_doc_path'] = f"docs/datasets/{validation_doc_filename}"

    ranges_display = _display_path(custom_ranges_path) if custom_ranges_path else _display_path(_resolve_default_ranges_file())
    plot_ranges_path: Optional[Path] = custom_ranges_path

    if validation_stats:
        metadata['validation_status'] = validation_stats.get('status')
        metadata['validation_pass_rate'] = validation_stats.get('pass_rate')
        metadata['validation_total_strides'] = validation_stats.get('total_strides')
        metadata['validation_passing_strides'] = validation_stats.get('passing_strides')
        if validation_stats.get('ranges_display'):
            ranges_display = validation_stats['ranges_display']
        ranges_path_str = validation_stats.get('ranges_path')
        if ranges_path_str:
            resolved = Path(ranges_path_str)
            if not resolved.is_absolute():
                resolved = (repo_root / resolved).resolve()
            plot_ranges_path = resolved
        status_text = validation_stats.get('status', '')
        pass_rate = validation_stats.get('pass_rate') or 0
        if 'PASSED' in status_text:
            metadata['quality_display'] = '✅ Validated'
        elif 'PARTIAL' in status_text:
            metadata['quality_display'] = f"⚠️ Partial ({pass_rate:.1f}%)"
        elif 'NEEDS REVIEW' in status_text:
            metadata['quality_display'] = f"❌ Needs Review ({pass_rate:.1f}%)"
        else:
            metadata['quality_display'] = status_text or '—'
    else:
        metadata['validation_status'] = 'UNKNOWN'
        metadata['validation_pass_rate'] = None
        metadata['validation_total_strides'] = None
        metadata['validation_passing_strides'] = None
        metadata['quality_display'] = '⚠️ Validation Pending'
    metadata['validation_ranges_file'] = ranges_display

    if plot_ranges_path is None:
        plot_ranges_path = _resolve_default_ranges_file()

    # Show validation results
    print(f"\n📊 Validation Results:")
    print(validation_summary)
    
    # Generate documentation
    print(f"\n📄 Generating documentation...")
    validation_doc_path = (repo_root / "docs" / "datasets" / validation_doc_filename)
    doc_path = generate_dataset_page(dataset_path, metadata, validation_doc_filename)
    validation_doc_path = generate_validation_page(
        dataset_path,
        metadata,
        validation_summary,
        validation_stats,
        validation_ranges,
        validation_doc_path,
    )
    print(f"✅ Overview created: {doc_path.relative_to(repo_root)}")
    print(f"✅ Validation report created: {validation_doc_path.relative_to(repo_root)}")
    
    # Generate plots directory structure
    plots_dir = repo_root / "docs" / "datasets" / "validation_plots" / dataset_name
    plots_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Plot directory created: {plots_dir.relative_to(repo_root)}/")

    plots_index = plots_dir / "index.md"
    if not plots_index.exists():
        plots_rel = _relative_path(plots_dir)
        dataset_hint = _relative_path(dataset_path)
        plots_index.write_text(
            "---\n"
            f"title: {metadata['display_name']} Validation Plots\n"
            "---\n\n"
            f"# Validation Plots — {metadata['display_name']}\n\n"
            "Generate visual validation outputs with:\n\n"
            "```bash\n"
            "python contributor_tools/quick_validation_check.py "
            f"{dataset_hint} --plot --output-dir {plots_rel}\n"
            "```\n\n"
            "When plots are saved in this folder they will be embedded below automatically.\n"
        )

    # Generate fresh validation plots for the dataset
    try:
        plot_ranges_for_cmd = None
        if plot_ranges_path and Path(plot_ranges_path).exists():
            plot_ranges_for_cmd = Path(plot_ranges_path)
        _generate_validation_plots(dataset_path, plots_dir, plot_ranges_for_cmd)
    except subprocess.CalledProcessError as exc:
        print(f"⚠️  Plot generation failed: {exc}")

    update_validation_gallery(validation_doc_path, dataset_name)

    # Persist metadata and refresh global tables
    write_metadata_file(metadata)
    update_dataset_tables()

    
    # Show submission checklist
    checklist = generate_submission_checklist(dataset_name, dataset_path, doc_path, validation_doc_path)
    print(checklist)
    
    # Save checklist to file
    checklist_path = repo_root / f"submission_checklist_{dataset_name}.txt"
    with open(checklist_path, 'w') as f:
        f.write(checklist)
    print(f"💾 Checklist saved to: {checklist_path.name}")
    
    print(f"\n🎉 SUCCESS! Your dataset submission is prepared!")
    print(f"   Follow the checklist above to complete your PR")
    
    return 0


def handle_reset_dataset_list(args):
    """Remove generated documentation so a dataset can be rebuilt."""

    dataset_slug = args.dataset
    expected_phrase = f"reset dataset {dataset_slug}"
    provided_phrase = (args.confirm_phrase or "").strip().lower()

    if provided_phrase != expected_phrase:
        print("🛑 Destructive command requires explicit confirmation.")
        print(f"Re-run with --confirm-phrase '{expected_phrase}' to proceed.")
        return 1

    removed_paths = reset_dataset_assets(dataset_slug, include_parquet=args.remove_parquet)

    if removed_paths:
        print("🧨 Removed generated assets:")
        for path in removed_paths:
            print(f"  - {path}")
    else:
        print(f"ℹ️ No generated assets found for '{dataset_slug}'.")

    if args.remove_parquet:
        print("⚠️ Converted parquet files were deleted. Re-run your conversion script before `add-dataset`.")

    print("Done. Re-run `add-dataset` to regenerate documentation and metadata.")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage dataset documentation with validation and reset workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool helps contributors prepare complete dataset submissions.

Example workflow:
  1. Convert your data to phase-normalized parquet format
  2. Run quick validation to check data quality
  3. Use this tool to add the dataset package:
     
     python contributor_tools/manage_dataset_documentation.py add-dataset \\
         --dataset converted_datasets/your_dataset_phase.parquet
  
  4. Follow the generated checklist to complete your PR
  
  Need to rebuild generated docs? Run:
      python contributor_tools/manage_dataset_documentation.py reset-dataset-list \\
          your_dataset_slug --confirm-phrase "reset dataset your_dataset_slug"
  
  The tool will:
  - Collect metadata interactively or via --metadata-file
  - Run validation and show results  
  - Generate standardized documentation
  - Create submission checklist
  - Prepare everything for PR submission
        """
    )
    
    # Create subcommand
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add-dataset command (primary contributor workflow)
    add_parser = subparsers.add_parser(
        'add-dataset',
        help='Add or refresh documentation and submission assets for a dataset'
    )
    add_parser.add_argument(
        '--dataset',
        required=True,
        help='Path to phase-normalized dataset parquet file'
    )
    add_parser.add_argument(
        '--metadata-file',
        help='Optional YAML/JSON metadata file to run non-interactively'
    )
    add_parser.add_argument(
        '--ranges-file',
        help='Optional validation ranges YAML to override defaults'
    )
    add_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing documentation without prompting'
    )
    add_parser.add_argument(
        '--replace-existing',
        action='store_true',
        help='Remove any existing dataset that uses the selected short code'
    )

    reset_parser = subparsers.add_parser(
        'reset-dataset-list',
        help='Delete generated docs/metadata/plots so a dataset can be rebuilt'
    )
    reset_parser.add_argument(
        'dataset',
        help='Dataset slug to reset (e.g., umich_2021_filtered)'
    )
    reset_parser.add_argument(
        '--confirm-phrase',
        help="Type 'reset dataset <slug>' to confirm this destructive action"
    )
    reset_parser.add_argument(
        '--remove-parquet',
        action='store_true',
        help='Also delete converted_datasets/*.parquet files for the slug'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    print(f"🚀 Manage Dataset Documentation Tool")
    print(f"{'='*60}")
    
    if args.command == 'add-dataset':
        return handle_add_dataset(args)
    if args.command == 'reset-dataset-list':
        return handle_reset_dataset_list(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Submission preparation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
