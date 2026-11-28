from copy import deepcopy
import pytest
from contributor_tools.check_mblue_native_metadata_scope import source_scope


def fixture():
 records=[{'subject':f'AB{i%10:02d}','source_path':f'bare/task{i}','subject_info_sha256':f'hash{i%10}'} for i in range(335)]
 sources=[{'subject':f'AB{i:02d}','sha256':f'hash{i}','tasks':[['bare',f'task{n}'] for n in range(335) if n%10==i]} for i in range(10)]
 return {'status':'all_normalized_blocks_reconstructed_unreviewed','planned_blocks':335,'records':records},{'status':'complete_mblue_scope_evidence_checked_unreviewed','blocks':335,'observations_after':15061,'retained_stair_windows':764},{'sources':sources}


def test_exact_full_scope():
 assert source_scope(*fixture())=={'blocks':335,'subjects':10,'observations_after':15061,'retained_stair_windows':764}


@pytest.mark.parametrize('change',['missingblock','duplicateblock','missingsubject','duplicatesubject','wronghash','missingtask','duplicatetask','wrongcondition','wrongscope'])
def test_incomplete_source_scope_refused(change):
 r,s,p=fixture()
 if change=='missingblock':r['records'].pop()
 elif change=='duplicateblock':r['records'][-1]=deepcopy(r['records'][0])
 elif change=='missingsubject':p['sources'].pop()
 elif change=='duplicatesubject':p['sources'][-1]=deepcopy(p['sources'][0])
 elif change=='wronghash':p['sources'][0]['sha256']='wrong'
 elif change=='missingtask':p['sources'][0]['tasks'].pop()
 elif change=='duplicatetask':p['sources'][0]['tasks'].append(p['sources'][0]['tasks'][0])
 elif change=='wrongcondition':r['records'][0]['source_path']='unknown/task'
 else:s['observations_after']=15060
 with pytest.raises(ValueError):source_scope(r,s,p)


def test_hash_merge_refuses_conflicting_evidence():
 from contributor_tools.check_mblue_native_metadata_scope import merge_bindings
 assert merge_bindings({'a':'hash'},{'a':'hash','b':'other'})=={'a':'hash','b':'other'}
 with pytest.raises(ValueError,match='Conflicting'):merge_bindings({'a':'hash'},{'a':'changed'})
