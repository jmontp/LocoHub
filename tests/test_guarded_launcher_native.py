"""Fake-host tests (synthetic; no MATLAB, no Windows process) for the DRAFT native launcher extension."""
import json
from pathlib import Path

import pytest

from contributor_tools import guarded_launcher as gl
from contributor_tools import guarded_launcher_native as gn

NONCE = '0123456789abcdef'


def spec_for(tmp_path, **over):
    bindings = {gn.SCRIPT: gl.sha256_file(gl.REPO_ROOT / gn.SCRIPT),
                'contributor_tools/guarded_launcher_native.py': gl.sha256_file(gn.__file__)}
    s = {'job_id': 'gt21-rb01-labels-AB06', 'subject': 'AB06', 'source_root': str(tmp_path / 'src'),
         'output_root': str(tmp_path / 'out' / 'AB06'), 'receipt_path': str(tmp_path / 'r' / 'AB06.json'),
         'bindings': bindings, 'timeout_seconds': 600}
    s.update(over)
    return s


class FakeHost:
    stop_requested = False

    def __init__(self, out_root, trees, win_free=6000, linux_free=8000, workers=None, ws_mib=500):
        self.out_root, self.trees, self.killed, self.ws_mib = Path(out_root), list(trees), [], ws_mib
        self.win_free, self.linux_free, self.workers = win_free, linux_free, workers or []
        self.created = '2026-11-23T00:00:00.0000000Z'

    def disk_free_mib(self, path): return 10 ** 6
    def linux_census(self): return {'workers': [], 'exempt': []}
    def windows_census(self): return {'workers': list(self.workers), 'free_physical_mib': self.win_free, 'process_count': 1}
    def linux_mem_available_mib(self): return self.linux_free
    def windows_free_mib(self): return self.win_free

    def start_matlab(self, script):
        assert 'Start-Process' in script and NONCE in script
        for name in ('labels_AB06.jsonl', 'subject_info_AB06.json'):
            (self.out_root / name).write_text('{}\n')
        return {'pid': 4242, 'created': self.created}

    def windows_tree(self, pid):
        if not self.trees:
            return []
        state = self.trees[0]
        if len(self.trees) > 1 or state == 'gone':
            self.trees.pop(0)
        if state == 'gone' or self.killed and self.killed[-1][1]:
            return []
        return [{'pid': 4242, 'ppid': 1, 'name': 'MATLAB.exe', 'cmdline': f'matlab.exe -batch x {NONCE}',
                 'ws': int(self.ws_mib * 1024 ** 2), 'created': self.created}]

    def taskkill(self, pid, force): self.killed.append((pid, force))


@pytest.fixture
def patched(tmp_path, monkeypatch):
    (tmp_path / 'src' / 'AB06').mkdir(parents=True)
    (tmp_path / 'src' / 'SubjectInfo.mat').write_bytes(b'x')
    fake_exe = tmp_path / 'matlab.exe'
    fake_exe.write_bytes(b'')
    monkeypatch.setattr(gn, 'MATLAB_EXE_WSL', str(fake_exe))
    monkeypatch.setattr(gn, 'to_windows_path', lambda p: 'S:\\fake\\' + Path(p).name)
    monkeypatch.setattr(gn, 'GRACE_S', 0)
    monkeypatch.setattr(gn.secrets, 'token_hex', lambda n: NONCE)
    return tmp_path


def test_spec_rejections(tmp_path):
    for bad in ({'subject': 'AB6'}, {'subject': "AB06'; calc"}, {'timeout_seconds': 3601}, {'extra': 1},
                {'receipt_path': str(tmp_path / 'out' / 'AB06' / 'r.json')},
                {'output_root': str(tmp_path / 'src' / 'AB06' / 'o')}, {'bindings': {gn.SCRIPT: 'a' * 64}}):
        with pytest.raises(gn.NativeSpecError):
            gn.validate_native_spec(spec_for(tmp_path, **bad))
    assert gn.validate_native_spec(spec_for(tmp_path))['subject'] == 'AB06'


def test_command_text_is_strict():
    with pytest.raises(gn.NativeSpecError):
        gn.matlab_expression('S:\\a', "S:\\b'); system('x", 'AB06', NONCE)
    with pytest.raises(gn.NativeSpecError):
        gn.matlab_expression('S:\\a', 'S:\\b', 'AB06', 'not-a-nonce')
    text = gn.start_script(gn.matlab_expression('S:\\a b', 'S:\\o', 'AB06', NONCE), 'S:\\scripts', 'S:\\l.log', NONCE)
    assert text.count('Start-Process') == 1 and '-batch' in text and 'gt21_rb01_label_export' in text


def test_stop_refuses_unverified_identity():
    ident = {'windows_pid': 4242, 'created_utc': 'T1', 'nonce': NONCE}
    host = FakeHost('/tmp', ['x'])
    host.created = 'T2'  # PID reused: different creation time
    actions = gn.stop_tree(host, ident, sleep=lambda s: None)
    assert [a['action'] for a in actions] == ['refused_identity_mismatch']
    assert host.killed == []


def test_dry_run_passes_and_writes_nothing(patched):
    s = spec_for(patched)
    r = gn.run_native_job(s, FakeHost(s['output_root'], []), dry_run=True)
    assert r['status'] == 'preflight_passed' and not Path(s['receipt_path']).exists()


def test_refuses_with_foreign_windows_worker_and_low_memory(patched):
    s = spec_for(patched)
    r = gn.run_native_job(s, FakeHost(s['output_root'], [], workers=[{'name': 'MATLAB.exe'}]), dry_run=True)
    assert r['refusal_reason'] == 'foreign_worker_windows'
    r = gn.run_native_job(s, FakeHost(s['output_root'], [], win_free=2000), dry_run=True)
    assert r['refusal_reason'] == 'startup_memory_reserve'


def test_clean_run_records_identity_and_outputs(patched):
    s = spec_for(patched)
    host = FakeHost(s['output_root'], ['run', 'run', 'gone'])
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'completed' and r['clean_success'] is True
    assert r['process_identity']['windows_pid'] == 4242 and host.killed == []
    assert json.loads(Path(s['receipt_path']).read_text())['clean_success'] is True


def test_working_set_cap_stops_only_the_verified_tree(patched):
    s = spec_for(patched)
    host = FakeHost(s['output_root'], ['run'], ws_mib=3000)
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'stopped_working_set_cap' and r['clean_success'] is False
    assert host.killed and all(pid == 4242 for pid, _ in host.killed)
