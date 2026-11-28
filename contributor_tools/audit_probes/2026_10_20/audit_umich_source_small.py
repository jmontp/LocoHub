# Archived read-only investigation probe, 2026-10-20.
# Run from repository root with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# and nice -n 19 ionice -c 3. Local source paths and file versions are required.
# Results are scoped samples, not release approval.
import resource,json
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import h5py,numpy as np,pyarrow.parquet as pq
with h5py.File('contributor_tools/conversion_scripts/Umich_2021/Streaming.mat') as f:
 t=f['Streaming/AB01/Tread/d10']; print('events',[(k,getattr(v,'shape','group')) for k,v in t['events'].items()]); print('RHS',t['events/RHS'][:,:5]); print('RStrideTime',t['events/RStrideTime'][:,:5]);print('cutPoints',t['events/cutPoints'][:,:3]); print('RHipAngles',t['jointAngles/RHipAngles'].shape)
with h5py.File('contributor_tools/conversion_scripts/Umich_2021/Normalized.mat') as f:
 t=f['Normalized/AB01/SitStand/ss/sit2stand'];print('normalized sts',[(k,getattr(v,'shape','group')) for k,v in t['jointAngles'].items()]);print('normalized first hip',t['jointAngles/HipAngles'][0,0,:5])
f=pq.ParquetFile('converted_datasets/umich_2021_phase_raw.parquet');cols=['subject','task','step','time_s','hip_flexion_angle_ipsi_rad','hip_flexion_angle_contra_rad','task_info']
# Only row group2 projected columns (~1MiB); selected 150 rows at known task start.
offset=164700-sum(f.metadata.row_group(i).num_rows for i in range(2));d=f.read_row_group(2,columns=cols,use_threads=False).slice(offset,150).to_pydict();print('raw sts first',{k:[v[0],v[-1]] for k,v in d.items()});print('bilateral_diff',np.max(np.abs(np.array(d[cols[4]])-d[cols[5]])))
