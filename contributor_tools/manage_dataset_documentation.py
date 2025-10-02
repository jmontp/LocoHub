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
        [--short-code UM21]
    python contributor_tools/manage_dataset_documentation.py update-documentation \
        --short-code UM21 [--dataset converted_datasets/your_dataset_phase.parquet] \
        [--metadata-file docs/datasets/_metadata/your_dataset.yaml]
    python contributor_tools/manage_dataset_documentation.py update-validation \
        --short-code UM21 [--dataset converted_datasets/your_dataset_phase.parquet] \
        [--ranges-file contributor_tools/validation_ranges/custom.yaml]
    python contributor_tools/manage_dataset_documentation.py remove-dataset \
        --short-code UM21 [--remove-parquet]

The tool will:
1. Collect dataset metadata (interactively or from --metadata-file)
2. Run validation and generate reports when requested
3. Create or refresh standardized documentation
4. Snapshot validation ranges for reproducibility
5. Package everything for PR submission
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
from typing import Dict, Optional, Tuple, List, Any
import os
import math
from collections import OrderedDict, defaultdict
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

VALIDATION_RANGES_DIR = repo_root / "contributor_tools" / "validation_ranges"
DEFAULT_RANGES_CANDIDATES = [
    VALIDATION_RANGES_DIR / "default_ranges_v3.yaml",
    VALIDATION_RANGES_DIR / "default_ranges.yaml",
]

DOCS_DATASETS_DIR = repo_root / "docs" / "datasets"
DOCS_DATASETS_GENERATED_DIR = DOCS_DATASETS_DIR / ".generated"


FEATURE_AVAILABILITY_STYLE = """
<style>
.feature-chip {display:inline-flex;align-items:center;justify-content:center;min-width:1.6rem;padding:0.1rem 0.55rem;border-radius:999px;font-weight:600;font-size:0.85rem;line-height:1;color:#ffffff;}
.feature-chip.feature-complete {background:#16a34a;}
.feature-chip.feature-partial {background:#facc15;color:#1f2937;}
.feature-chip.feature-missing {background:#ef4444;}
.feature-legend {margin-bottom:0.5rem;display:flex;gap:0.75rem;flex-wrap:wrap;}
.feature-legend .legend-item {display:flex;align-items:center;gap:0.35rem;font-size:0.9rem;}
.feature-source {font-size:0.85rem;color:#4b5563;margin:0.25rem 0 0.75rem 0;}
</style>
"""

FEATURE_STATUS_ICONS = {
    'complete': '✔',
    'partial': '≈',
    'missing': '✖',
}


def _render_feature_chip(status: str, coverage_pct: float) -> str:
    icon = FEATURE_STATUS_ICONS.get(status, '–')
    try:
        pct_value = float(coverage_pct)
    except (TypeError, ValueError):
        pct_value = 0.0
    title = f"{pct_value:.1f}% available"
    pct_display = f"{pct_value:05.2f}" if status == 'partial' else ''
    label = f"{icon} {pct_display.strip()}" if pct_display else icon
    return f'<span class="feature-chip feature-{status}" title="{title}">{label}</span>'


def _resolve_default_ranges_file() -> Path:
    for candidate in DEFAULT_RANGES_CANDIDATES:
        if candidate.exists():
            return candidate
    # Return first candidate even if missing to preserve prior behaviour
    return DEFAULT_RANGES_CANDIDATES[0]


def _resolve_ranges_argument(value: str) -> Path:
    """Resolve a user-supplied ranges argument to an absolute path."""

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate

    search_roots = [
        repo_root,
        VALIDATION_RANGES_DIR,
        Path.cwd(),
    ]

    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved

    # Fall back to treating it as relative to repo root (for error message consistency)
    return (repo_root / candidate).resolve()


def _infer_clean_dataset_path(dataset_path: Path) -> Tuple[Path, bool]:
    """Return the path to the clean dataset, falling back to the original."""

    stem = dataset_path.stem
    suffix = dataset_path.suffix

    # Already clean
    if stem.endswith('_clean'):
        return dataset_path, True

    candidates: List[Path] = []
    if stem.endswith('_dirty'):
        candidates.append(dataset_path.with_name(stem[:-6] + '_clean' + suffix))
    if stem.endswith('_raw'):
        candidates.append(dataset_path.with_name(stem[:-4] + '_clean' + suffix))

    candidates.append(dataset_path.with_name(stem + '_clean' + suffix))

    for candidate in candidates:
        if candidate.exists():
            return candidate, True

    return dataset_path, False


def _feature_group_for(feature_name: str) -> str:
    """Group feature names into broad categories for documentation tables."""

    lower = feature_name.lower()
    if 'grf' in lower:
        return 'Ground Reaction Forces'
    if 'power' in lower:
        return 'Joint Powers'
    if 'moment' in lower:
        return 'Joint Moments'
    if 'velocity' in lower:
        return 'Joint Velocities'
    if 'angle' in lower:
        return 'Joint Angles'
    return 'Other Features'


def _coverage_status(value: float) -> str:
    if value >= 0.99:
        return 'complete'
    if value <= 0.001:
        return 'missing'
    return 'partial'


def _compute_feature_task_groups(
    dataset_path: Path,
    tasks: List[str],
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[str]], Optional[Path]]:
    """Compute feature coverage per task using the clean dataset when available."""

    coverage_path, using_clean = _infer_clean_dataset_path(dataset_path)

    try:
        coverage_data = LocomotionData(str(coverage_path), phase_col='phase_ipsi')
    except Exception as exc:
        print(f"⚠️  Unable to compute feature availability ({exc})")
        return None, None, None

    feature_columns = coverage_data.features or []
    if not feature_columns:
        return None, None, None

    df = coverage_data.df
    if 'task' not in df.columns:
        return None, None, None

    # Restrict to columns that actually exist in the DataFrame
    feature_columns = [col for col in feature_columns if col in df.columns]
    if not feature_columns:
        return None, None, None

    grouped = df.groupby('task')
    try:
        coverage = grouped[feature_columns].agg(lambda col: float(col.notna().mean()))
    except Exception as exc:
        print(f"⚠️  Unable to compute feature availability ({exc})")
        return None, None, None

    ordered_tasks: List[str] = []
    seen = set()
    for candidate in list(tasks) + list(coverage.index.astype(str)):
        if candidate not in seen:
            ordered_tasks.append(candidate)
            seen.add(candidate)

    grouped_features: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for feature in feature_columns:
        group_name = _feature_group_for(feature)
        task_entries: Dict[str, Any] = {}
        for task_name in ordered_tasks:
            value = 0.0
            if task_name in coverage.index and feature in coverage.columns:
                value = float(coverage.loc[task_name, feature])
                if math.isnan(value):
                    value = 0.0
            status = _coverage_status(value)
            task_entries[task_name] = {
                'status': status,
                'coverage': round(value * 100, 1),
            }
        grouped_features[group_name].append({
            'name': feature,
            'tasks': task_entries,
        })

    groups_output: List[Dict[str, Any]] = []
    for group_name in sorted(grouped_features.keys()):
        features_output = sorted(grouped_features[group_name], key=lambda item: item['name'])
        groups_output.append({
            'group': group_name,
            'features': features_output,
        })

    relative_path = coverage_path
    return groups_output, ordered_tasks, relative_path if using_clean else dataset_path
def _load_locomotion_data(dataset_path: Path, reason: str) -> LocomotionData:
    """Load dataset with a helpful progress message."""

    dataset_display = _relative_path(dataset_path)
    print(f"⏳ Loading {dataset_display} ({reason})...")
    return LocomotionData(str(dataset_path), phase_col='phase_ipsi')


def _metadata_path_for_slug(slug: str) -> Path:
    return repo_root / "docs" / "datasets" / "_metadata" / f"{slug}.yaml"


def _load_metadata_for_slug(slug: str) -> Dict:
    metadata_path = _metadata_path_for_slug(slug)
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found for slug '{slug}'. Run add-dataset first."
        )
    metadata = load_metadata_file(metadata_path)
    metadata['dataset_name'] = slug
    metadata['short_code'] = metadata.get('short_code', slug).upper()
    return metadata


def _resolve_dataset_path(dataset_arg: Optional[str], metadata: Optional[Dict] = None) -> Path:
    if dataset_arg:
        candidate = Path(dataset_arg)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
    elif metadata and metadata.get('last_dataset_path'):
        candidate = (repo_root / metadata['last_dataset_path']).resolve()
    else:
        raise ValueError("Dataset path is required; pass --dataset or add last_dataset_path to metadata.")

    if not candidate.exists():
        raise FileNotFoundError(f"Dataset file not found: {candidate}")

    return candidate


def _prompt_metadata_updates(metadata: Dict) -> None:
    """Interactively prompt to update key metadata fields."""

    if metadata.get('download_clean_url') is None and metadata.get('download_url'):
        metadata['download_clean_url'] = metadata.get('download_url')
    metadata.setdefault('download_clean_url', '')
    metadata.setdefault('download_dirty_url', '')

    print("\n✏️ Update dataset details (press Enter to keep current values):")
    prompts = [
        ('display_name', 'Display name'),
        ('description', 'Dataset description'),
        ('institution', 'Institution or Lab'),
        ('year', 'Collection year'),
        ('download_clean_url', 'Clean dataset download URL (validated subset)'),
        ('download_dirty_url', 'Full dataset download URL (complete/dirty set)'),
        ('citation', 'Citation (DOI, BibTeX, or short reference)'),
        ('protocol', 'Collection protocol notes'),
        ('notes', 'Additional notes'),
    ]

    for key, label in prompts:
        current = metadata.get(key) or ''
        prompt = f"{label} [{current}]: " if current else f"{label}: "
        response = input(prompt).strip()
        if response:
            metadata[key] = response if key != 'year' else str(response)

    if not metadata.get('description'):
        metadata['description'] = 'Dataset description pending update.'


def _normalize_docs_link(path_value: Optional[str], slug: str, fallback_suffix: str) -> str:
    if not path_value:
        return f"./{slug}{fallback_suffix}"
    value = str(path_value)
    prefix = "docs/datasets/"
    if value.startswith(prefix):
        return "./" + value[len(prefix):]
    return value


def generate_comparison_snapshot() -> None:
    """Create a JSON snapshot for the comparison tool."""

    meta_dir = repo_root / "docs" / "datasets" / "_metadata"
    if not meta_dir.exists():
        return

    datasets_payload: List[Dict] = []

    for meta_file in sorted(meta_dir.glob('*.yaml')):
        data = load_metadata_file(meta_file)
        slug = meta_file.stem

        comparison_tasks = data.get('comparison_tasks') or {}
        if isinstance(comparison_tasks, list):
            comparison_tasks = {entry.get('task'): entry for entry in comparison_tasks if isinstance(entry, dict) and entry.get('task')}

        plots_dir = repo_root / "docs" / "datasets" / "validation_plots" / slug

        task_entries: List[Dict] = []
        for task_name, task_info in sorted(comparison_tasks.items()):
            if not task_name:
                continue
            plots: List[str] = []
            if plots_dir.exists():
                for img_path in sorted(plots_dir.glob(f"*{task_name}*.png")):
                    rel_path = Path('validation_plots') / slug / img_path.name
                    plots.append(rel_path.as_posix())

            task_entries.append({
                'task': task_name,
                'display_name': _format_task_name(task_name),
                'pass_rate': task_info.get('pass_rate'),
                'status': task_info.get('status'),
                'total_strides': task_info.get('total_strides'),
                'failing_strides': task_info.get('failing_strides'),
                'plots': plots,
            })

        dataset_entry = {
            'slug': slug,
            'display_name': data.get('display_name', slug),
            'short_code': data.get('short_code', slug.upper()),
            'quality': data.get('quality_display') or data.get('validation_status') or '—',
            'dataset_doc': _normalize_docs_link(data.get('doc_path'), slug, '.md'),
            'validation_report': _normalize_docs_link(data.get('validation_doc_path'), slug, '_validation.md'),
            'clean_url': data.get('download_clean_url') or data.get('download_url'),
            'dirty_url': data.get('download_dirty_url'),
            'tasks': task_entries,
        }

        datasets_payload.append(dataset_entry)

    snapshot_path = repo_root / "docs" / "datasets" / "comparison_data.json"
    snapshot_path.write_text(json.dumps({'datasets': datasets_payload}, indent=2))

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
    if metadata.get('download_clean_url'):
        fields['download_clean_url'] = metadata['download_clean_url']
    if metadata.get('download_dirty_url'):
        fields['download_dirty_url'] = metadata['download_dirty_url']
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
    if metadata.get('doc_body_path'):
        fields['doc_body_path'] = metadata.get('doc_body_path')
    if metadata.get('validation_doc_url'):
        fields['validation_doc_url'] = metadata.get('validation_doc_url')
    if metadata.get('validation_doc_path'):
        fields['validation_doc_path'] = metadata.get('validation_doc_path')
    if metadata.get('validation_body_path'):
        fields['validation_body_path'] = metadata.get('validation_body_path')
    fields['validation_summary'] = metadata.get('validation_summary')
    if metadata.get('validation_ranges_file'):
        fields['validation_ranges_file'] = metadata.get('validation_ranges_file')
    if metadata.get('validation_ranges_download'):
        fields['validation_ranges_download'] = metadata.get('validation_ranges_download')
    if metadata.get('validation_ranges_source'):
        fields['validation_ranges_source'] = metadata.get('validation_ranges_source')
    if metadata.get('comparison_tasks'):
        fields['comparison_tasks'] = metadata.get('comparison_tasks')
    if metadata.get('feature_task_groups'):
        fields['feature_task_groups'] = metadata.get('feature_task_groups')
    if metadata.get('feature_task_order'):
        fields['feature_task_order'] = metadata.get('feature_task_order')
    if metadata.get('feature_task_source'):
        fields['feature_task_source'] = metadata.get('feature_task_source')
    if metadata.get('last_dataset_path'):
        fields['last_dataset_path'] = metadata.get('last_dataset_path')

    with open(meta_path, 'w') as fh:
        yaml.safe_dump(dict(fields), fh, sort_keys=False)


def _relative_link(path_value: Optional[str], table_file: Path) -> Optional[str]:
    if not path_value:
        return None
    anchor = ''
    target_str = str(path_value)
    if '#' in target_str:
        target_str, anchor = target_str.split('#', 1)
        anchor = f"#{anchor}" if anchor else ''

    if not target_str:
        return anchor or None

    target = Path(target_str)
    if not target.is_absolute():
        target = (repo_root / target).resolve()
    if target.suffix != '.md':
        target = target.with_suffix('.md')
    try:
        docs_root = repo_root / "docs"
        target_rel = target.relative_to(docs_root)
    except ValueError:
        # Path outside docs; return as-is (with anchor if present)
        return target.as_posix() + anchor

    table_rel = table_file.relative_to(docs_root)
    rel_path = PurePosixPath(
        os.path.relpath(target_rel.as_posix(), start=table_rel.parent.as_posix())
    )
    return rel_path.as_posix() + anchor


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
    header = "| Dataset | Tasks | Quality | Documentation | Clean Dataset | Full Dataset |"
    separator = "|---------|-------|---------|---------------|---------------|---------------|"

    rows: List[str] = []
    for data in sorted(metadata_entries, key=lambda d: d.get('display_name', '').lower()):
        doc_url = _resolve_dataset_link(data, table_file, absolute_links)
        display_name = data.get('display_name') or data['dataset_name']
        dataset_cell = display_name
        doc_cell = f"[Open]({doc_url})" if doc_url else '—'

        tasks_list = data.get('tasks', []) or []
        tasks_cell = ', '.join(_format_task_name(task) for task in tasks_list) if tasks_list else '—'

        quality_cell = data.get('quality_display') or data.get('validation_status') or '—'

        clean_url = data.get('download_clean_url') or data.get('download_url')
        dirty_url = data.get('download_dirty_url')
        clean_cell = f"[Clean]({clean_url})" if clean_url else 'Coming soon'
        full_cell = f"[Full]({dirty_url})" if dirty_url else 'Coming soon'

        rows.append(
            "| "
            + " | ".join([
                dataset_cell,
                tasks_cell,
                quality_cell,
                doc_cell,
                clean_cell,
                full_cell,
            ])
            + " |"
        )

    if not rows:
        empty_cells = ['_No datasets available_'] + [''] * 5
        return header + "\n" + separator + "\n| " + " | ".join(empty_cells) + " |"

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
    _remove_path(docs_dir / f"{dataset_slug}_validation_ranges.yaml", removed)
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
    result = subprocess.run(cmd, cwd=repo_root)
    if result.returncode != 0:
        print('⚠️  Plot generation completed with non-zero exit code (plots saved for debugging).')


def update_validation_gallery(doc_path: Path, dataset_name: str) -> None:
    plots_dir = repo_root / 'docs' / 'datasets' / 'validation_plots' / dataset_name
    if not plots_dir.exists():
        return
    images = sorted(plots_dir.glob('*.png'))
    if not images:
        return

    tabs_lines = []
    for image_path in images:
        name = image_path.stem
        task_segment = name
        if '_phase_' in name and '_all_features' in name:
            task_segment = name.split('_phase_')[1].split('_all_features')[0]
        task_segment = task_segment.replace('filtered_', '').replace('raw_', '')
        task_title = _format_task_name(task_segment)
        rel_path = Path('validation_plots') / dataset_name / image_path.name
        tabs_lines.append(f"=== \"{task_title}\"")
        tabs_lines.append(f"    ![{task_title}](./{rel_path.as_posix()})")
        tabs_lines.append("")

    gallery = "\n".join(tabs_lines).strip() or "(Generate plots with quick_validation_check.py --plot)"
    content = doc_path.read_text()
    if '<!-- VALIDATION_GALLERY -->' in content:
        content = content.replace('<!-- VALIDATION_GALLERY -->', f"{gallery}\n")
    else:
        content = content + "\n" + gallery + "\n"
    doc_path.write_text(content)


def _snapshot_validation_ranges(
    dataset_name: str,
    validation_doc_dir: Path,
    ranges_source_path: Path,
    ranges_display: str,
    validation_summary: str,
    metadata: Dict,
) -> Tuple[Optional[str], str]:
    validation_doc_dir.mkdir(parents=True, exist_ok=True)
    metadata['validation_ranges_source'] = _display_path(ranges_source_path)

    if not ranges_source_path.exists():
        print(f"⚠️  Validation ranges source not found: {ranges_source_path}")
        metadata.pop('validation_ranges_download', None)
        return None, validation_summary

    suffix = ranges_source_path.suffix or '.yaml'
    snapshot_path = validation_doc_dir / f"{dataset_name}_validation_ranges{suffix}"
    try:
        shutil.copyfile(ranges_source_path, snapshot_path)
    except Exception as exc:
        print(f"⚠️  Unable to snapshot validation ranges: {exc}")
        metadata.pop('validation_ranges_download', None)
        return None, validation_summary

    download_filename = snapshot_path.name
    metadata['validation_ranges_download'] = str(snapshot_path.relative_to(repo_root))
    download_md = f"[Download validation ranges](./{download_filename})"
    metadata['validation_ranges_file'] = download_md

    if ranges_display and ranges_display in validation_summary:
        validation_summary = validation_summary.replace(ranges_display, download_md)

    return download_filename, validation_summary


def generate_dataset_page(dataset_path: Path, metadata: Dict, validation_doc_filename: str) -> Tuple[Path, Path]:
    """Generate the dataset overview wrapper and documentation body."""

    dataset_slug = metadata['dataset_name']
    dataset_rel = _relative_path(dataset_path)
    date_added = metadata.get('date_added') or datetime.now().strftime('%Y-%m-%d')
    generated_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    tasks_display = ', '.join(_format_task_name(task) for task in metadata['tasks'])

    task_catalog_section = ''
    task_table = metadata.get('task_table')
    if task_table:
        task_catalog_section = f"#### Task Catalog\n\n{task_table}\n"

    status_label = metadata.get('quality_display') or metadata.get('validation_status') or 'Validation pending'
    pass_rate = metadata.get('validation_pass_rate')
    pass_display = f"{float(pass_rate):.1f}%" if pass_rate is not None else '—'

    validation_link = "#validation"
    ranges_entry = metadata.get('validation_ranges_file', '—')
    ranges_source = metadata.get('validation_ranges_source')
    if ranges_source and ranges_entry != '—':
        ranges_entry = f"{ranges_entry} (source: {ranges_source})"

    clean_url = (metadata.get('download_clean_url') or metadata.get('download_url') or '').strip()
    dirty_url = (metadata.get('download_dirty_url') or '').strip()

    description_text = metadata.get('description') or 'Dataset description pending update.'

    download_buttons: List[str] = []
    if clean_url:
        download_buttons.append(
            f'<a class="download-button available" href="{clean_url}" target="_blank" rel="noopener">Download Clean Dataset</a>'
        )
    else:
        download_buttons.append(
            '<span class="download-button unavailable" title="Clean dataset download not yet available">Clean Dataset (coming soon)</span>'
        )
    if dirty_url:
        download_buttons.append(
            f'<a class="download-button available" href="{dirty_url}" target="_blank" rel="noopener">Download Full Dataset (Dirty)</a>'
        )
    else:
        download_buttons.append(
            '<span class="download-button unavailable" title="Full dataset download not yet available">Full Dataset (coming soon)</span>'
        )

    buttons_html = "\n  ".join(download_buttons)
    download_note = ''
    if not clean_url and not dirty_url:
        download_note = '\n*Downloads coming soon. Contact the authors for data access.*'

    download_section = (
        "<style>\n"
        ".download-grid { display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; }\n"
        ".download-button { display:inline-block; padding:0.65rem 1.4rem; border-radius:0.5rem; font-weight:600; text-decoration:none; }\n"
        ".download-button.available { background:#1f78d1; color:#fff; }\n"
        ".download-button.available:hover { background:#1663ad; }\n"
        ".download-button.unavailable { background:#d1d5db; color:#6b7280; cursor:not-allowed; }\n"
        "</style>\n"
        f"<div class=\"download-grid\">\n  {buttons_html}\n</div>"
        f"{download_note}"
    )

    doc_body_lines: List[str] = [
        "## Overview",
        "",
        f"- **Short Code**: {metadata['short_code']}",
        f"- **Year**: {metadata['year']}",
        f"- **Institution**: {metadata['institution']}",
        "",
        description_text,
        "",
        "## Downloads",
        "",
        download_section,
        "",
        "## Dataset Information",
        "",
        "### Subjects and Tasks",
        f"- **Number of Subjects**: {metadata['subjects']}",
        f"- **Tasks Included**: {tasks_display}",
        "",
    ]

    if task_catalog_section:
        doc_body_lines.append(task_catalog_section.rstrip())
        doc_body_lines.append("")

    feature_groups_meta = metadata.get('feature_task_groups') or []
    if feature_groups_meta:
        task_order = metadata.get('feature_task_order') or metadata.get('tasks', [])
        if not task_order:
            gathered_tasks: List[str] = []
            for group_entry in feature_groups_meta:
                for feature_entry in group_entry.get('features', []):
                    gathered_tasks.extend(feature_entry.get('tasks', {}).keys())
            seen_tasks: set = set()
            task_order = []
            for task_name in gathered_tasks:
                if task_name not in seen_tasks:
                    task_order.append(task_name)
                    seen_tasks.add(task_name)

        formatted_tasks = [(task, _format_task_name(task)) for task in task_order]

        doc_body_lines.extend([
            "### Feature Availability by Task",
            FEATURE_AVAILABILITY_STYLE.strip(),
            "",
            '<div class="feature-legend">'
            '<span class="legend-item"><span class="feature-chip feature-complete">✔</span>Complete</span>'
            '<span class="legend-item"><span class="feature-chip feature-partial">≈</span>Partial</span>'
            '<span class="legend-item"><span class="feature-chip feature-missing">✖</span>Missing</span>'
            '</div>',
        ])

        source_dataset = metadata.get('feature_task_source') or _relative_path(dataset_path)
        doc_body_lines.append(f'<p class="feature-source">Coverage computed from `{source_dataset}`.</p>')
        doc_body_lines.append("")

        for group_entry in feature_groups_meta:
            group_name = group_entry.get('group', 'Features')
            doc_body_lines.append(f"#### {group_name}")
            doc_body_lines.append("")

            header_cells = ["Feature"] + [display for _, display in formatted_tasks]
            header_line = "| " + " | ".join(header_cells) + " |"
            separator_line = "|" + "---|" * len(header_cells)
            doc_body_lines.append(header_line)
            doc_body_lines.append(separator_line)

            for feature_entry in group_entry.get('features', []):
                feature_name = feature_entry.get('name', '')
                task_statuses = feature_entry.get('tasks', {})
                row_cells = [f"`{feature_name}`"]
                for task_key, _ in formatted_tasks:
                    status_entry = task_statuses.get(task_key, {})
                    status = status_entry.get('status', 'missing')
                    coverage_pct = status_entry.get('coverage', 0.0)
                    row_cells.append(_render_feature_chip(status, coverage_pct))
                doc_body_lines.append("| " + " | ".join(row_cells) + " |")

            doc_body_lines.append("")

    doc_body_lines.extend([
        "### Data Structure",
        "- **Format**: Phase-normalized (150 points per gait cycle)",
        "- **Sampling**: Phase-indexed from 0-100%",
        "- **Variables**: Standard biomechanical naming convention",
        "",
        "## Validation Snapshot",
        "",
        f"- **Status**: {status_label}",
        f"- **Stride Pass Rate**: {pass_display}",
        f"- **Validation Ranges**: {ranges_entry}",
        f"- **Detailed Report**: [View validation report]({validation_link})",
        "",
        "## Citation",
        metadata.get('citation', 'Please cite appropriately when using this dataset.'),
        "",
        "## Collection Details",
        "",
        "### Protocol",
        metadata.get('protocol', 'Standard motion capture protocol was used.'),
        "",
        "### Processing Notes",
        metadata.get('notes', 'No additional notes.'),
        "",
        "## Files Included",
        "",
        f"- `{dataset_rel}` — Phase-normalized dataset",
        f"- [Validation report]({validation_link})",
        f"- Conversion script in `contributor_tools/conversion_scripts/{dataset_slug}/`",
        "",
        "---",
        "",
        f"*Generated by Dataset Submission Tool on {generated_timestamp}*",
    ])

    doc_body_content = "\n".join(line for line in doc_body_lines if line is not None) + "\n"

    DOCS_DATASETS_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    doc_body_path = DOCS_DATASETS_GENERATED_DIR / f"{dataset_slug}_documentation.md"
    doc_body_path.write_text(doc_body_content)

    doc_snippet_target = (PurePosixPath('datasets') / doc_body_path.relative_to(DOCS_DATASETS_DIR)).as_posix()
    validation_snippet_target = (PurePosixPath('datasets') / Path(validation_doc_filename)).as_posix()

    wrapper_content = (
        f"---\n"
        f"title: {metadata['display_name']}\n"
        f"short_code: {metadata['short_code']}\n"
        f"date_added: {date_added}\n"
        f"---\n\n"
        f"# {metadata['display_name']}\n\n"
        "=== \"Documentation\"\n\n"
        f"    --8<-- \"{doc_snippet_target}\"\n\n"
        "=== \"Validation\"\n\n"
        f"    --8<-- \"{validation_snippet_target}\"\n"
    )

    DOCS_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    wrapper_path = DOCS_DATASETS_DIR / f"{dataset_slug}.md"
    wrapper_path.write_text(wrapper_content)

    metadata['doc_body_path'] = str(doc_body_path.relative_to(repo_root))

    return wrapper_path, doc_body_path



def generate_validation_page(
    dataset_path: Path,
    metadata: Dict,
    validation_summary: str,
    validation_stats: Optional[Dict],
    validation_ranges: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
    validation_doc_path: Path,
    ranges_download_filename: Optional[str] = None,
    ranges_source_display: Optional[str] = None,
) -> Path:
    """Generate the per-dataset validation markdown body for tabbed layout."""

    generated_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    pass_rate = metadata.get('validation_pass_rate')
    pass_display = f"{float(pass_rate):.1f}%" if pass_rate is not None else '—'
    total_strides = (
        metadata.get('validation_total_strides')
        or metadata.get('total_strides')
        or '—'
    )
    passing_strides = (
        metadata.get('validation_passing_strides')
        or metadata.get('passing_strides')
        or '—'
    )

    stats_lines = [
        "| Metric | Value |",
        "|--------|-------|",
        f"| Stride Pass Rate | {pass_display} |",
        f"| Total Strides | {total_strides} |",
        f"| Passing Strides | {passing_strides} |",
    ]
    stats_table = "\n".join(stats_lines)

    if ranges_download_filename:
        ranges_section = (
            "Download the YAML snapshot used for this validation: "
            f"[Download](./{ranges_download_filename})"
        )
    else:
        ranges_section = "Validation ranges snapshot not available."

    if ranges_source_display:
        ranges_section += f"\n\n_Source ranges file: {ranges_source_display}_"

    validation_doc_path.parent.mkdir(parents=True, exist_ok=True)

    body_lines = [
        f"**Report generated:** {generated_timestamp}",
        "",
        "## Status Summary",
        "",
        stats_table,
        "",
        validation_summary.strip(),
        "",
        "## Validation Ranges Snapshot",
        "",
        ranges_section,
        "",
        "## Validation Plots",
        "",
        "<!-- VALIDATION_GALLERY -->",
        "",
        "---",
        "",
        f"*Generated from `{_relative_path(dataset_path)}` on {generated_timestamp}*",
    ]

    validation_content = "\n".join(body_lines) + "\n"
    validation_doc_path.write_text(validation_content)

    metadata['validation_body_path'] = str(validation_doc_path.relative_to(repo_root))

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
        locomotion_data = _load_locomotion_data(dataset_path, "gathering per-task validation stats")
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

        summary += "\n_Validation ranges snapshot embedded below._\n"

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


def generate_submission_checklist(
    dataset_slug: str,
    dataset_file: Path,
    doc_wrapper_path: Path,
    doc_body_path: Path,
    validation_doc_path: Path,
) -> str:
    """Generate a checklist for the PR submission.

    Args:
        dataset_slug: Slugified dataset identifier
        dataset_file: Path to dataset parquet file
        doc_wrapper_path: Path to the tabbed documentation wrapper
        doc_body_path: Path to the documentation body snippet
        validation_doc_path: Path to the validation body snippet

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
□ Documentation wrapper: {doc_wrapper_path.relative_to(repo_root)}
□ Documentation body: {doc_body_path.relative_to(repo_root)}
□ Validation body: {validation_doc_path.relative_to(repo_root)}
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
        custom_ranges_path = _resolve_ranges_argument(args.ranges_file)
        if not custom_ranges_path.exists():
            print(f"❌ Validation ranges file not found: {custom_ranges_path}")
            return 1
    
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
        locomotion_data = _load_locomotion_data(dataset_path, "extracting tasks and subjects")
    except Exception as exc:
        print(f"❌ Unable to load dataset for task extraction: {exc}")
        return 1

    detected_tasks, task_rows = _extract_task_catalog(locomotion_data)
    task_table = _build_task_table(task_rows)
    subject_count = len(locomotion_data.get_subjects())
    subjects_value = str(subject_count)

    non_interactive = metadata_source is not None
    preset_short_code = (getattr(args, 'short_code', None) or '').strip().upper() or None

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
    download_clean_url = ''
    download_dirty_url = ''
    download_url = ''
    citation = None
    protocol = None
    notes = None

    if non_interactive:
        existing_codes = check_existing_short_codes()
        display_name = metadata_source.get('display_name', display_name)
        metadata_short_code = metadata_source.get('short_code')
        if metadata_short_code and preset_short_code and metadata_short_code.upper() != preset_short_code:
            print("❌ Metadata file short_code does not match --short-code value")
            return 1
        short_code = (metadata_short_code or preset_short_code)
        if not short_code:
            print("❌ Provide a short code via metadata file or --short-code")
            return 1
        short_code = short_code.upper()

        if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
            print("❌ Short code must be 2 letters + 2 digits (optional trailing letter, e.g., UM21 or UM21F)")
            return 1

        candidate_slug = _slugify_short_code(short_code)
        existing_slug = existing_codes.get(short_code)
        if existing_slug and existing_slug != candidate_slug:
            print(f"❌ Short code '{short_code}' already used by dataset '{existing_slug}'. Run remove-dataset --short-code {short_code} first.")
            return 1
        if existing_slug == candidate_slug:
            print(f"❌ Dataset '{candidate_slug}' already exists. Use update commands or remove it before re-adding.")
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

        download_clean_url = metadata_source.get('download_clean_url') or metadata_source.get('download_url') or ''
        download_dirty_url = metadata_source.get('download_dirty_url') or ''
        download_url = metadata_source.get('download_url') or ''
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
                if preset_short_code:
                    short_code = preset_short_code
                    preset_short_code = None
                    print(f"ℹ️ Using provided short code '{short_code}'")
                else:
                    short_code_input = input(f"Short code (AA00 or AA00F) [{suggested_code}]: ").strip().upper()
                    short_code = short_code_input or suggested_code

                if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
                    print("❌ Short code must be 2 letters + 2 digits (optional trailing letter, e.g., UM21 or UM21F)")
                    continue

                candidate_slug = _slugify_short_code(short_code)
                existing_slug = existing_codes.get(short_code)
                if existing_slug and existing_slug != candidate_slug:
                    print(f"❌ Short code '{short_code}' is already assigned to dataset '{existing_slug}'. Run remove-dataset --short-code {short_code} first or choose another code.")
                    continue
                if existing_slug == candidate_slug:
                    print(f"❌ Dataset '{candidate_slug}' already exists. Use update-documentation/update-validation or remove it before re-adding.")
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
            download_clean_url = input("Clean dataset download URL (validated subset): ").strip()
            download_dirty_url = input("Full dataset download URL (complete/dirty set): ").strip()
            download_url = input("Legacy single download URL (optional fallback): ").strip()
            citation = input("Citation (DOI, BibTeX, or short reference): ").strip()
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

    feature_task_groups: Optional[List[Dict[str, Any]]] = None
    feature_task_order: Optional[List[str]] = None
    feature_task_source: Optional[str] = None

    coverage_groups, coverage_tasks, coverage_source_path = _compute_feature_task_groups(dataset_path, tasks)
    if coverage_groups:
        feature_task_groups = coverage_groups
        if coverage_tasks:
            feature_task_order = coverage_tasks
        if coverage_source_path:
            feature_task_source = _relative_path(coverage_source_path)

    # Prepare metadata dictionary
    dataset_name = dataset_slug

    doc_path = DOCS_DATASETS_DIR / f"{dataset_name}.md"
    validation_doc_filename = f".generated/{dataset_name}_validation.md"

    validation_doc_path = DOCS_DATASETS_DIR / validation_doc_filename
    metadata_path = _metadata_path_for_slug(dataset_slug)
    ranges_snapshot_path = repo_root / "docs" / "datasets" / f"{dataset_name}_validation_ranges.yaml"

    if doc_path.exists() or validation_doc_path.exists() or metadata_path.exists() or ranges_snapshot_path.exists():
        print(
            f"❌ Dataset assets already exist for '{dataset_slug}'. "
            "Use update-documentation/update-validation or run remove-dataset "
            f"--short-code {short_code} before re-adding."
        )
        return 1

    metadata = {
        'dataset_name': dataset_name,
        'display_name': display_name,
        'short_code': short_code,
        'description': description,
        'year': year,
        'institution': institution,
        'subjects': subjects_value,
        'tasks': tasks,
        'download_url': download_clean_url or download_url or None,
        'download_clean_url': download_clean_url if download_clean_url else None,
        'download_dirty_url': download_dirty_url if download_dirty_url else None,
        'citation': citation if citation else None,
        'protocol': protocol if protocol else None,
        'notes': notes if notes else None,
        'date_added': date_added or datetime.now().strftime('%Y-%m-%d'),
        'task_table': task_table,
        'last_dataset_path': _relative_path(dataset_path),
    }

    if feature_task_groups:
        metadata['feature_task_groups'] = feature_task_groups
    if feature_task_order:
        metadata['feature_task_order'] = feature_task_order
    if feature_task_source:
        metadata['feature_task_source'] = feature_task_source
    
    # Run validation
    print(f"\n🔍 Validating dataset...")
    _, validation_summary, validation_stats, validation_ranges = run_validation(dataset_path, custom_ranges_path)
    metadata['validation_summary'] = validation_summary
    metadata['doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_name}/"
    metadata['doc_path'] = f"docs/datasets/{dataset_name}.md"
    metadata['validation_doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_name}/#validation"
    metadata['validation_doc_path'] = f"docs/datasets/{dataset_name}.md#validation"

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
        metadata['comparison_tasks'] = validation_stats.get('tasks')
    else:
        metadata['validation_status'] = 'UNKNOWN'
        metadata['validation_pass_rate'] = None
        metadata['validation_total_strides'] = None
        metadata['validation_passing_strides'] = None
        metadata['quality_display'] = '⚠️ Validation Pending'
        metadata['comparison_tasks'] = metadata.get('comparison_tasks') or {}
    metadata['validation_ranges_file'] = ranges_display

    if plot_ranges_path is None:
        plot_ranges_path = _resolve_default_ranges_file()

    ranges_source_path = Path(plot_ranges_path)
    if not ranges_source_path.is_absolute():
        ranges_source_path = (repo_root / ranges_source_path).resolve()

    validation_doc_path = DOCS_DATASETS_DIR / validation_doc_filename

    ranges_download_filename, validation_summary = _snapshot_validation_ranges(
        dataset_name,
        DOCS_DATASETS_DIR,
        ranges_source_path,
        ranges_display,
        validation_summary,
        metadata,
    )
    metadata['validation_summary'] = validation_summary
    ranges_source_display = metadata.get('validation_ranges_source')

    # Show validation results
    print(f"\n📊 Validation Results:")
    print(validation_summary)
    
    # Generate documentation
    print(f"\n📄 Generating documentation...")
    doc_wrapper_path, doc_body_path = generate_dataset_page(dataset_path, metadata, validation_doc_filename)
    validation_body_path = generate_validation_page(
        dataset_path,
        metadata,
        validation_summary,
        validation_stats,
        validation_ranges,
        validation_doc_path,
        ranges_download_filename,
        ranges_source_display,
    )
    print(f"✅ Tab wrapper created: {doc_wrapper_path.relative_to(repo_root)}")
    print(f"✅ Documentation body created: {doc_body_path.relative_to(repo_root)}")
    print(f"✅ Validation body created: {validation_body_path.relative_to(repo_root)}")
    
    # Generate plots directory structure
    plots_dir = repo_root / "docs" / "datasets" / "validation_plots" / dataset_name
    plots_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Plot directory prepared: {plots_dir.relative_to(repo_root)}/")

    # Generate fresh validation plots for the dataset
    try:
        plot_ranges_for_cmd = None
        if plot_ranges_path and Path(plot_ranges_path).exists():
            plot_ranges_for_cmd = Path(plot_ranges_path)
        _generate_validation_plots(dataset_path, plots_dir, plot_ranges_for_cmd)
    except subprocess.CalledProcessError as exc:
        print(f"⚠️  Plot generation failed: {exc}")

    update_validation_gallery(validation_body_path, dataset_name)

    # Persist metadata and refresh global tables
    write_metadata_file(metadata)
    update_dataset_tables()
    generate_comparison_snapshot()

    
    # Show submission checklist
    checklist = generate_submission_checklist(
        dataset_name,
        dataset_path,
        doc_wrapper_path,
        doc_body_path,
        validation_body_path,
    )
    print(checklist)
    
    # Save checklist to file
    checklist_path = repo_root / f"submission_checklist_{dataset_name}.txt"
    with open(checklist_path, 'w') as f:
        f.write(checklist)
    print(f"💾 Checklist saved to: {checklist_path.name}")
    
    print(f"\n🎉 SUCCESS! Your dataset submission is prepared!")
    print(f"   Follow the checklist above to complete your PR")
    
    return 0





def handle_update_documentation(args):
    """Regenerate the dataset overview page and metadata."""
    short_code = args.short_code.upper()
    if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
        print("❌ Short code must be 2 letters + 2 digits (optional trailing letter)")
        return 1

    dataset_slug = _slugify_short_code(short_code)
    try:
        metadata = _load_metadata_for_slug(dataset_slug)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return 1

    dataset_arg = getattr(args, 'dataset', None)
    try:
        dataset_path = _resolve_dataset_path(dataset_arg, metadata)
    except (ValueError, FileNotFoundError) as exc:
        print(f"❌ {exc}")
        return 1

    metadata['short_code'] = short_code
    metadata['dataset_name'] = dataset_slug
    metadata['doc_url'] = metadata.get('doc_url') or f"{SITE_DATASET_BASE_URL}/{dataset_slug}/"
    metadata['doc_path'] = metadata.get('doc_path') or f"docs/datasets/{dataset_slug}.md"
    metadata['validation_doc_url'] = metadata.get('validation_doc_url') or f"{SITE_DATASET_BASE_URL}/{dataset_slug}/#validation"
    metadata['validation_doc_path'] = metadata.get('validation_doc_path') or f"docs/datasets/{dataset_slug}.md#validation"
    if metadata.get('validation_doc_path', '').endswith('_validation.md'):
        metadata['validation_doc_path'] = f"docs/datasets/{dataset_slug}.md#validation"
    if metadata.get('validation_doc_url', '').endswith('_validation/'):
        metadata['validation_doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_slug}/#validation"
    metadata['last_dataset_path'] = _relative_path(dataset_path)

    override_path = getattr(args, 'metadata_file', None)
    if override_path:
        override_path = Path(override_path)
        if not override_path.exists():
            print(f"❌ Metadata file not found: {override_path}")
            return 1
        try:
            overrides = load_metadata_file(override_path)
        except ValueError as exc:
            print(f"❌ {exc}")
            return 1
        override_code = overrides.get('short_code')
        if override_code and override_code.upper() != short_code:
            print("❌ Metadata file short_code does not match --short-code")
            return 1
        metadata.update({k: v for k, v in overrides.items() if v is not None})
        metadata['short_code'] = short_code
        metadata['dataset_name'] = dataset_slug

    try:
        locomotion_data = _load_locomotion_data(dataset_path, "refreshing tasks and subjects")
    except Exception as exc:
        print(f"❌ Unable to load dataset: {exc}")
        return 1

    detected_tasks, task_rows = _extract_task_catalog(locomotion_data)
    if detected_tasks:
        metadata['tasks'] = detected_tasks
    else:
        metadata['tasks'] = metadata.get('tasks', [])
    metadata['subjects'] = str(len(locomotion_data.get_subjects()))
    metadata['task_table'] = _build_task_table(task_rows)

    coverage_groups, coverage_tasks, coverage_source_path = _compute_feature_task_groups(dataset_path, metadata['tasks'])
    if coverage_groups:
        metadata['feature_task_groups'] = coverage_groups
        if coverage_tasks:
            metadata['feature_task_order'] = coverage_tasks
        if coverage_source_path:
            metadata['feature_task_source'] = _relative_path(coverage_source_path)

    if not override_path:
        _prompt_metadata_updates(metadata)

    validation_doc_filename = f".generated/{dataset_slug}_validation.md"
    doc_path, doc_body_path = generate_dataset_page(dataset_path, metadata, validation_doc_filename)
    write_metadata_file(metadata)
    update_dataset_tables()
    generate_comparison_snapshot()

    print(f"✅ Tab wrapper refreshed: {doc_path.relative_to(repo_root)}")
    print(f"✅ Documentation body refreshed: {doc_body_path.relative_to(repo_root)}")
    return 0


def handle_update_validation(args):
    """Re-run validation and refresh the validation report."""
    short_code = args.short_code.upper()
    if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
        print("❌ Short code must be 2 letters + 2 digits (optional trailing letter)")
        return 1

    dataset_slug = _slugify_short_code(short_code)
    try:
        metadata = _load_metadata_for_slug(dataset_slug)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return 1

    dataset_arg = getattr(args, 'dataset', None)
    try:
        dataset_path = _resolve_dataset_path(dataset_arg, metadata)
    except (ValueError, FileNotFoundError) as exc:
        print(f"❌ {exc}")
        return 1

    custom_ranges_path: Optional[Path] = None
    if getattr(args, 'ranges_file', None):
        custom_ranges_path = _resolve_ranges_argument(args.ranges_file)
        if not custom_ranges_path.exists():
            print(f"❌ Validation ranges file not found: {custom_ranges_path}")
            return 1

    metadata['short_code'] = short_code
    metadata['dataset_name'] = dataset_slug
    metadata['doc_url'] = metadata.get('doc_url') or f"{SITE_DATASET_BASE_URL}/{dataset_slug}/"
    metadata['doc_path'] = metadata.get('doc_path') or f"docs/datasets/{dataset_slug}.md"
    metadata['validation_doc_url'] = metadata.get('validation_doc_url') or f"{SITE_DATASET_BASE_URL}/{dataset_slug}/#validation"
    metadata['validation_doc_path'] = metadata.get('validation_doc_path') or f"docs/datasets/{dataset_slug}.md#validation"
    metadata['last_dataset_path'] = _relative_path(dataset_path)
    if metadata.get('validation_doc_path', '').endswith('_validation.md'):
        metadata['validation_doc_path'] = f"docs/datasets/{dataset_slug}.md#validation"
    if metadata.get('validation_doc_url', '').endswith('_validation/'):
        metadata['validation_doc_url'] = f"{SITE_DATASET_BASE_URL}/{dataset_slug}/#validation"

    coverage_groups, coverage_tasks, coverage_source_path = _compute_feature_task_groups(dataset_path, metadata.get('tasks', []))
    if coverage_groups:
        metadata['feature_task_groups'] = coverage_groups
        if coverage_tasks:
            metadata['feature_task_order'] = coverage_tasks
        if coverage_source_path:
            metadata['feature_task_source'] = _relative_path(coverage_source_path)


    try:
        locomotion_data = _load_locomotion_data(dataset_path, "updating tasks and subjects")
    except Exception as exc:
        print(f"❌ Unable to load dataset: {exc}")
        return 1

    detected_tasks, task_rows = _extract_task_catalog(locomotion_data)
    if detected_tasks:
        metadata['tasks'] = detected_tasks
    else:
        metadata['tasks'] = metadata.get('tasks', [])
    metadata['subjects'] = str(len(locomotion_data.get_subjects()))
    metadata['task_table'] = _build_task_table(task_rows)

    print(f"🔍 Updating validation for {dataset_slug}...")
    _, validation_summary, validation_stats, validation_ranges = run_validation(dataset_path, custom_ranges_path)
    metadata['validation_summary'] = validation_summary

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
        metadata['comparison_tasks'] = validation_stats.get('tasks')
    else:
        metadata['validation_status'] = 'UNKNOWN'
        metadata['validation_pass_rate'] = None
        metadata['validation_total_strides'] = None
        metadata['validation_passing_strides'] = None
        metadata['quality_display'] = '⚠️ Validation Pending'
        metadata['comparison_tasks'] = metadata.get('comparison_tasks') or {}
    metadata['validation_ranges_file'] = ranges_display

    if plot_ranges_path is None:
        plot_ranges_path = _resolve_default_ranges_file()

    ranges_source_path = Path(plot_ranges_path)
    if not ranges_source_path.is_absolute():
        ranges_source_path = (repo_root / ranges_source_path).resolve()

    validation_doc_filename = f".generated/{dataset_slug}_validation.md"
    validation_doc_path = DOCS_DATASETS_DIR / validation_doc_filename

    ranges_download_filename, validation_summary = _snapshot_validation_ranges(
        dataset_slug,
        DOCS_DATASETS_DIR,
        ranges_source_path,
        ranges_display,
        validation_summary,
        metadata,
    )
    metadata['validation_summary'] = validation_summary
    ranges_source_display = metadata.get('validation_ranges_source')
    metadata['tasks'] = metadata.get('tasks', [])
    metadata['task_table'] = metadata.get('task_table', '')

    print(f"\n📊 Validation Results:")
    print(validation_summary)

    print(f"\n📄 Updating documentation...")
    doc_path, doc_body_path = generate_dataset_page(dataset_path, metadata, validation_doc_filename)
    validation_body_path = generate_validation_page(
        dataset_path,
        metadata,
        validation_summary,
        validation_stats,
        validation_ranges,
        validation_doc_path,
        ranges_download_filename,
        ranges_source_display,
    )
    print(f"✅ Tab wrapper updated: {doc_path.relative_to(repo_root)}")
    print(f"✅ Documentation body updated: {doc_body_path.relative_to(repo_root)}")
    print(f"✅ Validation body updated: {validation_body_path.relative_to(repo_root)}")

    plots_dir = repo_root / "docs" / "datasets" / "validation_plots" / dataset_slug
    plots_dir.mkdir(parents=True, exist_ok=True)

    try:
        plot_ranges_for_cmd = ranges_source_path if ranges_source_path.exists() else None
        _generate_validation_plots(dataset_path, plots_dir, plot_ranges_for_cmd)
    except subprocess.CalledProcessError as exc:
        print(f"⚠️  Plot generation failed: {exc}")

    update_validation_gallery(validation_body_path, dataset_slug)

    write_metadata_file(metadata)
    update_dataset_tables()
    generate_comparison_snapshot()

    print("✅ Validation assets refreshed")
    return 0


def handle_remove_dataset(args):
    """Remove generated assets for a dataset."""
    short_code = args.short_code.upper()
    if not re.match(r'^[A-Z]{2}\d{2}[A-Z]?$', short_code):
        print("❌ Short code must be 2 letters + 2 digits (optional trailing letter)")
        return 1

    dataset_slug = _slugify_short_code(short_code)
    removed_paths = _remove_dataset_for_slug(dataset_slug, include_parquet=args.remove_parquet)
    if args.remove_parquet and removed_paths:
        print("⚠️ Converted parquet files were deleted. Re-run your conversion script before add-dataset.")
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
  
  Need to refresh the overview page after editing metadata? Run:
      python contributor_tools/manage_dataset_documentation.py update-documentation \\
          --short-code YOUR_CODE [--dataset converted_datasets/your_dataset_phase.parquet]
  
  Need to refresh validation results or plots? Run:
      python contributor_tools/manage_dataset_documentation.py update-validation \\
          --short-code YOUR_CODE [--dataset converted_datasets/your_dataset_phase.parquet]
  
  Need to clean everything up? Run:
      python contributor_tools/manage_dataset_documentation.py remove-dataset \\
          --short-code YOUR_CODE [--remove-parquet]
  
  The tool will:
  - Collect metadata interactively or via --metadata-file
  - Run validation and show results when requested  
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
        '--short-code',
        help='Optional explicit short code (otherwise derived during prompts)'
    )

    update_doc_parser = subparsers.add_parser(
        'update-documentation',
        help='Refresh dataset overview markdown and metadata for an existing short code'
    )
    update_doc_parser.add_argument(
        '--short-code',
        required=True,
        help='Dataset short code (e.g., UM21)'
    )
    update_doc_parser.add_argument(
        '--dataset',
        help='Path to dataset parquet; defaults to last_dataset_path from metadata'
    )
    update_doc_parser.add_argument(
        '--metadata-file',
        help='Optional metadata overrides to merge before regenerating the page'
    )

    update_val_parser = subparsers.add_parser(
        'update-validation',
        help='Re-run validation, plots, and snapshot ranges for an existing short code'
    )
    update_val_parser.add_argument(
        '--short-code',
        required=True,
        help='Dataset short code (e.g., UM21)'
    )
    update_val_parser.add_argument(
        '--dataset',
        help='Path to dataset parquet; defaults to last_dataset_path from metadata'
    )
    update_val_parser.add_argument(
        '--ranges-file',
        help='Optional validation ranges YAML to override defaults'
    )

    remove_parser = subparsers.add_parser(
        'remove-dataset',
        help='Delete generated docs/metadata/plots so a dataset can be rebuilt'
    )
    remove_parser.add_argument(
        '--short-code',
        required=True,
        help='Dataset short code to remove'
    )
    remove_parser.add_argument(
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
    if args.command == 'update-documentation':
        return handle_update_documentation(args)
    if args.command == 'update-validation':
        return handle_update_validation(args)
    if args.command == 'remove-dataset':
        return handle_remove_dataset(args)
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
