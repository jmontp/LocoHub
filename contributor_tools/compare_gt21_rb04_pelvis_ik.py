"""GT21-RB04 acceptance: pelvis tilt from markers (the merged pass) against the authors' own pelvis orientation (source IK).

Read-only probe (AGENTS.md exception): one recording at a time through the fail-closed numeric reader (ik only) plus the pass's
Parquet for the same recording; nothing written under converted_datasets/ or source folders; run under ``prlimit --as``, nice 19,
ionice idle, one thread, ARROW_DEFAULT_MEMORY_POOL=system.

Authors' tilt: R = Rz(pelvis_tilt) Rx(pelvis_list) Ry(pelvis_rotation) from the IK table (degrees; the model axes of GT21-C01), its
forward (body x) axis elevation above horizontal, atan2(x_y, |x_horizontal|): front up is positive, the pass's sign for pelvis
angle. Compared with the pass's pelvis_sagittal_angle_rad after removing each series' median (the marker and model pelvis
axes differ by a constant offset, as in GT21-C01's fit). Reported: wrapped RMS of the difference in degrees and the sample
correlation, against the GT21-C01 range (tilt RMS 0.9-2.7 deg after a constant offset; 8 recordings, 2 per mode). The GT21-C01
recordings are checked first, then a seeded set of recordings from the six new participants and others. No scientific approval claimed.
"""
import json
import os
from pathlib import Path
import random
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools.gt21_numeric_source import read_numeric_table  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)
INV = ROOT / 'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123/recording_ledger.jsonl'
C01 = ROOT / 'docs/quality/audits/gt21-c01-conventions.json'
OUT = ROOT / 'docs/quality/audits/gt21-rb04-pelvis-vs-ik.json'
ROOTS = {'local_2024_copy_bundle': ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET',
         'extracted_2024_copy_zip': Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')}
SEED = 20261128


def rz(a):
    c, s = np.cos(a), np.sin(a)
    o, i = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, -s, o], -1), np.stack([s, c, o], -1), np.stack([o, o, i], -1)], -2)


def rx(a):
    c, s = np.cos(a), np.sin(a)
    o, i = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([i, o, o], -1), np.stack([o, c, -s], -1), np.stack([o, s, c], -1)], -2)


def ry(a):
    c, s = np.cos(a), np.sin(a)
    o, i = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, o, s], -1), np.stack([o, i, o], -1), np.stack([-s, o, c], -1)], -2)


def authors_tilt(ik):
    tilt, lst, rot = (np.radians(ik[k]) for k in ('pelvis_tilt', 'pelvis_list', 'pelvis_rotation'))
    x = (rz(tilt) @ rx(lst) @ ry(rot))[:, :, 0]
    return np.arctan2(x[:, 1], np.hypot(x[:, 0], x[:, 2]))


def compare(row):
    base = ROOTS[row['source']] / row['subject'] / row['session'] / row['mode']
    rec = row['recording']
    sub = row['subject']
    mine = pq.read_table(ROOT / f"converted_datasets/reconversion_v2/gt21_rb_pass_batch_{sub}_20261124/{sub}/{row['mode']}/{rec}.parquet",
                         use_threads=False, columns=['time_s', 'pelvis_sagittal_angle_rad']).to_pandas()
    ik = read_numeric_table(base / 'ik' / f'{rec}.mat')
    t = mine['time_s'].to_numpy()
    if len(ik['Header']) != len(t) or np.max(np.abs(ik['Header'] - t)) > 1e-6:
        return {'recording': f"{sub}/{row['mode']}/{rec}", 'skipped': 'ik clock differs from the marker clock'}
    a = mine['pelvis_sagittal_angle_rad'].to_numpy()
    b = authors_tilt(ik)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok] - np.median(a[ok]), b[ok] - np.median(b[ok])
    d = (a - b + np.pi) % (2 * np.pi) - np.pi
    return {'recording': f"{sub}/{row['mode']}/{rec}", 'samples': int(ok.sum()),
            'rms_deg_after_median_removal': float(np.degrees(np.sqrt(np.mean(d ** 2)))),
            'r': float(np.corrcoef(a, b)[0, 1]),
            'median_offset_deg': float(np.degrees(np.median(mine['pelvis_sagittal_angle_rad'].to_numpy()[ok] - authors_tilt(ik)[ok]))),
            'range_deg_pass': [float(np.degrees(np.percentile(mine['pelvis_sagittal_angle_rad'].to_numpy()[ok], q))) for q in (5, 50, 95)]}


def main():
    inv = {}
    for line in INV.read_text().splitlines():
        r = json.loads(line)
        inv[f"{r['subject']}/{r['mode']}/{r['recording']}"] = r
    c01 = json.loads(C01.read_text())['pelvis_check']['recordings']
    c01_rows = []
    for x in c01:
        sub, _, mode, name = x['recording'].split('/')
        key = f"{sub}/{mode}/{name[:-4]}"
        c01_rows.append((key, x['zxy_agreement']['tilt']['rms_deg'], x['heading_removed_sagittal_tilt']['source_vs_marker_rms_deg']))
    rng = random.Random(SEED)
    chosen = []
    new = ['AB12', 'AB15', 'AB17', 'AB19', 'AB23', 'AB28']
    for sub in new:
        for mode in ('levelground', 'ramp', 'stair', 'treadmill'):
            names = sorted(k for k in inv if k.startswith(f'{sub}/{mode}/'))
            chosen.append(rng.choice(names))
    results = {'c01_recordings': [], 'seeded_new_participants': []}
    for key, rms_zxy, rms_hr in c01_rows:
        r = compare(inv[key])
        r['c01_tilt_rms_deg_zxy'] = rms_zxy
        r['c01_heading_removed_source_vs_marker_rms_deg'] = rms_hr
        results['c01_recordings'].append(r)
    for key in chosen:
        results['seeded_new_participants'].append(compare(inv[key]))
    allr = [r for v in results.values() for r in v if 'rms_deg_after_median_removal' in r]
    summary = {'c01_range_rms_deg': [0.9, 2.7], 'c01_recordings': len(results['c01_recordings']),
               'pass_vs_authors_rms_deg_c01_set': [min(r['rms_deg_after_median_removal'] for r in results['c01_recordings']),
                                                   max(r['rms_deg_after_median_removal'] for r in results['c01_recordings'])],
               'pass_vs_authors_rms_deg_seeded_new': [min(r['rms_deg_after_median_removal'] for r in results['seeded_new_participants']),
                                                      max(r['rms_deg_after_median_removal'] for r in results['seeded_new_participants'])],
               'recordings': len(allr), 'peak_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
    OUT.write_text(json.dumps({'scientific_approval': False, 'seed': SEED, 'summary': summary, **results}, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
