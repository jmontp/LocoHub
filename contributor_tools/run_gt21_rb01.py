"""GT21-RB01 source preservation for Georgia Tech 2021 (standard library only).

Two subcommands, each the single command of one guarded-launcher job. Nothing here decodes a MAT file, signals a
process, retries or overwrites; every output file is created exclusively and scientific_approval is always false.

extract    Stream ONE participant's zip from the authors' 2024 copy into a NEW root (never the existing source
           folder). Before any byte is written it requires that the zip sha256 and size equal the acquisition
           manifest, and that every member name, size and CRC32 in the zip central directory equals the manifest
           (and every size equals the bound expected 2024 listing). Each member is then streamed in 1 MiB blocks and
           its recomputed size, CRC32 and sha256 must equal the directory and the manifest. A per-member ledger is
           written outside the participant folder so the extracted tree keeps the same layout as the local 16.
inventory  Read-only walk (stat only, no file is opened) of the 16 local participants and the six extracted ones.
           Writes one row per recording (conditions file) with the 12 channel files and their sizes, per-mode counts
           and the checks the task states. This ledger is the single index a merged plate/force plus model-fit pass
           can use so each raw recording is opened once.

Mass unit evidence and the Weight literals are carried from the bound cohort crosswalk; reading SubjectInfo.mat and the
conditions tables needs MATLAB and waits for the reviewed native extension (guarded_launcher_native.py).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 1024 * 1024
RESERVE_BYTES = 5 * 1024 ** 3
CHANNELS = ('conditions', 'emg', 'fp', 'gcLeft', 'gcRight', 'gon', 'id', 'ik', 'ik_offset', 'imu', 'jp', 'markers')
MODES = ('levelground', 'ramp', 'stair', 'treadmill')
EXPECTED_LOCAL = {'levelground': 506, 'ramp': 1015, 'stair': 665, 'treadmill': 115}
EXPECTED_SIX = {'levelground': 174, 'ramp': 379, 'stair': 251, 'treadmill': 42}
SIX = ('AB12', 'AB15', 'AB17', 'AB19', 'AB23', 'AB28')
MIRROR = Path('/mnt/s/locomotion_data/gt21_author_mirror_2024')
EXTRACT_ROOT = Path('/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted')
LOCAL_ROOT = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
PLANS = ROOT / 'converted_datasets/reconversion_v2/gt21_s02_author_mirror_20261031/plans'
CROSSWALK = ROOT / 'docs/quality/audits/gt21-s01-cohort-crosswalk.json'
SUBJECT = re.compile(r'AB\d\d')
SAFE_PART = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.\- ]*')


class Rb01Error(RuntimeError):
    pass


def write_json_exclusive(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def safe_member(name):
    """Relative, forward-slash, no dot parts: the only member names that may be written."""
    parts = name.split('/')
    if not name or name.startswith('/') or '\\' in name or '\x00' in name:
        return False
    return all(p not in ('', '.', '..') and SAFE_PART.fullmatch(p) for p in parts)


def check_directory(infos, manifest, listing, subject):
    """Pure comparison of the zip central directory with the manifest and the bound listing.

    Returns the list of (ZipInfo, manifest row) to extract, in zip order. Raises Rb01Error on any difference.
    """
    files = [i for i in infos if not i.is_dir()]
    names = [i.filename for i in files]
    if len(set(names)) != len(names):
        raise Rb01Error('duplicate member names in the zip directory')
    rows = {r['zip_name']: r for r in manifest['files']}
    if len(rows) != len(manifest['files']):
        raise Rb01Error('duplicate zip_name in the manifest')
    listed = {f['path']: f['bytes'] for f in listing['files']}
    if listing.get('subject') != subject or manifest.get('subject') != subject:
        raise Rb01Error('subject differs between zip request, manifest and listing')
    if set(names) != set(rows):
        raise Rb01Error('zip member names differ from the manifest')
    if len(files) != manifest['members']:
        raise Rb01Error('member count differs from the manifest')
    out = []
    for info in files:
        row = rows[info.filename]
        if not safe_member(info.filename):
            raise Rb01Error(f'unsafe member name {info.filename!r}')
        if info.flag_bits & 0x1 or (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
            raise Rb01Error(f'encrypted or symlink member {info.filename!r}')
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise Rb01Error(f'unsupported compression for {info.filename!r}')
        if row['path'] != f'{subject}/{info.filename}':
            raise Rb01Error(f'manifest path differs for {info.filename!r}')
        if info.file_size != row['bytes'] or f'{info.CRC:08x}' != row['crc32']:
            raise Rb01Error(f'size or CRC32 differs from the manifest for {info.filename!r}')
        if listed.get(row['path']) != info.file_size:
            raise Rb01Error(f'size differs from the bound 2024 listing for {info.filename!r}')
        out.append((info, row))
    if sum(i.file_size for i, _ in out) != manifest['member_bytes']:
        raise Rb01Error('total member bytes differ from the manifest')
    return out


def copy_member(zf, info, target):
    """Exclusive create; stream 1 MiB blocks; return size, crc32 and sha256 of what was written."""
    size, crc, sha = 0, 0, hashlib.sha256()
    with zf.open(info) as source, Path(target).open('xb') as sink:
        while True:
            block = source.read(CHUNK)
            if not block:
                break
            size += len(block)
            if size > info.file_size:
                raise Rb01Error('member expanded beyond its declared size')
            sink.write(block)
            sha.update(block)
            crc = zlib.crc32(block, crc)
        sink.flush()
        os.fsync(sink.fileno())
    return {'bytes': size, 'crc32': f'{crc & 0xffffffff:08x}', 'sha256': sha.hexdigest()}


def mkdirs_no_symlink(root, relative):
    current = Path(root)
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise Rb01Error('symlink in extraction tree')
        current.mkdir(exist_ok=True)
    return current


def participant_paths(subject, mirror=MIRROR, plans=PLANS):
    """Zip, manifest, acquisition result and listing of one participant (AB23 is the second attempt)."""
    if not SUBJECT.fullmatch(subject) or subject not in SIX:
        raise Rb01Error('subject must be one of the six new participants')
    folder = 'AB23_attempt2' if subject == 'AB23' else subject
    return {'zip': mirror / folder / f'{subject}.zip',
            'manifest': mirror / 'acquisition_receipts' / folder / 'member_manifest.json',
            'result': mirror / 'acquisition_receipts' / folder / 'acquisition_result.json',
            'listing': plans / f'{subject}_expected_listing.json'}


def counts_by_mode(names):
    """Recordings per mode from conditions member names '<session>/<mode>/conditions/<name>.mat'."""
    counts = {m: 0 for m in MODES}
    for name in names:
        parts = name.split('/')
        if len(parts) >= 3 and parts[-2] == 'conditions' and parts[-3] in counts:
            counts[parts[-3]] += 1
    return counts


def extract(subject, out_root, ledger_path, paths=None, reserve=RESERVE_BYTES):
    paths = paths or participant_paths(subject)
    out_root, ledger_path = Path(out_root), Path(ledger_path)
    manifest = json.loads(Path(paths['manifest']).read_text())
    result = json.loads(Path(paths['result']).read_text())
    listing = json.loads(Path(paths['listing']).read_text())
    zip_path = Path(paths['zip'])
    if result.get('status') != 'acquired_verified_not_extracted' or result.get('subject') != subject:
        raise Rb01Error('acquisition result is not a verified, unextracted acquisition of this subject')
    if manifest['zip_sha256'] != result['zip_sha256'] or manifest['zip_bytes'] != result['zip_bytes']:
        raise Rb01Error('manifest and acquisition result disagree about the zip')
    if zip_path.stat().st_size != manifest['zip_bytes'] or sha256_file(zip_path) != manifest['zip_sha256']:
        raise Rb01Error('zip bytes differ from the acquisition (size or sha256)')
    with zipfile.ZipFile(zip_path) as zf:
        plan = check_directory(zf.infolist(), manifest, listing, subject)
        need = manifest['member_bytes'] + reserve
        free = shutil.disk_usage(out_root.parent if out_root.parent.exists() else out_root.parent.parent).free
        if free < need:
            raise Rb01Error(f'disk admission failed: free {free} < {need}')
        out_root.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        out_root.mkdir()  # exclusive: never resume or merge
        rows = []
        for info, row in plan:
            parent = Path(info.filename).parent
            mkdirs_no_symlink(out_root, parent)
            got = copy_member(zf, info, out_root / info.filename)
            same = (got['bytes'] == info.file_size and got['crc32'] == f'{info.CRC:08x}' and got['sha256'] == row['sha256'])
            if not same:
                raise Rb01Error(f'recomputed size, CRC32 or sha256 differs for {info.filename!r}')
            rows.append({'member': info.filename, **got, 'equals_zip_directory': True,
                         'equals_acquisition_manifest': True, 'equals_bound_listing_size': True})
    names = [r['member'] for r in rows]
    summary = {'schema': 'locohub.gt21_rb01_extraction/1', 'status': 'extracted_verified_unreviewed',
               'scientific_approval': False, 'subject': subject, 'zip_sha256': manifest['zip_sha256'],
               'zip_bytes': manifest['zip_bytes'], 'manifest_sha256': sha256_file(paths['manifest']),
               'listing_sha256': sha256_file(paths['listing']), 'script_sha256': sha256_file(__file__),
               'members_extracted': len(rows), 'bytes_extracted': sum(r['bytes'] for r in rows),
               'conditions_recordings_by_mode': counts_by_mode(names),
               'directory_listing_reread': 'not repeated: the zip was verified by sha256 against the acquisition, '
                                           'which re-listed the live folder before and after the download',
               'output_root': str(out_root), 'peak_rss_mib': peak_rss_mib(), 'members': rows}
    write_json_exclusive(ledger_path, summary)
    return summary


def scan_participant(root, subject, source):
    """Stat-only scan of one participant tree; returns recording rows and a list of problems."""
    base = Path(root) / subject
    sessions = sorted(p.name for p in base.iterdir() if p.is_dir() and p.name != 'osimxml')
    problems, rows = [], []
    if len(sessions) != 1:
        problems.append(f'{subject}: expected one session folder, found {sessions}')
    for session in sessions:
        for mode in MODES:
            cond = base / session / mode / 'conditions'
            names = sorted(p.stem for p in cond.glob('*.mat')) if cond.is_dir() else []
            for name in names:
                files, missing = {}, []
                for channel in CHANNELS:
                    path = base / session / mode / channel / f'{name}.mat'
                    try:
                        files[channel] = path.stat().st_size
                    except FileNotFoundError:
                        missing.append(channel)
                if missing:
                    problems.append(f'{subject}/{mode}/{name}: missing {missing}')
                rows.append({'subject': subject, 'source': source, 'session': session, 'mode': mode,
                             'recording': name, 'channel_bytes': files, 'missing_channels': missing})
    return rows, problems


def inventory(local_root, extract_root, out_root, crosswalk_path=CROSSWALK):
    local_root, extract_root, out_root = Path(local_root), Path(extract_root), Path(out_root)
    out_root.mkdir(parents=True)
    crosswalk = json.loads(Path(crosswalk_path).read_text())
    weights = {p['subject']: p['metadata']['Weight_literal'] for p in crosswalk['participants']}
    local = sorted(p.name for p in local_root.iterdir() if p.is_dir() and SUBJECT.fullmatch(p.name))
    rows, problems, per_subject = [], [], {}
    for subject, root, source in [(s, local_root, 'local_2024_copy_bundle') for s in local] + \
                                 [(s, extract_root, 'extracted_2024_copy_zip') for s in SIX]:
        r, p = scan_participant(root, subject, source)
        rows += r
        problems += p
        per_subject[subject] = {'source': source, 'recordings': len(r), **counts_by_mode_rows(r)}
    totals = {src: {m: 0 for m in MODES} for src in ('local_2024_copy_bundle', 'extracted_2024_copy_zip')}
    for r in rows:
        totals[r['source']][r['mode']] += 1
    checks = {'local_participants': len(local), 'six_participants': len(SIX),
              'local_mode_counts_equal_plan': totals['local_2024_copy_bundle'] == EXPECTED_LOCAL,
              'six_mode_counts_equal_plan': totals['extracted_2024_copy_zip'] == EXPECTED_SIX,
              'all_12_channel_files_present_for_every_recording': not any(r['missing_channels'] for r in rows),
              'recordings_total': len(rows), 'weight_literals_in_crosswalk': len(weights)}
    summary = {'schema': 'locohub.gt21_rb01_inventory/1', 'scientific_approval': False,
               'status': 'inventory_checked_unreviewed' if all(
                   v is not False for v in checks.values()) and not problems else 'inventory_failed',
               'script_sha256': sha256_file(__file__), 'crosswalk_sha256': sha256_file(crosswalk_path),
               'mode_totals': totals, 'expected': {'local': EXPECTED_LOCAL, 'six': EXPECTED_SIX},
               'checks': checks, 'problems': problems, 'per_subject': per_subject,
               'weight_literals_from_crosswalk': weights,
               'weights_reread_from_source': 'not done: SubjectInfo.mat is a MATLAB table; waits for the native export',
               'method': 'directory listing and file sizes only; no file opened', 'peak_rss_mib': peak_rss_mib()}
    with (out_root / 'recording_ledger.jsonl').open('x') as stream:
        for r in rows:
            stream.write(json.dumps(r, ensure_ascii=False) + '\n')
    summary['recording_ledger_sha256'] = sha256_file(out_root / 'recording_ledger.jsonl')
    write_json_exclusive(out_root / 'inventory_summary.json', summary)
    return summary


PUBLISHER_SUBJECTINFO_SHA256 = 'bc990b2c182e0cfc7b405b99fb429026585c224ce6d1ff5249734ec89cb2ce08'


def copy_subject_info(source, target, record_root, expected_sha256=PUBLISHER_SUBJECTINFO_SHA256):
    """Copy SubjectInfo.mat next to the extracted six (the label export reads it from its source root).

    The source must equal the publisher record hash (v1 and v2 manifests, also the authors' 2024 copy per GT21-S02);
    the copy is exclusive and re-hashed; a small record is written into the new ``record_root``."""
    source, target, record_root = Path(source), Path(target), Path(record_root)
    if sha256_file(source) != expected_sha256:
        raise Rb01Error('SubjectInfo.mat differs from the publisher record')
    record_root.mkdir(parents=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst, CHUNK)
    if sha256_file(target) != expected_sha256:
        raise Rb01Error('copied SubjectInfo.mat differs from the source')
    record = {'schema': 'locohub.gt21_rb01_subjectinfo_copy/1', 'scientific_approval': False, 'source': str(source),
              'target': str(target), 'sha256': expected_sha256, 'bytes': target.stat().st_size,
              'basis': 'equals the publisher v1/v2 manifest sha256 (cohort crosswalk) and the authors 2024 copy file (GT21-S02)'}
    write_json_exclusive(record_root / 'subjectinfo_copy.json', record)
    return record


def counts_by_mode_rows(rows):
    counts = {m: 0 for m in MODES}
    for r in rows:
        counts[r['mode']] += 1
    return {'by_mode': counts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    ex = sub.add_parser('extract')
    ex.add_argument('--subject', required=True)
    ex.add_argument('--out-root', type=Path, required=True)
    ex.add_argument('--ledger', type=Path, required=True)
    inv = sub.add_parser('inventory')
    inv.add_argument('--out-root', type=Path, required=True)
    si = sub.add_parser('subjectinfo')
    si.add_argument('--record-root', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.cmd == 'extract':
        summary = extract(args.subject, args.out_root, args.ledger)
        print(json.dumps({k: v for k, v in summary.items() if k != 'members'}, indent=2))
        return 0
    if args.cmd == 'subjectinfo':
        print(json.dumps(copy_subject_info(LOCAL_ROOT / 'SubjectInfo.mat', EXTRACT_ROOT / 'SubjectInfo.mat', args.record_root), indent=2))
        return 0
    summary = inventory(LOCAL_ROOT, EXTRACT_ROOT, args.out_root)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('per_subject', 'weight_literals_from_crosswalk')}, indent=2))
    return 0 if summary['status'] == 'inventory_checked_unreviewed' else 1


if __name__ == '__main__':
    sys.exit(main())
