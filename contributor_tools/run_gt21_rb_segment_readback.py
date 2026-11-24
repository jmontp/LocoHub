"""GT21-RB03 readback: a separate, read-only check of the 22 segmentation batches (not part of the frozen run code).

Independent of contributor_tools/gt21_rb_segment.py: step times, dispositions and the force mask are re-derived here with
their own scalar code from the source gait tables, the RB01 label rows and the merged-pass Parquet; only the source table
reader (data access) is shared. Reads one recording at a time, writes one JSON report (outside converted_datasets).

Checks
  accounting   inventory recordings = ledger recordings, one status each; steps.jsonl lines = ledger steps; unique step ids;
               one disposition each; local 16 participants reproduce 83,206 resets and 78,604 steps exactly
  identity     the 36 recordings of the old coverage report, step by step, against the old reasons
  terrain      eligible ramp/stair steps equal the source scalars and window labels; none defaulted
  mask         stored mask layer equals a fresh recomputation for EVERY converted recording; a scalar-loop recomputation
               for a seeded sample; no stance sample at or above 20 N is masked, every one below is
  authors      matched / extra / missed totals and offsets of the right-leg cutting
Usage: run_gt21_rb_segment_readback.py --batch-root-template ... --out FILE.json
"""
import argparse
import gc as pygc
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import random
import resource
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)
INVENTORY = ROOT / 'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123/recording_ledger.jsonl'
LABELS = ROOT / 'converted_datasets/reconversion_v2/gt21_rb01_labels_final_20261124'
PASS = 'converted_datasets/reconversion_v2/gt21_rb_pass_batch_{s}_20261124'
SEG = 'converted_datasets/reconversion_v2/gt21_rb_segment_batch_{s}_20261124'
COVERAGE = ROOT / 'converted_datasets/reconversion_v2/gt21_event_eligibility_review_20261021/source_coverage.json'
ROOTS = {'local_2024_copy_bundle': ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET',
         'extracted_2024_copy_zip': Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')}
LOCAL = ('AB06 AB07 AB08 AB09 AB10 AB11 AB13 AB14 AB16 AB18 AB20 AB21 AB24 AB25 AB27 AB30').split()
NEW = ('AB12 AB15 AB17 AB19 AB23 AB28').split()
MAPPED = {'levelground': {'walk', 'stand-walk', 'walk-stand'},
          'ramp': {'rampascent', 'rampdescent', 'walk-rampascent', 'rampascent-walk', 'walk-rampdescent', 'rampdescent-walk'},
          'stair': {'stairascent', 'stairdescent', 'walk-stairascent', 'stairascent-walk', 'walk-stairdescent', 'stairdescent-walk'}}
DISPOSITIONS = {'eligible', 'excluded', 'held'}


def peak_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def scalar_resets(pct):
    out = []
    for i in range(1, len(pct)):
        if pct[i] == 0 and pct[i - 1] > 0:
            out.append(i)
    return out


def jl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=20261127)
    args = ap.parse_args()
    out_path = Path(args.out)
    if out_path.exists():
        raise SystemExit('output exists')
    inv = {(r['subject'], r['mode'], r['recording']): r for r in jl(INVENTORY)}
    rep = {'scientific_approval': False, 'failures': []}
    fail = rep['failures']
    cover = json.loads(COVERAGE.read_text())['recordings']
    old = {(c['record']['subject'], c['record']['mode'], c['record']['recording'].replace('.mat', '')): c['source_pairs'] for c in cover}
    labels = {}
    by_mode = defaultdict(Counter)
    reasons = defaultdict(Counter)
    by_part = {}
    mask_tot = {'left': Counter(), 'right': Counter()}
    mask_by_mode = defaultdict(Counter)
    fcheck = defaultdict(Counter)
    offs_hs, offs_to = [], []
    auth = Counter()
    auth_off = []
    auth_class = Counter()
    stair = {'recordings': 0, 'recordings_with_eligible': 0, 'steps': 0, 'eligible': 0, 'straddle': 0, 'idle_or_unmapped': 0}
    rec_status = Counter()
    rec_by_mode = defaultdict(Counter)
    resets_local = pairs_local = 0
    resets_new = pairs_new = 0
    seen_rec = set()
    ident = {'recordings': 0, 'steps': 0, 'eligible_levelground': 0, 'old_exported_or_opposite': 0, 'old_outside': 0,
             'disagree': [], 'treadmill_steps': 0, 'treadmill_old_exported_or_opposite': 0}
    terrain = {'eligible_ramp_stair_steps': 0, 'mismatches': [], 'recordings_with_terrain_value': 0}
    mask_check = {'layers_compared': 0, 'layer_mismatch': [], 'masked_samples_total': 0, 'stance_samples_total': 0,
                  'masked_stance_at_or_above_20N': 0, 'unmasked_stance_below_20N': 0}
    ids = set()
    bwmap = {}
    sample_pool = []
    for s in LOCAL + NEW:
        root = ROOT / SEG.format(s=s)
        led = list(jl(root / 'ledger.jsonl'))
        labels_s = {(r['mode'], r['recording']): r for r in jl(LABELS / s / f'labels_{s}.jsonl')}
        bwmap[s] = {(r['mode'], r['recording']): r.get('body_weight_N') for r in jl(ROOT / PASS.format(s=s) / 'ledger.jsonl')}
        inv_s = {k for k in inv if k[0] == s}
        got = {(e['subject'], e['mode'], e['recording']) for e in led}
        if got != inv_s or len(led) != len(inv_s):
            fail.append(f'{s}: ledger recordings differ from inventory ({len(got)} vs {len(inv_s)})')
        n_steps_led = sum(e.get('steps', 0) for e in led)
        part = Counter()
        n_lines = 0
        # steps per recording
        per_rec = defaultdict(list)
        for st in jl(root / 'steps.jsonl'):
            n_lines += 1
            hid = hash(st['step_id'])
            if hid in ids:
                fail.append(f"duplicate step id {st['step_id']}")
            ids.add(hid)
            if st['disposition'] not in DISPOSITIONS:
                fail.append(f"bad disposition {st['step_id']}")
            if st['disposition'] == 'eligible' and st['reason'] is not None:
                fail.append(f"eligible with reason {st['step_id']}")
            if st['disposition'] != 'eligible' and not st['reason']:
                fail.append(f"no reason {st['step_id']}")
            per_rec[(st['mode'], st['recording'])].append({k: st[k] for k in ('step_id', 'leg', 'start_s', 'end_s', 'disposition', 'reason', 'label', 'incline_deg', 'stair_height_m')})
            by_mode[st['mode']][st['disposition']] += 1
            reasons[st['mode']][st['reason'] or 'eligible'] += 1
            part[st['disposition']] += 1
            fc = st.get('force_check')
            if fc:
                fcheck[st['mode']][fc['status']] += 1
                if fc['offset_ms'] is not None:
                    offs_hs.append(fc['offset_ms'])
                if fc.get('toe_off_offset_ms') is not None:
                    offs_to.append(fc['toe_off_offset_ms'])
            if st['mode'] == 'stair':
                stair['steps'] += 1
                stair['eligible'] += st['disposition'] == 'eligible'
                stair['straddle'] += st['reason'] == 'straddles_label_windows'
                stair['idle_or_unmapped'] += bool(st['reason'] and st['reason'].startswith('label_not_mapped'))
        if n_lines != n_steps_led:
            fail.append(f'{s}: steps.jsonl has {n_lines} lines, ledger {n_steps_led}')
        by_part[s] = {'recordings': len(led), 'steps': n_lines, **dict(part)}
        # authors
        for a in jl(root / 'authors_intervals.jsonl'):
            auth[(a['mode'], a['status'])] += 1
            if a['status'] == 'matched':
                auth_off.append(abs(a['start_offset_ms']))
                auth_off.append(abs(a['end_offset_ms']))
            if a['mode'] in ('ramp', 'stair') and a['status'] == 'matched' and a['kind'] == 'interior':
                ours = a['our_label'] or ('excluded' if a['our_disposition'] != 'eligible' else '?')
                auth_class[(a['mode'], a['authors_class'] == 'discard', a['our_disposition'] == 'eligible')] += 1
        # per recording
        for e in led:
            key = (e['mode'], e['recording'])
            rec_status[e['status']] += 1
            rec_by_mode[e['mode']][e['status']] += 1
            if e['status'] == 'excluded_unprocessable':
                fail.append(f"unprocessable {e['recording']}: {e['reason']}")
                continue
            if e['mode'] == 'stair':
                stair['recordings'] += 1
                stair['recordings_with_eligible'] += e['status'] == 'segmented'
            if sum(e['steps_by_disposition'].values()) != e['steps'] or len(per_rec[key]) != e['steps']:
                fail.append(f"{s}/{e['recording']}: step counts differ")
            if s in LOCAL:
                resets_local += sum(e['resets'].values())
                pairs_local += e['steps']
            else:
                resets_new += sum(e['resets'].values())
                pairs_new += e['steps']
            meta = labels_s[key]
            # terrain
            if e['mode'] in ('ramp', 'stair'):
                tv = meta.get('ramp_incline_top_level' if e['mode'] == 'ramp' else 'stair_height_top_level')
                terrain['recordings_with_terrain_value'] += isinstance(tv, (int, float)) and tv > 0
                for st in per_rec[key]:
                    if st['disposition'] != 'eligible':
                        continue
                    terrain['eligible_ramp_stair_steps'] += 1
                    wins = [w for w in meta['label_windows'] if w['start_header'] <= st['start_s'] + 1e-9 and w['end_header'] >= st['end_s'] - 1e-9]
                    ok = len(wins) == 1 and wins[0]['label'] == st['label'] and wins[0]['label'] in MAPPED[e['mode']]
                    if e['mode'] == 'ramp':
                        sign = -1 if 'rampdescent' in st['label'] else 1
                        ok = ok and st['incline_deg'] == sign * tv
                    else:
                        ok = ok and abs(st['stair_height_m'] - round(tv * 0.0254, 3)) < 1e-12
                    if not ok:
                        terrain['mismatches'].append(st['step_id'])
            elif e['mode'] == 'levelground':
                for st in per_rec[key]:
                    if st['disposition'] == 'eligible':
                        wins = [w for w in meta['label_windows'] if w['start_header'] <= st['start_s'] + 1e-9 and w['end_header'] >= st['end_s'] - 1e-9]
                        if not (len(wins) == 1 and wins[0]['label'] == st['label'] and st['label'] in MAPPED['levelground']):
                            terrain['mismatches'].append(st['step_id'])
            # identity with the old report
            okey = (s, e['mode'], e['recording'])
            if okey in old:
                ident['recordings'] += 1
                oldpairs = {(p['side'], round(p['start_s'], 3), round(p['end_s'], 3)): p['reason'] for p in old[okey]}
                for st in per_rec[key]:
                    ident['steps'] += 1
                    r = oldpairs.get((st['leg'], round(st['start_s'], 3), round(st['end_s'], 3)))
                    if r is None:
                        ident['disagree'].append(f"{st['step_id']}: not in old report")
                        continue
                    old_in = r != 'outside_complete_eligible_task_window'
                    if e['mode'] == 'treadmill':
                        ident['treadmill_steps'] += 1
                        ident['treadmill_old_exported_or_opposite'] += old_in
                        continue
                    ident['eligible_levelground'] += st['disposition'] == 'eligible'
                    ident['old_exported_or_opposite'] += old_in
                    ident['old_outside'] += not old_in
                    if (st['disposition'] == 'eligible') != old_in:
                        ident['disagree'].append(f"{st['step_id']}: ours {st['disposition']} {st['reason']}, old {r}")
                if len(oldpairs) != len(per_rec[key]):
                    ident['disagree'].append(f"{e['recording']}: old {len(oldpairs)} pairs, ours {len(per_rec[key])}")
            # mask totals and layer comparison, one recording at a time
            if e.get('force_mask'):
                for leg in ('left', 'right'):
                    for k, v in e['force_mask'][leg].items():
                        mask_tot[leg][k] += v
                        mask_by_mode[e['mode']][k] += v
                pe = pq.read_table(ROOT / PASS.format(s=s) / s / e['mode'] / f"{e['recording']}.parquet",
                                   columns=['time_s', 'stance_left', 'stance_right', 'grf_vertical_left_BW', 'grf_vertical_right_BW'],
                                   use_threads=False)
                layer = pq.read_table(root / e['force_mask_layer'], use_threads=False)
                bw = bwmap[s][(e['mode'], e['recording'])]
                for leg in ('left', 'right'):
                    st_ = pe.column(f'stance_{leg}').to_numpy(zero_copy_only=False).astype(bool)
                    v = pe.column(f'grf_vertical_{leg}_BW').to_numpy(zero_copy_only=False) * bw
                    stored = layer.column(f'force_missing_{leg}').to_numpy(zero_copy_only=False).astype(bool)
                    loaded = np.nan_to_num(v, nan=-1.0) >= 20.0
                    expect = st_ & ~loaded
                    if not np.array_equal(stored, expect) or not np.array_equal(layer.column('time_s').to_numpy(zero_copy_only=False),
                                                                                 pe.column('time_s').to_numpy(zero_copy_only=False)):
                        mask_check['layer_mismatch'].append(f"{s}/{e['mode']}/{e['recording']}/{leg}")
                    mask_check['masked_samples_total'] += int(stored.sum())
                    mask_check['stance_samples_total'] += int(st_.sum())
                    mask_check['masked_stance_at_or_above_20N'] += int((stored & loaded).sum())
                    mask_check['unmasked_stance_below_20N'] += int((st_ & ~loaded & ~stored).sum())
                    if stored[~st_].any():
                        mask_check['layer_mismatch'].append(f"{s}/{e['mode']}/{e['recording']}/{leg}: masked outside stance")
                mask_check['layers_compared'] += 1
                sample_pool.append((s, e['mode'], e['recording']))
                del pe, layer
                pygc.collect()
        del per_rec
        pygc.collect()
    # scalar-loop recomputation for a seeded sample: events from the source gait tables and the mask
    rng = random.Random(args.seed)
    sample = []
    for s in LOCAL + NEW:
        pool = sorted(k for k in sample_pool if k[0] == s)
        sample += rng.sample(pool, 3)
    scalar = {'sample': [f'{a}/{b}/{c}' for a, b, c in sample], 'step_time_mismatches': [], 'mask_mismatches': [], 'recordings': 0}
    for s, mode, rec in sample:
        row = inv[(s, mode, rec)]
        base = ROOTS[row['source']] / s / row['session'] / mode
        root = ROOT / SEG.format(s=s)
        steps = [st for st in jl(root / 'steps.jsonl') if st['recording'] == rec and st['mode'] == mode]
        for leg in ('left', 'right'):
            g = src.read_numeric_table(base / ('gcLeft' if leg == 'left' else 'gcRight') / f'{rec}.mat')
            h, p = g['Header'].tolist(), g['HeelStrike'].tolist()
            rs = scalar_resets(p)
            mine = [(round(h[rs[k]], 6), round(h[rs[k + 1]], 6)) for k in range(len(rs) - 1)]
            theirs = [(round(x['start_s'], 6), round(x['end_s'], 6)) for x in steps if x['leg'] == leg]
            if mine != theirs:
                scalar['step_time_mismatches'].append(f'{s}/{mode}/{rec}/{leg}')
        pe = pq.read_table(ROOT / PASS.format(s=s) / s / mode / f'{rec}.parquet',
                           columns=['stance_left', 'stance_right', 'grf_vertical_left_BW', 'grf_vertical_right_BW'], use_threads=False)
        bw = bwmap[s][(mode, rec)]
        layer = pq.read_table(root / 'force_mask' / s / mode / f'{rec}.parquet', use_threads=False)
        for leg in ('left', 'right'):
            stn = pe.column(f'stance_{leg}').to_pylist()
            vv = pe.column(f'grf_vertical_{leg}_BW').to_pylist()
            sm = layer.column(f'force_missing_{leg}').to_pylist()
            for i in range(len(stn)):
                f = vv[i]
                enough = f is not None and f == f and f * bw >= 20.0
                want = bool(stn[i]) and not enough
                if want != bool(sm[i]):
                    scalar['mask_mismatches'].append(f'{s}/{mode}/{rec}/{leg}@{i}')
                    break
        scalar['recordings'] += 1
    rep.update(accounting={'recordings_by_status': dict(rec_status), 'recordings_by_mode_status': {m: dict(c) for m, c in rec_by_mode.items()},
                           'inventory_recordings': len(inv), 'ledger_recordings': sum(rec_status.values()),
                           'local_resets': resets_local, 'local_steps': pairs_local, 'new_resets': resets_new, 'new_steps': pairs_new,
                           'expected_local_resets': 83206, 'expected_local_steps': 78604,
                           'local_resets_and_steps_reproduce_exactly': resets_local == 83206 and pairs_local == 78604,
                           'steps_total': len(ids), 'steps_by_mode_disposition': {m: dict(c) for m, c in by_mode.items()},
                           'steps_by_participant': by_part},
               reasons={m: dict(c.most_common()) for m, c in reasons.items()},
               stair=stair, identity_36_recordings=ident, terrain=terrain, mask=mask_check,
               mask_totals={'by_leg': {l: dict(c) for l, c in mask_tot.items()}, 'by_mode': {m: dict(c) for m, c in mask_by_mode.items()}},
               scalar_recomputation=scalar,
               force_check={'by_mode_status': {m: dict(c) for m, c in fcheck.items()},
                            'heel_strike_offset_ms': _pct(offs_hs), 'toe_off_offset_ms': _pct(offs_to)},
               authors={'by_mode_status': {f'{m}/{st}': n for (m, st), n in sorted(auth.items())},
                        'abs_offset_ms_matched': _pct(auth_off),
                        'ramp_stair_interior_authors_discard_vs_our_eligible': {f'{m} authors_discard={d} ours_eligible={e}': n for (m, d, e), n in sorted(auth_class.items())}},
               peak_rss_mib=peak_mib())
    rep['status'] = 'readback_passed' if not fail and not ident['disagree'] and not terrain['mismatches'] \
        and not mask_check['layer_mismatch'] and not scalar['step_time_mismatches'] and not scalar['mask_mismatches'] else 'readback_found_problems'
    with open(out_path, 'x') as f:
        json.dump(rep, f, indent=2, sort_keys=True, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
        f.write('\n')
    print(rep['status'], 'peak', peak_mib())
    return 0


def _pct(x):
    if not x:
        return None
    a = np.asarray(x, float)
    return {'n': int(a.size), 'p5': float(np.percentile(a, 5)), 'median': float(np.median(a)), 'p95': float(np.percentile(a, 95)),
            'max_abs': float(np.abs(a).max())}


if __name__ == '__main__':
    raise SystemExit(main())
