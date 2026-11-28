import json
from types import SimpleNamespace
from contributor_tools import watch_reconversion_storage as guard


def test_low_host_space_requests_boundary_stop_without_killing_workers(tmp_path,monkeypatch):
    queue=tmp_path/'queue';queue.mkdir();(queue/'run_queue.py').write_text('# fixture')
    status=tmp_path/'status.json'
    monkeypatch.setattr('sys.argv',['guard','--queue',str(queue),'--host-mount',str(tmp_path),'--min-free-mib','1024','--status',str(status)])
    monkeypatch.setattr(guard,'live_queue',lambda root:True)
    monkeypatch.setattr(guard.shutil,'disk_usage',lambda mount:SimpleNamespace(free=500*1024**2))
    monkeypatch.setattr(guard.os,'nice',lambda value:19)
    guard.main()
    assert (queue/'STOP_AFTER_CURRENT').exists()
    assert json.loads(status.read_text())['status']=='stop_requested_host_storage_low'


def test_finished_queue_is_not_modified(tmp_path,monkeypatch):
    queue=tmp_path/'queue';queue.mkdir();(queue/'run_queue.py').write_text('# fixture')
    status=tmp_path/'status.json'
    monkeypatch.setattr('sys.argv',['guard','--queue',str(queue),'--host-mount',str(tmp_path),'--status',str(status)])
    monkeypatch.setattr(guard,'live_queue',lambda root:False)
    monkeypatch.setattr(guard.os,'nice',lambda value:19)
    guard.main()
    assert not (queue/'STOP_AFTER_CURRENT').exists()
    assert json.loads(status.read_text())['status']=='queues_no_longer_running'
