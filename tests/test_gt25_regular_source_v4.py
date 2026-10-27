"""Synthetic independent event and segment-reference fixtures, no source datasets."""
import sqlite3
import pytest
from contributor_tools.audit_gt25_regular_source_v4 import gait_events,gait_segment_values,quantile


def database(n,contacts):
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE angle_filt(i INTEGER PRIMARY KEY,c0 REAL)');db.execute('CREATE TABLE grf(i INTEGER PRIMARY KEY,c1 REAL)')
    for i in range(n):
        db.execute('INSERT INTO angle_filt VALUES(?,?)',(i,i*.005));db.execute('INSERT INTO grf VALUES(?,?)',(i,100. if any(a<=i<b for a,b in contacts) else 0.))
    return db


def test_known_contacts_and_duration_exclusions():
    db=database(1100,[(100,140),(130,160),(300,340),(500,540),(1000,1040)])
    db.execute('UPDATE grf SET c1=c1*1.003')
    events,ledger,rule=gait_events(db,'c1','l')
    assert [(r['start'],r['end']) for r in events]==[(98,298),(298,498),(498,998)]
    assert rule['minimum_contact_samples'] in (59,60)
    assert all(r['leg']=='l' for r in ledger)
    assert len([r for r in ledger if r['kind']=='contact'])==4


def test_threshold_ambiguity_refused():
    db=database(1000,[(100,150),(300,350),(500,550),(700,750),(900,950)])
    with pytest.raises(ValueError,match='threshold'):gait_events(db,'c1','l')


def test_no_contacts_is_explicit_empty_not_missing_force_pass():
    db=database(100,[]);events,ledger,rule=gait_events(db,'c1','r')
    assert events==[] and ledger==[] and rule['legacy_low_amplitude_BW_heuristic_triggered']
    db.execute('UPDATE grf SET c1=NULL')
    with pytest.raises(ValueError,match='No assessed'):gait_events(db,'c1','r')


def test_quantile_independent_interpolation():
    assert quantile([1.,2.,3.,4.],.25)==1.75
    assert quantile([1.,2.,3.,4.],.75)==3.25


def test_gait_segment_whole_record_offset_and_missingness():
    import numpy as np
    times=np.linspace(0,1,201)
    def read(kind,column,optional=False):
        if '_r_' in column:return None
        return np.full(201,{'foot':10.,'shank':20.,'thigh':30.}[column.split('_')[0]])
    expected=gait_segment_values(read,times,.005,{'l':-.25,'r':.1})
    for body,speed in [('foot',10.),('shank',20.),('thigh',30.)]:
        angle=expected[f'{body}_sagittal_angle_ipsi_rad']
        assert angle[0]==pytest.approx(-.25+speed*.005*np.pi/180)
        assert angle[-1]==pytest.approx(-.25+speed*1.005*np.pi/180)
        assert np.isnan(expected[f'{body}_sagittal_angle_contra_rad']).all()


def test_minimum_contact_interval_rejection_is_accounted():
    db=database(700,[(100,110),(130,140),(300,310),(500,510)]);db.execute('UPDATE grf SET c1=c1*1.003')
    events,ledger,rule=gait_events(db,'c1','r')
    rejected=[x for x in ledger if x['reason']=='minimum_contact_interval']
    assert [x['sample'] for x in rejected]==[128]
    assert [(e['start'],e['end']) for e in events]==[(98,298),(298,498)]


def test_walk_shuffle_transfer_and_unmapped_scope():
    from contributor_tools.audit_gt25_regular_source_v4 import task_identity
    assert task_identity('normal_walk_1_0task_shuffle_on')==('level_walking','level_0.4ms')
    assert task_identity('normal_walk_1_baseline_0-6_on')==('level_walking','level_0.6ms')
    assert task_identity('sit_to_stand_1_4t4s_short-arm_on')==('sit_to_stand','sit_to_stand')
    with pytest.raises(ValueError):task_identity('ball_toss_1_0task_center_on')


def test_full_clock_rejects_gap_between_tables_and_duplicate_samples():
    from contributor_tools.audit_gt25_regular_source_v4 import check_clocks
    db=sqlite3.connect(':memory:')
    for name in ('angle_filt','grf'):
        db.execute(f'CREATE TABLE {name}(i INTEGER,c0 REAL)')
        db.executemany(f'INSERT INTO {name} VALUES(?,?)',[(0,0.),(1,.005),(2,.01)])
    meta={name:{'rows':3} for name in ('angle_filt','grf')}
    assert check_clocks(db,meta)==3
    db.execute('UPDATE grf SET c0=.011 WHERE i=2')
    with pytest.raises(ValueError,match='differ'):check_clocks(db,meta)
    db.execute('UPDATE grf SET c0=.005 WHERE i=2')
    with pytest.raises(ValueError,match='invalid'):check_clocks(db,meta)


def test_metadata_speed_model_and_zero_slope_explicit_not_inferred_ramp():
    from contributor_tools.audit_gt25_regular_source_v4 import expected_task_metadata
    value=expected_task_metadata('normal_walk_1_4t4s_shuffle_on','r',False)
    assert value['speed_m_s']==.4 and value['model']=='4t4s' and value['leg']=='r' and value['incline_deg']==0.
    assert expected_task_metadata('walk_backward_1_baseline_1-0_on','l',False)['speed_m_s']==1.
    with pytest.raises(ValueError):expected_task_metadata('ramp_10deg_0task_on','l',False)
    with pytest.raises(ValueError):expected_task_metadata('normal_walk_1_0task_0-6_off','l',False)
