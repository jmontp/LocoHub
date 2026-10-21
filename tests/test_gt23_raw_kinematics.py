"""Analytic synthetic source CSVs, no research data or native tools."""
import csv,json,math
from pathlib import Path
import pytest
from contributor_tools import audit_gt23_raw_kinematics as m


def write(path,cols,rows):
 with path.open('w',newline='') as f:w=csv.writer(f);w.writerow(cols);w.writerows(rows)


def fixture(tmp_path,mode='time',side='left',velocity_times=None):
 folder=tmp_path/'AB03/CSV_Data/example';folder.mkdir(parents=True,exist_ok=True);times=[10.,10.1,10.4]
 for family,filename,index in [('angle','Joint_Angle.csv',0),('velocity','Joint_Velocities.csv',1)]:
  clock=velocity_times or times if family=='velocity' else times
  cols=[f'{j[index]}_{leg}' for leg in ('l','r') for j in m.JOINTS]
  write(folder/filename,['time',*cols],[[t,*[(100 if family=='velocity' else 0)+20*k+2*(t-10) for k in range(6)]] for t in clock])
 targets=[10+.4*i/149 for i in range(150)] if mode=='phase' else times;rows=[]
 for i,t in enumerate(targets):
  row=dict(subject='GT23_AB03',source_recording_id='gt23:AB03/example',observation_id='synthetic1',reference_side=side,source_start_time_s=10.,source_end_time_s=10.4,time_s=t-10,phase_ipsi=100*i/149 if mode=='phase' else math.nan)
  for role,base in [('ipsi',0 if side=='left' else 3),('contra',3 if side=='left' else 0)]:
   for j,(_,_,canonical,sign) in enumerate(m.JOINTS):
    for family,units in [('angle','rad'),('velocity','rad_s')]:row[f'{canonical}_{family}_{role}_{units}']=sign*((100 if family=='velocity' else 0)+20*(base+j)+2*(t-10))*math.pi/180
  rows.append(row)
 return folder,rows

@pytest.mark.parametrize('mode',['time','phase'])
@pytest.mark.parametrize('side',['left','right'])
def test_analytic_source_clock_sign_units_physical_side(tmp_path,mode,side):
 folder,rows=fixture(tmp_path,mode,side);report=m.audit_batches([rows],folder,mode,len(rows));assert report['producer_transformation_checked'] and not report['anatomical_approval'];assert len(report['feature_coverage'])==12

@pytest.mark.parametrize('fault',['side','late','unit','sign','time','identity','missing'])
def test_actual_defects_reject(tmp_path,fault):
 folder,rows=fixture(tmp_path)
 if fault=='side':
  for row in rows:row['reference_side']='right'
 elif fault=='late':rows[-1]['hip_flexion_angle_ipsi_rad']+=1
 elif fault=='unit':rows[-1]['ankle_dorsiflexion_velocity_contra_rad_s']*=180/math.pi
 elif fault=='sign':rows[-1]['knee_flexion_angle_ipsi_rad']*=-1
 elif fault=='time':rows[-1]['time_s']=.3
 elif fault=='identity':rows[-1]['subject']='GT23_AB01'
 else:rows[-1]['hip_flexion_velocity_ipsi_rad_s']=None
 with pytest.raises(ValueError):m.audit_batches([rows],folder,'time',len(rows))


def test_phase_velocity_own_clock_disagreement_fails(tmp_path):
 folder,rows=fixture(tmp_path,'phase',velocity_times=[9.9,10.2,10.5])
 with pytest.raises(ValueError,match='actual source clocks differ'):m.audit_batches([rows],folder,'phase',150)


def test_time_uses_actual_velocity_clock_and_interpolation(tmp_path):
 folder,rows=fixture(tmp_path,velocity_times=[9.9,10.2,10.5]);assert m.audit_batches([rows],folder,'time',3)['rows_checked']==3


def test_all_missing_feature_is_partial_not_pass(tmp_path):
 folder,rows=fixture(tmp_path);p=folder/'Joint_Velocities.csv'
 with p.open() as f:data=list(csv.reader(f))
 for row in data[1:]:row[1]='NaN'
 write(p,data[0],data[1:])
 for row in rows:row['hip_flexion_velocity_ipsi_rad_s']=None
 report=m.audit_batches([rows],folder,'time',3);assert report['status']=='supplied_raw_kinematics_partial_unassessed';assert report['feature_coverage']['hip_flexion_velocity_ipsi_rad_s']=={'finite':0,'missing':3}


def test_no_phase_interpolation_halo(tmp_path):
 p=tmp_path/'source.csv';write(p,['time','a'],[[0,0],[1,1],[2,2]])
 result=m.interpolate(p,['a'],[.5,1,1.5],(.5,1.5));assert math.isnan(result[0][0]) and result[1]==[1] and math.isnan(result[2][0])


def test_alias_mode_requires_canonical_nulls(tmp_path):
 folder,rows=fixture(tmp_path)
 for row in rows:
  for name in list(row):
   if '_angle_' in name or '_velocity_' in name:row[m.ALIAS+name]=row[name];row[name]=None
 assert m.audit_batches([rows],folder,'time',3,aliases=True)['producer_transformation_checked']
 rows[-1]['hip_flexion_angle_ipsi_rad']=0
 with pytest.raises(ValueError,match='canonical'):m.audit_batches([rows],folder,'time',3,aliases=True)


def test_missing_header_and_conflicting_hash_fail(tmp_path):
 p=tmp_path/'source.csv';write(p,['time','a'],[[0,0],[1,1]])
 with pytest.raises(ValueError,match='column'):list(m.source_rows(p,['missing']))
 with pytest.raises(ValueError,match='Conflicting'):m.merge({'a':'x'},{'a':'y'})


def test_supervision_required_before_any_reads():
 with pytest.raises(ValueError,match='supervisor'):m.run(Path('/not/read'),'x')


def test_metadata_invariant_survives_512_row_boundary(tmp_path):
 folder,template=fixture(tmp_path);times=[10+i/1000 for i in range(600)]
 for filename,index in [('Joint_Angle.csv',0),('Joint_Velocities.csv',1)]:
  write(folder/filename,['time',*[f'{j[index]}_{leg}' for leg in ('l','r') for j in m.JOINTS]],[[t,*([0]*6)] for t in times])
 rows=[]
 for t in times:
  row=dict(template[0],source_end_time_s=times[-1],time_s=t-10)
  for k in row:
   if '_angle_' in k or '_velocity_' in k:row[k]=0.
  rows.append(row)
 rows[512]['reference_side']='right'
 with pytest.raises(ValueError,match='across chunks'):m.audit_batches([rows[:512],rows[512:]],folder,'time',600)


def test_canonical_path_hash_conflict(tmp_path):
 p=tmp_path/'a';p.write_text('a')
 with pytest.raises(ValueError,match='Conflicting'):m.merge({str(tmp_path/'x/../a'):'old'},{str(p):'new'})


def test_prepared_source_clipping_and_value_proof(tmp_path):
 original=tmp_path/'original/Joint_Angle.csv';prepared=tmp_path/'prepared/Joint_Angle.csv';original.parent.mkdir();prepared.parent.mkdir();cols=['time',*[f'{j[0]}_{leg}' for leg in ('l','r') for j in m.JOINTS]]
 write(original,cols,[[t,*([t]*6)] for t in [0,1,2,3]]);write(prepared,cols,[[t,*([t]*6)] for t in [1,2]])
 assert m.verify_window_support(original,prepared)==2
 write(prepared,cols,[[1,*([1]*6)],[3,*([3]*6)]])
 with pytest.raises(ValueError,match='skips'):m.verify_window_support(original,prepared)

@pytest.mark.parametrize('mode',['time','phase'])
def test_actual_receipt_shapes_prepare_and_persisted_run(tmp_path,monkeypatch,mode):
 import pyarrow as pa,pyarrow.parquet as pq
 pa.set_cpu_count(1);pa.set_io_thread_count(1)
 original,rows=fixture(tmp_path/'raw/RawData',mode);prepared=tmp_path/'prepared/RawData/AB03/CSV_Data/example';prepared.mkdir(parents=True)
 for name in ['Joint_Angle.csv','Joint_Velocities.csv']:(prepared/name).write_bytes((original/name).read_bytes())
 # Actual native time/phase receipt layouts, with synthetic values and identities.
 monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'windows_local',lambda value:tmp_path/'prepared')
 guardfile=tmp_path/'contributor_tools/preserve_mblue_planar_estimates.py';guardfile.parent.mkdir();guardfile.write_text('# synthetic guard binding')
 native=tmp_path/'native';native.mkdir();options={'subject':'AB03','recording':'example_parsing.mat','data_root':'S:\\synthetic'};(native/'options.json').write_text(json.dumps(options))
 evidence={'subject':'AB03','parsing':'example_parsing.mat','recording':'example','csv_files':{name:{'source':str(original/name),'source_sha256':m.digest(original/name),'window_sha256':m.digest(prepared/name)} for name in ['Joint_Angle.csv','Joint_Velocities.csv']}}
 if mode=='phase':
  parsing=tmp_path/'prepared/Segmentation/AB03/example_parsing.mat';parsing.parent.mkdir(parents=True);parsing.write_bytes(b'synthetic source parsing')
  evidence={'output_sha256':'native-output-hash','scientific_approval':False,'source_sha256':{str(original/name):m.digest(original/name) for name in ['Joint_Angle.csv','Joint_Velocities.csv']}|{str(parsing):m.digest(parsing)}|{str(prepared/name):m.digest(prepared/name) for name in ['Joint_Angle.csv','Joint_Velocities.csv']}}
 ep=native/'source_evidence.json';ep.write_text(json.dumps(evidence));manifest={'output_sha256':'native-output-hash','prepared_input_sha256':{f'RawData/AB03/CSV_Data/example/{name}':m.digest(prepared/name) for name in ['Joint_Angle.csv','Joint_Velocities.csv']}}
 if mode=='phase':manifest.pop('prepared_input_sha256')
 if mode=='time':manifest.update(prepared_input_manifest=m.digest(ep));manifest['prepared_input_sha256']['source_window_manifest.json']=m.digest(ep)
 mp=native/'conversion_manifest.json';mp.write_text(json.dumps(manifest));corrected=tmp_path/'normalization';corrected.mkdir();parquet=corrected/'corrected.parquet';pq.write_table(pa.Table.from_pylist(rows),parquet)
 report={'status':'force_cop_and_publisher_normalization_corrected_unreviewed','scientific_approval':False,'actual_producing_converter':{'mode':mode},'rows_checked':len(rows),'output_sha256':m.digest(parquet),'verified_input_sha256':{str(mp):m.digest(mp),str(native/'options.json'):m.digest(native/'options.json')}};rp=corrected/'report.json';rp.write_text(json.dumps(report))
 result=m.prepare(rp,mp,ep,m.digest(ep),tmp_path/'converted_datasets/reconversion_v2/audit');plan=Path(result['plan']);guards=[]
 monkeypatch.setattr(m,'runtime_guard',lambda *a:lambda:guards.append(1))
 m.run(plan,result['plan_sha256'],True)
 readback=json.loads(plan.with_name('raw_kinematics_readback.json').read_text());assert readback['rows_checked']==len(rows) and readback['anatomical_approval'] is False and guards
 assert json.loads(plan.read_text())['source_folder']==str(prepared)
 with pytest.raises(FileExistsError):m.run(plan,result['plan_sha256'],True)


def test_phase_original_prepared_pairs_selected_by_exact_input_root(tmp_path,monkeypatch):
 original=tmp_path/'original/RawData/AB03/CSV_Data/example';prepared=tmp_path/'prepared/RawData/AB03/CSV_Data/example';monkeypatch.setattr(m,'windows_local',lambda value:tmp_path/'prepared');options={'data_root':'S:\\prepared','subject':'AB03','recording':'example_parsing.mat'};manifest={'output_sha256':'native'}
 parsing=tmp_path/'prepared/Segmentation/AB03/example_parsing.mat';hashes={str(parsing):'parsing'}
 for name in ['Joint_Angle.csv','Joint_Velocities.csv']:hashes[str(original/name)]='original_'+name;hashes[str(prepared/name)]='prepared_'+name
 evidence={'scientific_approval':False,'output_sha256':'native','source_sha256':hashes}
 selected,extra=m.sources(manifest,evidence,options,'receipt','phase');assert set(selected)=={str(original/n) for n in ['Joint_Angle.csv','Joint_Velocities.csv']};assert str(prepared/'Joint_Velocities.csv') in extra
 with pytest.raises(ValueError,match='schema'):m.sources(manifest,evidence,options,'receipt','time')
 evidence['source_sha256'][str(tmp_path/'unrelated/RawData/AB03/CSV_Data/example/Joint_Angle.csv')]='x'
 with pytest.raises(ValueError,match='pair'):m.sources(manifest,evidence,options,'receipt','phase')
