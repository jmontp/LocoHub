"""Metadata/header-only accounting for all192 GT25 currently excluded records.

No numeric CSV rows, source segmentation, conversion, or source hash scans.
"""
import argparse,collections,csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'converted_datasets/reconversion_v2'
SOURCE=Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify(name):
 match=re.fullmatch(r'(ball_toss|cutting|start_stop)_(\d+)_(0task|4t4s|baseline)(?:_(.*))?_on',name)
 if not match:raise ValueError('Unknown excluded source name: '+name)
 family,trial,model,variant=match.groups();info={'source_task':family,'source_trial_number':int(trial),'source_model_condition':model,'source_exo_state':'on','source_variant':variant,'canonical_task':None}
 if family=='ball_toss':
  if variant not in ('center','left','right'):raise ValueError('Unknown ball toss variant')
  info.update(source_protocol_load_lb=15,source_description='Tossing/catching medicine ball '+('forwards' if variant=='center' else 'to the '+variant),readme_lines=[83,86])
 elif family=='cutting':
  if variant not in ('left-fast','left-slow','right-fast','right-slow'):raise ValueError('Unknown cutting variant')
  side,speed=variant.split('-');info.update(source_nominal_turn_deg=90,source_turn_direction=side,source_approach_description='fast running' if speed=='fast' else 'jogging',readme_lines=[88,92])
 else:
  if variant is not None:raise ValueError('Unknown start-stop variant')
  info.update(source_description='Starting and stopping walking on overground force plates',readme_lines=[112,112])
 return info


def units(kind,column):
 if column=='time':return {'source_unit':'s','status':'documented_source_unit'}
 value=None;context=None
 if kind in ('angle','angle_filt'):value='deg'
 elif kind in ('moment','moment_filt','moment_filt_bio'):value='Nm/kg';context='Publisher label retained; mass denominator unresolved, no renormalization.'
 elif kind.startswith('power'):value='W/kg';context='Publisher label retained; mass denominator unresolved, no renormalization.'
 elif kind=='velocity':value='deg/s'
 elif kind=='activity_flag':value='boolean'
 elif kind in ('grf','insole_sim'):
  if '_force_' in column:value='N'
  elif '_cop_' in column:value='m'
 elif kind in ('exo','exo_sim','imu_sim'):
  if '_torque_interaction' in column:context='Interaction torque unit not explicitly listed in README; retain unknown.'
  elif '_torque_estimated' in column:value='Nm/kg';context='Publisher label retained; mass denominator unresolved.'
  elif '_torque_desired' in column or '_torque_measured' in column:value='Nm'
  elif '_accel_' in column:value='m/s2'
  elif '_gyro_' in column or '_velocity' in column:value='deg/s'
  elif '_force_' in column:value='N'
  elif '_cop_' in column:value='unitless' if kind=='exo' else 'm'
  elif re.fullmatch(r'(hip|knee)_angle_[lr]',column):value='deg'
 return {'source_unit':value,'status':'documented_source_unit' if value else 'unit_unassessed','limitation':context}


def plan(output):
 inventory=BASE/'gt25_full_20261021/inventory.json';replacement=BASE/'gt25_ankle_pilot_handoff_v3_20261021/full_batch_replacement_preparation.json';readme=SOURCE/'readme.txt'
 original=json.loads(inventory.read_text());review=json.loads(replacement.read_text());records=[r for r in review['records'] if r['canonical_task'] is None]
 ids=lambda rows:{(r['subject'],r['recording']) for r in rows}
 if len(original)!=676 or ids(original)!=ids(review['records']) or len(records)!=192 or len(ids(records))!=192:raise ValueError('Exact676/192 membership mismatch')
 profiles={};matrix=[]
 for record in records:
  subject,name=record['subject'],record['recording'];info=classify(name);folder=SOURCE/'Parsed'/subject/name;files=[]
  for path in sorted(folder.iterdir()):
   if not path.is_file() or path.suffix!='.csv':raise ValueError('Unexpected source artifact: '+str(path))
   prefix=subject+'_'+name+'_'
   if not path.name.startswith(prefix):raise ValueError('Source identity mismatch')
   kind=path.name[len(prefix):-4]
   with path.open('rb') as stream:header=stream.readline(65537)
   if len(header)>65536 or not header.endswith(b'\n'):raise ValueError('Header admission exceeded')
   columns=next(csv.reader([header.decode('utf-8-sig').rstrip('\r\n')]))
   if len(columns)!=len(set(columns)) or not columns:raise ValueError('Duplicate/missing source headers')
   key=hashlib.sha256((kind+'\0').encode()+header).hexdigest()
   profiles.setdefault(key,{'source_kind':kind,'header_sha256':hashlib.sha256(header).hexdigest(),'columns':[{'source_name':c,'proposed_alias':f'source_{kind}__{c}',**units(kind,c)} for c in columns]})
   st=path.stat();files.append({'path':str(path),'kind':kind,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'header_profile':key,'has_source_time': 'time' in columns})
  matrix.append({'subject':subject,'recording':name,'source_recording_id':f'gt25:{subject}/{name}','source_metadata':info,'original_exclusion_reason':'Explicit TASK_MAPPING None for non-cyclic task; converter returns without producing observations. No evidence that raw source recording is invalid.','code_evidence':{'path':'contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py','lines':[81,84,839]},'proposed_disposition':'preserve_entire_parsed_source_recording_as_unreviewed_continuous_source_companion','observation_semantics':'Whole stored Parsed recording per source stream, including activity_flag false rows. Parsed source already removed some transitions; no claim to complete original acquisition.','canonical_task':None,'scientific_approval':False,'files':files,'all_csv_bytes':sum(f['bytes'] for f in files),'source_clocks_status':'headers_only_not_numerically_assessed','blockers':['Need independent row/clock/value preservation audit for every stream before source-companion acceptance.','No reference limb, gait cycles, phase150 grid, synthetic timestamps, or canonical moment/force/segment claims.']})
 counts=collections.Counter(r['source_metadata']['source_task'] for r in matrix)
 if counts!={'ball_toss':72,'cutting':96,'start_stop':24}:raise ValueError('Excluded category membership differs')
 result={'status':'all192_source_recording_dispositions_prepared_not_converted','scientific_approval':False,'bindings':{str(p):digest(p) for p in [inventory,replacement,readme,Path(__file__).resolve(),ROOT/'contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py']},'counts':{'records':192,'by_source_task':dict(counts),'files':sum(len(r['files']) for r in matrix),'bytes':sum(r['all_csv_bytes'] for r in matrix)},'header_profiles':profiles,'records':matrix,'read_limits':'Only directory stats and≤64KiBfirstline perCSV; no numeric rows loaded. SourceSHA256 to acquire under eventual serial execution, not claimed here.','proposed_storage':'Keep original source streams separate; lossless byte-preserving compressedCSV plus optional typed raw-alias Parquet. No common-grid joins, interpolation, activity filtering or normalization.','acceptance':'All192unique identities and all inventoried streams accounted; sourceSHA before/after, decompressed bytesSHA equality, native row order/time tokens/null tokens and per-column values compared independently; schema/clock gaps reported, not invented or discarded. This is source preservation, not canonical gait release approval.'}
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x') as f:json.dump(result,f,indent=2)
 return result['counts']


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(plan(a.output)))
if __name__=='__main__':main()
