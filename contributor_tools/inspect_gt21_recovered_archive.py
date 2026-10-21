"""Inspect a verified recovery ZIP directory and small README; never extract.

Admission applies to the versioned recovery root only, not to the active cohort.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import resource
import shutil
import stat
import zipfile

MAX_DIRECTORY = 32 * 1024**2
MAX_MEMBERS = 100000
MAX_README = 64 * 1024
RESERVE = 15 * 1024**3


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def inspect_members(members, subject, free_bytes):
    if len(members)>MAX_MEMBERS:raise ValueError('Member count exceeds admission')
    names=set();subjects=set();expanded=0;compressed=0;max_ratio=0.;readmes=[]
    channels=set();blocking=[]
    for member in members:
        name=member.filename
        path=PurePosixPath(name)
        if not name or '\\' in name or '\x00' in name or path.is_absolute() or any(p in ('..','.') or ':' in p for p in name.rstrip('/').split('/')):
            raise ValueError('Unsafe member path: '+repr(name))
        if any(p.endswith((' ','.')) or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',p) for p in path.parts):raise ValueError('Unsafe Windows member path')
        if '//' in name or name.rstrip('/').casefold() in names:raise ValueError('Ambiguous duplicate member path')
        names.add(name.rstrip('/').casefold())
        mode=member.external_attr>>16
        kind=stat.S_IFMT(mode)
        if kind not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError('Nonregular member or symbolic link')
        if member.flag_bits&1:raise ValueError('Encrypted archive member')
        if member.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise ValueError('Unsupported compression method')
        if member.file_size<0 or member.compress_size<0:raise ValueError('Invalid member size')
        ids=[part for part in path.parts if re.fullmatch(r'AB\d\d',part)]
        subjects.update(ids)
        if not member.is_dir():
            expanded+=member.file_size;compressed+=member.compress_size
            ratio=member.file_size/max(1,member.compress_size);max_ratio=max(max_ratio,ratio)
            if ratio>1000:blocking.append('Member compression ratio exceeds1000: '+name)
            if member.file_size>8*1024**3:blocking.append('Single member exceeds8GiB: '+name)
        for channel in ('static','ik_offset','ik','id','fp','gcLeft','gcRight'):
            if channel in path.parts:channels.add(channel)
        if path.name.lower().startswith('readme') and path.suffix.lower() in ('.txt','.md',''):
            readmes.append(name)
    if subjects!={subject}:raise ValueError('Archive subject set differs from requested single subject')
    # A regular file cannot also be a directory prefix, even under Windows case folding.
    files={m.filename.rstrip('/').casefold() for m in members if not m.is_dir()}
    for name in names:
        parts=name.rstrip('/').split('/')
        if any('/'.join(parts[:n]) in files for n in range(1,len(parts))):raise ValueError('File/directory collision')
    if free_bytes<expanded+RESERVE:blocking.append('Insufficient disk for expanded members plus15GiB reserve')
    return {'subject':subject,'members':len(members),'expanded_bytes':expanded,'compressed_member_bytes':compressed,
        'maximum_member_compression_ratio':max_ratio,'disk_free_bytes_at_check':free_bytes,'required_free_bytes':expanded+RESERVE,
        'subject_directories':sorted(subjects),'source_channel_directories':sorted(channels),'readme_members':readmes,
        'extraction_admitted':not blocking,'blocking_reasons':blocking,
        'admission_scope':'Separate versioned recovery root only; no extraction performed; recheck disk immediately before extraction.'}


def inspect(archive, receipt_path, output):
    archive=Path(archive).resolve();receipt_path=Path(receipt_path).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Preserve existing inspection')
    receipt=json.loads(receipt_path.read_text())
    if receipt.get('status')!='publisher_archive_sha256_verified_not_extracted' or Path(receipt['archive_path']).resolve()!=archive:
        raise ValueError('Verified acquisition receipt required')
    receipt_hash=digest(receipt_path)
    plan_path=receipt_path.parent/'acquisition_plan.json'
    if digest(plan_path)!=receipt['plan_sha256']:raise ValueError('Acquisition plan changed')
    plan=json.loads(plan_path.read_text());subject=plan['subject']
    expected=plan['archive']
    if archive.stat().st_size!=expected['size'] or receipt['sha256']!=expected['sha256_hash'] or digest(archive)!=expected['sha256_hash']:
        raise ValueError('Archive size/hash differs from publisher')
    # Read only bounded end-of-central-directory metadata before ZipFile allocates its index.
    with archive.open('rb') as stream:
        end=zipfile._EndRecData(stream)
    if end is None or end[zipfile._ECD_SIZE]>MAX_DIRECTORY or end[zipfile._ECD_ENTRIES_TOTAL]>MAX_MEMBERS:
        raise ValueError('Central directory admission exceeded or invalid')
    if end[zipfile._ECD_DISK_NUMBER] or end[zipfile._ECD_DISK_START] or end[zipfile._ECD_ENTRIES_THIS_DISK]!=end[zipfile._ECD_ENTRIES_TOTAL]:
        raise ValueError('Multidisk archive unsupported')
    with zipfile.ZipFile(archive) as z:
        result=inspect_members(z.infolist(),subject,shutil.disk_usage(archive.parent).free)
        readmes=[]
        for name in result['readme_members']:
            info=z.getinfo(name)
            if info.file_size>MAX_README or len(readmes)>=4:
                readmes.append({'member':name,'status':'not_read_over_metadata_limit'});continue
            with z.open(info) as stream:content=stream.read(MAX_README+1)
            if len(content)>MAX_README:raise ValueError('README metadata limit exceeded')
            readmes.append({'member':name,'sha256':hashlib.sha256(content).hexdigest(),'text':content.decode('utf-8',errors='replace')})
    if digest(receipt_path)!=receipt_hash or digest(plan_path)!=receipt['plan_sha256'] or digest(archive)!=expected['sha256_hash']:
        raise ValueError('Input changed during inspection')
    result.update(status='archive_directory_checked_not_extracted',scientific_approval=False,
        archive_sha256=expected['sha256_hash'],acquisition_receipt_sha256=receipt_hash,acquisition_plan_sha256=receipt['plan_sha256'],
        inspector_sha256=digest(__file__),archive_doi=expected['doi'],readme_metadata=readmes,
        version_reconciliation={'local_documented_update':'2024-04-28 static and ik_offset additions',
        'archive_static_directory_present':'static' in result['source_channel_directories'],
        'archive_ik_offset_directory_present':'ik_offset' in result['source_channel_directories'],
        'interpretation':'Directory presence is not processing equivalence. Retain publisher version1 provenance; compare source README/scripts/member hashes and conventions before combining with current cohort.',
        'next_gate':'Safe extraction with renewed disk admission into a fresh subject/version root, then bounded schema/source-clock pilot and independent source validation. No canonical publication approval.'})
    with output.open('x') as stream:json.dump(result,stream,indent=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    print(json.dumps(inspect(args.archive,args.receipt,args.output)))


if __name__=='__main__':main()
