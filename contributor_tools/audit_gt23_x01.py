"""Independent audit of one GT23-X01 participant batch (separate code: does not import the reader).

Re-reads the source and the batch root READ-ONLY and checks, per recording: source and companion hashes equal the
ledger; row counts by raw byte count equal the ledger, the companions and the marker file; every companion value
equals a fresh parse of its CSV (relative 1e-12: pandas' default text parser is less exact than the round-trip parser the companions use); the marker finite shares recomputed with a plain-text parser equal
the ledger; the authors' stride counts re-read with scipy (no simplify_cells) equal the ledger. Writes only
<output-root>/audit_report.json. Ledger 'issues' are reported, not judged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ('Activity_Flag', 'GroundFrame_GRFs', 'Joint_Angle', 'Joint_Moments', 'Joint_Powers', 'Joint_Velocities',
            'Raw_EMGs', 'Real_IMUs', 'Virtual_IMUs', 'Virtual_Insoles')
NEEDED = ('LASI', 'RASI', 'LPSI', 'RPSI', 'LGTR', 'RGTR', 'LKNE', 'LMKNE', 'RKNE', 'RMKNE', 'LANK', 'LMANK', 'RANK',
          'RMANK', 'LCAL', 'RCAL', 'LMT1', 'LMT5', 'RMT1', 'RMT5', 'LTHC', 'RTHC')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def count_rows(path):
    n, last = 0, b'\n'
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            n += block.count(b'\n')
            last = block[-1:]
    return n + (0 if last == b'\n' else 1) - 1  # minus header


def csv_vs_parquet(csv_path, pq_path):
    pf = pq.ParquetFile(str(pq_path), buffer_size=0)
    names = list(pf.schema_arrow.names)
    batches = pf.iter_batches(batch_size=4096, use_threads=False)
    worst, rows = 0.0, 0
    for chunk in pd.read_csv(csv_path, dtype=np.float64, chunksize=4096):
        batch = next(batches)
        if list(chunk.columns) != names or batch.num_rows != len(chunk):
            return {'ok': False, 'why': 'names or chunk length differ'}
        for i, name in enumerate(names):
            a, b = chunk[name].to_numpy(np.float64), batch.column(i).to_numpy(zero_copy_only=False)
            if not np.array_equal(np.isnan(a), np.isnan(b)):
                return {'ok': False, 'why': f'NaN pattern differs in {name}'}
            ok = ~np.isnan(a)
            if ok.any():
                denom = np.maximum(np.abs(a[ok]), 1e-300)
                worst = max(worst, float(np.max(np.abs(a[ok] - b[ok]) / denom)))
        rows += len(chunk)
    return {'ok': worst <= 1e-12 and rows == pf.metadata.num_rows, 'worst_relative_difference': worst, 'rows': rows}


def trc_text_coverage(path, stance):
    with open(path, 'r', newline='') as f:
        head = [f.readline() for _ in range(8)]
    first = next(i for i, l in enumerate(head) if i > 3 and l[:1].isdigit())
    names = [n for n in head[3].rstrip('\r\n').split('\t')[2:] if n]
    idx = {m: names.index(m) for m in NEEDED if m in names}
    finite = {m: 0 for m in idx}
    stance_ok = {m: 0 for m in idx}
    n = 0
    with open(path, 'r', newline='') as f:
        for k, line in enumerate(f):
            if k < first or not line.strip():
                continue
            parts = line.rstrip('\r\n').split('\t')
            for m, i in idx.items():
                try:
                    good = all(np.isfinite(float(parts[2 + 3 * i + j])) for j in range(3))
                except (ValueError, IndexError):
                    good = False
                if good:
                    finite[m] += 1
                    if stance is not None and m[0] in 'LR' and n < len(stance[m[0]]) and stance[m[0]][n]:
                        stance_ok[m] += 1
            n += 1
    return {'rows': n, 'share': {m: finite[m] / n for m in idx},
            'stance_share': {m: (stance_ok[m] / stance[m[0]].sum() if stance[m[0]].sum() else None) for m in idx if m[0] in 'LR'} if stance else None,
            'missing': [m for m in NEEDED if m not in names]}


def close(a, b, tol=2e-6):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)


def audit(args):
    batch = Path(args.batch_root)
    source = Path(args.source)
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'locohub.gt23_x01_audit/1', 'scientific_approval': False, 'subject': args.subject,
              'batch_root': str(batch), 'status': 'running', 'recordings': {}, 'failures': []}
    target = out / 'audit_report.json'
    try:
        ledger = [json.loads(x) for x in (batch / 'ledger.jsonl').read_text().splitlines()]
        wanted = set(args.records or []) or None
        events = {}
        for e in json.loads((Path(args.events_root) / f'events_{args.subject}.json').read_text())['files']:
            events.setdefault(e['recording'], []).append(e)
        part = json.loads((batch / 'participant.json').read_text())
        raw = source / 'RawData' / args.subject
        for kind in ('models', 'motion_files'):
            for name, v in part[kind].items():
                folder = 'Models' if kind == 'models' else 'MotionFile_EH'
                if sha(raw / folder / name) != v['sha256']:
                    report['failures'].append(f'{kind}/{name} hash differs')
        for entry in ledger:
            rec = entry['recording']
            if wanted and f'{args.subject}/{rec}' not in wanted:
                continue
            bad = []
            if entry['status'] == 'failed':
                bad.append('ledger says the recording failed')
            folder = raw / 'CSV_Data' / rec
            on_disk = sorted(p.stem for p in folder.glob('*.csv') if p.stem in CHANNELS)
            if on_disk != sorted(entry['channels']):
                bad.append(f'channel set differs: disk {on_disk} ledger {sorted(entry["channels"])}')
            stance = None
            for ch, info in entry['channels'].items():
                csv_path, pq_path = folder / f'{ch}.csv', batch / rec / f'{ch}.parquet'
                if 'error' in info:
                    bad.append(f'{ch} had a conversion error in the ledger')
                    continue
                if sha(csv_path) != info['sha256']:
                    bad.append(f'{ch} source hash differs from the ledger')
                if sha(pq_path) != info['parquet_sha256']:
                    bad.append(f'{ch} companion hash differs from the ledger')
                n = count_rows(csv_path)
                meta = pq.ParquetFile(str(pq_path), buffer_size=0).metadata
                if not (n == info['rows'] == meta.num_rows):
                    bad.append(f'{ch} rows: raw {n}, ledger {info["rows"]}, companion {meta.num_rows}')
                cmp = csv_vs_parquet(csv_path, pq_path)
                if not cmp['ok']:
                    bad.append(f'{ch} companion differs from a fresh parse: {cmp}')
                if ch == 'GroundFrame_GRFs':
                    t = pq.ParquetFile(str(pq_path), buffer_size=0).read(columns=['LForceY_Vertical', 'RForceY_Vertical'], use_threads=False)
                    stance = {s: np.nan_to_num(t.column(c).to_numpy(), nan=0.0) > 20.0
                              for s, c in (('L', 'LForceY_Vertical'), ('R', 'RForceY_Vertical'))}
            if 'markers' in entry and 'rows' in entry['markers']:
                trc = raw / 'MarkerData' / f'{rec}.trc'
                if sha(trc) != entry['markers']['sha256']:
                    bad.append('marker file hash differs')
                cov = trc_text_coverage(trc, stance)
                if cov['rows'] != entry['markers']['rows']:
                    bad.append(f'marker rows {cov["rows"]} vs ledger {entry["markers"]["rows"]}')
                if sorted(cov['missing']) != sorted(entry['markers']['missing_needed']):
                    bad.append('missing-marker list differs')
                for m, v in cov['share'].items():
                    if not close(v, entry['markers']['finite_share'].get(m)):
                        bad.append(f'finite share {m}: {v} vs {entry["markers"]["finite_share"].get(m)}')
                if cov['stance_share']:
                    for m, v in cov['stance_share'].items():
                        if not close(v, entry['markers'].get('finite_share_in_own_stance', {}).get(m)):
                            bad.append(f'stance share {m} differs')
            elif 'markers' not in entry:
                bad.append('no marker entry in the ledger')
            eu = entry.get('euler')
            if eu and 'rows' in eu:
                p = raw / 'Transforms_Euler' / f'{rec}.csv'
                if sha(p) != eu['sha256'] or count_rows(p) != eu['rows']:
                    bad.append('Transforms_Euler hash or rows differ')
            import scipy.io as sio
            for f in events.get(rec, []):
                p = source / 'Segmentation' / args.subject / f['file']
                if sha(p) != f['sha256']:
                    bad.append(f'{f["file"]} hash differs')
                mat = sio.loadmat(str(p))
                counts = {'left': 0, 'right': 0}
                for key in mat:
                    side = key.split('_')[0]
                    if key.startswith('__') or key == 'types' or side not in counts:
                        continue
                    a = np.asarray(mat[key])
                    counts[side] += 0 if a.size == 0 else a.reshape(-1, 2).shape[0]
                if (counts['left'], counts['right']) != (f['windows_left'], f['windows_right']):
                    bad.append(f'{f["file"]} windows {counts} vs events file')
            report['recordings'][rec] = {'reproduced': not bad, 'differences': bad, 'ledger_issues': entry['issues']}
            if bad:
                report['failures'].append(f'{rec}: {len(bad)} differences')
            target.write_text(json.dumps(report, indent=2) + '\n')
        report['recordings_checked'] = len(report['recordings'])
        report['status'] = 'pass' if not report['failures'] and report['recordings'] else 'fail'
    except BaseException as error:
        report.update(status='runner_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report['peak_rss_mib'] = round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                           resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)
        target.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['status'] == 'pass' else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('audit')
    a.add_argument('--output-root', type=Path, required=True)
    a.add_argument('--batch-root', type=Path, required=True)
    a.add_argument('--events-root', type=Path, required=True)
    a.add_argument('--subject', required=True)
    a.add_argument('--records', action='append')
    a.add_argument('--source', type=Path, required=True)
    args = p.parse_args(argv)
    return audit(args)


if __name__ == '__main__':
    sys.exit(main())
