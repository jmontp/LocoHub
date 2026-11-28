"""Isolated GT25 v4: participant BW and honest unknown source denominators.

Consumes the immutable ankle v3 snapshot; no conversion or active edits.
"""
import argparse
import ast
import json
from pathlib import Path
import re
from contributor_tools.prepare_gt25_ankle_fix import ADAPTER, README_SHA, ROOT, digest, once

AUDIT = Path('contributor_tools/audit_gt25_streaming_transfer_ankle_v3.py')
NEW_AUDIT = Path('contributor_tools/audit_gt25_streaming_transfer_normalization_v4.py')
METADATA = {
    'grf_normalization_basis': 'participant_mass_without_exoskeleton_times_9.81',
    'mass_source_readme_sha256': README_SHA,
    'moment_semantics': 'canonical_withheld_source_Nm_per_kg_denominator_unverified',
    'source_moment_mass_denominator': 'unknown; README gives Nm/kg but does not identify which listed mass',
    'source_interaction_torque_units': 'unknown; actual torque_interaction columns absent from README exo.csv definitions',
    'assistance_moment_semantics': 'canonical_withheld_source_interaction_units_unverified',
    'ankle_canonical_transform': 'negate angle; derive velocity and acceleration; canonical moments withheld pending source mass denominator',
}


def source_aliases():
    result = []
    for role in ('ipsi', 'contra'):
        for joint in ('hip_flexion', 'knee_angle', 'ankle_angle'):
            for kind in ('moment', 'biological_moment'):
                result.append(f'source_{joint}_{kind}_{role}_Nm_kg')
        for joint in ('hip_angle', 'knee_angle'):
            result.append(f'source_{joint}_torque_interaction_{role}_source_units')
        result.append(f'source_grf_global_y_{role}_N')
    return result


def patch_converter(source):
    before = ast.parse(source)
    source = once(source, "return SUBJECT_MASS[subject_id]['with_exo']", "return SUBJECT_MASS[subject_id]['without_exo']")
    source = once(source, 'Get subject mass (with exo) in kg.', 'Get participant mass without exoskeleton in kg.')
    source = once(source, '# Using with_exo mass since all data collected with exo worn', '# Canonical BW uses participant mass without exoskeleton; retain both source masses.')
    start = source.index('    # Exo assistance moments (interaction torque)')
    end = source.index('    ankle_assist_ipsi =', start)
    replacement = '''    # Actual interaction columns have no unit definition in the pinned README.
    # Preserve original values and do not invent a normalization or unit.
    source_interaction = {}
    for role, side in [('ipsi', ipsi), ('contra', contra)]:
        for joint in ('hip_angle', 'knee_angle'):
            source_interaction[f'source_{joint}_torque_interaction_{role}_source_units'] = (
                resample(data['exo'][f'{joint}_{side}_torque_interaction'].values[start_idx:end_idx + 1])
                if 'exo' in data else np.full(NUM_POINTS, np.nan))
    hip_assist_ipsi = np.full(NUM_POINTS, np.nan)
    hip_assist_contra = np.full(NUM_POINTS, np.nan)
    knee_assist_ipsi = np.full(NUM_POINTS, np.nan)
    knee_assist_contra = np.full(NUM_POINTS, np.nan)

'''
    source = source[:start] + replacement + source[end:]
    # Preserve original source moment orientation and published Nm/kg values.
    rows = ['        **source_interaction,']
    for role in ('ipsi', 'contra'):
        for output, short, raw, sign in [('hip_flexion','hip','hip_flexion',1), ('knee_flexion','knee','knee_angle',-1), ('ankle_dorsiflexion','ankle','ankle_angle',-1)]:
            for quantity, variable in [('moment',f'{short}_mom_{role}'), ('biological_moment',f'{short}_bio_mom_{role}')]:
                rows.append(f"        'source_{raw}_{quantity}_{role}_Nm_kg': {sign} * {variable},")
                source = once(source, f"'{output}_{quantity}_{role}_Nm_kg': {variable},", f"'{output}_{quantity}_{role}_Nm_kg': np.full(NUM_POINTS, np.nan),")
        rows.append(f"        'source_grf_global_y_{role}_N': resample(grf_df[f'fp_{{{role}}}_force_y'].values[start_idx:end_idx + 1]),")
    source = once(source, "        'subject': f\"GT25D_{subject_id}\",", '\n'.join(rows) + '\n' + "        'subject': f\"GT25D_{subject_id}\",")
    source = once(source, '    task_info_str = json.dumps(info, sort_keys=True, allow_nan=False)',
                  '    info.update(' + repr(METADATA) + ')\n    task_info_str = json.dumps(info, sort_keys=True, allow_nan=False)')
    source = once(source, "'weight_basis': 'source_model_including_worn_exo'", "'weight_basis': 'participant_without_exoskeleton',\n                                   'mass_with_worn_exo_kg': SUBJECT_MASS.get(subject_id, {}).get('with_exo'),\n                                   'mass_source_readme_sha256': " + repr(README_SHA))
    funcs = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
    a, b = funcs(before), funcs(ast.parse(source))
    if a.keys() != b.keys() or {k for k in a if a[k] != b[k]} != {'get_subject_mass', 'process_stride'}:
        raise ValueError('Unexpected numerical function changes')
    return source


def patch_audit(source):
    source = once(source, "result[f'{output}_moment_{role}_Nm_kg']=resample(read('moment_filt',f'{source}_{side}_moment'))*sign", "result[f'{output}_moment_{role}_Nm_kg']=missing\n            result[f'source_{source}_moment_{role}_Nm_kg']=resample(read('moment_filt',f'{source}_{side}_moment'))")
    source = once(source, "result[f'{output}_biological_moment_{role}_Nm_kg']=missing if bio is None else resample(bio)*sign", "result[f'{output}_biological_moment_{role}_Nm_kg']=missing\n            result[f'source_{source}_biological_moment_{role}_Nm_kg']=missing if bio is None else resample(bio)")
    source = once(source, "result[f'{output}_assistance_moment_{role}_Nm_kg']=missing if exo is None else resample(exo)*(-1/mass)", "result[f'{output}_assistance_moment_{role}_Nm_kg']=missing\n            if source!='ankle_angle':\n                result[f'source_{source.replace(\"flexion\",\"angle\")}_torque_interaction_{role}_source_units']=missing if exo is None else resample(exo)")
    source = once(source, "        result[f'grf_vertical_{role}_BW']=", "        result[f'source_grf_global_y_{role}_N']=resample(read('grf',f'fp_{side}_force_y'))\n        result[f'grf_vertical_{role}_BW']=")
    source = once(source, r"r':\s*[\d.]+ kg\s*\|\s*([\d.]+) kg'", r"r':\s*([\d.]+) kg\s*\|\s*([\d.]+) kg'")
    source = once(source, "{'weight_kg':mass,'weight_basis':'source_model_including_worn_exo'}", "{'weight_kg':mass,'weight_basis':'participant_without_exoskeleton','mass_with_worn_exo_kg':float(match[2]),'mass_source_readme_sha256':" + repr(README_SHA) + "}")
    source = once(source, "            if any(json.loads(x)!=required_info for x in frame.task_info)", '            required_info.update(' + repr(METADATA) + ')\n            if any(json.loads(x)!=required_info for x in frame.task_info)')
    source = source.replace("'source_mass_with_exo_kg':mass", "'participant_mass_kg':mass,'source_mass_with_exo_kg':float(match[2])")
    ast.parse(source)
    return source


def prepare(base, readme, output):
    base, readme, output = (Path(p).resolve() for p in (base, readme, output))
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):
        raise ValueError('Isolated staging root required')
    parent = base/'preparation_manifest.json'
    manifest = json.loads(parent.read_text())
    if digest(readme) != README_SHA or manifest['readme']['sha256'] != README_SHA:
        raise ValueError('Unreviewed source README')
    masses = {m[0]: {'without_exo': float(m[1]), 'with_exo': float(m[2])}
              for m in re.findall(r'^(BT\d+):\s*([\d.]+) kg\s*\|\s*([\d.]+) kg', readme.read_text(), re.M)}
    data = {}
    bindings = {str(parent):digest(parent), str(readme):README_SHA, str(Path(__file__).resolve()):digest(__file__)}
    for name, sha in manifest['snapshot_code'].items():
        path = (base/'isolated_repo'/name).resolve()
        if not path.is_relative_to(base/'isolated_repo') or digest(path) != sha:
            raise ValueError('Changed v3 snapshot')
        data[Path(name)] = path.read_text(); bindings[str(path)] = sha
    tree = ast.parse(data[ADAPTER])
    declared = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUBJECT_MASS' for t in n.targets))
    if len(masses) != 8 or masses != declared:
        raise ValueError('All eight source mass pairs must match exactly')
    data[ADAPTER] = patch_converter(data[ADAPTER])
    data[NEW_AUDIT] = patch_audit(data[AUDIT])
    for name, source in data.items(): ast.parse(source, filename=str(name))
    output.mkdir(parents=True, exist_ok=False)
    written = {}
    for name, source in data.items():
        path = output/'isolated_repo'/name
        path.parent.mkdir(parents=True, exist_ok=True);path.write_text(source);path.chmod(0o444)
        written[str(name)] = digest(path)
    (output/'source_readme.txt').write_bytes(readme.read_bytes())
    result = {'status':'ankle_and_normalization_v4_prepared_not_run','scientific_approval':False,
              'parent_preparation':str(parent),'source_bindings':bindings,'snapshot_code':written,
              'readme':{'original_path':str(readme),'sha256':README_SHA},'source_mass_pairs':masses,
              'metadata':METADATA,'additional_source_aliases':source_aliases(),
              'limitations':['Source interaction units and source Nm/kg denominator are unresolved; canonical moments remain missing.',
                             'Raw source aliases preserve original sign and source normalization, with phase interpolation explicitly inherited.',
                             'No full dataset regeneration or anatomical validation. v3 remains historical ankle-only evidence.']}
    (output/'preparation_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','readme','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=prepare(a.base,a.readme,a.output)
    print(json.dumps({'status':r['status'],'snapshot_files':len(r['snapshot_code'])}))


if __name__ == '__main__':main()
