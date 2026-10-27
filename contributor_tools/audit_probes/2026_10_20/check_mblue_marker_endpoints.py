"""Reproduce MBLUE's final stair-descent endpoint rule from original TRC markers."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import argparse
import json
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def five_point_slope(clock, values):
    """Derivative at the center of a quadratic least-squares fit on uniform time."""
    import numpy as np
    clock=np.asarray(clock);values=np.asarray(values)
    dt=np.diff(clock)
    if len(clock)<5 or not np.isfinite(clock).all() or not np.allclose(dt,dt[0],rtol=0,atol=1e-8) or dt[0]<=0:
        raise ValueError('Uniform increasing marker clock required')
    result=np.full(len(clock),np.nan)
    result[2:-2]=(-2*values[:-4]-values[1:-3]+values[3:-1]+2*values[4:])/(10*dt[0])
    result[1]=2*result[2]-result[3];result[0]=3*result[2]-2*result[3]
    result[-2]=2*result[-3]-result[-4];result[-1]=3*result[-3]-2*result[-4]
    return result


def endpoint_from_markers(clock, y, z, start):
    import numpy as np
    from scipy.signal import find_peaks
    vy=five_point_slope(clock,y);vz=five_point_slope(clock,z)
    peaks,_=find_peaks(-vz[start:],prominence=1000)
    if not len(peaks):raise ValueError('No qualifying midswing peak')
    swing=int(peaks[0])+start
    stance=np.flatnonzero(np.abs(vy[swing:])<50)
    if not len(stance):raise ValueError('No source-rule stance marker')
    stance=int(stance[0])+swing
    contact=np.flatnonzero(z[swing:]-z[stance]<1)
    if not len(contact):raise ValueError('No source-rule endpoint')
    end=int(contact[0])+swing
    if not np.isfinite(np.column_stack([y[start:end+1],z[start:end+1]])).all():
        raise ValueError('Missing marker positions in selected interval')
    return end,{'midswing_index':swing,'midstance_index':stance}


def read_markers(path):
    import pandas as pd
    if path.stat().st_size>128*1024**2:raise MemoryError('TRC exceeds bounded admission')
    with path.open() as stream:header=[next(stream) for _ in range(5)]
    if header[2].split()[4]!='mm':raise ValueError('Source rule expects marker positions in millimetres')
    names=header[3].split()[2:];columns={'time':1}
    for side,prefix in [('right','R'),('left','L')]:
        if names.count(prefix+'MET3')!=1:raise ValueError('Missing or ambiguous metatarsal marker')
        offset=2+3*names.index(prefix+'MET3')
        columns[side+'_y']=offset+1;columns[side+'_z']=offset+2
    frame=pd.read_csv(path,sep=r'\s+',skiprows=5,header=None,usecols=list(columns.values()))
    return {name:frame[index].to_numpy() for name,index in columns.items()}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recovery',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    import numpy as np
    recovery=json.loads(a.recovery.read_text());assert recovery['status']=='all_stair_reference_windows_recovered_unreviewed'
    a.output_root.mkdir(parents=True,exist_ok=False)
    source=Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Utility_TrialParsing')
    report={'status':'checking','scientific_approval':False,'recovery_sha256':digest(a.recovery),'probe_sha256':digest(Path(__file__)),
        'source_code_sha256':{str(p):digest(p) for p in [source/'getHeelstrikeWithoutForceplate.m',source/'num_deriv.m']},'records':[],
        'limitations':['Reproduces the source marker rule; does not independently validate physical heel contact',
            'Uniform-clock quadratic least-squares slopes are evaluated analytically; peak detection uses scipy.signal.find_peaks']}
    try:
        for rec in recovery['records']:
            candidate=next(c for c in rec['candidates'] if c['status']=='all_windows_matched')
            windows=[w for w in candidate['windows'] if not w['end_matches_same_side_force_event']]
            marker_path=Path(candidate['force_path']).with_suffix('.trc');markers=read_markers(marker_path);clock=markers['time']
            checked=[]
            for window in windows:
                start=np.flatnonzero(np.isclose(clock,window['source_event_start_s'],rtol=0,atol=1e-7))
                expected=np.flatnonzero(np.isclose(clock,window['source_event_end_s'],rtol=0,atol=1e-7))
                assert len(start)==len(expected)==1,'Recovered event not on marker clock'
                side=window['reference_side']
                actual,details=endpoint_from_markers(clock,markers[side+'_y'],markers[side+'_z'],int(start[0]))
                checked.append(dict(window,computed_end_index=actual,expected_end_index=int(expected[0]),
                                    matches=actual==int(expected[0]),**details))
            report['records'].append({'subject':rec['subject'],'condition':rec['condition'],'marker_path':str(marker_path),
                                      'marker_sha256':digest(marker_path),'windows':checked})
        matches=[w['matches'] for r in report['records'] for w in r['windows']]
        report.update(status='all_marker_endpoints_reproduced_unreviewed' if matches and all(matches) else 'marker_endpoint_mismatch',
                      windows_checked=len(matches),windows_matched=sum(matches))
    except Exception as error:report.update(status='failed',reason=str(error));raise
    finally:(a.output_root/'marker_endpoints.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','windows_checked','windows_matched')}))
    if report['status']!='all_marker_endpoints_reproduced_unreviewed':raise SystemExit(1)


if __name__=='__main__':main()
