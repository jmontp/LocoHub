# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource,json
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import h5py,numpy as np,pyarrow.parquet as pq
with h5py.File('contributor_tools/conversion_scripts/Umich_2021/Normalized.mat') as f:
 t=f['Normalized/AB01/SitStand/ss/sit2stand'];print('keys',list(t.keys()));print('events',[(k,getattr(v,'shape',None)) for k,v in t.get('events',{}).items()]);
 if 'events' in t and 'StrideDetails' in t['events']:print('StrideDetails',t['events/StrideDetails'][...].tolist())
with h5py.File('contributor_tools/conversion_scripts/Umich_2021/Streaming.mat') as f:
 t=f['Streaming/AB01/Tread/d10'];a=t['jointAngles/RHipAngles'][0,1857:1964]*np.pi/180
 p=pq.ParquetFile('converted_datasets/umich_2021_phase_raw.parquet');d=next(p.iter_batches(batch_size=150,columns=['hip_flexion_angle_ipsi_rad','grf_vertical_ipsi_BW'],use_threads=False)).to_pydict();expected=np.interp(np.linspace(0,len(a)-1,150),np.arange(len(a)),a);print('first_raw_hip_vs_source_max_error',float(max(abs(expected-d['hip_flexion_angle_ipsi_rad']))));print('force_shape',t['forceplates/RForce'].shape,'force_slab_minmax',float(t['forceplates/RForce'][2,18570:19640].min()),float(t['forceplates/RForce'][2,18570:19640].max()),'outputBWminmax',min(d['grf_vertical_ipsi_BW']),max(d['grf_vertical_ipsi_BW']))
p=pq.ParquetFile('converted_datasets/umich_2021_phase_clean.parquet')
for i in range(3):
 d=next(p.iter_batches(row_groups=[i],batch_size=450,columns=['task','step','hip_flexion_angle_ipsi_rad','thigh_sagittal_angle_ipsi_rad','pelvis_sagittal_angle_rad','time_s','hip_flexion_velocity_ipsi_rad_s'],use_threads=False)).to_pydict()
 for j in range(3):
  h=np.array(d['hip_flexion_angle_ipsi_rad'][j*150:(j+1)*150]);th=np.array(d['thigh_sagittal_angle_ipsi_rad'][j*150:(j+1)*150]);pe=np.array(d['pelvis_sagittal_angle_rad'][j*150:(j+1)*150]);time=np.array(d['time_s'][j*150:(j+1)*150]);v=np.array(d['hip_flexion_velocity_ipsi_rad_s'][j*150:(j+1)*150]);grad=np.gradient(h,time)
  print('clean_sample',i,j,'task',d['task'][j*150],'chain_residual',max(abs(h-(th-pe))),'velocity_ratio_median',np.nanmedian(v[1:-1]/grad[1:-1]))
