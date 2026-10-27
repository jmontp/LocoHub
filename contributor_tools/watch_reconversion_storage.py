#!/usr/bin/env python3
"""Stop specified serial queues at recording boundaries if host storage runs low.

This guard supplements per-worker output-drive checks. In WSL, free space inside
ext4 does not establish free space on the Windows drive containing its VHD.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time


def live_queue(root):
    try:
        state=json.loads((root/'queue_status.json').read_text())
        command=Path(f"/proc/{int(state['pid'])}/cmdline").read_bytes()
        return any(Path(token.decode()).resolve()==root/'run_queue.py' for token in command.split(b'\0') if token)
    except (FileNotFoundError,KeyError,ValueError,ProcessLookupError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',type=Path,action='append',required=True)
    parser.add_argument('--host-mount',type=Path,default=Path('/mnt/c'))
    parser.add_argument('--min-free-mib',type=int,default=1024)
    parser.add_argument('--status',type=Path,required=True)
    args=parser.parse_args()
    if args.min_free_mib<1:parser.error('Positive free-space floor required')
    roots=[p.resolve() for p in args.queue]
    if any(not (p/'run_queue.py').is_file() for p in roots):parser.error('Each queue must have an existing run_queue.py')
    os.nice(max(0,19-os.nice(0)));args.status.parent.mkdir(parents=True,exist_ok=True)
    state={'pid':os.getpid(),'queues':[str(p) for p in roots],'host_mount':str(args.host_mount),'minimum_free_mib':args.min_free_mib}
    def save():
        tmp=args.status.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(args.status)
    while True:
        active=[p for p in roots if live_queue(p)]
        free=shutil.disk_usage(args.host_mount).free
        state.update(active_queues=[str(p) for p in active],free_bytes=free,checked_at_unix=time.time())
        if not active:state['status']='queues_no_longer_running';save();return
        if free<args.min_free_mib*1024**2:
            # Never kill native MATLAB or interrupt a file write. Queue markers
            # propagate the stop to the active worker at its next safe boundary.
            for root in roots:(root/'STOP_AFTER_CURRENT').touch()
            state['status']='stop_requested_host_storage_low';save();return
        state['status']='watching';save();time.sleep(10)


if __name__=='__main__':main()
