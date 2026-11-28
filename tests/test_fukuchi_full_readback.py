"""Small synthetic readback cases; coordinator schedules numerical imports."""
import importlib.util
from pathlib import Path
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
PAIR=load('full_pair_for_readback','contributor_tools/convert_fukuchi_ensemble_pair.py')
BASE=load('base_for_full_readback','contributor_tools/conversion_scripts/Fukuchi_2018_Walking/convert_ensemble_pilot.py')
CHECK=load('checker_for_full_readback','contributor_tools/conversion_scripts/Fukuchi_2018_Walking/check_ensemble_pilot.py')


def synthetic(stem):
    import pandas as pd
    angles={'Time':list(range(101)),'RHipAngleZ':[10.]*101,'LHipAngleZ':[20.]*101}
    moments={'Time':list(range(101)),'RKneeMomentZ':[2.]*101,'LKneeMomentZ':[3.]*101}
    values={name:values for table in [angles,moments] for name,values in table.items() if name!='Time'}
    return pd.DataFrame(PAIR.expanded_rows(angles,moments,stem,BASE)),values


@pytest.mark.parametrize('stem',['WBDS01walkOS','WBDS51walkT06'])
def test_full_pair_independent_source_readback(stem):
    frame,values=synthetic(stem)
    count,error=PAIR.independent_readback(frame,values,stem,CHECK)
    assert count==600 and error==0


@pytest.mark.parametrize('column,value',[('task_id','overground_C'),('source_recording_id','wrong'),('observation_id','wrong'),('subject','FU18_42')])
def test_full_pair_identity_corruption_rejected(column,value):
    frame,values=synthetic('WBDS51walkT06');frame.loc[76,column]=value
    with pytest.raises(AssertionError):PAIR.independent_readback(frame,values,'WBDS51walkT06',CHECK)


def test_treadmill_speed_cannot_be_fabricated():
    frame,values=synthetic('WBDS51walkT06');info=json.loads(frame.loc[149,'task_info']);info['speed_m_s']=1.0;frame.loc[149,'task_info']=json.dumps(info)
    with pytest.raises(AssertionError):PAIR.independent_readback(frame,values,'WBDS51walkT06',CHECK)
