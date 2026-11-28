"""Synthetic metadata-only full-scope fixtures."""
import pytest
from contributor_tools.plan_gt23_full_source_restoration import CHANNELS,scope


def evidence():
    windows=[{'subject':'AB99','parsing':'one_left_parsing.mat','recording':'one','has_intervals':True},
             {'subject':'AB99','parsing':'one_right_parsing.mat','recording':'one','has_intervals':False}]
    members=[{'name':f'AB99/CSV_Data/{record}/{channel}','crc32':1,'uncompressed_size':100} for record in ('one','not_parsed') for channel in CHANNELS]
    return windows,members,{('AB99','one'),('AB99','not_parsed')}


def test_unparsed_recording_not_silently_dropped_or_given_cycles():
    d=scope(*evidence())
    assert d['parsing_inventory_entries']==2 and d['raw_recordings']==2 and d['unmapped_raw_recordings']==1
    assert d['empty_parsing_entries']==1 and d['published_csv_files']==20
    assert next(r for r in d['records'] if r['recording']=='not_parsed')['nonempty_parsing_files']==[]


@pytest.mark.parametrize('damage',['missing_folder','missing_channel','duplicate_channel','missing_recording','duplicate_window'])
def test_scope_corruption_rejected(damage):
    w,p,f=evidence()
    if damage=='missing_folder':f.remove(('AB99','not_parsed'))
    elif damage=='missing_channel':p.pop()
    elif damage=='duplicate_channel':p.append(p[0])
    elif damage=='missing_recording':w[0]['recording']='not_in_source'
    else:w.append(w[0])
    with pytest.raises(ValueError):scope(w,p,f)
