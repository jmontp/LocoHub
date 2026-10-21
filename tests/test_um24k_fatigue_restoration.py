"""Small artificial fatigue summaries; actual source arrays never loaded."""
import json
import math
import pytest
from contributor_tools import restore_um24k_fatigue_summaries as producer
from contributor_tools import audit_um24k_fatigue_summaries as reviewer


def source():
    import numpy as np
    result={name:{c:np.arange(210,dtype=float).reshape(21,10)+offset for c in ('bare','exo')} for offset,name in enumerate(producer.PROGRESSION)}
    result.update({name:{c:np.arange(10,dtype=float)+offset for c in ('bare','exo')} for offset,name in enumerate(producer.SUMMARY)})
    result['modifiedquest']={'headers':np.array(['LL original','Walking','Up','Down','Ramp+','Ramp-'],dtype=object),'data':np.arange(60,dtype=float).reshape(6,10)}
    return result


def test_all_cells_and_distinct_progression_semantics():
    raw=producer.validate(source());tables=producer.tables(raw)
    assert [t.num_rows for t in tables.values()]==[2100,100,60]
    for kind,table in tables.items():assert reviewer.verify_table(table,raw,kind)['missing_unassessed']==0
    p=tables['progression'];assert p['trial_progression_percent'].to_pylist()[:21]==list(range(-100,101,10))
    assert 'phase_ipsi' not in p.column_names and 'time_s' not in p.column_names
    assert tables['questionnaire']['source_task_label'][0].as_py()=='LL original'


def test_missing_and_signed_zero_preserved():
    raw=source();raw['LLrepDuration_progression']['bare'][0,0]=-0.;raw['LLrepDuration_progression']['bare'][1,0]=math.nan
    table=producer.tables(raw)['progression'];assert reviewer.verify_table(table,raw,'progression')['missing_unassessed']==1
    actual=table.to_pylist()[0];wanted=dict(actual);actual['value']=0.
    with pytest.raises(ValueError,match='bits'):reviewer.verify_rows(actual,wanted)


@pytest.mark.parametrize('field,value',[('condition','exo'),('source_subject_column',2),('trial_progression_percent',0),('unit','ms')])
def test_identity_units_progression_corruption(field,value):
    wanted=next(reviewer.expected_rows(source(),'progression'));actual={**wanted,field:value}
    with pytest.raises(ValueError,match='identity'):reviewer.verify_rows(actual,wanted)


def test_bad_schema_and_unknown_questionnaire_labels():
    raw=source();raw['modifiedquest']['headers'][1]=raw['modifiedquest']['headers'][0]
    with pytest.raises(ValueError,match='Duplicate'):producer.validate(raw)
    raw=source();raw['fatiguedPeakLean']['bare']=raw['fatiguedPeakLean']['bare'][:9]
    with pytest.raises(ValueError,match='shape'):producer.validate(raw)


def test_persisted_independent_s2_readback(tmp_path):
    from scipy.io import savemat
    import pyarrow.parquet as pq
    raw=source();path=tmp_path/'dataset_S2.mat';savemat(path,raw)
    for name,table in producer.tables(raw).items():pq.write_table(table,tmp_path/(name+'.parquet'))
    plan={'output_root':str(tmp_path),'source':str(path),'bindings':{str(path):producer.digest(path)},'limitations':['synthetic only']};p=tmp_path/'plan.json';p.write_text(json.dumps(plan))
    result=reviewer.audit(p);assert result['scientific_approval'] is False and result['tables']['progression']['rows']==2100
    table=producer.tables(raw)['questionnaire'].slice(0,59);pq.write_table(table,tmp_path/'questionnaire.parquet')
    with pytest.raises(ValueError,match='scope'):reviewer.audit(p)
