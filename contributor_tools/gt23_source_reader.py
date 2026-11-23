"""Georgia Tech 2023 source reader for GT23-X01 (Python only; no MATLAB).

Reads one recording at a time from the publisher's folders, never writes into them, and fails closed: a missing
file, an unparsable table or a count that differs is named in the returned record, never repaired or skipped.

Memory: pyarrow uses the system pool (set ARROW_DEFAULT_MEMORY_POOL before import by the caller), tables are read
in 4096-row chunks, and one recording is resident at a time.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

CHANNELS = ('Activity_Flag', 'GroundFrame_GRFs', 'Joint_Angle', 'Joint_Moments', 'Joint_Powers', 'Joint_Velocities',
            'Raw_EMGs', 'Real_IMUs', 'Virtual_IMUs', 'Virtual_Insoles')
NEEDED_MARKERS = ('LASI', 'RASI', 'LPSI', 'RPSI', 'LGTR', 'RGTR', 'LKNE', 'LMKNE', 'RKNE', 'RMKNE', 'LANK', 'LMANK',
                  'RANK', 'RMANK', 'LCAL', 'RCAL', 'LMT1', 'LMT5', 'RMT1', 'RMT5', 'LTHC', 'RTHC')
RATE_HZ = 200.0
CHANNEL_RATE_HZ = {'Raw_EMGs': 2000.0}  # every other channel file, the markers and the Euler table are 200 Hz
CLOCK_TOLERANCE_S = 1e-5
CHUNK_ROWS = 4096
STANCE_N = 20.0
PLATE_VERTICAL = {'L': 'LForceY_Vertical', 'R': 'RForceY_Vertical'}
PARQUET_COMPRESSION = 'zstd'


class SourceError(RuntimeError):
    pass


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def combine_column_digests(digests):
    """Chunk-independent content digest: sha256 over the per-column hex digests in column order."""
    return hashlib.sha256(''.join(digests).encode()).hexdigest()


def _header(path):
    with Path(path).open('r', newline='') as stream:
        line = stream.readline().rstrip('\r\n')
    names = line.split(',')
    if not line or any(n == '' for n in names) or len(set(names)) != len(names):
        raise SourceError(f'{Path(path).name}: header empty, has blank names or duplicate names')
    return names


def convert_channel(csv_path, parquet_path, plate_columns=None, rate_hz=RATE_HZ):
    """Stream one channel CSV to a lossless float64 Parquet companion (NaN stays NaN; small row groups).

    Returns facts: rows, columns, clock check, finite shares, per-column digests combined, source hash.
    ``plate_columns``: optional list of columns whose full values are returned (ground-reaction vertical force).
    """
    names = _header(csv_path)
    dtype = {n: np.float64 for n in names}
    reader = pd.read_csv(csv_path, dtype=dtype, float_precision='round_trip', chunksize=CHUNK_ROWS)
    schema = pa.schema([(n, pa.float64()) for n in names])
    Path(parquet_path).parent.mkdir(parents=True, exist_ok=True)
    digests = [hashlib.sha256() for _ in names]
    finite = np.zeros(len(names), np.int64)
    rows, t_prev, t_first, dev_max = 0, None, None, 0.0
    kept = {c: [] for c in (plate_columns or [])}
    with pq.ParquetWriter(str(parquet_path), schema, compression=PARQUET_COMPRESSION) as writer:
        for chunk in reader:
            if list(chunk.columns) != names:
                raise SourceError(f'{Path(csv_path).name}: columns changed between chunks')
            arrays = []
            for i, name in enumerate(names):
                values = np.ascontiguousarray(chunk[name].to_numpy(np.float64))
                digests[i].update(values.astype('<f8', copy=False).tobytes())
                finite[i] += int(np.isfinite(values).sum())
                arrays.append(pa.array(values, type=pa.float64(), from_pandas=False))
                if name in kept:
                    kept[name].append(values)
            writer.write_table(pa.Table.from_arrays(arrays, schema=schema))
            if 'time' in names:
                t = chunk['time'].to_numpy(np.float64)
                if t_first is None:
                    t_first = float(t[0])
                joined = t if t_prev is None else np.concatenate(([t_prev], t))
                if len(joined) > 1:
                    dev_max = max(dev_max, float(np.nanmax(np.abs(np.diff(joined) - 1.0 / rate_hz))))
                t_prev = float(t[-1])
            rows += len(chunk)
    facts = {'rows': rows, 'columns': len(names), 'column_names_sha256': hashlib.sha256('\n'.join(names).encode()).hexdigest(),
             'values_sha256': combine_column_digests([d.hexdigest() for d in digests]),
             'finite_share_all': float(finite.sum() / (rows * len(names))) if rows else None,
             'finite_by_column': {n: round(float(finite[i] / rows), 6) for i, n in enumerate(names)} if rows else {},
             'time_first': t_first, 'time_last': t_prev, 'time_step_max_abs_dev_s': dev_max if 'time' in names else None,
             'has_time_column': 'time' in names, 'rate_hz': rate_hz}
    return facts, {c: np.concatenate(v) if v else np.zeros(0) for c, v in kept.items()}


def parquet_values_digest(path):
    """Independent readback of a companion: row count, names and the combined per-column digest."""
    pf = pq.ParquetFile(str(path), buffer_size=0)
    names = list(pf.schema_arrow.names)
    digests = [hashlib.sha256() for _ in names]
    rows = 0
    for batch in pf.iter_batches(batch_size=CHUNK_ROWS, use_threads=False):
        for i, col in enumerate(batch.columns):
            if col.null_count:
                raise SourceError(f'{Path(path).name}: nulls in a lossless companion')
            digests[i].update(col.to_numpy(zero_copy_only=False).astype('<f8', copy=False).tobytes())
        rows += batch.num_rows
    return {'rows': rows, 'columns': len(names), 'row_groups': pf.metadata.num_row_groups,
            'column_names_sha256': hashlib.sha256('\n'.join(names).encode()).hexdigest(),
            'values_sha256': combine_column_digests([d.hexdigest() for d in digests])}


def read_trc_header(path):
    with Path(path).open('r', newline='') as stream:
        head = [stream.readline() for _ in range(8)]
    first = next((i for i, line in enumerate(head) if i > 3 and line[:1].isdigit()), None)
    if first is None:
        raise SourceError(f'{Path(path).name}: first data row not found in the first 8 lines')
    names = head[3].rstrip('\r\n').split('\t')
    markers = [n for n in names[2:] if n]
    values = head[2].rstrip('\r\n').split('\t')
    declared = {'rate_hz': float(values[0]), 'frames': int(float(values[2])), 'markers': int(float(values[3]))}
    return first, markers, declared


def trc_coverage(path, stance=None):
    """Finite shares of the needed markers (overall and in own-leg stance) read in chunks; rows by the file's own table."""
    first, markers, declared = read_trc_header(path)
    present = [m for m in NEEDED_MARKERS if m in markers]
    cols, layout = [0, 1], {}
    for m in sorted(present, key=markers.index):
        i = markers.index(m)
        layout[m] = 2 + 3 * i
        cols += [2 + 3 * i, 3 + 3 * i, 4 + 3 * i]
    use = sorted(cols)
    pos = {c: k for k, c in enumerate(use)}
    rows, t_first, t_last = 0, None, None
    finite = {m: 0 for m in present}
    in_stance = {m: 0 for m in present}
    stance_n = {s: int(stance[s].sum()) for s in 'LR'} if stance else None
    n_stance = len(next(iter(stance.values()))) if stance else 0
    for chunk in pd.read_csv(path, sep='\t', skiprows=first, header=None, usecols=use, dtype=np.float64, chunksize=20000):
        arr = chunk.to_numpy(np.float64)
        t = arr[:, pos[1]]
        if t_first is None:
            t_first = float(t[0])
        t_last = float(t[-1])
        for m in present:
            ok = np.isfinite(arr[:, pos[layout[m]]]) & np.isfinite(arr[:, pos[layout[m] + 1]]) & np.isfinite(arr[:, pos[layout[m] + 2]])
            finite[m] += int(ok.sum())
            side = m[0]
            if stance is not None and side in 'LR':
                lo, hi = rows, min(rows + len(arr), n_stance)
                if hi > lo:
                    in_stance[m] += int((ok[:hi - lo] & stance[side][lo:hi]).sum())
        rows += len(arr)
    out = {'rows': rows, 'declared': declared, 'time_first': t_first, 'time_last': t_last,
           'markers_in_file': len(markers), 'missing_needed': [m for m in NEEDED_MARKERS if m not in markers],
           'finite_share': {m: round(finite[m] / rows, 6) if rows else None for m in present}}
    if stance is not None:
        out['finite_share_in_own_stance'] = {m: (round(in_stance[m] / stance_n[m[0]], 6) if stance_n[m[0]] else None)
                                             for m in present if m[0] in 'LR'}
        out['stance_samples'] = stance_n
    return out


def euler_facts(path):
    names = _header(path)
    rows, finite, t_prev, dev = 0, 0, None, 0.0
    for chunk in pd.read_csv(path, dtype={n: np.float64 for n in names}, float_precision='round_trip', chunksize=CHUNK_ROWS):
        arr = chunk.to_numpy(np.float64)
        finite += int(np.isfinite(arr).sum())
        rows += len(chunk)
        if 'time' in names:
            t = chunk['time'].to_numpy(np.float64)
            joined = t if t_prev is None else np.concatenate(([t_prev], t))
            if len(joined) > 1:
                dev = max(dev, float(np.nanmax(np.abs(np.diff(joined) - 1.0 / RATE_HZ))))
            t_prev = float(t[-1])
    return {'rows': rows, 'columns': len(names), 'finite_share_all': finite / (rows * len(names)) if rows else None,
            'has_time_column': 'time' in names, 'time_step_max_abs_dev_s': dev if 'time' in names else None}


def parse_readme_masses(text):
    masses = dict(re.findall(r'^(AB\d\d): ([0-9.]+) kg\s*$', text, flags=re.M))
    return {k: float(v) for k, v in masses.items()}


def parsing_file_facts(path):
    """The authors' stride file: every ``left``/``right`` interval matrix (start, end) read with scipy.

    Plain files hold ``left`` and ``right``. Files with a ``types`` list hold ``<side>_<type>`` matrices
    (README line 51); the side is the first word of the key. Any other key is named as an issue.
    """
    import scipy.io as sio
    mat = sio.loadmat(str(path), simplify_cells=True)
    keys = sorted(k for k in mat if not k.startswith('__'))
    by_key, sides, issues = {}, {'left': 0, 'right': 0}, []
    for key in keys:
        if key == 'types':
            continue
        side = key.split('_')[0]
        if side not in sides:
            issues.append(f'unrecognised key {key}')
            continue
        arr = np.asarray(mat[key])
        n = 0
        if arr.size:
            arr = np.atleast_2d(arr)
            if arr.ndim != 2 or arr.shape[1] != 2:
                issues.append(f'{key} is not an n-by-2 matrix: shape {arr.shape}')
            else:
                n = int(arr.shape[0])
        by_key[key] = n
        sides[side] += n
    if not by_key:
        issues.append('no left or right matrices')
    return {'keys': keys, 'windows_by_key': by_key, 'windows_left': sides['left'], 'windows_right': sides['right'],
            'issues': issues}


def assign_parsing_files(stems, recordings):
    """Map each ``<name>_parsing`` stem to a recording: exact name, else the longest recording name that prefixes it."""
    out, unassigned = {}, []
    names = sorted(recordings, key=len, reverse=True)
    for stem in stems:
        base = stem[:-len('_parsing')] if stem.endswith('_parsing') else stem
        if base in recordings:
            out[stem] = base
            continue
        hit = next((r for r in names if base.startswith(r + '_')), None)
        if hit is None:
            unassigned.append(stem)
        else:
            out[stem] = hit
    return out, unassigned


class Subject:
    """Paths of one participant; every access is read-only."""

    def __init__(self, root, subject):
        self.root = Path(root)
        self.subject = subject
        self.raw = self.root / 'RawData' / subject
        self.seg = self.root / 'Segmentation' / subject

    def recordings(self):
        return sorted(p.name for p in (self.raw / 'CSV_Data').iterdir() if p.is_dir())

    def parsing_files(self):
        return sorted(p for p in self.seg.glob('*_parsing.mat')) if self.seg.is_dir() else []


def recording_record(subj, rec, out_root, event_files, started=None):
    """The ledger entry for one recording; companions are written under ``out_root/<rec>/``."""
    t0 = time.time()
    entry = {'subject': subj.subject, 'recording': rec, 'issues': [], 'channels': {}, 'event_files': event_files}
    issues = entry['issues']
    folder = subj.raw / 'CSV_Data' / rec
    stance = None
    for channel in CHANNELS:
        src = folder / f'{channel}.csv'
        if not src.is_file():
            issues.append(f'missing channel file {channel}.csv')
            continue
        info = {'size': src.stat().st_size, 'sha256': sha256_file(src)}
        try:
            facts, kept = convert_channel(src, Path(out_root) / rec / f'{channel}.parquet',
                                          list(PLATE_VERTICAL.values()) if channel == 'GroundFrame_GRFs' else None,
                                          CHANNEL_RATE_HZ.get(channel, RATE_HZ))
        except Exception as error:  # named, never skipped silently
            info['error'] = f'{type(error).__name__}: {error}'
            issues.append(f'{channel}.csv not converted: {info["error"]}')
            entry['channels'][channel] = info
            continue
        info.update(facts)
        out = Path(out_root) / rec / f'{channel}.parquet'
        info['parquet_size'] = out.stat().st_size
        info['parquet_sha256'] = sha256_file(out)
        back = parquet_values_digest(out)
        info['parquet_readback_matches'] = (back['rows'] == facts['rows'] and back['values_sha256'] == facts['values_sha256']
                                            and back['column_names_sha256'] == facts['column_names_sha256'])
        info['row_groups'] = back['row_groups']
        if not info['parquet_readback_matches']:
            issues.append(f'{channel} companion does not read back equal to the parsed values')
        if channel == 'GroundFrame_GRFs':
            if all(c in kept for c in PLATE_VERTICAL.values()) and all(len(kept[c]) for c in PLATE_VERTICAL.values()):
                stance = {s: np.nan_to_num(kept[c], nan=0.0) > STANCE_N for s, c in PLATE_VERTICAL.items()}
            else:
                issues.append('vertical force columns missing from GroundFrame_GRFs.csv; no stance')
            plates = {}
            for side in 'LR':
                share = [v for k, v in facts['finite_by_column'].items() if k.startswith(side)]
                plates[side] = {'columns': len(share), 'finite_share_mean': round(float(np.mean(share)), 6) if share else None,
                                'vertical_finite_share': facts['finite_by_column'].get(PLATE_VERTICAL[side])}
            entry['plates'] = plates
        entry['channels'][channel] = info
    all_rows = {c: v.get('rows') for c, v in entry['channels'].items()}
    entry['channel_rows'] = all_rows
    # 200 Hz channels must agree; Raw_EMGs is 2000 Hz and must hold exactly ten rows per 200 Hz row
    rows = {c: r for c, r in all_rows.items() if c not in CHANNEL_RATE_HZ}
    if len(set(rows.values())) > 1:
        issues.append(f'channel files differ in row count: {sorted(set(rows.values()))}')
    for c, factor in ((c, CHANNEL_RATE_HZ[c] / RATE_HZ) for c in CHANNEL_RATE_HZ if c in all_rows):
        if len(set(rows.values())) == 1 and all_rows[c] != factor * next(iter(rows.values())):
            issues.append(f'{c} rows {all_rows[c]} are not {factor:g} times the 200 Hz rows {sorted(set(rows.values()))}')
    for channel, v in entry['channels'].items():
        dev = v.get('time_step_max_abs_dev_s')
        if v.get('has_time_column') is False:
            issues.append(f'{channel} has no time column')
        elif dev is not None and dev > CLOCK_TOLERANCE_S:
            issues.append(f'{channel} clock step differs from 5 ms by up to {dev:.6g} s')
    trc = subj.raw / 'MarkerData' / f'{rec}.trc'
    if trc.is_file():
        entry['markers'] = {'size': trc.stat().st_size, 'sha256': sha256_file(trc)}
        try:
            entry['markers'].update(trc_coverage(trc, stance))
        except Exception as error:
            entry['markers']['error'] = f'{type(error).__name__}: {error}'
            issues.append(f'marker file not read: {entry["markers"]["error"]}')
        m = entry['markers']
        if 'rows' in m:
            if set(rows.values()) and m['rows'] not in set(rows.values()):
                issues.append(f'marker rows {m["rows"]} differ from channel rows {sorted(set(rows.values()))}')
            if m['declared']['rate_hz'] != RATE_HZ:
                issues.append(f'marker file declares {m["declared"]["rate_hz"]} Hz')
            if m['declared']['frames'] != m['rows']:
                issues.append(f'marker header declares {m["declared"]["frames"]} frames, file has {m["rows"]}')
            if m['missing_needed']:
                issues.append('needed markers missing: ' + ','.join(m['missing_needed']))
            if stance is None:
                issues.append('stance share not computed (no ground-reaction vertical force)')
    else:
        issues.append('missing marker file')
    euler = subj.raw / 'Transforms_Euler' / f'{rec}.csv'
    if euler.is_file():
        entry['euler'] = {'size': euler.stat().st_size, 'sha256': sha256_file(euler)}
        try:
            entry['euler'].update(euler_facts(euler))
            if set(rows.values()) and entry['euler']['rows'] not in set(rows.values()):
                issues.append(f'Transforms_Euler rows {entry["euler"]["rows"]} differ from channel rows')
        except Exception as error:
            entry['euler']['error'] = f'{type(error).__name__}: {error}'
            issues.append(f'Transforms_Euler not read: {entry["euler"]["error"]}')
    else:
        issues.append('missing Transforms_Euler file')
    old = subj.raw / 'Transforms' / f'{rec}.mat'
    entry['opaque_transform_table'] = {'present': old.is_file(), 'size': old.stat().st_size if old.is_file() else None,
                                       'used': False}
    entry['status'] = 'ok' if not issues else 'issues'
    entry['seconds'] = round(time.time() - t0, 2)
    return entry


def participant_facts(subj, readme_masses, csv_masses):
    """Per-participant files: models, authors' IK and inverse-dynamics tables (hash), derived Link files (size only)."""
    facts = {'subject': subj.subject, 'models': {}, 'motion_files': {}, 'derived_not_publisher': {}}
    models = subj.raw / 'Models'
    for p in sorted(models.iterdir()) if models.is_dir() else []:
        if p.is_file():
            facts['models'][p.name] = {'size': p.stat().st_size, 'sha256': sha256_file(p)}
    mot = subj.raw / 'MotionFile_EH'
    for p in sorted(mot.iterdir()) if mot.is_dir() else []:
        if p.is_file():
            facts['motion_files'][p.name] = {'size': p.stat().st_size, 'sha256': sha256_file(p)}
    mass = {'readme': readme_masses.get(subj.subject), 'publisher_csv': csv_masses.get(subj.subject)}
    mass['agree'] = mass['readme'] is not None and mass['readme'] == mass['publisher_csv']
    facts['mass_kg'] = mass
    return facts


def load_mass_tables(readme_path, csv_path):
    readme = parse_readme_masses(Path(readme_path).read_text())
    csv = {}
    for line in Path(csv_path).read_text().splitlines()[1:]:
        if line.strip():
            k, v = line.split(',')
            csv[k] = float(v)
    return readme, csv


def event_ledger(subj, wanted_recordings=None):
    """Window counts per authors' stride file and its recording; unassigned files are named."""
    recs = subj.recordings()
    files = subj.parsing_files()
    stems = [p.stem for p in files]
    assigned, unassigned = assign_parsing_files(stems, set(recs))
    out = []
    for p in files:
        if p.stem in assigned and wanted_recordings is not None and assigned[p.stem] not in wanted_recordings:
            continue
        item = {'file': p.name, 'recording': assigned.get(p.stem), 'size': p.stat().st_size, 'sha256': sha256_file(p)}
        try:
            item.update(parsing_file_facts(p))
        except Exception as error:
            item['error'] = f'{type(error).__name__}: {error}'
        out.append(item)
    return out, unassigned


def dumps(obj):
    return json.dumps(obj, sort_keys=True)
