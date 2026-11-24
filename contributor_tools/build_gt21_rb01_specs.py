"""Write the guarded-launcher specs for GT21-RB01 (plan only; nothing is launched). Standard library only.

Specs go to docs/quality/audits/gt21-rb01-<job>-spec.json and refuse to overwrite. Each binds the runner and the
evidence it reads, so a changed file refuses the launch. Receipts name the same job under the same folder.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import run_gt21_rb01 as rb  # noqa: E402

AUDITS = ROOT / 'docs/quality/audits'
INVENTORY_ROOT = 'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123'
COMMON = {'cwd': str(ROOT), 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
          'startup_memory_mib': {'linux': 3584, 'windows': 2816},
          'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'address_space_mib': 768}


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT)) if Path(path).resolve().is_relative_to(ROOT) else str(path)


def extract_spec(subject):
    paths = rb.participant_paths(subject)
    out = rb.EXTRACT_ROOT / subject
    ledger = rb.EXTRACT_ROOT / '_ledgers' / f'{subject}_extraction.json'
    bound = [Path(rb.__file__), paths['manifest'], paths['result'], paths['listing']]
    return {'job_id': f'gt21-rb01-extract-{subject}',
            'command': ['python3', 'contributor_tools/run_gt21_rb01.py', 'extract', '--subject', subject,
                        '--out-root', str(out), '--ledger', str(ledger)],
            'output_root': str(out), 'receipt_path': f'docs/quality/audits/gt21-rb01-extract-{subject}-launcher-receipt.json',
            'bindings': {str(p): rb.sha256_file(p) for p in bound},
            'disk_admission': [{'path': '/mnt/s/locomotion_data', 'min_free_mib': 16384}], **COMMON}


def inventory_spec():
    bound = [Path(rb.__file__), rb.CROSSWALK]
    bound += [rb.EXTRACT_ROOT / '_ledgers' / f'{s}_extraction.json' for s in rb.SIX]
    return {'job_id': 'gt21-rb01-inventory', 'command': ['python3', 'contributor_tools/run_gt21_rb01.py', 'inventory',
                                                          '--out-root', INVENTORY_ROOT],
            'output_root': INVENTORY_ROOT, 'receipt_path': 'docs/quality/audits/gt21-rb01-inventory-launcher-receipt.json',
            'bindings': {str(p): rb.sha256_file(p) for p in bound},
            'disk_admission': [{'path': '/mnt/s/workspace', 'min_free_mib': 8192}], **COMMON}


def write(name, spec):
    target = AUDITS / f'gt21-rb01-{name}-spec.json'
    with target.open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return target


if __name__ == '__main__':
    which = sys.argv[1]
    print(write(f'extract-{which}' if which in rb.SIX else 'inventory', extract_spec(which) if which in rb.SIX else inventory_spec()))
