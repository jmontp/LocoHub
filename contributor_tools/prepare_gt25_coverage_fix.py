#!/usr/bin/env python3
"""Prepare, but never run, an isolated GT25 shuffle/admission correction.

No frozen project files are modified. A coordinator must validate and schedule
native-data pilots before adopting this snapshot. Large inputs stay deferred.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILY = Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Reviewed source shape changed: ' + old[:80])
    return source.replace(old, new, 1)


def patch_converter(source):
    source = replace_once(source, '# Shuffle is lateral, exclude',
                          '# Source README: level treadmill walking at 0.4 m/s')
    return replace_once(source,
        "r'normal_walk.*_shuffle': (None, 'shuffle', {}),",
        "r'normal_walk.*_shuffle': ('level_walking', 'level_0.4ms', "
        "{'speed_m_s': 0.4, 'incline_deg': 0.0, 'source_variant': 'shuffle'}),")


def patch_mapping(source):
    source = replace_once(source, '# Shuffle is lateral, exclude from standard tasks',
                          '# Source README: level treadmill walking at 0.4 m/s')
    return replace_once(source,
        "r'normal_walk.*_shuffle': (None, 'shuffle', {'speed_m_s': 0.4, 'incline_deg': 0.0, 'surface': 'treadmill'}),",
        "r'normal_walk.*_shuffle': ('level_walking', 'level_0.4ms', {'speed_m_s': 0.4, 'incline_deg': 0.0, 'surface': 'treadmill', 'source_variant': 'shuffle'}),")


ADMISSION_HELPER = '''
def selected_source_bytes(source, subject, recording):
    # Call the exact worker source discovery; never count unused trial CSVs.
    import importlib.util
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('gt25_source_adapter', CODE/'reconvert_recording.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    _, paths, _ = adapter.source_paths(SimpleNamespace(
        source_root=source, subject=subject, recording=recording))
    return sum(path.stat().st_size for path in paths)

'''


def patch_runner(source):
    source = replace_once(source, '\ndef inventory(source):', ADMISSION_HELPER+'\ndef inventory(source):')
    source = replace_once(source,
        "'source_csv_bytes':sum(p.stat().st_size for p in folder.glob('*.csv'))})",
        "'source_csv_bytes':sum(p.stat().st_size for p in folder.glob('*.csv')),\n"
        "                'selected_source_bytes':selected_source_bytes(source,subject.name,folder.name)})")
    source = replace_once(source,
        "sum(r['source_csv_bytes']>64*1024**2 for r in plan)",
        "sum(r['selected_source_bytes']>64*1024**2 for r in plan)")
    return replace_once(source,
        "record['source_csv_bytes']+(source.parent/'readme.txt').stat().st_size>64*1024**2",
        "record['selected_source_bytes']>64*1024**2")


def prepare(output, readme, root=ROOT):
    output = Path(output).resolve()
    readme = Path(readme).resolve()
    text = readme.read_text()
    for evidence in ['normal_walk: ambulating at different speeds on a level treadmill',
                     '_shuffle: walking at 0.4 m/s']:
        if evidence not in text:
            raise ValueError('Required original README evidence missing: '+evidence)
    files = {p.relative_to(root): p for p in (root/'contributor_tools/common').rglob('*.py')}
    files.update({p.relative_to(root): p for p in (root/FAMILY).glob('*.py')})
    for name in ['reconvert_recording.py', 'run_reconversion_batch.py', 'run_gt25_batch.py']:
        p = root/'contributor_tools'/name
        files[p.relative_to(root)] = p
    init = root/'contributor_tools/__init__.py'
    if init.exists():
        files[init.relative_to(root)] = init
    patches = {FAMILY/'convert_gtech_2025_da_to_parquet.py': patch_converter,
               FAMILY/'task_mapping.py': patch_mapping,
               Path('contributor_tools/run_gt25_batch.py'): patch_runner}
    contents = {}
    for rel, original in files.items():
        value = original.read_text()
        if rel in patches:
            value = patches[rel](value)
        ast.parse(value, filename=str(rel))
        contents[rel] = value
    # Fail closed before creating anything if a dependency or patch changed.
    if not patches.keys() <= contents.keys():
        raise ValueError('Required source dependency missing')
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'isolated_repo'
    for rel, value in contents.items():
        target = snapshot/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)
    evidence_copy = output/'source_readme.txt'
    evidence_copy.write_bytes(readme.read_bytes())
    plan = {'status': 'prepared_unreviewed_not_run', 'scientific_approval': False,
        'preparation_tool_sha256': sha(Path(__file__)),
        'readme': {'original_path': str(readme), 'sha256': sha(evidence_copy)},
        'original_code': {str(p): sha(p) for p in files.values()},
        'snapshot_code': {str(rel): sha(snapshot/rel) for rel in contents},
        'changes': ['README-supported shuffle mapping only', 'Exact worker-selected source admission; limits unchanged'],
        'output_constraint': str(snapshot/'converted_datasets/reconversion_v2'),
        'pilot_required': ['one shuffle recording', 'one previously false-oversize sit/stand recording',
                           'unchanged ordinary recording exact preservation', 'snapshot import and provenance validation'],
        'unresolved': ['34 mapped oversized recordings still require bounded reading',
                       '192 cutting/ball-toss/start-stop recordings still excluded',
                       'anatomical conventions and source segmentation approval'],
        'execution': 'No command is launched by this tool. Coordinator must verify snapshot hashes and host guards before scheduling.'}
    (output/'preparation_manifest.json').write_text(json.dumps(plan, indent=2)+'\n')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--source-readme', type=Path, required=True)
    args = parser.parse_args()
    allowed = ROOT/'converted_datasets/reconversion_v2'
    if not args.output_root.resolve().is_relative_to(allowed.resolve()):
        parser.error('Output must remain under converted_datasets/reconversion_v2')
    print(prepare(args.output_root, args.source_readme)['status'])


if __name__ == '__main__':
    main()
