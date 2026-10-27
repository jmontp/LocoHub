"""Source metadata semantics only; no research data loaded."""
import pytest
from contributor_tools.plan_gt25_unmapped_source_scope import classify,units


def test_source_tasks_are_preserved_without_invented_canonical_cycles():
 ball=classify('ball_toss_1_0task_left_on');assert ball['canonical_task'] is None and ball['source_protocol_load_lb']==15
 cut=classify('cutting_2_4t4s_right-fast_on');assert cut['source_trial_number']==2 and cut['source_nominal_turn_deg']==90 and cut['source_approach_description']=='fast running'
 start=classify('start_stop_2_4t4s_on');assert start['source_variant'] is None


@pytest.mark.parametrize('name',['ball_toss_1_0task_diagonal_on','cutting_1_baseline_left-medium_on','start_stop_1_4t4s_walk_on','normal_walk_1_0task_shuffle_on'])
def test_unreviewed_task_name_rejected(name):
 with pytest.raises(ValueError):classify(name)


def test_unknown_interaction_and_mass_denominator_remain_unassessed():
 assert units('exo','hip_angle_l_torque_interaction')['source_unit'] is None
 assert 'unresolved' in units('moment','hip_flexion_l_moment')['limitation']
 assert units('exo','insole_l_cop_x')['source_unit']=='unitless'
 assert units('exo_sim','insole_l_cop_x')['source_unit']=='m'
 assert units('grf','fp_l_force_y')['source_unit']=='N'
