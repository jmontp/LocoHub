"""Publishing and displaying precomputed summaries without reading research files."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('static_averages', ROOT / 'docs/build.py')
SITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SITE)


def test_task_json_is_checked_and_copied_relative_to_manifest(tmp_path):
    source = tmp_path / 'docs'
    nested = source / 'datasets/aggregate_previews/example'
    nested.mkdir(parents=True)
    (source / 'index.html').write_text('<html><title>Data</title><main data-aggregate-source="datasets/aggregate_previews/manifest.json">Data</main></html>')
    manifest = nested.parent / 'manifest.json'
    manifest.write_text(json.dumps({'datasets': {'example': {'tasks': [{'url': 'example/walking.json'}]}}}))
    task = nested / 'walking.json'
    subject = nested / 'subject.json'
    subject.write_text('{"signals":{}}')
    task.write_text(json.dumps({'phase': [], 'subjects': {'S1': {'url': 'subject.json'}}}))
    out = tmp_path / 'output'
    SITE.build(out, source)
    assert (out / 'datasets/aggregate_previews/example/walking.json').read_bytes() == task.read_bytes()
    assert (out / 'datasets/aggregate_previews/example/subject.json').read_bytes() == subject.read_bytes()
    subject.unlink()
    with pytest.raises(ValueError, match='missing subject file'):
        SITE.check_site(source)
    task.unlink()
    with pytest.raises(ValueError, match='missing local task'):
        SITE.check_site(source)
    manifest.write_text(json.dumps({'datasets': {'example': {'tasks': [{'url': '../../../../outside.json'}]}}}))
    with pytest.raises(ValueError, match='escapes docs'):
        SITE.check_site(source)


def test_browser_scripts_parse():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    for name in ['aggregate-preview.js', 'visual-styles.js']:
        subprocess.run([node, '--check', str(ROOT / 'docs/javascripts' / name)], check=True)


def test_published_overall_mean_weights_subjects_equally():
    directory = ROOT / 'docs/datasets/aggregate_previews'
    manifest = json.loads((directory / 'manifest.json').read_text())
    catalog = json.loads((ROOT / 'docs/datasets/comparison_data.json').read_text())
    assert set(manifest['datasets']) == {dataset['slug'] for dataset in catalog['datasets']}
    task = next(task for dataset in manifest['datasets'].values() for task in dataset.get('tasks', []) if len(task['subjects']) > 1 and task['signals'])
    assert not task['url'].startswith('/')
    payload = json.loads((directory / task['url']).read_text())
    assert len(payload['phase']) == 150
    signal = task['signals'][0]['column']
    means = []
    for group in payload['subjects'].values():
        if 'url' in group:
            group = json.loads((directory / task['url']).parent.joinpath(group['url']).read_text())
        if signal in group['signals']:
            means.append(group['signals'][signal]['mean'])
    overall = payload['all']['signals'][signal]
    for i in range(150):
        values = [row[i] for row in means if row[i] is not None]
        assert overall['n'][i] == len(values)
        if values:
            assert overall['mean'][i] == pytest.approx(np.mean(values), rel=2e-5, abs=2e-6)
        else:
            assert overall['mean'][i] is None
        if len(values) > 1:
            assert overall['sd'][i] == pytest.approx(np.std(values, ddof=1), rel=2e-5, abs=2e-6)
        else:
            assert overall['sd'][i] is None
