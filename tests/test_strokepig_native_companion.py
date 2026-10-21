"""Synthetic source companions preserve values without assuming biomechanics."""
import json

import numpy as np
import pyarrow.parquet as pq
import pytest

from contributor_tools import reconvert_strokepig_native as native


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / 'raw'
    folder = root / 'TVC47'
    folder.mkdir(parents=True)
    (folder / 'BWA (0).c3d').write_bytes(b'synthetic fixture, decoded by test double')
    values = np.array([[[1000., 2000., np.nan]], [[3., 4., 5.]],
                       [[6., 7., 8.]], [[0., -1., 0.]]])
    decoded = {'header': {'points': {'frame_rate': 100., 'first_frame': 815, 'last_frame': 817}},
        'data': {'points': values}, 'parameters': {
            'POINT': {'LABELS': {'value': ['LKneeMoment']},
                      'MOMENTS': {'value': ['LKneeMoment']}, 'MOMENT_UNITS': {'value': ['Nmm']}},
            'EVENT': {'TIMES': {'value': np.array([[0.], [8.17]])},
                      'LABELS': {'value': ['Foot Strike']}, 'CONTEXTS': {'value': ['Left']}},
            'PROCESSING': {'Bodymass': {'value': [72.]}}}}
    monkeypatch.setattr(native.ezc3d, 'c3d', lambda _: decoded)
    return root, decoded


def test_original_values_residual_clock_and_events_survive(source, tmp_path):
    root, decoded = source
    out = tmp_path / 'out'
    report = native.export(root, 'TVC47/BWA (0).c3d', out)
    table = pq.read_table(out / 'source_time.parquet')
    np.testing.assert_allclose(table['time_s'].to_numpy(), [8.16, 8.17, 8.18])
    for i, suffix in enumerate(['component_1', 'component_2', 'component_3', 'residual']):
        np.testing.assert_equal(table[f'LKneeMoment__{suffix}'].to_numpy(), decoded['data']['points'][i, 0])
    assert report['source_events']['TIMES'] == [[0.], [8.17]]
    assert report['channels'][0]['c3d_declared_group_units'] == ['Nmm']
    assert report['affected_side'] == 'unknown'
    assert report['scientific_approval'] is False
    assert report['source_recording_id'].endswith('TVC47/BWA (0).c3d')
    assert json.loads(table.schema.metadata[b'locohub_source'])['source_sha256'] == report['source_sha256']
    with pytest.raises(FileExistsError):
        native.export(root, 'TVC47/BWA (0).c3d', out)


def test_ambiguous_labels_rejected_before_output(source, tmp_path):
    root, decoded = source
    decoded['parameters']['POINT']['LABELS']['value'] = ['LKneeMoment', 'LKneeMoment']
    with pytest.raises(ValueError, match='Ambiguous'):
        native.export(root, 'TVC47/BWA (0).c3d', tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_recording_cannot_escape_source_root(source, tmp_path):
    root, _ = source
    with pytest.raises(ValueError, match='within source root'):
        native.export(root, '../outside.c3d', tmp_path / 'out')
