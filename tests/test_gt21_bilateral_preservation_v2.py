"""Synthetic dictionaries and persisted Parquet only; no real GT21 data."""
import copy
import pytest
from contributor_tools.check_gt21_bilateral_preservation_v2 import check_observations


def curve(identity,side='left',value=1.):
 columns=['observation_id','reference_side','value','missing','source_start_time_s','source_end_time_s']
 return columns,[dict(observation_id=identity,reference_side=side,value=value,missing=None,source_start_time_s=2.,source_end_time_s=3.) for _ in range(150)]


def test_complete_baseline_and_opposite_leg_addition():
 old=curve('left');new=curve('right','right')
 r=check_observations(iter([old]),iter([old,new]))
 assert r['preserved_observations']==1 and r['added_observations']==1
 assert r['scientific_approval'] is False and r['source_pair_coverage_checked'] is False


def test_conflicting_duplicate_baseline_cannot_collapse_to_last_value():
 earlier=curve('same',value=2.);last=curve('same',value=1.);added=curve('new','right')
 # Default old gate rejects through its row-count assert; -O removes that gate.
 with pytest.raises(ValueError,match='Duplicate baseline'):check_observations([earlier,last],[last,added])


def test_identical_duplicate_baseline_also_rejected():
 c=curve('same')
 with pytest.raises(ValueError,match='Duplicate baseline'):check_observations([c,c],[c,curve('new','right')])


@pytest.mark.parametrize('defect',['signedzero','missing','columns','side','partial','mixed'])
def test_exact_preservation_defects_rejected(defect):
 old=curve('same',value=-0.);bad=copy.deepcopy(old)
 if defect=='signedzero':bad[1][0]['value']=0.
 elif defect=='missing':bad[1][0]['missing']=float('nan')
 elif defect=='columns':bad[0].reverse()
 elif defect=='side':
  for row in bad[1]:row['reference_side']='right'
 elif defect=='partial':bad[1].pop()
 else:bad[1][0]['observation_id']='other'
 with pytest.raises(ValueError):check_observations([old],[bad,curve('new','right')])


def test_duplicate_candidate_and_dropped_baseline_rejected():
 c=curve('same')
 with pytest.raises(ValueError,match='Duplicate candidate'):check_observations([c],[c,c])
 with pytest.raises(ValueError,match='disappeared'):check_observations([c],[curve('new','right')])


def test_hash_only_ledger_has_explicit_record_bound():
 with pytest.raises(MemoryError):check_observations([curve('a'),curve('b')],[curve('a')],max_observations=1)


def write_curves(path, observations, metadata=None):
 import pyarrow as pa
 import pyarrow.parquet as pq
 rows=[row for _, observation in observations for row in observation]
 table=pa.Table.from_pylist(rows).replace_schema_metadata(metadata)
 pq.write_table(table,path,row_group_size=73)
 return path


def test_arrow_wrapper_preserves_metadata_and_added_interval(tmp_path):
 from contributor_tools.check_gt21_bilateral_preservation_v2 import verify_preserved
 old=curve('old');new=curve('new','right')
 baseline=write_curves(tmp_path/'old.parquet',[old],{b'provenance':b'synthetic'})
 candidate=write_curves(tmp_path/'new.parquet',[old,new],{b'provenance':b'synthetic'})
 report=verify_preserved(baseline,candidate)
 assert report['added_cycles']==[dict(observation_id='new',reference_side='right',start_s=2.,end_s=3.)]
 assert report['exact_schema_metadata_checked'] is True
 assert len(report['input_sha256'])==2
 write_curves(candidate,[old,new],{b'provenance':b'changed'})
 with pytest.raises(ValueError,match='metadata'):verify_preserved(baseline,candidate)


@pytest.mark.parametrize('defect',['partial','mixed_identity','mixed_interval'])
def test_arrow_wrapper_actual_batches_reject_invalid_observations(tmp_path,defect):
 from contributor_tools.check_gt21_bilateral_preservation_v2 import verify_preserved
 old=curve('old');new=curve('new','right')
 if defect=='partial':new[1].pop()
 elif defect=='mixed_identity':new[1][80]['observation_id']='unexpected'
 else:new[1][80]['source_end_time_s']=4.
 baseline=write_curves(tmp_path/'old.parquet',[old])
 candidate=write_curves(tmp_path/'new.parquet',[old,new])
 with pytest.raises(ValueError):verify_preserved(baseline,candidate)


def test_persisted_duplicate_default_rejected_optimization_exposes_old_gate(tmp_path):
 import os,subprocess,sys
 from pathlib import Path
 baseline=write_curves(tmp_path/'old.parquet',[curve('same',value=2.),curve('same')])
 candidate=write_curves(tmp_path/'new.parquet',[curve('same'),curve('added','right')])
 env=os.environ.copy();env.pop('PYTHONOPTIMIZE',None)
 for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS'):env[name]='1'
 root=Path(__file__).resolve().parents[1]
 for module,optimized,expected in [('prepare_gt21_bilateral_recovery',False,'AssertionError'),('prepare_gt21_bilateral_recovery',True,'ACCEPTED'),('check_gt21_bilateral_preservation_v2',False,'ValueError'),('check_gt21_bilateral_preservation_v2',True,'ValueError')]:
  script=f"""import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import ast
from pathlib import Path
source=Path('contributor_tools/{module}.py').read_text()
if {module!r}=='prepare_gt21_bilateral_recovery':
 tree=ast.parse(source)
 function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='verify_preserved')
 isolated=ast.Module(body=[function],type_ignores=[])
 exec(compile(isolated,'frozen_verify_preserved','exec',optimize={2 if optimized else 0}))
else:
 from contributor_tools.check_gt21_bilateral_preservation_v2 import verify_preserved
try:
 verify_preserved({str(baseline)!r},{str(candidate)!r})
except Exception as exc:
 print(type(exc).__name__)
else:
 print('ACCEPTED')
"""
  result=subprocess.run([sys.executable,*(['-O'] if optimized else []),'-c',script],cwd=root,env=env,text=True,capture_output=True,timeout=30)
  assert result.returncode==0,result.stderr
  assert result.stdout.strip()==expected,result.stderr
