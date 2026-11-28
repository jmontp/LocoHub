"""Source exclusions must preserve subject and anatomical-side context."""
import importlib.util
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'contributor_tools/audit_probes/2026_10_20/check_gt24_invalid_torques.py'
spec=importlib.util.spec_from_file_location('gt24_invalid',path)
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_source_exclusions_reset_side_and_stop_at_next_section():
    text='''Due to a failure in one of the loadcells
- BT01 (Phase1)
    - Invalid left leg joint torques
        - trial_left
    - Invalid right leg joint torques (none)
- BT02
    - Invalid right leg joint torques
        - trial_right
///// OTHER NOTES /////
- BT03
    - Invalid right leg joint torques
        - not_in_failure_list
'''
    assert probe.invalid_trials(text)==[
        {'subject':'BT01','side':'left','recording':'trial_left'},
        {'subject':'BT02','side':'right','recording':'trial_right'},
    ]


def test_zero_and_infinity_are_not_missing_torques(tmp_path):
    source=tmp_path/'moment.csv'
    source.write_text('time,hip_flexion_r_moment,hip_flexion_l_moment\n0,NaN,1\n1,0,2\n2,inf,3\n')
    result=probe.inspect_csv(source,'right')
    assert result['invalid_side_columns']['hip_flexion_r_moment']=={'finite':1,'nan':1,'infinite':1}
    assert not result['documented_invalid_values_are_all_nan']
    assert result['opposite_side_finite_values']==3
