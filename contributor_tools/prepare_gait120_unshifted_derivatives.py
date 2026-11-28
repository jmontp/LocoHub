"""Prepare isolated Gait120 derivative policy correction; never edit live code.

Nineteen derivative calls must explicitly disable repair for circularly shifted
signals because this adapter does not shift source sample order. This does not
remove genuine source anomalies, or approve planar estimates anatomically.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py'
SOURCE_SHA='950579287b8c34cc97ae7e7e9372aacb924e7709e73287b943164b756804f55e'
POLICY={'derivative_method':'physical_duration_uniform_endpoint_and_centered_finite_differences','automatic_discontinuity_repair':False,'derivative_source_order':'unshifted source; source anomalies retained, not silently spline-repaired'}


def patch(source):
    anchor='discontinuity_idx=disc_idx)'
    if source.count(anchor)!=19:raise ValueError('Expected exactly19 reviewed derivative calls')
    modified=source.replace(anchor,'discontinuity_idx=disc_idx, detect_discontinuity=False)')
    anchor="    task_info_str = json.dumps({\n"
    if modified.count(anchor)!=1:raise ValueError('Reviewed task metadata insertion absent')
    added=''.join('        '+repr(k)+': '+repr(v)+',\n' for k,v in POLICY.items());modified=modified.replace(anchor,anchor+added)
    before=ast.parse(source);after=ast.parse(modified);normal=copy.deepcopy(after);calls=0;metadata=0
    for node in ast.walk(normal):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('compute_velocity_from_shifted_angle','compute_acceleration_from_velocity'):
            found=[kw for kw in node.keywords if kw.arg=='detect_discontinuity']
            if found:
                if len(found)!=1 or not isinstance(found[0].value,ast.Constant) or found[0].value.value is not False:raise ValueError('Unexpected derivative keyword')
                calls+=1;node.keywords=[kw for kw in node.keywords if kw.arg!='detect_discontinuity']
        if isinstance(node,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='derivative_method' for k in node.keys):
            pairs=[]
            for key,value in zip(node.keys,node.values):
                if isinstance(key,ast.Constant) and key.value in POLICY:
                    if ast.literal_eval(value)!=POLICY[key.value]:raise ValueError('Unexpected metadata value')
                    metadata+=1
                else:pairs.append((key,value))
            node.keys=[k for k,v in pairs];node.values=[v for k,v in pairs]
    if calls!=19 or metadata!=3 or ast.dump(before,include_attributes=False)!=ast.dump(normal,include_attributes=False):raise ValueError('Unrelated producer AST changed')
    return modified


def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():raise ValueError('Fresh isolated root required')
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Original converter changed')
    modified=patch(raw.decode());target=output/'isolated_repo'/SOURCE.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=False);target.write_text(modified)
    bindings={str(SOURCE):SOURCE_SHA}
    for p in [Path(__file__).resolve(),ROOT/'contributor_tools/audit_gait120_extended_sources.py',ROOT/'contributor_tools/withhold_gait120_planar_segments.py',*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]:bindings[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    report={'status':'isolated_derivative_policy_prepared_not_executed','scientific_approval':False,'bindings':bindings,'patched_converter':str(target),'patched_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'ast_equivalence':'Original AST restored exactly after removing19 explicit detect_discontinuity=False keywords and3 metadata fields.','source_only_segment_successor':'contributor_tools/withhold_gait120_planar_segments.py','scope':'All6882 records remain required; no pilot/full run launched. Root must bind a separate execution snapshot before use.','required_readback':'Independent raw resampled angles -> scalar finite differences using actual duration. All19 derivative outputs require comparison; planar segment estimates remain source-only, not anatomical approval.','policy':POLICY}
    (output/'proposal_manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.output_root),indent=2))
if __name__=='__main__':main()
