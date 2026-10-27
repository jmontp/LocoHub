"""Small synthetic clocks/axes; no OpenSim or research arrays loaded."""
import csv
import math
import pytest
from contributor_tools import audit_mblue_orientation_pose_pilot as audit
from contributor_tools.prepare_mblue_orientation_pose_pilot import windows


def test_windows_path_matches_guard_prefix():
    result = windows('/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/synthetic/options.json')
    assert result == r'S:\workspace\locomotion-data-standardization\converted_datasets\reconversion_v2\synthetic\options.json'
    assert result.startswith('S:\\workspace\\locomotion-data-standardization\\converted_datasets\\reconversion_v2\\')
    assert '\\\\' not in result
    assert str(audit.linux(result)).endswith('/synthetic/options.json')


@pytest.fixture
def output(tmp_path):
    path = tmp_path/'axes.csv'
    rows = [[t, 1, 0, 0] + [value for b in audit.BODIES for value in
        ([1, 0, 0, 0] if b.startswith('calcn') else [0, -1, 0, 0])] for t in (1., 1.5, 2.)]
    def write(rows=rows):
        with path.open('w') as stream:
            writer = csv.writer(stream); writer.writerow(audit.COLUMNS); writer.writerows(rows)
        return path
    return rows, write


def test_valid_axes_and_exact_window(output):
    _, write = output
    assert audit.verify_csv(write(), [1., 1.5, 2.]) == 3


@pytest.mark.parametrize('kind', ['clock', 'axis', 'heading', 'angle', 'missing', 'extra'])
def test_corruption_refused(output, kind):
    rows, write = output
    if kind == 'clock': rows[1][0] = 1.6
    if kind == 'axis': rows[0][4] = 5
    if kind == 'heading': rows[0][2] = .1
    if kind == 'angle': rows[0][7] = .2
    if kind == 'missing': rows.pop()
    if kind == 'extra': rows.append(rows[-1])
    with pytest.raises(ValueError): audit.verify_csv(write(rows), [1., 1.5, 2.])


def test_degenerate_axis_requires_nan(output):
    rows, write = output
    rows[0][4:8] = [0, 0, 1, math.nan]
    assert audit.verify_csv(write(rows), [1., 1.5, 2.]) == 3
    rows[0][7] = 0
    with pytest.raises(ValueError, match='Undefined'): audit.verify_csv(write(rows), [1., 1.5, 2.])


def test_source_clock_reads_inclusive_window_only(tmp_path):
    path = tmp_path/'synthetic.mot'
    path.write_text('synthetic\ninDegrees=yes\nendheader\ntime coordinate\n0 90\n1 90\n1.5 90\n2 90\n3 90\n')
    assert audit.source_clock(path, 1, 2) == [1, 1.5, 2]
    path.write_text('endheader\ntime coordinate\n1 90\n1 90\n')
    with pytest.raises(ValueError, match='clock'): audit.source_clock(path, 1, 2)


def test_changed_binding_refused(tmp_path):
    path = tmp_path/'code.py'; path.write_text('original')
    bindings = {str(path):audit.digest(path)}
    audit.recheck(bindings)
    path.write_text('changed')
    with pytest.raises(ValueError, match='Changed'): audit.recheck(bindings)


def test_audit_binds_native_status_and_source_clock(tmp_path, monkeypatch, output):
    import json
    from pathlib import Path
    rows, write = output
    csv_path = write()
    root = tmp_path/'pilot'; root.mkdir()
    (root/'body_axes.csv').write_bytes(csv_path.read_bytes())
    source = tmp_path/'synthetic.mot'
    source.write_text('endheader\ntime coordinate\n1 90\n1.5 90\n2 90\n')
    model = tmp_path/'synthetic.osim'; model.write_text('synthetic')
    options_path = root/'options.json'
    options = {'output_path':str(root/'body_axes.csv'), 'ik_path':str(source),
               'model_path':str(model), 'start_s':1, 'end_s':2}
    options_path.write_text(json.dumps(options))
    monkeypatch.setattr(audit, 'linux', Path)
    sources = (source, model, options_path, Path(audit.__file__).resolve())
    plan = root/'plan.json'
    plan.write_text(json.dumps({'status':'prepared_not_executed',
        'inputs_sha256':{str(p):audit.digest(p) for p in sources}}))
    (root/'native_status.json').write_text(json.dumps({'status':'completed','exit_code':0,'options':str(options_path)}))
    result = audit.audit(plan)
    assert result['rows_checked'] == 3
    assert result['scientific_approval'] is False
    assert str(plan) in result['inputs_sha256']
    with pytest.raises(ValueError, match='Existing'): audit.audit(plan)


def test_changed_input_refuses_before_native_launch(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    source = tmp_path/'source'; source.write_text('original')
    plan = tmp_path/'plan.json'
    plan.write_text(json.dumps({'status':'prepared_not_executed', 'inputs_sha256':{
        str(Path(audit.__file__).resolve()):audit.digest(audit.__file__), str(source):audit.digest(source)}}))
    source.write_text('changed')
    def forbidden(*args, **kwargs):
        pytest.fail('Native launch occurred before binding check')
    monkeypatch.setattr(audit.subprocess, 'run', forbidden)
    with pytest.raises(ValueError, match='Changed'): audit.audit(plan, run=True)
    assert not (tmp_path/'pose_attempt.json').exists()
