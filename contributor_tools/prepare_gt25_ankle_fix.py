"""Prepare isolated README-backed GT25 ankle correction and independent audit.

Never changes active/frozen files or executes scientific conversions.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py')
README_SHA='aabd45edb66e565a5238f86e26e5c1c1b47469764f3fd611014caf742d20ab63'
METADATA={'ankle_source_positive_direction':'plantarflexion',
          'ankle_canonical_transform':'negate angle and total/biological moment; derive velocity and acceleration from corrected angle',
          'ankle_convention_readme_sha256':README_SHA,
          'ankle_convention_evidence':'GT25 README lines 68-71 and angle_filt/moment_filt/moment_filt_bio column definitions',
          'ankle_assistance_status':'unavailable; hip-knee exoskeleton, no ankle interaction column mapped'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Reviewed source shape changed: '+old[:80])
    return source.replace(old,new,1)


def aliases():
    return {f'source_ankle_plantarflexion_{quantity}_{side}_{unit}':variable
            for side in ('ipsi','contra')
            for quantity,variable,unit in [('angle',f'ankle_{side}_rad','rad'),
                ('derived_velocity',f'ankle_vel_{side}','rad_s'),('derived_acceleration',f'ankle_acc_{side}','rad_s2'),
                ('moment',f'ankle_mom_{side}','Nm_kg'),('biological_moment',f'ankle_bio_mom_{side}','Nm_kg')]}


def patch_converter(source):
    before=ast.parse(source)
    for side in ('ipsi','contra'):
        old=f'ankle_{side}_rad = resample(ankle_{side}_deg * deg2rad)'
        source=once(source,old,old.replace('resample(','resample(-',1))
        for frame,indent in [('moment_df','        '),('bio_moment_df','            ')]:
            old=indent+f"{frame}[f'ankle_angle_{{{side}}}_moment'].values[start_idx:end_idx + 1]"
            source=once(source,old,indent+'-'+old[len(indent):])
    source=once(source,'    # Ankle dorsiflexion (OpenSim: plantarflexion positive — keep as-is, dorsiflexion = negative plantarflexion)',
                '    # Source README: plantarflexion positive; negate for dorsiflexion positive.')
    source=once(source,'    task_info_str = json.dumps(info, sort_keys=True, allow_nan=False)',
                '    info.update('+repr(METADATA)+')\n    task_info_str = json.dumps(info, sort_keys=True, allow_nan=False)')
    anchor="        'ankle_dorsiflexion_angle_ipsi_rad': ankle_ipsi_rad,"
    rows='\n'.join('        '+repr(name)+': -'+variable+',' for name,variable in aliases().items())
    source=once(source,anchor,rows+'\n'+anchor)
    funcs=lambda tree:{n.name:ast.dump(n) for n in tree.body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(before),funcs(ast.parse(source))
    if a.keys()!=b.keys() or {name for name in a if a[name]!=b[name]}!={'process_stride'}:
        raise ValueError('Unexpected change outside process_stride')
    return source


def patch_audit(source):
    source=once(source,"('ankle_dorsiflexion','ankle_angle',1)","('ankle_dorsiflexion','ankle_angle',-1)")
    marker="            result[f'{output}_assistance_moment_{role}_Nm_kg']=missing if exo is None else resample(exo)*(-1/mass)"
    extra='''
            if source=='ankle_angle':
                # Source aliases are evaluated directly from source columns,
                # independently of the converter's negated canonical variables.
                raw_angle=resample(read('angle_filt',f'ankle_angle_{side}'))*np.pi/180
                raw_velocity=np.gradient(raw_angle)/dt
                result[f'source_ankle_plantarflexion_angle_{role}_rad']=raw_angle
                result[f'source_ankle_plantarflexion_derived_velocity_{role}_rad_s']=raw_velocity
                result[f'source_ankle_plantarflexion_derived_acceleration_{role}_rad_s2']=np.gradient(raw_velocity)/dt
                result[f'source_ankle_plantarflexion_moment_{role}_Nm_kg']=resample(read('moment_filt',f'ankle_angle_{side}_moment'))
                raw_bio=read('moment_filt_bio',f'ankle_angle_{side}_moment',optional=True)
                result[f'source_ankle_plantarflexion_biological_moment_{role}_Nm_kg']=missing if raw_bio is None else resample(raw_bio)
'''
    source=once(source,marker,marker+extra)
    marker="            if any(json.loads(x)!=required_info for x in frame.task_info):raise ValueError('Task/source semantics metadata differs')"
    source=once(source,marker,'            required_info.update('+repr(METADATA)+')\n'+marker)
    marker="        mass=float(match[1]);imu_dt=None"
    source=once(source,marker,
        "        if digest(readmes[0])!="+repr(README_SHA)+":raise ValueError('Ankle convention README differs')\n"+marker)
    ast.parse(source)
    return source


def prepare(base,readme,output):
    base=Path(base).resolve();readme=Path(readme).resolve();output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Isolated local output required')
    parent=base/'preparation_manifest.json';manifest=json.loads(parent.read_text());snapshot=base/'isolated_repo'
    if digest(readme)!=README_SHA or manifest['readme']['sha256']!=README_SHA:raise ValueError('Unreviewed README version')
    data={};original={str(parent):digest(parent),str(readme):digest(readme)}
    for rel,h in manifest['snapshot_code'].items():
        path=(snapshot/rel).resolve()
        if not path.is_relative_to(snapshot) or digest(path)!=h:raise ValueError('Base snapshot changed')
        data[Path(rel)]=path.read_bytes();original[str(path)]=h
    data[ADAPTER]=patch_converter(data[ADAPTER].decode()).encode()
    audit=ROOT/'contributor_tools/audit_gt25_streaming_transfer.py'
    original[str(audit)]=digest(audit)
    data[Path('contributor_tools/audit_gt25_streaming_transfer_ankle_v3.py')]=patch_audit(audit.read_text()).encode()
    for rel,raw in data.items():
        if rel.suffix=='.py':ast.parse(raw.decode(),filename=str(rel))
    for path,h in original.items():
        if digest(path)!=h:raise ValueError('Preparation input changed')
    output.mkdir(parents=True,exist_ok=False);snap=output/'isolated_repo';written={}
    for rel,raw in data.items():
        path=snap/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(0o444);written[str(rel)]=digest(path)
    (output/'source_readme.txt').write_bytes(readme.read_bytes())
    result={'status':'ankle_sign_correction_prepared_not_run','scientific_approval':False,'parent_preparation':str(parent),
            'source_bindings':original,'snapshot_code':written,'readme':{'original_path':str(readme),'sha256':README_SHA},
            'source_aliases':list(aliases()),'metadata':METADATA,
            'scope':'Both physical sides: angle, derived velocity/acceleration, net/biological moment. Segment IMU functions unchanged; unavailable ankle assistance remains NaN.',
            'limitations':'No execution or anatomical source regeneration. README-specific sign correction; unchanged power as velocity and moment both negate. Independent source audit also uses README-backed signs.'}
    (output/'preparation_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','readme','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=prepare(a.base,a.readme,a.output);print(json.dumps({'status':r['status'],'snapshot_files':len(r['snapshot_code'])}))


if __name__=='__main__':main()
