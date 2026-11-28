"""Plan MBLUE orientation lineage from JSON evidence and bounded XML only.

No MAT arrays, IK numerical samples, OpenSim evaluation or conversion is run.
A missing FileInfo receipt or model execution binding remains an explicit gap.
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import xml.etree.ElementTree as ET


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_evidence(ik, condition, availability):
    if condition not in ('bare', 'exo'):
        raise ValueError('Unsupported source condition')
    path = Path(ik)
    matching = [r for r in availability['records'] if any(x['path'] == ik for x in r['corrected_ik_headers'])]
    if len(matching) != 1:
        return {'status': 'missing_or_ambiguous_header_census_entry'}
    row = matching[0]
    header = next(x for x in row['corrected_ik_headers'] if x['path'] == ik)
    if header['missing_required_coordinates'] or not header['in_degrees']:
        return {'status': 'missing_coordinates_or_unreviewed_units'}
    expected_name = f'gait2392_simbody_{row["subject"]}_placed' + ('_exo' if condition == 'exo' else '') + '.osim'
    models = [m for m in row['models'] if Path(m['path']).name == expected_name]
    if len(models) != 1:
        return {'status': 'missing_or_ambiguous_placed_model'}
    model = models[0]
    if digest(model['path']) != model['sha256']:
        raise ValueError('Model XML changed since census')
    stem = path.name.removesuffix('_IK_Results.mot')
    setups = []
    for suffix in ('_IK.XML', '_ID.XML'):
        setup = path.parent / 'OpenSimGenFiles' / (stem + suffix)
        if not setup.exists():
            setups.append({'path': str(setup), 'status': 'missing'}); continue
        if setup.stat().st_size > 2 * 1024**2:
            raise MemoryError('Unexpected setup XML size')
        raw = setup.read_bytes(); tree = ET.fromstring(raw)
        fields = {name: tree.findtext('.//' + name) for name in
                  ('model_file', 'output_motion_file', 'coordinates_file')}
        setups.append({'path': str(setup), 'sha256': hashlib.sha256(raw).hexdigest(), 'fields': fields})
    # Do not promote a script-selected filename into a recorded execution hash.
    named_models = [s['fields'].get('model_file') for s in setups if 'fields' in s]
    named = any(v and v != 'Unassigned' and PureWindowsPath(v).name == expected_name for v in named_models)
    return {'status': 'model_filename_named_but_execution_hash_unverified' if named else 'documented_recipe_model_selected_historical_execution_hash_unrecorded',
            'model': {'path': model['path'], 'sha256': model['sha256']},
            'ik_header_sha256': header['header_sha256'], 'ik_columns_present': header['columns'],
            'setups': setups, 'scientific_approval': False}


def plan(inventory, rebuild, recovery, availability, fileinfo=None):
    records = []; windows = {}; models = {}
    for rec in recovery['records']:
        candidates = [c for c in rec['candidates'] if c['status'] == 'all_windows_matched']
        if rec['status'] != 'unique_source_matched' or len(candidates) != 1:
            raise ValueError('Unique source recovery required')
        candidate = candidates[0]
        for window in candidate['windows']:
            key = (rec['subject'], window['source_path'])
            windows.setdefault(key, []).append((rec, candidate, window))
    observed = {(r['subject'], r['source_path']): r for r in rebuild['records']}
    if len(observed) != len(rebuild['records']):
        raise ValueError('Duplicate rebuild blocks')
    expected = [(r['subject'], r['source_path']) for r in inventory['blocks']]
    if len(set(expected)) != len(expected) or set(expected) != set(observed):
        raise ValueError('Exact unique inventory/rebuild block set required')
    for block in inventory['blocks']:
        subject, source_path = block['subject'], block['source_path']
        condition, task, *_ = source_path.split('/')
        if condition not in ('bare', 'exo'):
            raise ValueError('Unsupported source condition')
        record = {'subject': subject, 'source_path': source_path, 'condition': condition, 'task': task,
                  'status': 'needs_hash_bound_fileinfo_metadata_receipt', 'retained_windows': []}
        evidence = observed.get((subject, source_path))
        if evidence is None:
            raise ValueError('Rebuild missing inventoried block')
        record['fileinfo_sha256'] = evidence['subject_info_sha256']
        mapped = windows.get((subject, source_path), [])
        if mapped:
            iks = {c['ik_path'] for _, c, _ in mapped}
            if len(iks) != 1:
                raise ValueError('Multiple IK files for one normalized block')
            record['ik_path'] = iks.pop()
            record['ik_sha256'] = mapped[0][1]['ik_sha256']
            for rec, candidate, window in mapped:
                if (rec['subject_info_sha256'] != evidence['subject_info_sha256']
                        or rec['normalized_sha256'] != evidence['source_sha256']):
                    raise ValueError('Stair recovery and rebuild source lineage differ')
                side = window['reference_side']; index = window['source_curve_index']
                record['retained_windows'].append({
                    'observation_id': f'mblue:{subject}_NormalizedStrides.mat:dataOut/{source_path}:{side[0]}:column:{index}',
                    'source_event_start_s': window['source_event_start_s'],
                    'source_event_end_s': window['source_event_end_s'],
                    'note': 'Event bounds differ from normalized target clock; obtain actual preserved target times before pose interpolation'})
            record['status'] = 'stair_ik_source_matched_model_binding_pending'
        elif fileinfo and subject in fileinfo.get('subjects', {}):
            info = fileinfo['subjects'][subject]
            if info['source_fileinfo_sha256'] != evidence['subject_info_sha256']:
                raise ValueError('FileInfo receipt not bound to rebuilt source')
            details = info['tasks'][condition][task]
            name = details['vicon_filename'] if condition == 'bare' else 'exo_' + details['filename_suffix']
            if Path(name).name != name or Path(info['date']).name != info['date']:
                raise ValueError('Unsafe FileInfo path')
            matches = [x['path'] for r in availability['records']
                       if r['subject'] == subject and r['date'] == info['date']
                       for x in r['corrected_ik_headers'] if Path(x['path']).name == name + '_corrected_IK_Results.mot']
            if len(matches) == 1:
                record.update(ik_path=matches[0], status='fileinfo_path_matched_raw_window_validation_pending')
            else:
                record['status'] = 'fileinfo_ik_missing_or_ambiguous'
        if 'ik_path' in record:
            model_key = (record['ik_path'], condition)
            if model_key not in models:
                models[model_key] = model_evidence(record['ik_path'], condition, availability)
            record['model_evidence'] = models[model_key]
        records.append(record)
    return {'status': 'orientation_lineage_plan_incomplete_unreviewed', 'scientific_approval': False,
            'blocks': len(records), 'records': records,
            'stair_windows_mapped': sum(len(r['retained_windows']) for r in records),
            'blocks_with_ik_path': sum('ik_path' in r for r in records),
            'remaining_gates': ['Hash-bound FileInfo date/task metadata receipt for nonstair blocks',
                'Raw IK full hashes, actual normalized clocks and all window coverage checks',
                'Use the uniquely selected placed model from documented recipe, hashing current inputs and declaring this reproducible derivation; historical execution hash absence is not itself a blocker',
                'Reviewed spatial orientation definition and native OpenSim body-pose pilot'],
            'next_pilot': 'One bounded matched stair window, actual placed bare/exo model and complete raw IK coordinates; use OpenSim body transforms, never scalar angle sums. Do not execute until serial numerical slot is assigned.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'rebuild', 'recovery', 'availability'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--fileinfo-json', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ('inventory', 'rebuild', 'recovery', 'availability')}
    hashes = {name: digest(path) for name, path in paths.items()}
    reports = {name: json.loads(path.read_text()) for name, path in paths.items()}
    if reports['rebuild']['inventory_sha256'] != hashes['inventory']:
        raise ValueError('Rebuild inventory hash mismatch')
    fileinfo = None
    if args.fileinfo_json:
        paths['fileinfo_json'] = args.fileinfo_json
        hashes['fileinfo_json'] = digest(args.fileinfo_json)
        fileinfo = json.loads(args.fileinfo_json.read_text())
    result = plan(**reports, fileinfo=fileinfo)
    result['input_sha256'] = hashes; result['planner_sha256'] = digest(Path(__file__))
    if any(digest(path) != hashes[name] for name, path in paths.items()):
        raise ValueError('Evidence changed during planning')
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'blocks', 'stair_windows_mapped', 'blocks_with_ik_path')}))


if __name__ == '__main__':
    main()
