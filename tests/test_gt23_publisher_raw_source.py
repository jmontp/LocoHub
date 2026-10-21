"""Synthetic raw CSV expectations, independent of correction transformations."""
import csv,math
from pathlib import Path
import pytest
from contributor_tools import audit_gt23_publisher_raw_source as tool


def write(path,columns,rows):
 with path.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(columns);w.writerows(rows)


def fixture(tmp_path,side='left',mode='phase'):
 write(tmp_path/'Joint_Angle.csv',['time'],[[0],[1]])
 columns=[f'{raw}_{leg}_moment' for leg in ('l','r') for raw,_,_ in tool.JOINTS]
 write(tmp_path/'Joint_Moments.csv',['time',*columns],[[0,113.5,227,340.5,454,567.5,681],[1,227,340.5,454,567.5,681,794.5]])
 force=[leg+'Force'+axis for leg in ('L','R') for axis in ('X','Y_Vertical','Z')]
 write(tmp_path/'GroundFrame_GRFs.csv',['time',*force],[[0,1113.435,2226.87,3340.305,4453.74,5567.175,6680.61],[1,1113.435,2226.87,3340.305,4453.74,5567.175,6680.61]])
 rows=[]
 for i in range(150 if mode=='phase' else 2):
  t=i/149 if mode=='phase' else i
  r={'observation_id':'synthetic1','source_recording_id':'gt23:AB03/example','subject':'GT23_AB03','reference_side':side,'source_start_time_s':0.,'source_end_time_s':1.,'time_s':t,'phase_ipsi':100*t}
  for role,base in [('ipsi',0 if side=='left' else 3),('contra',3 if side=='left' else 0)]:
   for j,(raw,canonical,sign) in enumerate(tool.JOINTS):
    r[f'source_{raw}_moment_{role}_Nm']=113.5*(base+j+1+t)
    r[f'{canonical}_moment_{role}_Nm_kg']=sign*(base+j+1+t)
   for j,name in enumerate((f'source_grf_global_x_{role}_BW',f'grf_vertical_{role}_BW',f'source_grf_global_z_{role}_BW')):r[name]=base+j+1.
   r[f'grf_anterior_{role}_BW']=None;r[f'grf_lateral_{role}_BW']=None
  rows.append(r)
 return rows


@pytest.mark.parametrize('side',['left','right'])
@pytest.mark.parametrize('mode',['time','phase'])
def test_independent_raw_nm_newton_and_ab03_mass(tmp_path,side,mode):
 rows=fixture(tmp_path,side,mode)
 assert tool.check_rows(rows,tmp_path,mode,113.5)==(len(rows)*12,len(rows))
 with pytest.raises(ValueError):tool.check_rows(rows,tmp_path,mode,82.18)


@pytest.mark.parametrize('defect',['late_cycle','wrong_side','missing_alias','old_raw_moment','clock'])
def test_adversarial_errors(tmp_path,defect):
 rows=fixture(tmp_path)
 if defect=='late_cycle':rows[-1]['knee_flexion_moment_ipsi_Nm_kg']+=1
 elif defect=='wrong_side':
  for r in rows:r['reference_side']='right'
 elif defect=='missing_alias':rows[-1]['source_hip_flexion_moment_ipsi_Nm']=None
 elif defect=='old_raw_moment':rows[-1]['hip_flexion_moment_ipsi_Nm_kg']*=113.5
 else:rows[-1]['phase_ipsi']=99
 with pytest.raises(ValueError):tool.check_rows(rows,tmp_path,'phase',113.5)


def test_phase_interval_does_not_extrapolate_from_neighbor_samples(tmp_path):
 p=tmp_path/'raw.csv';write(p,['time','x'],[[0,0],[1,10],[2,20]])
 assert tool.interpolate(p,['x'],[.5,1,1.5])==[[5],[10],[15]]
 result=tool.interpolate(p,['x'],[.5,1,1.5],(.5,1.5))
 assert math.isnan(result[0][0]) and result[1]==[10] and math.isnan(result[2][0])


def test_missing_source_and_nonmonotonic_clock(tmp_path):
 p=tmp_path/'raw.csv';write(p,['time','x'],[[0,0],[1,10]])
 assert all(math.isnan(r[0]) for r in tool.interpolate(p,['unavailable'],[0,.5,1]))
 write(p,['time','x'],[[0,0],[0,10]])
 with pytest.raises(ValueError,match='clock'):tool.interpolate(p,['x'],[0,.5])


@pytest.mark.parametrize('mode',['time','phase'])
@pytest.mark.parametrize('nan_feature',[False,True])
def test_small_persisted_readback_and_no_implicit_retry(tmp_path,monkeypatch,mode,nan_feature):
 import json
 import pyarrow as pa
 import pyarrow.parquet as pq
 folder=tmp_path/'AB03/CSV_Data/example';folder.mkdir(parents=True)
 rows=fixture(folder,mode=mode)
 if nan_feature:
  raw=folder/'Joint_Moments.csv'
  with raw.open() as f:data=list(csv.reader(f))
  for row in data[1:]:row[1]='NaN'
  write(raw,data[0],data[1:])
  for row in rows:row['source_hip_flexion_moment_ipsi_Nm']=math.nan;row['hip_flexion_moment_ipsi_Nm_kg']=math.nan
 for r in rows:r['subject_metadata']=json.dumps({'weight_kg':113.5})
 target=tmp_path/'corrected.parquet';pq.write_table(pa.Table.from_pylist(rows),target)
 mass=tmp_path/'mass.csv';write(mass,['Subject','Mass'],[['AB03',113.5]])
 monkeypatch.setattr(tool,'MASS',mass);monkeypatch.setattr(tool.resource,'setrlimit',lambda *a:None);monkeypatch.setattr(tool.os,'nice',lambda *a:19)
 output=tmp_path/'audit';output.mkdir();plan=output/'plan.json'
 plan.write_text(json.dumps({'bindings':{str(target):tool.digest(target),str(mass):tool.digest(mass)},'parquet':str(target),'source_folder':str(folder),'mode':mode,'expected_rows':len(rows)}))
 tool.run(plan,tool.digest(plan))
 report=json.loads((output/'raw_source_readback.json').read_text())
 assert report['status']==('publisher_normalization_raw_source_partial_unassessed' if nan_feature else 'publisher_normalization_raw_source_checked_unreviewed')
 assert report['rows_checked']==len(rows) and report['observations_checked']==1 and report['publisher_mass_kg']==113.5
 with pytest.raises(FileExistsError):tool.run(plan,tool.digest(plan))


def test_missing_required_moment_header_refused(tmp_path):
 rows=fixture(tmp_path)
 p=tmp_path/'Joint_Moments.csv'
 with p.open() as f:data=list(csv.reader(f))
 write(p,data[0][:-1],[r[:-1] for r in data[1:]])
 with pytest.raises(ValueError,match='required raw source header'):tool.check_rows(rows,tmp_path,'phase',113.5)


def test_one_all_nan_feature_is_explicitly_unassessed(tmp_path):
 rows=fixture(tmp_path);p=tmp_path/'Joint_Moments.csv'
 with p.open() as f:data=list(csv.reader(f))
 for r in data[1:]:r[1]='NaN'
 write(p,data[0],data[1:])
 for r in rows:
  r['source_hip_flexion_moment_ipsi_Nm']=math.nan;r['hip_flexion_moment_ipsi_Nm_kg']=math.nan
 coverage={};tool.check_rows(rows,tmp_path,'phase',113.5,coverage=coverage)
 assert coverage['hip_flexion_moment_ipsi_Nm_kg']=={'finite':0,'missing':150}
 assert coverage['knee_flexion_moment_ipsi_Nm_kg']=={'finite':150,'missing':0}


def test_phase_shared_clock_disagreement_fails_closed(tmp_path):
 fixture(tmp_path);tool.phase_clock_agreement(tmp_path)
 write(tmp_path/'Joint_Angle.csv',['time'],[[0],[.9]])
 with pytest.raises(ValueError,match='producer clock bug'):tool.phase_clock_agreement(tmp_path)


@pytest.mark.parametrize('case_index',[0,1])
def test_actual_sanitized_native_receipt_shapes(case_index):
 import json,copy
 cases=json.loads((Path(__file__).parent/'fixtures/gt23_native_receipt_shapes.json').read_text());case=cases[case_index]
 selected,extra=tool.resolve_sources(case['manifest'],case['evidence'],case['options'],case['original_evidence_sha256'],case['mode'])
 assert len(selected)==3 and all('/AB01/CSV_Data/' in p for p in selected)
 options={**case['options'],'subject':'AB03'}
 with pytest.raises(ValueError):tool.resolve_sources(case['manifest'],case['evidence'],options,case['original_evidence_sha256'],case['mode'])
 evidence=copy.deepcopy(case['evidence'])
 if case_index==0:evidence['csv_files']['Joint_Moments.csv']['window_sha256']='wrong'
 else:evidence['output_sha256']='wrong'
 with pytest.raises(ValueError):tool.resolve_sources(case['manifest'],evidence,case['options'],case['original_evidence_sha256'],case['mode'])


@pytest.mark.parametrize('case_index',[0,1])
def test_actual_producer_mode_cannot_switch_source_schema(case_index):
 import json
 case=json.loads((Path(__file__).parent/'fixtures/gt23_native_receipt_shapes.json').read_text())[case_index]
 with pytest.raises(ValueError,match='mode/source schema'):
  tool.resolve_sources(case['manifest'],case['evidence'],case['options'],case['original_evidence_sha256'],'phase' if case['mode']=='time' else 'time')
