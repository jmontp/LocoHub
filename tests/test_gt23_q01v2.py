"""GT23-Q01 v2 tests. SYNTHETIC fixtures (made-up recordings, known values); no scientific dataset is regenerated.
Checks the v2 rule: L2 on the time table only, mapped to the phase observations whose span contains the jump."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from contributor_tools import gt23_fixes as fx
from contributor_tools import run_gt23_e01 as rn1
from contributor_tools import run_gt23_e02 as rn2
from contributor_tools import run_gt23_q01_assessment as q
from contributor_tools import run_gt23_q01v2 as v2
from tests import test_gt23_e01 as t1
from tests import test_gt23_e02 as t2

STEP_AT = 200   # source sample of a real 60 degree step of the left foot in normal_walk_1 (not a wrap)


@pytest.fixture(scope='module')
def world(tmp_path_factory):
    base = tmp_path_factory.mktemp('gt23q01v2') / 'inputs'
    roots = t1.build_inputs(base)
    c06_root = Path(roots['c06'])
    ledger = [json.loads(line) for line in (c06_root / 'ledger.jsonl').read_text().splitlines()]
    for entry in ledger:
        rec = entry['recording']
        path = c06_root / f'{rec}.parquet'
        table = pq.read_table(str(path)).to_pandas()
        cols = t2.smooth_angles(len(table), wrap_in_left_foot=(rec == 'jump_1'))
        if rec == 'normal_walk_1':
            for name in ('foot_sagittal_angle_left_rad', 'ankle_dorsiflexion_angle_left_rad'):
                cols[name] = cols[name].copy()
                cols[name][STEP_AT:] += np.radians(60.0)
            cols['ankle_dorsiflexion_velocity_left_rad_s'] = fx.central_derivative(cols['ankle_dorsiflexion_angle_left_rad'])
        for k, v in cols.items():
            table[k] = v
        t1.write_parquet(path, {c: table[c].to_numpy() for c in table.columns})
        entry['output']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (c06_root / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in ledger))
    e01 = base.parent / 'e01'
    assert rn1.run(argparse.Namespace(subject=t1.SUBJECT, output_root=str(e01), records=None, base=str(base))) == 0
    mp = pytest.MonkeyPatch()
    mp.setattr(fx, 'STEP_UP_TASK', 'poses')
    mp.setattr(rn2, 'heel_evidence', lambda subject, rec, cols: {'left': {'loaded_samples': 1}, 'right': {'loaded_samples': 1}})
    e02 = base.parent / 'e02'
    assert rn2.run(argparse.Namespace(subject=t1.SUBJECT, output_root=str(e02), records=None, base=str(base))) == 0
    audit = base.parent / 'audit' / 'audit_report.json'
    audit.parent.mkdir()
    audit.write_text(json.dumps({'status': 'pass'}))
    rs = json.loads((e01 / 'run_summary.json').read_text())
    mp.setattr(q, 'root_for', lambda s: str(e01))
    mp.setattr(v2, 'e02_root', lambda s: str(e02))
    mp.setattr(v2, 'e02_audit', lambda s: str(audit))
    mp.setattr(q, 'source_fidelity', lambda s, root: {'e01_run_summary': rs, 'file_hashes': {}, 'e01_readback': {},
                                                       'unit_evidence': q.UNIT_EVIDENCE_TEXT})
    out = base.parent / 'q'
    a = v2.assess_participant(t1.SUBJECT, out)
    yield a, out, e01, e02
    mp.undo()


def entries(out):
    return [json.loads(line) for line in (out / 'observations.jsonl').read_text().splitlines()]


def test_composite_input_has_the_e01_observation_set(world):
    a, out, e01, e02 = world
    assert a['table_problems'] == []
    assert a['counts']['by_kind'] == {'individual_cycle': 3, 'transfer': 4, 'continuous_recording': 3}
    assert a['counts']['time']['rows'] == 3 * t1.N and a['counts']['phase']['rows'] == 7 * 150
    assert sorted(a['inputs']['superseded_e01_recordings']) == [f'{t1.SUBJECT}/jump_1', f'{t1.SUBJECT}/poses_1']


def test_time_table_jump_fails_and_maps_only_to_spans_that_contain_it(world):
    a, out, *_ = world
    es = {(e['table'], e['observation_id'], e['reference_side']): e for e in entries(out)}
    t = es[('time', f'{t1.SUBJECT}/normal_walk_1/continuous', 'none')]
    assert 'L2' in t['plausibility']['failed_limits'] and t['overall'] == 'failed'
    hit = es[('phase', f'{t1.SUBJECT}/normal_walk_1/L/0000100', 'left')]       # span 100..300 contains samples 199 and 200
    miss = es[('phase', f'{t1.SUBJECT}/normal_walk_1/L/0000300', 'left')]      # span 300..520 does not
    assert 'L2' in hit['plausibility']['failed_limits'] and hit['overall'] == 'failed'
    assert 'L2' not in miss['plausibility']['failed_limits']
    assert 'foot_sagittal_angle_ipsi_rad' in hit['plausibility']['failed_channels']
    assert a['l2_mapping']['time_l2_recordings'] == {f'{t1.SUBJECT}/normal_walk_1': 2}   # foot and ankle, one sample each


def test_mapped_failure_names_its_time_sample(world):
    a, out, *_ = world
    fails = [json.loads(line) for line in (out / 'failures.jsonl').read_text().splitlines()]
    mapped = [f for f in fails if f['table'] == 'phase' and f['limit'] == 'L2']
    assert mapped and all(f['mapped_from']['sample_index'] == STEP_AT for f in mapped)
    assert all(abs(abs(f['value']) - 60.0) < 1.0 for f in mapped)


def test_phase_observations_are_not_tested_for_l2_on_their_own_samples(world):
    a, out, *_ = world
    # the wrap in jump_1 is fixed, and no phase observation outside the mapped spans carries L2
    es = [e for e in entries(out) if e['table'] == 'phase' and 'L2' in e['plausibility']['failed_limits']]
    assert {e['observation_id'] for e in es} == {f'{t1.SUBJECT}/normal_walk_1/L/0000100', f'{t1.SUBJECT}/normal_walk_1/R/0000130'}


def test_jump_1_wrap_is_gone_after_e02(world):
    a, out, *_ = world
    es = {(e['table'], e['observation_id']): e for e in entries(out)}
    assert 'L2' not in es[('time', f'{t1.SUBJECT}/jump_1/continuous')]['plausibility']['failed_limits']


def test_step_up_hold_flag_and_not_checked_columns(world):
    a, out, *_ = world
    es = [e for e in entries(out) if e['source_recording_id'] == f'{t1.SUBJECT}/poses_1']
    assert es and all('step_up_cop_held' in e['limitations'] for e in es)
    assert all('cop_anterior_left_m' in e['plausibility']['channel_states'].get('not_checked_no_column', []) for e in es)
    assert not any('step_up_cop_held' in e['limitations'] for e in entries(out) if e['source_recording_id'].endswith('/jump_1'))
