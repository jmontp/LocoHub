"""Bounded full inventory of normalized MBLUE source blocks and their clocks."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib
import json
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def blocks(value,path=()):
    while getattr(value,'shape',None)==(1,1):value=value[0,0]
    names=getattr(getattr(value,'dtype',None),'names',None)
    if not names:return
    if 'hip_flexion_l' in names or 'hip_flexion_r' in names:
        yield path,value;return
    if len(path)>8:raise ValueError('Unexpected source nesting')
    for name in names:yield from blocks(value[name],(*path,name))


def main():
    out=ROOT/'converted_datasets/reconversion_v2/mblue_source_inventory_20261021';out.mkdir(exist_ok=False)
    records=[];sources=[]
    for source in sorted(SOURCE.glob('AB*_NormalizedStrides.mat')):
        if source.stat().st_size>64*1024**2:raise MemoryError('Source exceeds 64 MiB admission')
        sources.append({'path':str(source),'sha256':digest(source),'bytes':source.stat().st_size})
        data=loadmat(source,squeeze_me=False,struct_as_record=True)['dataOut']
        for path,block in blocks(data):
            entry={'subject':source.name.split('_')[0],'source_path':'/'.join(path),'sides':{}}
            clocks={}
            for side in ['l','r']:
                hip=block['hip_flexion_'+side] if 'hip_flexion_'+side in block.dtype.names else np.empty((0,0))
                cycles=hip.shape[1] if hip.ndim==2 else 1 if hip.size else 0
                clock=block['time_'+side] if 'time_'+side in block.dtype.names else np.empty((0,0))
                clocks[side]=clock;valid=0;nonuniform=0
                for i in range(cycles):
                    t=clock[:,i] if clock.ndim==2 and i<clock.shape[1] else clock if clock.ndim==1 and i==0 else []
                    if len(t)<2 or not np.isfinite(t).all() or not (np.diff(t)>0).all():continue
                    valid+=1
                    if not np.allclose(t,np.linspace(t[0],t[-1],len(t)),rtol=0,atol=1e-10):nonuniform+=1
                entry['sides'][side]={'cycles':cycles,'valid_clocks':valid,'nonuniform_clocks':nonuniform,'clock_shape':list(clock.shape),'hip_shape':list(hip.shape)}
            entry['bilateral_clocks_exactly_equal']=bool(np.array_equal(clocks['l'],clocks['r'],equal_nan=True))
            entry['signal_fields']=list(block.dtype.names);records.append(entry)
        del data
    report={'sources':sources,'blocks':records,'scientific_approval':False,'probe_sha256':digest(Path(__file__)),
        'limitations':['Inventory and clock structure only; source measurement conventions and task segmentation not approved',
            'Empty blocks and unequal bilateral clocks require explicit treatment in reconstruction']}
    (out/'source_inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'subjects':len(sources),'blocks':len(records),'side_cycles':sum(v['cycles'] for r in records for v in r['sides'].values()),
        'invalid_or_missing_clocks':sum(v['cycles']-v['valid_clocks'] for r in records for v in r['sides'].values()),
        'nonuniform_clocks':sum(v['nonuniform_clocks'] for r in records for v in r['sides'].values()),
        'bilateral_blocks_with_unequal_clocks':[r['subject']+':'+r['source_path'] for r in records if ('/STS/' in r['source_path'] or r['source_path'].endswith('/crouch')) and not r['bilateral_clocks_exactly_equal']]}))


if __name__=='__main__':main()
