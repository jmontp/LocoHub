"""Account for native ramp plate contacts against an existing converted recording.

Diagnostic only. Candidate errors identify exported channels, never choose a
physical force sign. Nearest-foot geometry is supporting contact evidence.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,hashlib,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import numpy as np
import pyarrow.parquet as pq


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('converted',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    source=json.loads((a.source/'source_comparison.json').read_text())
    assert source['native_status']['status']=='completed' and source['native_status']['exit_code']==0
    for t in source['tables']:assert digest(a.source/t['file'])==t['sha256']
    fp=pq.ParquetFile(a.source/'source_fp_data.parquet').read(use_threads=False).to_pandas(use_threads=False)
    markers=pq.ParquetFile(a.source/'source_markers_data.parquet').read(use_threads=False).to_pandas(use_threads=False)
    ft=fp.Header.to_numpy();mt=markers.Header.to_numpy();assert np.all(np.diff(ft)>0) and np.all(np.diff(mt)>0)
    plates=[c[:-3] for c in fp if c.endswith('_vy')];records=[]
    for b in pq.ParquetFile(a.converted).iter_batches(batch_size=150,use_threads=False):
        d=b.to_pandas(use_threads=False);r=d.iloc[0];assert len(d)==150 and d.observation_id.nunique()==1
        pieces=r.source_recording_id.split(':',1)[1].split('/');assert any('/'.join(pieces[:-1]+['fp',pieces[-1]]) in x for x in source['inputs']['sources'])
        t=np.linspace(r.source_start_time_s,r.source_end_time_s,150);assert t[0]>=max(ft[0],mt[0]) and t[-1]<=min(ft[-1],mt[-1])
        mass=json.loads(r.subject_metadata)['weight_kg'];assert mass>0
        feet={side:np.column_stack([sum(np.interp(t,mt,markers[f'{side}_{name}_{axis}']) for name in ('Heel','Toe_Tip'))/2000 for axis in 'xyz']) for side in ('L','R')}
        forward=np.column_stack([sum(np.interp(t,mt,markers[f'{side}_ASIS_{axis}'])-np.interp(t,mt,markers[f'{side}_PSIS_{axis}']) for side in ('L','R'))/2 for axis in 'xyz'])
        item={'observation_id':r.observation_id,'task':r.task,'reference_side':r.reference_side,'start_s':float(t[0]),'end_s':float(t[-1]),'median_anterior_pelvis_xyz':np.median(forward/np.linalg.norm(forward,axis=1)[:,None],axis=0).tolist(),'plates':[]}
        for plate in plates:
            force=np.interp(t,ft,fp[plate+'_vy'])/(mass*9.81);cop=np.column_stack([np.interp(t,ft,fp[plate+'_p'+axis]) for axis in 'xyz']);contact=force>=.2
            dist={side:np.linalg.norm(cop-feet[side],axis=1) for side in feet}
            rec={'plate':plate,'contact_samples':int(contact.sum()),'legs':{}}
            for side in ('ipsi','contra'):
                leg=r.reference_side if side=='ipsi' else ('right' if r.reference_side=='left' else 'left');key=leg[0].upper();opposite='L' if key=='R' else 'R'
                near=contact&np.isfinite(dist[key])&np.isfinite(dist[opposite])&(dist[key]<dist[opposite])
                output=d[f'grf_vertical_{side}_BW'].to_numpy();finite=np.isfinite(output)&np.isfinite(force)
                rec['legs'][side]={'anatomical_leg':leg,'contact_samples_nearer_this_foot':int(near.sum()),'nearer_foot_contact_with_missing_export':int((near&~np.isfinite(output)).sum()),'export_finite_samples':int(np.isfinite(output).sum()),'max_vertical_channel_difference_BW':float(np.max(abs(force[finite]-output[finite]))) if finite.any() else None}
            direction_z = item['median_anterior_pelvis_xyz'][2]
            # For these straight portions, report both candidate signs and the
            # independently measured anterior direction, never fit to moments.
            rec['anterior_direction_z'] = direction_z
            rec['anterior_source_sign_errors_BW'] = {}
            shear=np.interp(t,ft,fp[plate+'_vz'])/(mass*9.81)
            for side in ('ipsi','contra'):
                output=d[f'grf_anterior_{side}_BW'].to_numpy();valid=np.isfinite(output)&np.isfinite(shear)
                rec['anterior_source_sign_errors_BW'][side]={label:float(np.max(abs(output[valid]-sign*shear[valid]))) if valid.any() else None for label,sign in [('positive',1),('negative',-1)]}
            item['plates'].append(rec)
        records.append(item)
    report={'status':'source_contact_accounting','scientific_approval':False,'records':records,'source_readback_sha256':digest(a.source/'source_comparison.json'),'converted_sha256':digest(a.converted),'probe_sha256':digest(Path(__file__)),'limitations':['Two-foot proximity is supporting evidence, not a force-plate contact ground truth','Checks exported cycles only; omitted source cycles remain a separate coverage issue','No sign chosen by moment or waveform fit']}
    a.output.mkdir(parents=True,exist_ok=False);(a.output/'source_contacts.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({'records':len(records),'output':str(a.output)}))


if __name__=='__main__':main()
