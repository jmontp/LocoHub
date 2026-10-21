"""Independently check a bounded native GT21 export against original source tables."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
sys.path.insert(0,str(Path.cwd()))
from contributor_tools.common.data_contract import inspect_contract
from contributor_tools.reconvert_recording import digest
pa.set_cpu_count(1);pa.set_io_thread_count(1)
base=Path('converted_datasets/reconversion_v2/gt21_inclusive_pilot_20261020')
frame=pq.ParquetFile(base/'phase.parquet').read(use_threads=False).to_pandas(use_threads=False)
assessment=inspect_contract(frame,mode='phase');assert assessment.schema_passed,assessment.issues
angles=pd.read_csv(base/'source_ik_offset_data.csv')
moments=pd.read_csv(base/'source_id_data.csv')
events={side:pd.read_csv(base/f'source_gc{side.capitalize()}_data.csv') for side in ['left','right']}
errors={};count=0
for identity,curve in frame.groupby('observation_id',sort=False):
 assert len(curve)==150
 side=curve.reference_side.iloc[0];start=curve.source_start_time_s.iloc[0];end=curve.source_end_time_s.iloc[0]
 target=np.linspace(start,end,150);clock=events[side]
 hs=clock.loc[clock.HeelStrike.eq(0),'Header'].to_numpy()
 assert np.any(np.isclose(hs,start,rtol=0,atol=1e-9)) and np.any(np.isclose(hs,end,rtol=0,atol=1e-9))
 assert not np.any((hs>start+1e-9)&(hs<end-1e-9))
 np.testing.assert_allclose(curve.phase_ipsi,np.linspace(0,100,150))
 mass=json.loads(curve.subject_metadata.iloc[0])['weight_kg']
 for role,leg in [('ipsi','l' if side=='left' else 'r'),('contra','r' if side=='left' else 'l')]:
  for standard,source,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]:
   for kind,table,src,scale,suffix in [('angle',angles,f'{source}_{leg}',sign*np.pi/180,'rad'),('moment',moments,f'{source}_{leg}_moment',sign/mass,'Nm_kg')]:
    expected=np.interp(target,table.Header,table[src])*scale
    feature=f'{standard}_{kind}_{role}_{suffix}'
    actual=curve[feature].to_numpy()
    np.testing.assert_allclose(actual,expected,atol=1e-8,rtol=1e-8,equal_nan=True)
    errors[feature]=max(errors.get(feature,0),float(np.nanmax(abs(actual-expected))))
    if kind=='angle':
     velocity=f'{standard}_velocity_{role}_rad_s'
     expected_v=np.gradient(expected,target)
     np.testing.assert_allclose(curve[velocity],expected_v,atol=1e-7,rtol=1e-7)
 count+=1
report={'scientific_approval':False,'observations_checked':count,'schema_passed':True,
 'checks':['Unique 150-point observations','Both endpoints match consecutive source heel-strike resets','All bilateral hip/knee/ankle angle, velocity and moment samples compared with source tables'],
 'max_error_by_signal':errors,'limitations':['One subject, one levelground recording only.','Force/COP mapping, all-task coverage and exclusion accounting remain open.','Source conventions and measured mass require broader independent reconciliation.'],
 'files':{p.name:digest(p) for p in [base/'phase.parquet',base/'source_manifest.json',*sorted(base.glob('source_*.csv'))]}}
(base/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'observations':count,'max_error':max(errors.values()),'schema_passed':True}))
