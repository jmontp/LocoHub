# Read-only probe (one participant, three angle columns + moment, streamed; peak RSS printed). Run: prlimit --as=700MiB nice -n 19 ionice -c 3 python3 -W ignore THIS from the repo root.
# Prints, for the 8 GT21 AB24 recordings with the largest ankle-angle RMS difference (and 2 median ones), the range of training (x) and LocoHub (y) angles in degrees.
import sys; sys.path.insert(0,'.')
import numpy as np
from contributor_tools import compare_training_vs_locohub as c
import resource
maps=tuple(m for m in c.column_maps() if m.name in('ankle_angle','shank_angle','foot_angle','ankle_moment'))
cfg=c.Cfg()
his=c.Path(c.HIS_DIR_DEFAULT)/'gate'/c.HIS_FILES['gt21']
raw={s for s in c.list_subjects(his) if c.norm_subject(s)=='AB24'}
hs=c.his_recordings(his,maps,raw,290)
lh=c.ROOT/'converted_datasets/reconversion_v2/gt21_rb07_export_AB24/time.parquet'
cols=[x for x in c.gt21_lh_columns(maps)]
res=[]
for key,l in c.iter_runs(c.read_batches(lh,cols),'source_recording_id'):
    name=str(key).split('/')[-1]
    for rid,h in hs.items():
        if not c.name_match(rid.split('|',1)[-1],name) or not np.isfinite(h['vals']['ankle_moment']).any(): continue
        fit=c.fit_gt21(h,l,maps,cfg)
        if fit is None or fit['rms']>0.1: continue
        task,pairs=c.gt21_pairs(h,l,fit,maps)
        out=[]
        for k in('ankle_angle','shank_angle','foot_angle'):
            x,y=pairs[k]; m=np.isfinite(x)&np.isfinite(y); d=x[m]-y[m]
            if not len(d): d=np.array([np.nan])
            out.append((np.sqrt(np.mean(d**2)),np.mean(d),np.median(d),np.abs(d).max(),np.mean(np.abs(d)>90)))
        x,y=pairs['ankle_angle']; x2,y2=pairs['foot_angle']
        res.append((out[0][0],rid,out+[(np.nanmin(x),np.nanmax(x),np.nanmin(y),np.nanmax(y),np.nanmin(x2),np.nanmax(x2),np.nanmin(y2),np.nanmax(y2))]))
res.sort(key=lambda t:-t[0])
for r,rid,o in res[:8]+res[len(res)//2:len(res)//2+2]:
    print(rid[-50:],'ankle x[%.0f,%.0f] y[%.0f,%.0f] foot x[%.0f,%.0f] y[%.0f,%.0f]'%o[3])
print('peak',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
