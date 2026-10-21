#!/usr/bin/env python3
"""Prepare exact CSV source windows without loading whole GT23 recordings.

Prepared inputs are not converted data. Original transform extraction is a
separate required step before native reconstruction can use this input view.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom

KINDS = ('Joint_Angle', 'Joint_Velocities', 'Joint_Moments',
         'Link_Angle', 'Link_Velocities', 'GroundFrame_GRFs')


def resolve_recording(csv_root, parsing_name):
    base = Path(parsing_name).stem.removesuffix('_parsing')
    candidates = [p.name for p in csv_root.iterdir() if p.is_dir()
                  and (base == p.name or base.startswith(p.name+'_'))]
    if not candidates:
        raise ValueError(f'No source recording matches {parsing_name}')
    return max(candidates, key=len)


def copy_csv_window(source, output, start, end):
    """Preserve literal source lines and one available neighbor at each edge.

    Scan/hash the entire source once and verify its time axis. One pending row is
    retained in memory. Source row indices below exclude the header and are zero based.
    """
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError('Invalid requested time window')
    source_hash = hashlib.sha256()
    before = source.stat()
    count = 0; first = None; last = None; previous = None; previous_time = None
    wrote_start = False; wrote_after = False; source_rows = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as reader, output.open('xb') as writer:
        header = reader.readline(1024**2+1)
        if len(header) > 1024**2 or header.split(b',')[0].strip().lower() != b'time':
            raise ValueError('Expected a bounded CSV header with time first')
        writer.write(header); source_hash.update(header)
        def emit(row, index):
            nonlocal count, first, last
            writer.write(row)
            if first is None: first = index
            last = index; count += 1
        for index, line in enumerate(iter(lambda: reader.readline(1024**2+1), b'')):
            if len(line) > 1024**2:
                raise ValueError('CSV row exceeds 1 MiB bound')
            source_hash.update(line)
            clock = float(line.split(b',',1)[0])
            if not math.isfinite(clock) or (previous_time is not None and clock <= previous_time):
                raise ValueError(f'Source time is not strictly increasing at row {index}')
            if clock >= start and not wrote_start:
                if previous is not None: emit(previous, index-1)
                wrote_start = True
            if start <= clock <= end:
                emit(line, index)
            elif clock > end and not wrote_after:
                emit(line, index); wrote_after = True
            previous = line; previous_time = clock; source_rows += 1
        # A source ending before the window provides no supported interpolation.
        if not wrote_start:
            raise ValueError('Source ends before the requested window')
    if count < 2:
        raise ValueError('Fewer than two source samples cover this window')
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed during window preparation')
    return {'source': str(source.resolve()), 'source_sha256': source_hash.hexdigest(),
            'source_rows': source_rows, 'first_source_row': first, 'last_source_row': last,
            'window_rows': count, 'window_sha256': digest(output), 'window_bytes': output.stat().st_size}


def prepare(source_root, subject, parsing_name, output):
    import numpy as np
    from scipy.io import loadmat
    ensure_storage_headroom(output)
    parsing = source_root/'Segmentation'/subject/parsing_name
    if parsing.stat().st_size > 4*1024**2:
        raise MemoryError('Parsing file exceeds 4 MiB admission')
    parsed = loadmat(parsing)
    intervals = [values for name, values in parsed.items() if not name.startswith('_')
                 and isinstance(values, np.ndarray) and values.ndim == 2 and values.shape[1] == 2
                 and np.issubdtype(values.dtype, np.number) and values.size]
    if not intervals:
        raise ValueError('No source intervals; do not invent a window')
    for values in intervals:
        if not np.isfinite(values).all() or not (values[:,1] > values[:,0]).all():
            raise ValueError('Invalid original source intervals')
    start = min(float(values[:,0].min()) for values in intervals)
    end = max(float(values[:,1].max()) for values in intervals)
    original_csv = source_root/'RawData'/subject/'CSV_Data'
    recording = resolve_recording(original_csv, parsing_name)
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for kind in KINDS:
        name = kind+'.csv'
        records[name] = copy_csv_window(original_csv/recording/name,
            output/'RawData'/subject/'CSV_Data'/recording/name, start, end)
    extra = [parsing, source_root/'RawData/Subject_masses.csv']
    for source in extra:
        target = output/source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    transforms = source_root/'RawData'/subject/'Transforms'/(recording+'.mat')
    manifest = {'status': 'csv_window_prepared_transform_cache_required',
                'subject': subject, 'parsing': parsing_name, 'recording': recording,
                'start_s': start, 'end_s': end, 'csv_files': records,
                'other_source_sha256': {str(p.resolve()): digest(p) for p in extra+[transforms]},
                'original_transforms': str(transforms.resolve()),
                'transform_status': 'not_extracted', 'converted_data': False}
    (output/'source_window_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/Gtech_2023'))
    parser.add_argument('--subject',required=True)
    parser.add_argument('--parsing',required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    for name in [args.subject,args.parsing]:
        if Path(name).name != name or name in {'.','..'}:
            parser.error('Subject and parsing file must be single path components')
    import resource
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    manifest=prepare(args.source_root.resolve(),args.subject,args.parsing,args.output_root.resolve())
    print(json.dumps({'status':manifest['status'],'start_s':manifest['start_s'],'end_s':manifest['end_s'],
                      'csv_window_mib':sum(v['window_bytes'] for v in manifest['csv_files'].values())/1024**2}))


if __name__=='__main__':
    main()
