"""Synthetic scalar FileInfo export fixtures; no MAT source reads."""
import pytest
from contributor_tools.export_mblue_fileinfo_metadata import select_fields


def info():
    return {'subject': 'SYN', 'date': '01012020',
            'bare': {'stairs': {'vicon_filename': 'bare_stairs'}},
            'exo': {'level_1x0': {'filename_suffix': 'level'}}}


def test_source_date_and_config_filenames_preserved():
    result = select_fields('SYN', info(), [('bare', 'stairs'), ('exo', 'level_1x0')])
    assert result == {'date': '01012020', 'tasks': {
        'bare': {'stairs': {'vicon_filename': 'bare_stairs'}},
        'exo': {'level_1x0': {'filename_suffix': 'level'}}}}


@pytest.mark.parametrize('field,value', [('subject', 'OTHER'), ('date', 'latest'),
                                        ('date', '../01012020'), ('date', ['01012020'])])
def test_bad_source_identity_or_date_rejected(field, value):
    source = info(); source[field] = value
    with pytest.raises(ValueError):
        select_fields('SYN', source, [('bare', 'stairs')])


def test_unknown_condition_rejected():
    with pytest.raises(ValueError):
        select_fields('SYN', info(), [('unknown', 'stairs')])
