"""GT21 merged pass runner (GT21-RB02 plates and forces + GT21-RB04 conventions).

Reads each named recording ONCE (markers, fp, gcLeft, gcRight, id from the numeric source tables; the participant's scaled
model; the RB01 weight export) and writes, into a NEW output root, one continuous 200 Hz Parquet per recording plus a
per-recording ledger line. A recording that cannot be processed becomes a listed exclusion with its reason and the run goes
on; nothing stops a batch. One recording is resident at a time. Method: contributor_tools/gt21_rb_pass.py.

Subcommands
  run   --record SUBJECT/MODE/RECORDING (repeated)  --out-root NEW_DIR
        Only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``.
  spec  Writes the guarded-launcher spec (binds code, the RB01 recording ledger and the weight exports).

No scientific approval is claimed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402
from contributor_tools import gt21_rb_pass as rb  # noqa: E402

INVENTORY = 'converted_datasets/reconversion_v2/gt21_rb01_inventory_20261123/recording_ledger.jsonl'
LABELS = 'converted_datasets/reconversion_v2/gt21_rb01_labels_final_20261124'
ROOTS = {'local_2024_copy_bundle': ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET',
         'extracted_2024_copy_zip': Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')}
CODE = ('contributor_tools/gt21_rb_pass.py', 'contributor_tools/run_gt21_rb_pass.py', 'contributor_tools/gt21_numeric_source.py')
CHANNELS = ('markers', 'fp', 'gcLeft', 'gcRight', 'id')
MODES = ('levelground', 'ramp', 'stair', 'treadmill')
PILOT = (('AB06', 'levelground', 'levelground_ccw_fast_01_01'), ('AB06', 'treadmill', 'treadmill_01_01'),
         ('AB06', 'ramp', None), ('AB06', 'stair', 'stair_1_l_01_02'), ('AB17', 'treadmill', None))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def load_inventory(path=None):
    rows = {}
    for line in Path(path or ROOT / INVENTORY).read_text().splitlines():
        r = json.loads(line)
        rows[(r['subject'], r['mode'], r['recording'])] = r
    return rows


def read_table(path):
    """Named float columns of one source table; the fail-closed reader (never assigns axes or signs)."""
    return src.read_numeric_table(path)


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def process_one(row, out_root, read=read_table, roots=None, labels=None, geometry_cache=None):
    """One recording: read once, convert, write. Returns the ledger dict (status converted or excluded)."""
    roots = roots or ROOTS
    labels = Path(labels or ROOT / LABELS)
    geometry_cache = geometry_cache if geometry_cache is not None else {}
    subject, session, mode, rec = row['subject'], row['session'], row['mode'], row['recording']
    entry = {'subject': subject, 'session': session, 'mode': mode, 'recording': rec, 'source': row['source']}
    try:
        base = roots[row['source']] / subject
        if subject not in geometry_cache:
            text = (base / 'osimxml' / f'{subject}.osim').read_text()
            geometry_cache[subject] = {s: rb.model_geometry(text, s) for s in 'rl'}
            geometry_cache[subject + '_sha256'] = hashlib.sha256(text.encode()).hexdigest()
            info = json.loads((labels / subject / f'subject_info_{subject}.json').read_text())
            geometry_cache[subject + '_weight'] = rb.weight_kg_from_subject_info(info)
        entry['model_sha256'] = geometry_cache[subject + '_sha256']
        tables = {}
        for ch in CHANNELS:
            path = base / session / mode / ch / f'{rec}.mat'
            try:
                tables[ch] = read(path)
            except Exception as exc:                       # an unreadable optional channel is missing, not fatal
                if ch == 'markers':
                    raise rb.RecordingExcluded(f'markers unreadable: {type(exc).__name__}: {exc}')
                tables[ch] = None
                entry.setdefault('channel_read_errors', {})[ch] = f'{type(exc).__name__}: {exc}'[:200]
        cols, led = rb.process_recording(tables['markers'], tables['fp'], tables['gcLeft'], tables['gcRight'], tables['id'],
                                         geometry_cache[subject], geometry_cache[subject + '_weight'], mode)
        del tables
        out = Path(out_root) / subject / mode
        out.mkdir(parents=True, exist_ok=True)
        table = pa.table({k: pa.array(v) for k, v in cols.items()})
        with open(out / f'{rec}.parquet', 'xb') as f:                  # exclusive create: never overwrites
            pq.write_table(table, f, row_group_size=4096, compression='zstd')
        entry.update(status='converted', parquet=f'{subject}/{mode}/{rec}.parquet', **led)
    except rb.RecordingExcluded as exc:
        entry.update(status='excluded', reason=str(exc))
    except Exception as exc:                                           # never stop the batch; the reason is listed
        entry.update(status='excluded', reason=f'error: {type(exc).__name__}: {exc}'[:400])
    return entry


def run(args):
    out_root = Path(args.out_root)
    if out_root.exists() and any(out_root.iterdir()):
        raise SystemExit(f'{out_root} is not empty; outputs go to a new root')
    out_root.mkdir(parents=True, exist_ok=True)
    inv = load_inventory()
    cache, entries = {}, []
    records = list(args.record or [])
    if args.subject:
        records += [f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject]
    if not records:
        raise SystemExit('no recordings named')
    for rec in records:
        subject, mode, name = rec.split('/')
        row = inv.get((subject, mode, name))
        if row is None:
            entries.append({'subject': subject, 'mode': mode, 'recording': name, 'status': 'excluded', 'reason': 'not in RB01 inventory'})
            continue
        entries.append(process_one(row, out_root, geometry_cache=cache))
        entries[-1]['peak_rss_mib_after'] = peak_rss_mib()
    with open(out_root / 'ledger.jsonl', 'x') as f:
        for e in entries:
            f.write(json.dumps(e, sort_keys=True, default=_json_default) + '\n')
    summary = {'status': 'run_done_unreviewed', 'scientific_approval': False, 'recordings': len(entries),
               'converted': sum(e['status'] == 'converted' for e in entries),
               'excluded': [{'recording': f"{e['subject']}/{e['mode']}/{e['recording']}", 'reason': e['reason']}
                            for e in entries if e['status'] != 'converted'],
               'peak_rss_mib': peak_rss_mib(), 'code_sha256': {c: sha256_file(ROOT / c) for c in CODE}}
    with open(out_root / 'run_summary.json', 'x') as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write('\n')
    return 0


def pilot_records(inv, seed=20261124):
    """One recording per mode from AB06 plus one new-participant treadmill recording; named ones are fixed, the ramp and
    the AB17 treadmill recording are drawn with a recorded seed (not hand-picked)."""
    rng = random.Random(seed)
    out = []
    for subject, mode, name in PILOT:
        if name is None:
            names = sorted(r for (s, m, r) in inv if s == subject and m == mode)
            name = rng.choice(names)
        if (subject, mode, name) not in inv:
            raise SystemExit(f'pilot recording {subject}/{mode}/{name} is not in the inventory')
        out.append(f'{subject}/{mode}/{name}')
    return out


def pilot_records_r4(inv, seed=20261125):
    """The r3 five plus two seeded levelground recordings: one from a local participant other than AB06 and one from a
    participant extracted from the zips (new)."""
    out = pilot_records(inv)
    rng = random.Random(seed)
    local = sorted({s for (s, m, r), row in inv.items() if row['source'] == 'local_2024_copy_bundle' and s != 'AB06'})
    new = sorted({s for (s, m, r), row in inv.items() if row['source'] == 'extracted_2024_copy_zip'})
    for pool in (local, new):
        subject = rng.choice(pool)
        name = rng.choice(sorted(r for (s, m, r) in inv if s == subject and m == 'levelground'))
        out.append(f'{subject}/levelground/{name}')
    return out


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    inv = load_inventory()
    if args.subject:
        records = [f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject]
    else:
        records = args.record or (pilot_records_r4(inv) if args.pilot == 'r4' else pilot_records(inv))
    subjects = sorted({r.split('/')[0] for r in records})
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE + ('contributor_tools/guarded_launcher.py',)}
    bindings[INVENTORY] = gl.sha256_file(ROOT / INVENTORY)
    for s in subjects:
        bindings[f'{LABELS}/{s}/subject_info_{s}.json'] = gl.sha256_file(ROOT / LABELS / s / f'subject_info_{s}.json')
        row = next(r for (sj, _, _), r in inv.items() if sj == s)
        model = ROOTS[row['source']] / s / 'osimxml' / f'{s}.osim'
        bindings[str(model)] = gl.sha256_file(model)
    command = ['python3', 'contributor_tools/run_gt21_rb_pass.py', 'run', '--out-root', args.out_root]
    if args.subject:
        command += ['--subject', args.subject]
    else:
        for r in records:
            command += ['--record', r]
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.out_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json', 'ledger.jsonl'], 'address_space_mib': 768,
            'disk_admission': [{'path': str(ROOT / 'converted_datasets'), 'min_free_mib': 15360}]}
    with open(args.spec_out, 'x') as f:
        json.dump(spec, f, indent=2)
        f.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--out-root', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject')
    s = sub.add_parser('spec')
    s.add_argument('--job-id', required=True)
    s.add_argument('--out-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject')
    s.add_argument('--pilot', choices=('r3', 'r4'), default='r3')
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
