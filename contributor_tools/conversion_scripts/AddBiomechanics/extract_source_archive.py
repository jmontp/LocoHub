"""Inspect or extract one source ZIP without flattening or deleting source paths."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile


def digest(path, guard=lambda: None):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            guard()
            result.update(block)
    return result.hexdigest()


def members(archive):
    result = []
    seen = set()
    files = set()
    for item in archive.infolist():
        name = item.filename
        path = PurePosixPath(name)
        if (not name or '\\' in name or path.is_absolute()
                or any(part in ('', '.', '..') or ':' in part for part in name.rstrip('/').split('/'))):
            raise ValueError('Unsafe source member path: ' + name)
        mode = item.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
            raise ValueError('Nonregular source member: ' + name)
        key = str(path).casefold()
        if key in seen:
            raise ValueError('Duplicate or case-colliding source member: ' + name)
        seen.add(key)
        if not item.is_dir():
            files.add(key)
        result.append(item)
    for item in result:
        if any(str(parent).casefold() in files for parent in PurePosixPath(item.filename).parents):
            raise ValueError('File/directory collision: ' + item.filename)
    return result


def extract(source, output, *, run=False, reserve_bytes=5 * 1024**3, guard=lambda: None):
    guard()
    source = Path(source).resolve()
    output = Path(output).resolve()
    before = source.stat()
    with zipfile.ZipFile(source) as archive:
        entries = members(archive)
        report = {
            'status': 'inspected_not_extracted', 'scientific_approval': False,
            'source_path': str(source), 'source_bytes': before.st_size,
            'source_sha256': digest(source, guard),
            'files': [{'member': item.filename, 'bytes': item.file_size,
                       'crc32': item.CRC, 'directory': item.is_dir()} for item in entries],
            'uncompressed_bytes': sum(item.file_size for item in entries),
        }
        if not run:
            return report
        if output.exists():
            raise FileExistsError('Use a fresh output directory; existing evidence is preserved')
        if not output.parent.is_dir():
            raise ValueError('Output parent must already exist')
        if shutil.disk_usage(output.parent).free < reserve_bytes + report['uncompressed_bytes']:
            raise OSError('Insufficient disk space while preserving the reserve')
        output.mkdir()
        payload = output / 'source'
        payload.mkdir()
        report['status'] = 'extracting'

        def save():
            temp = output / 'extraction.tmp'
            temp.write_text(json.dumps(report, indent=2) + '\n')
            temp.replace(output / 'extraction.json')

        try:
            save()
            for item, row in zip(entries, report['files']):
                guard()
                target = payload.joinpath(*PurePosixPath(item.filename).parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256()
                size = 0
                with archive.open(item) as original, target.open('xb') as restored:
                    for block in iter(lambda: original.read(1024 * 1024), b''):
                        guard()
                        if shutil.disk_usage(output).free < reserve_bytes + len(block):
                            raise OSError('Disk reserve reached; partial evidence retained')
                        h.update(block)
                        restored.write(block)
                        size += len(block)
                if size != item.file_size or digest(target, guard) != h.hexdigest():
                    raise ValueError('Extracted source member failed independent file readback')
                row['sha256'] = h.hexdigest()
                row['extracted_path'] = str(target.relative_to(output))
                save()
            after = source.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or digest(source, guard) != report['source_sha256']:
                raise ValueError('Source archive changed during extraction')
            report['status'] = 'all_archive_members_extracted_byte_checked_unreviewed'
        except BaseException as error:
            report.update(status='incomplete_partial_preserved', reason=str(error))
            raise
        finally:
            save()
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true', help='Explicitly extract after disk admission')
    args = parser.parse_args()
    import os
    import resource
    import sys
    import time
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    os.nice(max(0, 19 - os.nice(0)))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from contributor_tools.preserve_mblue_planar_estimates import headroom, windows_available_mib
    last_check = [0.]
    def guard():
        if time.monotonic() - last_check[0] < 15:
            return
        headroom(args.output.parent)
        required = 2816 if last_check[0] == 0 else 2048
        if windows_available_mib() < required:
            raise MemoryError('Source extraction memory reserve insufficient')
        last_check[0] = time.monotonic()
    result = extract(args.archive, args.output, run=args.run, guard=guard)
    print(json.dumps({key: value for key, value in result.items() if key != 'files'}, indent=2))
