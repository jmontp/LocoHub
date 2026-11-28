"""Collect ankle-convention evidence without fitting or applying a sign change.

Local segment gyros are not in a demonstrated common frame. Their relationship
to joint velocity is diagnostic only, not an anatomical sign calibration.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import argparse,json,resource,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));os.nice(max(0,19-os.nice(0)))
    import pandas as pd
    import numpy as np
    source=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic');a.output_root.mkdir(parents=True,exist_ok=False)
    records=[];files={};missing=[]
    def table(folder,subject,suffix,columns):
        path=folder/(subject+'_'+folder.name+'_'+suffix+'.csv')
        result=pd.read_csv(path,nrows=5000,usecols=columns)
        files[str(path)]={'sha256':digest(path),'rows_read':len(result),'row_limit':5000}
        assert np.isfinite(result.time).all() and (np.diff(result.time)>0).all()
        return result
    for phase,subject in [('Phase1And2','BT01'),('Phase1And2','BT02'),('Phase1And2','BT03'),('Phase3','BT20'),('Phase3','BT21'),('Phase3','BT24')]:
        parent=source/(phase+'_Parsed')/'Parsed'/subject
        normals=sorted(parent.glob('normal_walk*'))
        if not normals:missing.append([phase,subject,'normal_walk']);continue
        folder=normals[0]
        velocity=table(folder,subject,'velocity',['time','ankle_angle_l_velocity','ankle_angle_r_velocity'])
        gyro=table(folder,subject,'imu_sim',['time',*[f'{segment}_imu_{side}_gyro_z' for segment in ['foot','shank'] for side in ['l','r']]])
        np.testing.assert_allclose(velocity.time,gyro.time,rtol=0,atol=1e-9)
        record={'phase':phase,'subject':subject,'normal_recording':folder.name,'rows':len(velocity),'gyro_diagnostics':{},'heel_toe_diagnostics':[]}
        for side in ['l','r']:
            joint=velocity[f'ankle_angle_{side}_velocity'].to_numpy()
            relative=(gyro[f'foot_imu_{side}_gyro_z']-gyro[f'shank_imu_{side}_gyro_z']).to_numpy()
            good=np.isfinite(joint)&np.isfinite(relative);assert good.sum()>100
            record['gyro_diagnostics'][side]={'finite_pairs':int(good.sum()),'correlation':float(np.corrcoef(joint[good],relative[good])[0,1]),
                'same_sign_rmse_deg_s':float(np.sqrt(np.mean((joint[good]-relative[good])**2))),
                'opposite_sign_rmse_deg_s':float(np.sqrt(np.mean((joint[good]+relative[good])**2)))}
        for heel in sorted(parent.glob('*heel-walk*')):
            toe=parent/heel.name.replace('heel-walk','toe-walk')
            if not toe.is_dir():missing.append([phase,subject,heel.name,'paired toe trial']);continue
            columns=['time','ankle_angle_l','ankle_angle_r']
            h=table(heel,subject,'angle_filt',columns);t=table(toe,subject,'angle_filt',columns)
            record['heel_toe_diagnostics'].append({'heel_trial':heel.name,'toe_trial':toe.name,
                'heel_median_source_angle_deg':{side:float(h[f'ankle_angle_{side}'].median()) for side in ['l','r']},
                'toe_median_source_angle_deg':{side:float(t[f'ankle_angle_{side}'].median()) for side in ['l','r']}})
        records.append(record)
    archives=[]
    for name in ['Phase1And2_Complete.zip','Phase3_Complete.zip']:
        path=source/name
        with zipfile.ZipFile(path) as z:
            candidates=[x.filename for x in z.infolist() if x.filename.lower().endswith(('.osim','.xml','.m','.py'))]
            archives.append({'path':str(path),'bytes':path.stat().st_size,'entries':len(z.infolist()),'model_or_processing_code_entries':candidates,'scope':'Central-directory listing only; archive content was not extracted or fully hashed'})
    report={'status':'ankle_convention_conflict_requires_model_or_author_confirmation','scientific_approval':False,
        'source_readme_sha256':digest(source/'readme.txt'),'source_declared_positive_direction':'ankle plantarflexion',
        'current_converter_mapping':'Unchanged source ankle angle and moment labeled as dorsiflexion',
        'probe_sha256':digest(Path(__file__)),'records':records,'source_files':files,'missing':missing,'archives':archives,
        'limitations':['Gyros are in different local segment frames; subtraction is diagnostic, not an exact joint angular velocity',
            'Heel/toe trial names describe intended tasks, not independently measured anatomical postures',
            'Only the first 5000 samples per selected source file were examined',
            'No waveform-derived sign correction is applied; anatomical verification remains open']}
    (a.output_root/'convention_evidence.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'records':len(records),'files':len(files),'missing':missing,'status':report['status']}))


if __name__=='__main__':main()
