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

    def find_matlab_by_nonce(self, nonce): return []
    def taskkill(self, pid, force): self.killed.append((pid, force))


@pytest.fixture
def patched(tmp_path, monkeypatch):
    (tmp_path / 'src' / 'AB06').mkdir(parents=True)
    (tmp_path / 'src' / 'SubjectInfo.mat').write_bytes(b'x')
    fake_exe = tmp_path / 'matlab.exe'
    fake_exe.write_bytes(b'')
    monkeypatch.setattr(gn, 'MATLAB_EXE_WSL', str(fake_exe))
    monkeypatch.setattr(gn, 'to_windows_path', lambda p: 'S:\\fake\\' + Path(p).name)
    monkeypatch.setattr(gn, 'ALLOWED_SOURCE_ROOTS', (tmp_path / 'src',))
    monkeypatch.setattr(gn, 'ALLOWED_OUTPUT_ROOTS', (tmp_path / 'out',))
    monkeypatch.setattr(gn, 'GRACE_S', 0)
    monkeypatch.setattr(gn.secrets, 'token_hex', lambda n: NONCE)
    return tmp_path


def test_spec_rejections(patched):
    tmp_path = patched
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
    assert 'cmd.exe' in text and 'RedirectStandard' not in text and NONCE in text and "''S:\\a b''" in text


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


def test_roots_restricted_to_reviewed_locations(patched):
    for bad in ({'source_root': str(patched / 'elsewhere')}, {'output_root': str(patched / 'elsewhere' / 'AB06')}):
        with pytest.raises(gn.NativeSpecError):
            gn.validate_native_spec(spec_for(patched, **bad))


class StubHost(FakeHost):
    """bin matlab.exe is only a stub: the recorded root exits at once and the real MATLAB (pid 5000) carries the nonce."""

    def __init__(self, out_root, orphan_polls=3, write_outputs=True, **kw):
        super().__init__(out_root, [], **kw)
        self.orphan_polls, self.write_outputs, self.calls = orphan_polls, write_outputs, 0
        self.orphan_created = '2026-11-23T00:00:05.0000000Z'

    def start_matlab(self, script):
        if self.write_outputs:
            for name in ('labels_AB06.jsonl', 'subject_info_AB06.json'):
                (self.out_root / name).write_text('{}\n')
        return {'pid': 4242, 'created': self.created}

    def orphan_row(self):
        return {'pid': 5000, 'ppid': 4242, 'name': 'MATLAB.exe', 'cmdline': f'MATLAB.exe -batch x {NONCE}',
                'ws': int(500 * 1024 ** 2), 'created': self.orphan_created}

    def find_matlab_by_nonce(self, nonce):
        return [self.orphan_row()] if self.calls < self.orphan_polls else []

    def windows_tree(self, pid):
        if pid != 5000:
            return []
        self.calls += 1
        return [self.orphan_row()] if self.calls <= self.orphan_polls else []


def test_orphaned_matlab_is_adopted_watched_and_recorded(patched):
    s = spec_for(patched)
    host = StubHost(s['output_root'])
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'completed' and r['clean_success'] is True
    assert len(r['adoptions']) == 1
    a = r['adoptions'][0]
    assert (a['from_pid'], a['to_pid'], a['to_created_utc']) == (4242, 5000, host.orphan_created)
    assert r['process_identity']['windows_pid'] == 5000
    assert json.loads(Path(s['receipt_path']).read_text())['adoptions'][0]['to_pid'] == 5000


def test_orphan_still_running_at_cap_is_stopped_by_verified_identity(patched):
    s = spec_for(patched)
    host = StubHost(s['output_root'], orphan_polls=10 ** 6)
    host.orphan_row = lambda: {'pid': 5000, 'ppid': 4242, 'name': 'MATLAB.exe', 'cmdline': f'MATLAB.exe {NONCE}',
                               'ws': int(3000 * 1024 ** 2), 'created': host.orphan_created}
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'stopped_working_set_cap'
    assert host.killed and all(pid == 5000 for pid, _ in host.killed)


def test_root_gone_no_orphan_and_no_outputs_fails(patched):
    s = spec_for(patched)
    host = StubHost(s['output_root'], orphan_polls=0, write_outputs=False)
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'failed_outputs_missing' and r['clean_success'] is False and r['adoptions'] == []


def test_start_failure_with_no_process_is_a_launcher_error(patched):
    s = spec_for(patched)
    host = StubHost(s['output_root'], orphan_polls=0)
    def boom(script): raise RuntimeError('powershell died')
    host.start_matlab = boom
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['status'] == 'launcher_error' and r['clean_success'] is False


def test_start_failure_but_process_exists_is_adopted(patched):
    s = spec_for(patched)
    host = StubHost(s['output_root'])
    def boom(script):
        for name in ('labels_AB06.jsonl', 'subject_info_AB06.json'):
            (host.out_root / name).write_text('{}\n')
        raise RuntimeError('powershell died after Start-Process')
    host.start_matlab = boom
    r = gn.run_native_job(s, host, sleep=lambda x: None)
    assert r['adoptions'] and r['adoptions'][0]['to_pid'] == 5000
    assert r['clean_success'] is False  # the start error stays on the record


# ---- B1: the real Host.linux_census over a fake /proc -------------------------------------------------------------
def fake_proc(root, rows):
    """rows: {pid: (argv list, cwd)}; every process has ppid 1 so the ancestor walk ends at once."""
    for pid, (argv, cwd) in rows.items():
        d = root / str(pid)
        d.mkdir(parents=True)
        (d / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv) + b'\0')
        fields = ['S', '1', str(pid), str(pid)] + ['0'] * 15 + ['12345'] + ['0'] * 5
        (d / 'stat').write_text(f'{pid} (python3) ' + ' '.join(fields) + '\n')
        (d / 'cwd').symlink_to(cwd)
    boot = root / 'sys/kernel/random'
    boot.mkdir(parents=True)
    (boot / 'boot_id').write_text('fake-boot\n')
    return root


def census_with(tmp_path, monkeypatch, me_argv, others=None):
    import os
    rows = {os.getpid(): (me_argv, str(gl.REPO_ROOT)), **(others or {})}
    host = gl.Host()
    host.proc = fake_proc(tmp_path / 'proc', rows)
    monkeypatch.setattr(os, 'getppid', lambda: 1)
    return host.linux_census()


def test_native_module_cli_is_exempt_in_the_real_census(tmp_path, monkeypatch):
    census = census_with(tmp_path, monkeypatch, ['python3', '-m', 'contributor_tools.guarded_launcher_native', 's.json'])
    assert census['workers'] == []
    assert [e['why'] for e in census['exempt']] == ['launcher itself (CLI)']


def test_launcher_cli_exemption_does_not_widen(tmp_path, monkeypatch):
    for argv in (['python3', '-c', 'import contributor_tools.guarded_launcher_native'],
                 ['python3', '-m', 'contributor_tools.guarded_launcher_native_evil'],
                 ['python3', '-m', 'contributor_tools.other', 'contributor_tools.guarded_launcher_native']):
        assert gl.is_launcher_cli(argv) is False
        sub = tmp_path / str(len(argv)) / argv[2]
        census = census_with(sub, monkeypatch, argv)
        assert [w['why'] for w in census['workers']] == ['library caller of run_job']


def test_unrelated_python_process_is_still_counted(tmp_path, monkeypatch):
    census = census_with(tmp_path, monkeypatch, ['python3', '-m', 'contributor_tools.guarded_launcher_native', 's.json'],
                         others={999999: (['python3', '-c', 'print(1)'], str(gl.REPO_ROOT))})
    assert [w['pid'] for w in census['workers']] == [999999]


def test_dotdot_paths_are_rejected(patched):
    for key, value in (('source_root', str(patched / 'src' / '..' / 'src')),
                       ('output_root', str(patched / 'out' / '..' / 'out' / 'AB06')),
                       ('output_root', str(patched / 'out' / '..' / 'elsewhere' / 'AB06')),
                       ('receipt_path', str(patched / 'r' / '..' / 'AB06.json'))):
        with pytest.raises(gn.NativeSpecError):
            gn.validate_native_spec(spec_for(patched, **{key: value}))
