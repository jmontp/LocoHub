"""Independent all-recording readback of UM21 running events and source components."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import json
from pathlib import Path
import sys
import numpy as np
import h5py
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.interpolate import interp1d
pa.set_cpu_count(1);pa.set_io_thread_count(1)
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def main():
    base=ROOT/'converted_datasets/reconversion_v2/um21_running_full_20261020'
    summary=json.loads((base/'conversion_summary.json').read_text())
    assert summary['status']=='complete_running_source_channels_unreviewed'
    source=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat'
    assert digest(source)==summary['source_sha256']
    checks=[];errors={};total_values=0
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as f:
        expected_trials={(s,c) for s in f['Streaming'] if 'Run' in f['Streaming'][s] for c in f['Streaming'][s]['Run']}
        assert {(r['subject'],r['condition']) for r in summary['recordings']}==expected_trials
        for record in summary['recordings']:
            subject,condition=record['subject'],record['condition'];trial=f[f'Streaming/{subject}/Run/{condition}']
            for path,value in record['outputs'].items():assert digest(base/path)==value
            expected=set()
            for side,event in [('left','LHS'),('right','RHS')]:
                hs=trial['events'][event][...].reshape(-1)
                expected.update((side,int(a),int(b)) for a,b in zip(hs[:-1],hs[1:]))
            observed=set();rows=0
            for batch in pq.ParquetFile(base/subject/condition/'phase.parquet').iter_batches(batch_size=150,use_threads=False):
                frame=batch.to_pandas(use_threads=False)
                assert len(frame)==150 and frame.observation_id.nunique()==1 and frame.task.eq('run').all()
                np.testing.assert_allclose(frame.phase_ipsi,np.linspace(0,100,150),rtol=0,atol=1e-12)
                side=frame.reference_side.iloc[0]
                start=int(round(frame.source_start_time_s.iloc[0]*100))+1
                end=int(round(frame.source_end_time_s.iloc[0]*100))+1
                key=(side,start,end);assert key in expected and key not in observed;observed.add(key)
                clock=np.arange(start-1,end)/100;target=np.linspace(clock[0],clock[-1],150)
                np.testing.assert_allclose(frame.time_s,target-target[0],atol=1e-12)
                expected_columns=set()
                for group,kind,unit in [('jointAngles','joint_angle','deg'),('jointForces','joint_force','N_kg'),('jointMoments','joint_moment','Nm_kg'),('jointPowers','joint_power','W_kg')]:
                    if group not in trial:continue
                    for name,dataset in trial[group].items():
                        raw=dataset[:,start-1:end]
                        values=interp1d(clock,raw,axis=1,bounds_error=True)(target)
                        for component,expected_values in enumerate(values):
                            col=f'source_{kind}_{name.lower()}_component_{component}_{unit}';expected_columns.add(col)
                            actual=frame[col].to_numpy()
                            np.testing.assert_allclose(actual,expected_values,rtol=1e-10,atol=1e-9,equal_nan=True)
                            finite=np.isfinite(expected_values);total_values+=int(finite.sum())
                            if finite.any():errors[col]=max(errors.get(col,0),float(np.max(abs(actual[finite]-expected_values[finite]))))
                assert {c for c in frame if c.startswith('source_joint_')}==expected_columns
                for role,leg in [('ipsi',side[0].upper()),('contra','R' if side=='left' else 'L')]:
                    for joint in ['Hip','Knee']:
                        raw=trial['jointAngles'][leg+joint+'Angles'][0,start-1:end]
                        values=interp1d(clock,raw)(target)*np.pi/180
                        np.testing.assert_allclose(frame[f'{joint.lower()}_flexion_angle_{role}_rad'],values,rtol=1e-10,atol=1e-9,equal_nan=True)
                rows+=len(frame)
            assert observed==expected and rows==record['rows']
            checks.append({'subject':subject,'condition':condition,'observations':len(observed),'rows':rows})
    report={'recordings':checks,'total_rows':sum(r['rows'] for r in checks),'total_observations':sum(r['observations'] for r in checks),
        'finite_source_values_checked':total_values,'source_component_max_errors':errors,
        'source_sha256':summary['source_sha256'],'summary_sha256':digest(base/'conversion_summary.json'),
        'probe_sha256':digest(Path(__file__)),'scientific_approval':False,
        'limitations':['Original event boundaries not independently measured','Canonical kinetic frames/signs and ankle offsets remain unverified','Markers and forceplate signals not reconstructed in this pass']}
    (base/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['total_rows','total_observations','finite_source_values_checked']}))


if __name__=='__main__':main()
