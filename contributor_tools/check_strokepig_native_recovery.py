"""Receipt-only exact StrokePiG walking scope, with calibration inventory retained."""
import hashlib
import json
from pathlib import Path


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()


def scope(inventory,census):
 rows=inventory['c3d_sources']
 if any(r['kind'] not in ('walking','calibration') for r in rows):raise ValueError('Unknown source role')
 names=[r['source_recording'] for r in rows]
 if len(names)!=200 or len(set(names))!=200:raise ValueError('Expected200unique C3D files')
 walking={r['source_recording'] for r in rows if r['kind']=='walking'}
 calibration={r['source_recording'] for r in rows if r['kind']!='walking'}
 if len(walking)!=151 or len(calibration)!=49:raise ValueError('Expected151walking and49calibration')
 records=census['records'];actual=[r['source_recording'] for r in records]
 if census['status']!='source_census_complete_unreviewed' or len(actual)!=151 or len(set(actual))!=151 or set(actual)!=walking or any(r['status']!='inventoried' for r in records):raise ValueError('Census walking scope differs')
 return sorted(walking),sorted(calibration)


def record_links(record,metadata,comparison,source,output_hash,probe_hash,converter_hash):
 if comparison.get('status')!='exact_source_companion_readback' or comparison.get('scientific_approval') is not False:raise ValueError('Native readback not completed/unreviewed')
 if comparison.get('rows')!=record['rows'] or metadata.get('rows')!=record['rows'] or record['rows']<=0:raise ValueError('Native row counts differ')
 if comparison.get('source_sha256')!=source['sha256'] or metadata.get('source_sha256')!=source['sha256']:raise ValueError('Native source hashes differ')
 if comparison.get('output_sha256')!=output_hash or metadata.get('output_sha256')!=output_hash or record['output_sha256']!=output_hash:raise ValueError('Native output hashes differ')
 if comparison.get('probe_sha256')!=probe_hash or metadata.get('converter_sha256')!=converter_hash:raise ValueError('Producing/checking code differs')
 count=comparison.get('components_and_residuals_checked')
 if type(count) is not int or count<=0 or count!=record['components_checked']:raise ValueError('Native checked component count differs')


def check(plan_path,output):
 plan_path=Path(plan_path);plan=json.loads(plan_path.read_text())
 for p,h in plan['bindings'].items():
  if digest(p)!=h:raise ValueError('Recovery input changed: '+p)
 census=json.loads(Path(plan['census']).read_text());inventory=json.loads(Path(plan['inventory']).read_text());walking,calibration=scope(inventory,census)
 root=Path(plan['output_root']);batch_path=root/'batch_status.json';batch=json.loads(batch_path.read_text())
 if batch.get('status')!='all_native_companions_readback_unreviewed' or batch.get('scientific_approval') is not False or batch.get('planned_recordings')!=151:raise ValueError('Full native batch incomplete')
 records=batch['records'];names=[r['source_recording'] for r in records]
 if len(names)!=151 or len(set(names))!=151 or set(names)!=set(walking):raise ValueError('Completed native record set differs')
 hashes={str(batch_path):digest(batch_path)};byname={r['source_recording']:r for r in census['records']}
 for r in records:
  folder=root/'recordings'/r['source_recording'];comparison=folder/'source_comparison.json';metadata=folder/'source_metadata.json';parquet=folder/'source_time.parquet'
  c=json.loads(comparison.read_text());m=json.loads(metadata.read_text())
  if digest(comparison)!=r['readback_sha256']:raise ValueError('Native readback receipt hash differs')
  root_code=Path(__file__).resolve().parents[1]
  probe=plan['bindings'][str(root_code/'contributor_tools/audit_probes/2026_10_20/check_strokepig_native_readback.py')]
  converter=plan['bindings'][str(root_code/'contributor_tools/reconvert_strokepig_native.py')]
  record_links(r,m,c,byname[r['source_recording']],digest(parquet),probe,converter)
  hashes.update({str(comparison):digest(comparison),str(metadata):digest(metadata),str(parquet):r['output_sha256']})
 for p,h in plan['bindings'].items():
  if digest(p)!=h:raise ValueError('Recovery input changed during check')
 result={'status':'all151_walking_native_companions_accounted_unreviewed','scientific_approval':False,'walking_recordings':walking,'calibration_recordings_not_exported':calibration,'bindings':plan['bindings'],'plan_sha256':digest(plan_path),'output_sha256':hashes,'limitation':'49calibration recordings remain source inventory, not walking exports. Native companions preserve source component conventions; no canonical anatomical phase approval.'}
 with Path(output).open('x') as f:json.dump(result,f,indent=2)
 return result
