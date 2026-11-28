"""GT21-RB06 read-only evidence: source toe-off times against belt load onset/offset, one treadmill recording per participant."""
import json, resource, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.run_gt21_rb_pass import ROOTS, load_inventory  # noqa: E402
from contributor_tools.run_gt21_rb_segment import load_pass_ledger, read_pass_table  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402
LOAD_BW = 0.1


def ev(col, h):
    return h[np.flatnonzero(np.diff(col) < -50) + 1]


def main(out):
    inv = load_inventory()
    res = {}
    for sj in sorted({k[0] for k in inv}):
        rec = sorted(r for (s, m, r) in inv if s == sj and m == 'treadmill')[0]
        r = inv[(sj, 'treadmill', rec)]
        base = ROOTS[r['source']] / sj / r['session'] / 'treadmill'
        g = {l: src.read_numeric_table(base / d / f'{rec}.mat') for l, d in (('left', 'gcLeft'), ('right', 'gcRight'))}
        root, rows = load_pass_ledger(sj)
        tb = read_pass_table(root, rows[('treadmill', rec)])
        t = tb['time_s']
        o = {'recording': rec, 'toe_off_columns_identical': bool(np.array_equal(g['left']['ToeOff'], g['right']['ToeOff'], equal_nan=True))}
        for leg in ('left', 'right'):
            h = np.asarray(g[leg]['Header'], float)
            hs, to = ev(np.asarray(g[leg]['HeelStrike'], float), h), ev(np.asarray(g[leg]['ToeOff'], float), h)
            loaded = np.nan_to_num(tb[f'grf_vertical_{leg}_BW']) > LOAD_BW
            d = np.diff(np.r_[0, loaded.astype(int), 0])
            on, off = t[np.flatnonzero(d == 1)], t[np.minimum(np.flatnonzero(d == -1), len(t) - 1)]
            # per step: source toe off (first inside the step) offset from the nearest belt load offset, and stance/loaded fractions
            frs, frl, dto = [], [], []
            for i in range(len(hs) - 1):
                a, b = hs[i], hs[i + 1]
                k = to[(to > a) & (to < b)]
                if k.size:
                    frs.append((k[0] - a) / (b - a))
                    j = np.argmin(np.abs(off - k[0])); dto.append(float(off[j] - k[0]))
                m = (t >= a) & (t < b)
                if m.any():
                    frl.append(float(loaded[m].mean()))
            o[leg] = {'source_toe_off_fraction_median': float(np.median(frs)) if frs else None,
                      'belt_loaded_fraction_median': float(np.median(frl)) if frl else None,
                      'belt_load_offset_minus_source_toe_off_s_median': float(np.median(dto)) if dto else None,
                      'steps': len(hs) - 1}
        res[sj] = o
        print(sj, rec, o['left']['source_toe_off_fraction_median'], o['left']['belt_loaded_fraction_median'], o['right']['source_toe_off_fraction_median'],
              o['right']['belt_loaded_fraction_median'], file=sys.stderr, flush=True)
    res['peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
