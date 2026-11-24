"""Synthetic fixtures only (not GT21 data) for the RB01 extraction and inventory runner."""
import hashlib
import json
import zipfile
import zlib

import pytest

from contributor_tools import run_gt21_rb01 as rb

SUBJ = 'AB17'


def make_case(tmp_path, tamper=None, extra_name=None):
    """A tiny synthetic zip plus manifest, acquisition result and listing with independently known values."""
    payloads = {'s1/levelground/conditions/a_01_01.mat': b'abc' * 5,
                's1/levelground/fp/a_01_01.mat': b'0123456789',
                'osimxml/AB17.osim': b'<x/>'}
    if extra_name:
        payloads[extra_name] = b'z'
    zpath = tmp_path / 'AB17.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in payloads.items():
            zf.writestr(name, data)
    files = [{'path': f'{SUBJ}/{n}', 'zip_name': n, 'bytes': len(d), 'crc32': f'{zlib.crc32(d):08x}',
              'sha256': hashlib.sha256(d).hexdigest()} for n, d in payloads.items()]
    if tamper == 'crc':
        files[0]['crc32'] = '00000000'
    zsha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    manifest = {'subject': SUBJ, 'zip_sha256': zsha, 'zip_bytes': zpath.stat().st_size, 'members': len(files),
                'member_bytes': sum(len(d) for d in payloads.values()), 'files': files}
    result = {'status': 'acquired_verified_not_extracted', 'subject': SUBJ, 'zip_sha256': zsha,
              'zip_bytes': zpath.stat().st_size}
    listing = {'subject': SUBJ, 'files': [{'path': f['path'], 'bytes': f['bytes']} for f in files]}
    if tamper == 'listing':
        listing['files'][1]['bytes'] += 1
    paths = {}
    for key, value in (('manifest', manifest), ('result', result), ('listing', listing)):
        paths[key] = tmp_path / f'{key}.json'
        paths[key].write_text(json.dumps(value))
    paths['zip'] = zpath
    return paths, payloads


def test_extract_writes_exact_bytes_and_ledger(tmp_path):
    paths, payloads = make_case(tmp_path)
    out, ledger = tmp_path / 'out' / SUBJ, tmp_path / 'out' / '_ledgers' / 'AB17.json'
    summary = rb.extract(SUBJ, out, ledger, paths=paths, reserve=0)
    for name, data in payloads.items():
        assert (out / name).read_bytes() == data
    assert summary['members_extracted'] == 3 and summary['bytes_extracted'] == 15 + 10 + 4
    assert summary['conditions_recordings_by_mode'] == {'levelground': 1, 'ramp': 0, 'stair': 0, 'treadmill': 0}
    assert json.loads(ledger.read_text())['scientific_approval'] is False
    with pytest.raises(FileExistsError):  # never resumes or merges
        rb.extract(SUBJ, out, tmp_path / 'again.json', paths=paths, reserve=0)


@pytest.mark.parametrize('tamper', ['crc', 'listing'])
def test_extract_refuses_before_writing_when_evidence_differs(tmp_path, tamper):
    paths, _ = make_case(tmp_path, tamper=tamper)
    out = tmp_path / 'out' / SUBJ
    with pytest.raises(rb.Rb01Error):
        rb.extract(SUBJ, out, tmp_path / 'l.json', paths=paths, reserve=0)
    assert not out.exists()


def test_extract_refuses_unsafe_member_and_changed_zip(tmp_path):
    paths, _ = make_case(tmp_path, extra_name='s1/../evil.mat')
    with pytest.raises(rb.Rb01Error):
        rb.extract(SUBJ, tmp_path / 'o' / SUBJ, tmp_path / 'l.json', paths=paths, reserve=0)
    paths, _ = make_case(tmp_path / 'b' if (tmp_path / 'b').mkdir() is None else tmp_path)
    with paths['zip'].open('ab') as stream:
        stream.write(b'x')
    with pytest.raises(rb.Rb01Error):
        rb.extract(SUBJ, tmp_path / 'o2' / SUBJ, tmp_path / 'l2.json', paths=paths, reserve=0)


def test_safe_member():
    assert rb.safe_member('a/b/c.mat')
    for bad in ('/a', 'a//b', '../a', 'a/./b', 'a\\b', ''):
        assert not rb.safe_member(bad)


def build_tree(root, subject, n_by_mode, drop=None):
    for mode, n in n_by_mode.items():
        for i in range(n):
            for ch in rb.CHANNELS:
                if drop == (mode, i, ch):
                    continue
                path = root / subject / 'sess' / mode / ch / f'{mode}_{i:02d}.mat'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'x' * (i + 1))


def test_scan_participant_counts_and_missing_channel(tmp_path):
    build_tree(tmp_path, 'AB06', {'levelground': 2, 'ramp': 1}, drop=('ramp', 0, 'imu'))
    rows, problems = rb.scan_participant(tmp_path, 'AB06', 'synthetic')
    assert [r['mode'] for r in rows].count('levelground') == 2 and len(rows) == 3
    assert any('missing' in p and 'imu' in p for p in problems)
    assert next(r for r in rows if r['mode'] == 'levelground' and r['recording'].endswith('01'))['channel_bytes']['fp'] == 2


def test_inventory_reports_failed_status_for_wrong_counts(tmp_path):
    local, ext = tmp_path / 'local', tmp_path / 'ext'
    build_tree(local, 'AB06', {'levelground': 1})
    for s in rb.SIX:
        build_tree(ext, s, {'levelground': 1})
    cross = tmp_path / 'c.json'
    cross.write_text(json.dumps({'participants': [{'subject': 'AB06', 'metadata': {'Weight_literal': '70.0'}}]}))
    summary = rb.inventory(local, ext, tmp_path / 'inv', crosswalk_path=cross)
    assert summary['status'] == 'inventory_failed'  # counts differ from the plan on purpose
    assert summary['checks']['local_mode_counts_equal_plan'] is False
    assert summary['checks']['all_12_channel_files_present_for_every_recording'] is True
    assert len((tmp_path / 'inv/recording_ledger.jsonl').read_text().splitlines()) == 1 + len(rb.SIX)


def test_copy_subject_info_exact_and_exclusive(tmp_path):
    src = tmp_path / 'SubjectInfo.mat'
    src.write_bytes(b'synthetic bytes')
    sha = hashlib.sha256(b'synthetic bytes').hexdigest()
    rec = rb.copy_subject_info(src, tmp_path / 'copy.mat', tmp_path / 'rec', expected_sha256=sha)
    assert (tmp_path / 'copy.mat').read_bytes() == b'synthetic bytes' and rec['sha256'] == sha
    with pytest.raises(rb.Rb01Error):  # a source that is not the publisher record is refused before any write
        rb.copy_subject_info(src, tmp_path / 'copy2.mat', tmp_path / 'rec2', expected_sha256='0' * 64)
    assert not (tmp_path / 'copy2.mat').exists()
    with pytest.raises(FileExistsError):
        rb.copy_subject_info(src, tmp_path / 'copy3.mat', tmp_path / 'rec', expected_sha256=sha)
