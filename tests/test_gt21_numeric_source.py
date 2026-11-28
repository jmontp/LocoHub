"""Known numeric columns and fail-closed checks; no real dataset loads in tests."""
import numpy as np
import pytest
from scipy.io import savemat
from contributor_tools.gt21_numeric_source import numeric_columns, read_numeric_table

# Serialization metadata only; numeric test data below is synthetic.
LAYOUT=bytes.fromhex('0300000008000000600000008000000080000000b00000001001000020010000000000000000000064617461006e64696d73006e726f777300726f776e616d6573006e76617273007661726e616d65730070726f7073007461626c6500000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000010000000100000000000000000000000700000001000000010000000000000002000000010000000100000003000000010000000200000004000000010000000300000005000000010000000400000006000000010000000500000007000000010000000600000000000000000000000000000000000000')


def cells():
    result=[None]*11
    result[0]=np.frombuffer(LAYOUT,dtype=np.uint8)
    result[2]=np.empty((1,2),dtype=object)
    result[2][0,0]=np.array([[0.],[1.]])
    result[2][0,1]=np.array([[4.],[np.nan]])
    result[3]=np.array([[2.]])
    result[4]=np.array([[2.]])
    result[5]=np.empty((0,0),dtype=object)
    result[6]=np.array([[2.]])
    result[7]=np.empty((1,2),dtype=object)
    result[7][0,0]=np.array(['Header'])
    result[7][0,1]=np.array(['Signal'])
    return result


def test_known_numeric_columns_preserve_values_and_missingness():
    result=numeric_columns(cells())
    assert list(result)==['Header','Signal']
    np.testing.assert_array_equal(result['Header'],[0.,1.])
    np.testing.assert_array_equal(result['Signal'],[4.,np.nan])


@pytest.mark.parametrize('fault',['metadata','names','dtype','clock','rows'])
def test_unsupported_layout_is_rejected(fault):
    data=cells()
    if fault=='metadata':data[0]=np.zeros(288,dtype=np.uint8)
    elif fault=='names':data[7][0,1]=np.array(['Header'])
    elif fault=='dtype':data[2][0,1]=np.ones((2,1),dtype=np.int32)
    elif fault=='clock':data[2][0,0]=np.array([[1.],[0.]])
    elif fault=='rows':data[4]=np.array([[3.]])
    with pytest.raises(ValueError):numeric_columns(data)


def test_ordinary_mat_and_oversized_inputs_are_not_admitted(tmp_path):
    path=tmp_path/'ordinary.mat';savemat(path,{'data':np.ones((2,2))})
    with pytest.raises(ValueError):read_numeric_table(path)
    with pytest.raises(MemoryError):read_numeric_table(path,max_source_bytes=1)
