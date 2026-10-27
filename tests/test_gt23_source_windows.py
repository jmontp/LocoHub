"""Exact source excerpts and time-axis admission without whole-file data loads."""
import hashlib
import pytest
from contributor_tools.prepare_gt23_recording import copy_csv_window, resolve_recording


def test_window_preserves_literal_samples_and_interpolation_neighbors(tmp_path):
    content=b'time,value\r\n0,0.0000001\r\n1,NaN\r\n2,-3.125000\r\n3,4\r\n4,5\r\n'
    source=tmp_path/'source.csv';source.write_bytes(content)
    output=tmp_path/'window.csv'
    result=copy_csv_window(source,output,1.2,2.8)
    assert output.read_bytes()==b'time,value\r\n1,NaN\r\n2,-3.125000\r\n3,4\r\n'
    assert result['source_sha256']==hashlib.sha256(content).hexdigest()
    assert (result['first_source_row'],result['last_source_row'],result['source_rows'])==(1,3,5)
    with pytest.raises(FileExistsError):copy_csv_window(source,output,1.2,2.8)


def test_invalid_source_clock_is_detected_even_after_requested_window(tmp_path):
    source=tmp_path/'source.csv';source.write_text('time,value\n0,1\n1,2\n2,3\n2,4\n')
    with pytest.raises(ValueError,match='strictly increasing'):
        copy_csv_window(source,tmp_path/'window.csv',.2,.8)


def test_recording_prefix_respects_numeric_boundaries(tmp_path):
    for name in ['sit_to_stand_1','sit_to_stand_1_2','sit_to_stand_1_20']:
        (tmp_path/name).mkdir()
    assert resolve_recording(tmp_path,'sit_to_stand_1_2_short-arm_parsing.mat')=='sit_to_stand_1_2'
    assert resolve_recording(tmp_path,'sit_to_stand_1_short-noarm_parsing.mat')=='sit_to_stand_1'
    with pytest.raises(ValueError,match='No source'):
        resolve_recording(tmp_path,'stairs_1_up_parsing.mat')
