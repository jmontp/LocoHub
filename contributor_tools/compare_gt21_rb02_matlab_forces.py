"""GT21-RB02 acceptance: compare the Python merged pass forces with the MATLAB-fixed pilot forces.

Read-only probe (AGENTS.md exception): one recording at a time, bounded reads, nothing written under converted_datasets/ or the
source folders; run under ``prlimit --as``, nice 19, ionice idle, one thread, ARROW_DEFAULT_MEMORY_POOL=system.

Inputs: the MATLAB-fixed phase files (converted_datasets/reconversion_v2/gt21_force_corrected_full_20261021/AB06/**/phase.parquet,
150 samples per cycle at linspace(source_start_time_s, source_end_time_s, 150), forces in BW from 1000 Hz plates interpolated
linearly at those times) and the Python pass batch for AB06 (continuous 200 Hz table on the marker clock). Both are put on the same
grid the same way: the Python table is linearly interpolated at the MATLAB cycle's target times (numpy interp; NaN where either
neighbour is not finite).

Sign mapping. Vertical and anterior share one convention. MATLAB sideways force is the lab-X value for both legs; the Python
pass is outward per leg, so Python = (-s if right leg else +s) x MATLAB with s the sign of the mean pelvis forward lab-Z over the
cycle (from the Python table). CoP is not compared: the MATLAB files hold the old lateral-malleolus lab-offset CoP.

Reported: finite pairs, the share within 1e-9 BW, the largest and median differences, cycles whose 150 target times all fall on
the 200 Hz grid (no interpolation difference possible), the two end samples of every cycle (always on the 200 Hz grid when the
cycle starts and ends on source samples), and every MATLAB-missing/Python-present or reverse pair counted by cause class.
No scientific approval is claimed.
"""
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

MATLAB = ROOT / 'converted_datasets/reconversion_v2/gt21_force_corrected_full_20261021/AB06'
PASS = ROOT / 'converted_datasets/reconversion_v2/gt21_rb_pass_batch_AB06_20261124/AB06'
OUT = ROOT / 'docs/quality/audits/gt21-rb02-matlab-force-comparison.json'
TOL = 1e-9
LOADED_BW = 0.002          # a foot with more than about 1.5 N on its plate counts as loaded
CH = ('vertical', 'anterior', 'lateral')


def interp(t_new, t, y):
    out = np.full(len(t_new), np.nan)
    j = np.clip(np.searchsorted(t, t_new, side='right') - 1, 0, len(t) - 2)
    inside = (t_new >= t[0]) & (t_new <= t[-1])
    t0, t1, y0, y1 = t[j], t[j + 1], y[j], y[j + 1]
    with np.errstate(invalid='ignore', divide='ignore'):
        w = (t_new - t0) / (t1 - t0)
        v = np.where(t_new == t0, y0, y0 + w * (y1 - y0))
    out[inside] = v[inside]
    return out


def main():
    stats = {}
    strata = {}
    classes = {}
    exact_cycles = {'cycles': 0, 'max_abs_diff': 0.0, 'pairs': 0}
    ends = {'pairs': 0, 'max_abs_diff': 0.0, 'within_tol': 0}
    sign_rule = {'cycles_checked': 0, 'cycles_with_factor_mismatch': 0}
    worst = []
    recordings = []
    for f in sorted(MATLAB.glob('*/*/*/phase.parquet')):
        mode, rec = f.parts[-3], f.parts[-2]
        mine_path = PASS / mode / f'{rec}.parquet'
        if not mine_path.exists():
            recordings.append({'recording': f'{mode}/{rec}', 'skipped': 'not converted by the pass'})
            continue
        m = pq.read_table(f, use_threads=False, columns=['observation_id', 'reference_side', 'source_start_time_s', 'source_end_time_s'] +
                          [f'grf_{c}_{p}_BW' for c in CH for p in ('ipsi', 'contra')]).to_pandas()
        mine = pq.read_table(mine_path, use_threads=False).to_pandas()
        t = mine['time_s'].to_numpy()
        rec_stats = {'cycles': 0}
        for oid, g in m.groupby('observation_id', sort=False):
            side = g['reference_side'].iloc[0]
            t0, t1 = float(g['source_start_time_s'].iloc[0]), float(g['source_end_time_s'].iloc[0])
            tt = np.linspace(t0, t1, 150)
            on_grid = np.abs(np.interp(tt, t, np.arange(len(t))) - np.rint(np.interp(tt, t, np.arange(len(t))))) < 1e-9 * 200
            fwd = mine['pelvis_forward_lab_z'].to_numpy()[(t >= t0) & (t <= t1)]
            s = np.sign(np.nanmean(fwd)) if fwd.size and np.isfinite(fwd).any() else np.nan
            rec_stats['cycles'] += 1
            for part, leg in (('ipsi', side), ('contra', 'left' if side == 'right' else 'right')):
                for c in CH:
                    a = g[f'grf_{c}_{part}_BW'].to_numpy(float)
                    b = interp(tt, t, mine[f'grf_{c}_{leg}_BW'].to_numpy(float))
                    if c == 'lateral':
                        fac = (-s if leg == 'right' else s)
                        a = a * fac
                        sign_rule['cycles_checked'] += 1
                    fin = np.isfinite(a) & np.isfinite(b)
                    key = (mode, c)
                    st = stats.setdefault(key, {'pairs': 0, 'within_tol': 0, 'max_abs_diff': 0.0, 'diffs': []})
                    d = np.abs(a[fin] - b[fin])
                    st['pairs'] += int(fin.sum())
                    st['within_tol'] += int((d <= TOL).sum())
                    if d.size:
                        st['max_abs_diff'] = max(st['max_abs_diff'], float(d.max()))
                        st['diffs'].append(np.percentile(d, 50))
                    cls = classes.setdefault(mode, {'both_finite': 0, 'matlab_missing_python_present': 0,
                                                    'matlab_present_python_missing': 0, 'both_missing': 0})
                    cls['both_finite'] += int(fin.sum())
                    cls['matlab_missing_python_present'] += int((~np.isfinite(a) & np.isfinite(b)).sum())
                    cls['matlab_present_python_missing'] += int((np.isfinite(a) & ~np.isfinite(b)).sum())
                    cls['both_missing'] += int((~np.isfinite(a) & ~np.isfinite(b)).sum())
                    e = np.array([0, 149])
                    ef = fin[e] & on_grid[e]
                    if ef.any():
                        de = np.abs(a[e][ef] - b[e][ef])
                        ends['pairs'] += int(ef.sum())
                        ends['within_tol'] += int((de <= TOL).sum())
                        ends['max_abs_diff'] = max(ends['max_abs_diff'], float(de.max()))
                    loaded = g[f'grf_vertical_{part}_BW'].to_numpy(float) > LOADED_BW
                    for name, sel in (('loaded', loaded), ('unloaded', ~loaded)):
                        ss = fin & sel
                        dd = np.abs(a[ss] - b[ss])
                        agg = strata.setdefault(('all_cycles', name, c), {'pairs': 0, 'within_tol': 0, 'max': 0.0})
                        agg['pairs'] += int(ss.sum()); agg['within_tol'] += int((dd <= TOL).sum())
                        agg['max'] = max(agg['max'], float(dd.max()) if dd.size else 0.0)
                        if on_grid.all():
                            agg = strata.setdefault(('on_grid_cycles', name, c), {'pairs': 0, 'within_tol': 0, 'max': 0.0})
                            agg['pairs'] += int(ss.sum()); agg['within_tol'] += int((dd <= TOL).sum())
                            agg['max'] = max(agg['max'], float(dd.max()) if dd.size else 0.0)
                    if on_grid.all() and fin.any():
                        exact_cycles['pairs'] += int(fin.sum())
                        exact_cycles['max_abs_diff'] = max(exact_cycles['max_abs_diff'], float(d.max()))
                        if c == 'vertical' and part == 'ipsi':
                            exact_cycles['cycles'] += 1
                    if d.size and d.max() > 0.05:
                        worst.append({'observation_id': oid, 'leg': leg, 'channel': c, 'max_abs_diff': round(float(d.max()), 4)})
        recordings.append({'recording': f'{mode}/{rec}', **rec_stats})
    res = {k[0] + '/' + k[1]: {'pairs': v['pairs'], 'share_within_1e-9': (v['within_tol'] / v['pairs']) if v['pairs'] else None,
                               'max_abs_diff_BW': v['max_abs_diff'],
                               'median_of_cycle_medians_BW': float(np.median(v['diffs'])) if v['diffs'] else None}
           for k, v in sorted(stats.items())}
    out = {'task': 'GT21-RB02 force comparison', 'scientific_approval': False, 'tolerance_BW': TOL,
           'matlab_files': len([r for r in recordings if 'skipped' not in r]), 'recordings': recordings,
           'by_mode_channel': res, 'pair_classes_by_mode': classes,
           'cycles_with_all_150_targets_on_the_200Hz_grid': exact_cycles,
           'strata_loaded_vs_unloaded': {'/'.join(k): {**v, 'share_within_1e-9': (v['within_tol'] / v['pairs']) if v['pairs'] else None} for k, v in sorted(strata.items())},
           'cycle_end_samples_on_grid': ends, 'worst_cycles_over_0p05_BW': worst[:30], 'n_worst': len(worst),
           'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({'peak_rss_mib': out['peak_rss_mib'], 'n_files': out['matlab_files']}))


if __name__ == '__main__':
    main()
