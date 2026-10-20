# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import csv,json,numpy as np,pyarrow.parquet as pq
from pathlib import Path
from scipy.io import loadmat
base=Path('/mnt/s/locomotion_data/Gtech_2023');parse=base/'Segmentation/AB01/ball_toss_1_center_parsing.mat';assert parse.stat().st_size<1024**2
intervals=loadmat(parse);t0=min(v[:,0].min() for k,v in intervals.items() if not k.startswith('_'));t1=max(v[:,1].max() for k,v in intervals.items() if not k.startswith('_'))
mappings={
 'Joint_Angle.csv':[(f'{j}_flexion_angle_ipsi_rad',c,scale) for j,c,scale in [('hip','hip_flexion_r',np.pi/180),('knee','knee_angle_r',-np.pi/180)]]+[('ankle_dorsiflexion_angle_ipsi_rad','ankle_angle_r',np.pi/180)],
 'Joint_Moments.csv':[('hip_flexion_moment_ipsi_Nm_kg','hip_flexion_r_moment',1),('knee_flexion_moment_ipsi_Nm_kg','knee_angle_r_moment',-1),('ankle_dorsiflexion_moment_ipsi_Nm_kg','ankle_angle_r_moment',1)],
 'GroundFrame_GRFs.csv':[(f'grf_{axis}_ipsi_BW',raw,1/(78.85*9.81)) for axis,raw in [('anterior','RForceX'),('vertical','RForceY_Vertical'),('lateral','RForceZ')]]}
cols=['time_s','subject','task_id','task_info','reference_leg']+[m[0] for v in mappings.values() for m in v];f=pq.ParquetFile('converted_datasets/gtech_2023_time.parquet');b=next(f.iter_batches(batch_size=8,columns=cols,row_groups=[0],use_threads=False)).to_pydict()
assert b['subject'][0]=='GT23_AB01' and b['task_id'][0]=='ball_toss' and 'variant:center' in b['task_info'][0] and b['reference_leg'][0]=='right'
target=t0+np.array(b['time_s']);errors={}
for file,mapping in mappings.items():
 rows=[]
 with (base/'RawData/AB01/CSV_Data/ball_toss_1'/file).open() as h:
  for row in csv.DictReader(h):
   t=float(row['time'])
   if t>=t0-0.005:rows.append(row)
   if t>target[-1]+0.005:break
 times=np.array([float(r['time']) for r in rows])
 for exported,raw,factor in mapping:
  expected=np.interp(target,times,[float(r[raw])*factor for r in rows]);actual=np.array(b[exported]);errors[exported]={'max_abs_error':float(np.max(abs(actual-expected))),'expected_first':float(expected[0]),'actual_first':float(actual[0])}
out={'source_parsing':str(parse),'source_csv_directory':str(base/'RawData/AB01/CSV_Data/ball_toss_1'),'match_basis':'Stored subject AB01, task_id ball_toss, variant center, right reference; unique matching local parsing name. Parse envelope22.44..34.81s and eight numeric sample comparisons support reconciliation. No immutable recording identifier in artifact, so this remains a manually matched representative source check.','t0':float(t0),'t1':float(t1),'rows_checked':8,'checks':errors}
Path('/tmp/gtech23-source-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
