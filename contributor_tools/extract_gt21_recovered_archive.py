"""Extract verified publisher v1 ZIP into a fresh isolated root; default plan only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import time
import zipfile
import zlib

from contributor_tools import inspect_gt21_recovered_archive as inspector

CHUNK = 1024 * 1024


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)


def copy_member(source, target, expected_size, expected_crc, guard=lambda: None):
    """Exclusive creation; retain partial file on failure for diagnosis."""
    size = crc = 0
    sha = hashlib.sha256()
    with Path(target).open('xb') as output:
        while True:
            guard()
            chunk = source.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > expected_size:
                raise ValueError('Member expanded beyond declared size')
            output.write(chunk)
            sha.update(chunk)
            crc = zlib.crc32(chunk, crc)
        output.flush()
        os.fsync(output.fileno())
    if size != expected_size or crc & 0xffffffff != expected_crc:
        raise ValueError('Member size or CRC mismatch')
    return {'bytes': size, 'crc32': f'{crc & 0xffffffff:08x}', 'sha256': sha.hexdigest()}


def safe_directories(root, relative):
    """Create one component at a time; never traverse an existing symlink."""
    current = root
    if root.is_symlink():
        raise ValueError('Extraction root became a symlink')
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink appeared in extraction tree')
        try:
            current.mkdir()
        except FileExistsError:
            if not current.is_dir():
                raise ValueError('Unexpected file in directory path')
    return current


def prepare(receipt_path, inspection_path, output_root):
    receipt_path = Path(receipt_path).resolve()
    inspection_path = Path(inspection_path).resolve()
    requested = Path(output_root).absolute()
    # Explicit isolated sibling only, never the active participant source tree.
    if requested.parent != receipt_path.parent or not requested.name.startswith('extracted_v1_'):
        raise ValueError('Output must be an extracted_v1_* sibling of acquisition receipt')
    if requested.exists() or requested.is_symlink():
        raise FileExistsError('Fresh output root required')
    receipt = json.loads(receipt_path.read_text())
    inspection = json.loads(inspection_path.read_text())
    acquisition_path = receipt_path.parent / 'acquisition_plan.json'
    acquisition = json.loads(acquisition_path.read_text())
    archive = Path(receipt['archive_path']).resolve()
    expected = acquisition['archive']
    bindings = {str(p): inspector.digest(p) for p in (receipt_path, inspection_path, acquisition_path, Path(__file__).resolve(), Path(inspector.__file__).resolve())}
    if receipt['status'] != 'publisher_archive_sha256_verified_not_extracted' or inspection['status'] != 'archive_directory_checked_not_extracted' or inspection.get('extraction_admitted') is not True:
        raise ValueError('Successful acquisition and inspection required')
    if (receipt['plan_sha256'] != bindings[str(acquisition_path)] or inspection['acquisition_plan_sha256'] != receipt['plan_sha256'] or inspection['acquisition_receipt_sha256'] != bindings[str(receipt_path)] or inspection['inspector_sha256'] != bindings[str(Path(inspector.__file__).resolve())]):
        raise ValueError('Receipt or inspector binding changed')
    if receipt['sha256'] != expected['sha256_hash'] or inspection['archive_sha256'] != receipt['sha256'] or archive.stat().st_size != expected['size'] or receipt['bytes'] != expected['size'] or inspection['subject'] != acquisition['subject']:
        raise ValueError('Archive provenance differs')
    return {'status': 'prepared_not_extracted', 'archive': str(archive), 'archive_sha256': expected['sha256_hash'], 'archive_doi': expected['doi'], 'subject': acquisition['subject'], 'output_root': str(requested), 'bindings': bindings, 'inspection': inspection}


def extract(plan, timeout_seconds=3600):
    root = Path(plan['output_root'])
    archive = Path(plan['archive'])
    start = time.monotonic()
    def check_bindings():
        for path, expected in plan['bindings'].items():
            if inspector.digest(path) != expected:
                raise ValueError('Bound evidence changed: ' + path)
        if inspector.digest(archive) != plan['archive_sha256']:
            raise ValueError('Publisher archive hash mismatch')
    check_bindings()
    with archive.open('rb') as stream:
        end = zipfile._EndRecData(stream)
    if end is None or end[zipfile._ECD_SIZE] > inspector.MAX_DIRECTORY or end[zipfile._ECD_ENTRIES_TOTAL] > inspector.MAX_MEMBERS or end[zipfile._ECD_DISK_NUMBER] or end[zipfile._ECD_DISK_START] or end[zipfile._ECD_ENTRIES_THIS_DISK] != end[zipfile._ECD_ENTRIES_TOTAL]:
        raise ValueError('Central directory admission failed')
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        admission = inspector.inspect_members(members, plan['subject'], shutil.disk_usage(root.parent).free)
        for field in ('members', 'expanded_bytes', 'compressed_member_bytes', 'subject_directories', 'source_channel_directories'):
            if admission[field] != plan['inspection'][field]:
                raise ValueError('Inspection scope changed: ' + field)
        if not admission['extraction_admitted']:
            raise ValueError('Renewed extraction admission failed')
        root.mkdir()  # Exclusive; never resume an incomplete extraction implicitly.
        write_json(root / 'extraction_plan.json', plan)
        completed = 0
        remaining = admission['expanded_bytes']
        last_disk = 0.0
        def guard():
            nonlocal last_disk
            now = time.monotonic()
            if now - start > timeout_seconds or (root / 'STOP').exists():
                raise RuntimeError('Extraction timeout or STOP requested')
            if now - last_disk > 5:
                if shutil.disk_usage(root).free < inspector.RESERVE:
                    raise RuntimeError('Disk reserve violated')
                last_disk = now
        try:
            with (root / 'member_manifest.jsonl').open('x') as manifest:
                for member in members:
                    guard()
                    # Re-admit all remaining bytes before every member.
                    if shutil.disk_usage(root).free < remaining + inspector.RESERVE:
                        raise RuntimeError('Remaining extraction disk admission failed')
                    target = root / 'files' / member.filename
                    if member.is_dir():
                        if member.file_size != 0:
                            raise ValueError('Directory contains unexpected payload')
                        safe_directories(root, Path('files') / member.filename)
                        continue
                    safe_directories(root, Path('files') / Path(member.filename).parent)
                    # Refuse unexpected parent substitutions, including symlinks.
                    if any(p.is_symlink() for p in [target, *target.parents] if p == root or root in p.parents):
                        raise ValueError('Symlink appeared in extraction tree')
                    with source.open(member) as stream:
                        result = copy_member(stream, target, member.file_size, member.CRC, guard)
                    manifest.write(json.dumps({'member': member.filename, **result}) + '\n')
                    manifest.flush()
                    completed += 1
                    remaining -= member.file_size
            check_bindings()
            result = {'status': 'publisher_v1_extracted_integrity_checked_unreviewed', 'scientific_approval': False, 'files': completed, 'expanded_bytes': admission['expanded_bytes'], 'archive_sha256': plan['archive_sha256'], 'archive_doi': plan['archive_doi'], 'manifest_sha256': inspector.digest(root / 'member_manifest.jsonl'), 'version_reconciliation': plan['inspection'].get('version_reconciliation'), 'next_gate': 'Bounded MAT schema and source-clock pilot; establish source processing conventions before combining with 2024 cohort. Version1 lacks documented 2024 static/ik_offset additions; no equivalence inferred.'}
            write_json(root / 'extraction_result.json', result)
            return result
        except BaseException as exc:
            write_json(root / 'extraction_failure.json', {'status': 'failed_preserved', 'completed_files': completed, 'error': str(exc)})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--inspection', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2,) * 2)
    os.nice(19)
    plan = prepare(args.receipt, args.inspection, args.output_root)
    print(json.dumps(extract(plan) if args.run else plan, indent=2))


if __name__ == '__main__':
    main()
