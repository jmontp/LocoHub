"""Independent fixtures for unpaired UM21 transfer preservation."""
import h5py
import numpy as np
import pytest
from contributor_tools.reconvert_umich_transfers import transfer_frame


def test_transfer_keeps_source_values_without_bilateral_or_timing_claims(tmp_path):
    with h5py.File(tmp_path/'source.h5', 'w') as file:
        group=file.create_group('sit2stand')
        values=np.arange(2*3*150,dtype=float).reshape(2,3,150)
        values[1,1,25]=np.nan
        group.create_dataset('jointAngles/HipAngles',data=values)
        frame=transfer_frame(group,'AB01','sit2stand',1)
        assert len(frame)==150
        assert frame.observation_id.iloc[0].endswith(':source_curve:2')
        assert frame.reference_side.eq('unknown').all()
        assert frame.time_s.isna().all()
        assert not any('_contra_' in name or 'velocity' in name for name in frame)
        for plane in range(3):
            np.testing.assert_array_equal(frame[f'source_jointAngles_HipAngles_plane{plane+1}'],values[1,plane])
        assert transfer_frame(group,'AB02','sit2stand',1).observation_id.iloc[0]!=frame.observation_id.iloc[0]


def test_transfer_rejects_incompatible_source_shapes(tmp_path):
    with h5py.File(tmp_path/'source.h5','w') as file:
        file.create_dataset('jointAngles/HipAngles',data=np.zeros((2,3,149)))
        with pytest.raises(ValueError,match='Unexpected source dimensions'):
            transfer_frame(file,'AB01','sit2stand',0)
