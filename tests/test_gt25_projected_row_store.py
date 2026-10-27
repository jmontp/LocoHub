"""Synthetic CSV fixtures only; no GT25 source recordings are read."""
import math
import hashlib
import pytest
from contributor_tools import gt25_projected_row_store as store


def test_projection_across_chunks_preserves_absolute_window_and_nan(tmp_path):
    csv=tmp_path/'source.csv';csv.write_bytes(b'time,wanted,unused\r\n0,1,text\r\n1,,text\r\n2,-0,text\r\n3,4,text\r\n4,5,text\r\n')
    report=store.build(csv,tmp_path/'spool',['time','wanted'],chunk_rows=2)
    assert report['source_sha256']==hashlib.sha256(csv.read_bytes()).hexdigest()
    rows=store.Store(tmp_path/'spool')
    assert rows.window(2,4)==[(2.,-0.),(3.,4.),(4.,5.)]
    assert math.isnan(rows.window(1,1)[0][1])
    assert math.copysign(1,rows.window(2,2)[0][1])==-1
    assert [index for index,_ in rows.iter_rows(2)]==[0,1,2,3,4]
    with pytest.raises(FileExistsError):store.build(csv,tmp_path/'spool',['time'])


@pytest.mark.parametrize('text',['time,x\n0,1\n0,2\n','time,x\n0,1\nnan,2\n','time,x,x\n0,1,2\n1,2,3\n','time,x\n0,1,2\n1,2\n'])
def test_bad_clock_schema_or_width_fails_closed(tmp_path,text):
    csv=tmp_path/'bad.csv';csv.write_text(text)
    with pytest.raises(ValueError):store.build(csv,tmp_path/'out',['time','x'],chunk_rows=1)
    assert not (tmp_path/'out/metadata.json').exists()


def test_cross_file_clock_mismatch_and_window_admission(tmp_path):
    stores={}
    for i,times in enumerate(([0,1,2],[0,1.1,2])):
        path=tmp_path/f'{i}.csv';path.write_text('time,x\n'+'\n'.join(f'{t},9' for t in times)+'\n')
        store.build(path,tmp_path/f's{i}',['time','x']);stores[i]=store.Store(tmp_path/f's{i}')
    with pytest.raises(ValueError,match='clocks'):store.aligned_windows(stores,0,2)
    with pytest.raises(ValueError):stores[0].window(-1,1)
    with pytest.raises(ValueError):stores[0].window(0,store.MAX_WINDOW_ROWS)


def test_selected_columns_cover_transfer_and_gait():
    assert len(store.projection('imu_sim',transfer=True))==19
    assert len(store.projection('imu_sim'))==7
    assert store.projection('power')==['time']
    assert len(store.projection('velocity'))==5


def test_store_rejects_same_size_corruption(tmp_path):
    csv=tmp_path/'source.csv';csv.write_text('time,x\n0,1\n1,2\n')
    store.build(csv,tmp_path/'spool',['time','x'])
    path=tmp_path/'spool/rows.f64';data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
    with pytest.raises(ValueError,match='hash'):store.Store(tmp_path/'spool')
