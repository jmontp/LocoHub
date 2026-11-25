import pyarrow as pa; pa.set_cpu_count(1); pa.set_io_thread_count(1)
import numpy as np,pyarrow.parquet as pq,json
R='/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/'
for s,m,r,x,a,n in [('AB12','treadmill_06_01','left',15892,93,0),('AB12','treadmill_07_01','left',15050,91,0)]:
    pass
for s,m,x,a,n in [('AB12','treadmill_06_01','left',15892,93),('AB12','treadmill_07_01','left',15050,91)]:
    t=pq.read_table(R+f'gt21_rb_pass_batch_{s}_20261124/{s}/treadmill/{m}.parquet',columns=['time_s','stance_left','plate_loaded_left','grf_vertical_left_BW','stance_right','grf_vertical_right_BW'],use_threads=False)
    v=t['grf_vertical_left_BW'].to_numpy(); st=t['stance_left'].to_numpy(zero_copy_only=False); vr=t['grf_vertical_right_BW'].to_numpy(); pl=t['plate_loaded_left'].to_numpy(zero_copy_only=False)
    sl=slice(a-5,a+n+5)
    print(s,m,'left v(BW) stance',np.round(v[sl][::4],2).tolist()); print(' stance flag',st[sl][::4].astype(int).tolist()); print(' right v',np.round(vr[sl][::4],2).tolist()); print(' plate_loaded_left',pl[sl][::4].astype(int).tolist())
