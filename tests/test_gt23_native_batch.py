"""Full-inventory and immutable-resume guards for GT23 native reconstruction."""
import numpy as np
import pytest
from scipy.io import savemat
from contributor_tools import run_gt23_native_batch as batch


def test_inventory_retains_empty_annotations_and_nonwalking_tasks(tmp_path):
    for task,empty in [('ball_toss_1_center',False),('normal_walk_1_fast',True)]:
        folder=tmp_path/'Segmentation/AB01';folder.mkdir(parents=True,exist_ok=True)
        savemat(folder/(task+'_parsing.mat'),{'left':np.empty((0,2)) if empty else np.array([[1.,2.]])})
        (tmp_path/'RawData/AB01/CSV_Data'/task.rsplit('_',1)[0]).mkdir(parents=True,exist_ok=True)
    records=batch.inventory(tmp_path)
    assert len(records)==2
    assert sum(r['has_intervals'] for r in records)==1
    assert records[0]['recording']=='ball_toss_1'


def test_inventory_rejects_reversed_annotations(tmp_path):
    folder=tmp_path/'Segmentation/AB01';folder.mkdir(parents=True)
    savemat(folder/'ball_toss_1_center_parsing.mat',{'left':np.array([[2.,1.]])})
    with pytest.raises(ValueError,match='Invalid source intervals'):batch.inventory(tmp_path)


def test_resume_requires_both_artifacts_and_unchanged_evidence(tmp_path):
    outputs={}
    for name in ['time/time.parquet','phase/phase.parquet']:
        path=tmp_path/name;path.parent.mkdir();path.write_bytes(name.encode())
        outputs[name]=batch.digest(path)
    m={'status':'converted_unreviewed','sources':{'s':'1'},'code':{'c':'1'},'outputs':outputs}
    assert batch.resume_matches(m,{'s':'1'},{'c':'1'},tmp_path)
    assert not batch.resume_matches(m,{'s':'2'},{'c':'1'},tmp_path)
    assert not batch.resume_matches(m,{'s':'1'},{'c':'2'},tmp_path)
    (tmp_path/'time/time.parquet').write_bytes(b'changed')
    assert not batch.resume_matches(m,{'s':'1'},{'c':'1'},tmp_path)
    del outputs['time/time.parquet']
    assert not batch.resume_matches(m,{'s':'1'},{'c':'1'},tmp_path)
