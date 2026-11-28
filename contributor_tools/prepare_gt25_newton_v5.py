"""Prepare immutable GT25 v5 explicit-Newton event thresholds, without data jobs.

Only isolated GT25-used gait/transfer branches change; shared originals, v4,
normalization/sign transforms, source aliases and jump behavior are preserved.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.prepare_gt25_ankle_fix import README_SHA,ADAPTER,digest,once
COMMON=Path('contributor_tools/common/stride_segmentation.py')
TRANSFER_AUDIT=Path('contributor_tools/audit_gt25_streaming_transfer_newton_v5.py')
REGULAR_AUDIT=Path('contributor_tools/audit_gt25_regular_source_newton_v5.py')
STREAM=Path('contributor_tools/gt25_streaming_transfers_newton_v5.py')
RUNNER=Path('contributor_tools/run_gt25_streaming_transfer_newton_v5.py')


def functions(source):return {n.name:ast.dump(n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}


def patch_common(source):
    before=functions(source)
    source=once(source,'threshold = config.grf_threshold_BW if np.nanmax(grf_values) < 10 else config.grf_threshold_N',"threshold = config.grf_threshold_N  # GT25 README declares source GRF in Newtons.\n    if config.grf_vertical_col != 'grf_vertical_ipsi_N' or threshold != 20.:\n        raise ValueError('Isolated GT25 gait requires explicit N column and20N threshold')")
    old='''    is_bw_units = np.nanmax(total_grf) < 10
    sitting_thresh = config.sitting_grf_threshold_BW if is_bw_units else config.sitting_grf_threshold_N
    standing_thresh = config.standing_grf_threshold_BW if is_bw_units else config.standing_grf_threshold_N'''
    new='''    sitting_thresh = config.sitting_grf_threshold_N
    standing_thresh = config.standing_grf_threshold_N
    if (config.grf_vertical_ipsi_col, config.grf_vertical_contra_col) != ('grf_vertical_ipsi_N','grf_vertical_contra_N') or (sitting_thresh,standing_thresh)!=(400.,600.):
        raise ValueError('Isolated GT25 transfer requires explicit N columns and400/600N thresholds')'''
    source=once(source,old,new);after=functions(source)
    if before.keys()!=after.keys() or {k for k in before if before[k]!=after[k]}!={'segment_gait_cycles','segment_sit_stand_transfers'}:raise ValueError('Unexpected shared helper changes')
    return source


def patch_stream(source):
    source=once(source,'sitting=config.sitting_grf_threshold_BW if max_grf<10 else config.sitting_grf_threshold_N','sitting=config.sitting_grf_threshold_N')
    source=once(source,'standing=config.standing_grf_threshold_BW if max_grf<10 else config.standing_grf_threshold_N',"standing=config.standing_grf_threshold_N\n        if (sitting,standing)!=(400.,600.):raise ValueError('GT25 source uses Newton thresholds400/600')")
    return source


def patch_transfer_audit(source):
    return once(source,'lower,upper=(.5,.8) if maximum is not None and maximum<10 else (400.,600.)','lower,upper=400.,600.  # Source README GRF in N, irrespective of amplitude.')


def patch_regular_audit(source,audit_sha,common_sha):
    source=once(source,"AUDIT_SHA='800dcf9af5f99269da9ac461ae40f564b2193b1f52459d860654637310379138'",'AUDIT_SHA='+repr(audit_sha))
    source=source.replace('audit_gt25_streaming_transfer_normalization_v4.py',TRANSFER_AUDIT.name)
    source=once(source,'threshold=.05 if maximum<10 else 20.','threshold=20.  # Independently use source Newton units, never infer from amplitude.')
    source=once(source,"'legacy_low_amplitude_BW_heuristic_triggered':maximum<10","'legacy_low_amplitude_BW_heuristic_triggered':False,'low_force_below10N':maximum<10,'force_units':'N'")
    marker="    bindings.update({x['path']:x['sha256'] for x in manifest['converter_code']})"
    source=once(source,marker,"    helpers=[x for x in manifest['converter_code'] if Path(x['path']).name=='stride_segmentation.py']\n    if len(helpers)!=1 or helpers[0]['sha256']!="+repr(common_sha)+":raise ValueError('Manifest does not bind explicitNewton v5 helper')\n"+marker)
    return source


def prepare(base,readme,output):
    base,readme,output=[Path(p).resolve() for p in (base,readme,output)]
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Isolated output required')
    parent=base/'preparation_manifest.json';manifest=json.loads(parent.read_text())
    if manifest['status']!='ankle_and_normalization_v4_prepared_not_run' or digest(readme)!=README_SHA or manifest['readme']['sha256']!=README_SHA:raise ValueError('Reviewed v4 parent and exact README required')
    data={};bindings={str(parent):digest(parent),str(readme):README_SHA,str(Path(__file__).resolve()):digest(__file__),str(ROOT/'contributor_tools/prepare_gt25_ankle_fix.py'):digest(ROOT/'contributor_tools/prepare_gt25_ankle_fix.py')}
    for name,sha in manifest['snapshot_code'].items():
        path=(base/'isolated_repo'/name).resolve()
        if not path.is_relative_to(base/'isolated_repo') or digest(path)!=sha:raise ValueError('Changed parent snapshot')
        data[Path(name)]=path.read_text();bindings[str(path)]=sha
    original_converter=data[ADAPTER]
    data[COMMON]=patch_common(data[COMMON])
    data[TRANSFER_AUDIT]=patch_transfer_audit(data[Path('contributor_tools/audit_gt25_streaming_transfer_normalization_v4.py')])
    for name in ('gt25_streaming_transfers.py','run_gt25_streaming_transfer_pilot.py','audit_gt25_regular_source_v4.py'):
        path=ROOT/'contributor_tools'/name;bindings[str(path)]=digest(path)
    data[STREAM]=patch_stream((ROOT/'contributor_tools/gt25_streaming_transfers.py').read_text())
    runner=(ROOT/'contributor_tools/run_gt25_streaming_transfer_pilot.py').read_text()
    runner=once(runner,'ROOT=Path(__file__).resolve().parents[1]','ROOT=Path('+repr(str(ROOT))+')')
    runner=once(runner,'from contributor_tools import gt25_streaming_transfers as segmentation',"_segpath=Path(__file__).resolve().with_name('"+STREAM.name+"')\n_segspec=importlib.util.spec_from_file_location('gt25_newton_streaming',_segpath)\nsegmentation=importlib.util.module_from_spec(_segspec);_segspec.loader.exec_module(segmentation)")
    data[RUNNER]=runner
    textsha=lambda text:hashlib.sha256(text.encode()).hexdigest()
    data[REGULAR_AUDIT]=patch_regular_audit((ROOT/'contributor_tools/audit_gt25_regular_source_v4.py').read_text(),textsha(data[TRANSFER_AUDIT]),textsha(data[COMMON]))
    # Original ROOT imports reusable reviewed guards; actual converter/helper binding
    # is always the explicit snapshot supplied to each audit invocation.
    data[REGULAR_AUDIT]=once(data[REGULAR_AUDIT],'ROOT=Path(__file__).resolve().parents[1]','ROOT=Path('+repr(str(ROOT))+')')
    if data[ADAPTER]!=original_converter:raise ValueError('Unrelated scientific transforms changed')
    for name,text in data.items():ast.parse(text,filename=str(name))
    output.mkdir(parents=True,exist_ok=False);written={}
    for name,text in data.items():
        path=output/'isolated_repo'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);path.chmod(0o444);written[str(name)]=digest(path)
    (output/'source_readme.txt').write_bytes(readme.read_bytes())
    result={'status':'explicit_newton_v5_prepared_not_run','scientific_approval':False,'parent_preparation':str(parent),'source_bindings':bindings,'snapshot_code':written,'readme':{'original_path':str(readme),'sha256':README_SHA},'inherited_normalization_metadata':manifest['metadata'],'source_mass_pairs':manifest['source_mass_pairs'],'additional_source_aliases':manifest['additional_source_aliases'],'changed_parent_files':[str(COMMON)],'new_files':[str(x) for x in (STREAM,RUNNER,TRANSFER_AUDIT,REGULAR_AUDIT)],'unchanged_converter_sha256':written[str(ADAPTER)],'force_units':'N per exact source README grf.csv/force column definitions','thresholds_N':{'gait':20,'sitting':400,'standing':600},'limits':['No scientific data converted; real walking/shuffle/transfer pilots required before full-run successor.','Source moment denominator, actual interaction torque units and global segment orientation remain unresolved.','Jump and other unused segmentation branches unchanged; isolated helper restricted toGT25Ncolumn configs.','v4 sources/plans immutable and historical.']}
    (output/'preparation_manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('base','readme','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();r=prepare(a.base,a.readme,a.output);print(json.dumps({'status':r['status'],'snapshot_files':len(r['snapshot_code'])}))
if __name__=='__main__':main()
