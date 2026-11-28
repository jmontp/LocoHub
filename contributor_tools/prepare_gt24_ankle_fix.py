"""Prepare an isolated README-backed GT24 ankle correction; never launch workers."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILY = Path('contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic')
ADAPTER = FAMILY/'convert_gtech_2024_phase_to_parquet.py'
README_SHA256 = 'e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Reviewed source shape changed: '+old[:80])
    return source.replace(old, new, 1)


def patch_converter(source):
    original = ast.parse(source)
    for side in ('ipsi', 'contra'):
        old = f'ankle_{side}_rad = resample(ankle_{side}_deg * deg2rad)'
        source = replace_once(source, old, old.replace('resample(', 'resample(-', 1))
        for frame in ('moment_df', 'bio_moment_df'):
            old = f"{frame}[f'ankle_angle_{{{side}}}_moment'].values[start_idx:end_idx + 1]"
            indent = '        ' if frame == 'moment_df' else '            '
            source = replace_once(source, '\n'+indent+old, '\n'+indent+'-'+old)
    source = replace_once(source, '    task_info_str = json.dumps(info, sort_keys=True)',
        "    info.update(ankle_source_positive_direction='plantarflexion',\n"
        "                ankle_canonical_transform='negation for dorsiflexion positive',\n"
        "                ankle_convention_evidence='source README lines 90-94 and 483-563',\n"
        f"                ankle_convention_readme_sha256='{README_SHA256}',\n"
        "                ankle_source_alias_method='source sign retained after phase interpolation; velocity and acceleration derived')\n"
        '    task_info_str = json.dumps(info, sort_keys=True)')
    aliases = []
    for side in ('ipsi', 'contra'):
        for name, variable, unit in [('angle', f'ankle_{side}_rad', 'rad'),
                                     ('derived_velocity', f'ankle_vel_{side}', 'rad_s'),
                                     ('derived_acceleration', f'ankle_acc_{side}', 'rad_s2'),
                                     ('moment', f'ankle_mom_{side}', 'Nm_kg'),
                                     ('biological_moment', f'ankle_bio_mom_{side}', 'Nm_kg')]:
            aliases.append(f"        'source_ankle_coordinate_{name}_{side}_{unit}': -{variable},")
    source = replace_once(source, '        # Assistance flag',
                          '        # Original source coordinate signs; not additional measurements.\n'+'\n'.join(aliases)+'\n\n        # Assistance flag')
    updated = ast.parse(source)
    before = {node.name: ast.dump(node) for node in original.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    after = {node.name: ast.dump(node) for node in updated.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if before.keys() != after.keys() or any(before[name] != after[name] for name in before if name != 'process_stride'):
        raise ValueError('Unexpected change outside process_stride')
    return source


def prepare(output, readme, root=ROOT):
    output, readme, root = Path(output).resolve(), Path(readme).resolve(), Path(root).resolve()
    if not output.is_relative_to(root/'converted_datasets/reconversion_v2'):
        raise ValueError('Snapshot must remain under local reconversion root')
    if sha(readme) != README_SHA256:
        raise ValueError('Original README hash differs from reviewed evidence')
    files = {p.relative_to(root): p for p in (root/'contributor_tools/common').rglob('*.py')}
    files.update({p.relative_to(root): p for p in (root/FAMILY).glob('*.py')})
    for name in ['reconvert_recording.py', '__init__.py']:
        p = root/'contributor_tools'/name
        if p.exists():
            files[p.relative_to(root)] = p
    originals = {str(p): sha(p) for p in files.values()}
    contents = {rel: p.read_bytes() for rel, p in files.items()}
    contents[ADAPTER] = patch_converter(contents[ADAPTER].decode()).encode()
    for rel, data in contents.items():
        ast.parse(data.decode(), filename=str(rel))
    for name, expected in originals.items():
        if sha(name) != expected:
            raise ValueError('Source changed during preparation: '+name)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'isolated_repo'
    for rel, data in contents.items():
        target = snapshot/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o444)
    evidence = output/'source_readme.txt'
    evidence.write_bytes(readme.read_bytes())
    if sha(evidence) != README_SHA256:
        raise ValueError('README changed during preparation')
    evidence.chmod(0o444)
    manifest = {'status': 'prepared_unreviewed_not_run', 'scientific_approval': False,
                'preparation_tool_sha256': sha(__file__), 'original_code': originals,
                'snapshot_code': {str(rel): sha(snapshot/rel) for rel in contents},
                'readme': {'original_path': str(readme), 'sha256': README_SHA256},
                'output_constraint': str(snapshot/'converted_datasets/reconversion_v2'),
                'changed_functions': ['process_stride'],
                'changes': ['Negate source ankle angle, net moment and biological moment for both sides',
                            'Velocities and accelerations follow the corrected angle exactly once',
                            'Retain ten explicit source-coordinate aliases and README-bound metadata'],
                'unchanged': ['Segmentation and observation identity', 'Source missingness and units',
                              'Assistance structural zeros and NaNs', 'All IMU-derived segment helpers'],
                'segment_dependency_review': 'Segment paths use IMU columns, not corrected source ankle angle arrays. Their local variable ankle_angle is independently integrated gyro differences. No associated segment sign change is mathematically required; their separate anatomical approval is unchanged.',
                'deferred': ['Continuous exporter is copied unchanged and is NOT authorized by this pilot; it needs a separate reviewed correction',
                             'Native-versus-parsed bounded readback and real numerical pilot',
                             'Independent anatomical validation beyond the released README definition'],
                'pilot_specification': 'docs/quality/audits/gt24-ankle-evidence-ranking.json',
                'execution': 'Use isolated_repo/contributor_tools/reconvert_recording.py only in the coordinator serial slot after verifying every snapshot/source binding. No command launched.'}
    target = output/'preparation_manifest.json'
    target.write_text(json.dumps(manifest, indent=2)+'\n')
    target.chmod(0o444)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--source-readme', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.output_root, args.source_readme)['status'])


if __name__ == '__main__':
    main()
