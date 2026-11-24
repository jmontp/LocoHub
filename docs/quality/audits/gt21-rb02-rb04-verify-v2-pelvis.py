import sys,json,numpy as np,pyarrow.parquet as pq,random,glob,os
sys.path.insert(0,'/mnt/s/workspace/locomotion-data-standardization')
from contributor_tools import gt21_numeric_source as rd
R='/mnt/s/workspace/locomotion-data-standardization/'
inv=[json.loads(l) for l in open(R+'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123/recording_ledger.jsonl')]
BASES={'local_2024_copy_bundle':R+'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/','extracted_2024_copy_zip':'/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted/'}
rng=random.Random(20261209)
new=['AB12','AB15','AB17','AB19','AB23','AB28']
pick=[]
for sub in rng.sample(new,3):
    for mode in ('levelground','ramp','treadmill'):
        c=[r for r in inv if r['subject']==sub and r['mode']==mode]
        if mode=='treadmill': c=[r for r in c if r['channel_bytes'].get('ik',0)<5e6] or c
        pick.append(rng.choice(c))
def rz(a): c,s=np.cos(a),np.sin(a); z=np.zeros_like(a); o=np.ones_like(a); return np.stack([np.stack([c,-s,z],-1),np.stack([s,c,z],-1),np.stack([z,z,o],-1)],-2)
def rx(a): c,s=np.cos(a),np.sin(a); z=np.zeros_like(a); o=np.ones_like(a); return np.stack([np.stack([o,z,z],-1),np.stack([z,c,-s],-1),np.stack([z,s,c],-1)],-2)
def ry(a): c,s=np.cos(a),np.sin(a); z=np.zeros_like(a); o=np.ones_like(a); return np.stack([np.stack([c,z,s],-1),np.stack([z,o,z],-1),np.stack([-s,z,c],-1)],-2)
for r in pick:
    sub,mode,rec=r['subject'],r['mode'],r['recording']; b=BASES[r['source']]+f"{sub}/{r['session']}/{mode}/"
    ik=rd.read_numeric_table(b+f'ik/{rec}.mat'); it=np.asarray(ik['Header'])
    deg=np.nanmax(np.abs(ik['pelvis_tilt']))>6.5
    f=(lambda x:np.radians(x)) if deg else (lambda x:x)
    tilt,lst,rot=[f(np.asarray(ik[k])) for k in ('pelvis_tilt','pelvis_list','pelvis_rotation')]
    Rm=rz(tilt)@rx(lst)@ry(rot); ex=Rm[:,:,0]   # model +x axis in the lab
    el=np.arcsin(np.clip(ex[:,1],-1,1))
    t=pq.read_table(R+f'converted_datasets/reconversion_v2/gt21_rb_pass_batch_{sub}_20261124/{sub}/{mode}/{rec}.parquet',columns=['time_s','pelvis_sagittal_angle_rad']).to_pydict()
    mt=np.array(t['time_s']); pa=np.array(t['pelvis_sagittal_angle_rad'])
    ok=(it>=mt[0])&(it<=mt[-1]); pai=np.interp(it[ok],mt,pa); e=el[ok]
    # pelvis forward vs model +x: allow either sign of elevation by trying both, report the better and which
    out={}
    for nm,x in (('plus',e),('minus',-e)):
        a=pai-np.nanmedian(pai); bb=x-np.nanmedian(x); g=np.isfinite(a)&np.isfinite(bb)
        out[nm]=(float(np.degrees(np.sqrt(np.mean((((a-bb)[g]+np.pi)%(2*np.pi)-np.pi)**2)))),float(np.corrcoef(a[g],bb[g])[0,1]))
    print(sub,mode,rec,'deg' if deg else 'rad','n',int(ok.sum()),'RMS deg / corr  (+elev) %.2f %.2f  (-elev) %.2f %.2f'%(*out['plus'],*out['minus']),'pass median %.1f deg'%np.degrees(np.nanmedian(pa)),flush=True)
