#!/usr/bin/env python3
"""Publish exact configured ranges and an actual pytest JUnit result for the static site."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.config_manager import ValidationConfigManager


def export_ranges(source):
    config = ValidationConfigManager(source)
    tasks = {}
    for task in config.get_tasks():
        features = {}
        for phase, variables in config.get_task_data(task).items():
            for feature, bounds in variables.items():
                index = round(float(phase) * 149 / 100)
                features.setdefault(feature, []).append({
                    'phase': float(phase), 'sample_index': index, 'sample_phase': index * 100 / 149,
                    'min': bounds['min'], 'max': bounds['max'],
                })
        tasks[task] = features
    return {'source': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'metadata': config.get_metadata(), 'tasks': tasks}


def read_results(path):
    tree = ET.parse(path)
    groups = {}
    for case in tree.iter('testcase'):
        name = case.attrib.get('classname', 'unknown')
        group = groups.setdefault(name, {'passed': 0, 'failed': 0, 'skipped': 0, 'cases': []})
        state = 'failed' if case.find('failure') is not None or case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        group[state] += 1
        record = {'name': case.attrib['name'], 'status': state}
        if state == 'skipped':
            record['reason'] = case.find('skipped').attrib.get('message', '')
        group['cases'].append(record)
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junit', type=Path, required=True, help='JUnit XML from an actual pytest run')
    args = parser.parse_args()
    output = ROOT / 'docs/quality'
    output.mkdir(exist_ok=True)
    ranges = export_ranges(ROOT / 'contributor_tools/validation_ranges/default_ranges.yaml')
    (output / 'phase_ranges.json').write_text(json.dumps(ranges, separators=(',', ':'), allow_nan=False) + '\n')
    groups = read_results(args.junit)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    result = {'recorded_at': datetime.fromtimestamp(args.junit.stat().st_mtime, timezone.utc).isoformat(),
              'base_revision': revision, 'working_tree_changes': bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True).strip()), 'scope': 'Small synthetic fixtures and source checks; not a validation run over the downloaded datasets.',
              'command': 'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 -m pytest -q --junitxml=/tmp/locohub-quality-tests.xml',
              'junit_sha256': hashlib.sha256(args.junit.read_bytes()).hexdigest(), 'groups': groups,
              'totals': {state: sum(g[state] for g in groups.values()) for state in ['passed', 'failed', 'skipped']}}
    (output / 'test_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['totals'])


if __name__ == '__main__':
    main()
