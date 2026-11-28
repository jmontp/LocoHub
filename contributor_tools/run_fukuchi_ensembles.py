"""Serial bounded range acquisition and per-pair ensemble conversion.

Default is plan-only. Coordinator schedules --run with no competing data worker
or bulk download. Explicit --resume verifies completed artifacts; never overwrites.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import signal
import html
from pathlib import Path
import struct
import subprocess
import time
import urllib.request
import zlib

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def write_json(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def verify(bindings):
    for name,expected in bindings.items():
        if digest(name)!=expected:raise ValueError('Changed bound file: '+name)


def member_bytes(member,fetch):
    header=fetch(member['offset'],30)
    signature,version,flags,method,mtime,mdate,crc,compressed,uncompressed,nlen,xlen=struct.unpack('<I5H3I2H',header)
    if signature!=0x04034b50 or flags&1 or flags!=member['flags'] or method!=member['method'] or not 1<=nlen<=512:
        raise ValueError('Unsupported ZIP local header')
    name=fetch(member['offset']+30,nlen).decode('utf-8')
    if name!=member['name']:raise ValueError('Local/central member name mismatch')
    if not flags&8 and (crc!=member['crc32'] or compressed!=member['compressed_size'] or uncompressed!=member['uncompressed_size']):
        raise ValueError('Local/central ZIP sizes or CRC mismatch')
    compressed=fetch(member['offset']+30+nlen+xlen,member['compressed_size'])
    decoder=zlib.decompressobj(-15)
    raw=decoder.decompress(compressed,member['uncompressed_size']+1)
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or len(raw)!=member['uncompressed_size'] or zlib.crc32(raw)&0xffffffff!=member['crc32']:
        raise ValueError('Member decompression, size or CRC mismatch')
    return raw


def completed_pair(path):
    manifest_path=path/'conversion_manifest.json';report_path=path/'source_readback.json'
    manifest=json.loads(manifest_path.read_text());report=json.loads(report_path.read_text())
    if report['status']!='ensemble_source_values_checked_unreviewed' or report['ensembles']!=2 or report['individual_cycles']!=0 or manifest['rows']!=300:
        raise ValueError('Incomplete pair readback')
    if report['manifest_sha256']!=digest(manifest_path) or manifest['output_sha256']!=digest(path/'ensemble.parquet'):
        raise ValueError('Changed pair output')
    verify(report['verified_input_sha256'])
    return {'stem':path.name,'status':report['status'],'rows':300,'observations':2,'readback_sha256':digest(report_path),'output_sha256':manifest['output_sha256']}


def verify_previous_receipts(previous,out_root,allowed_stems):
    """Reject altered completed evidence before replacing the previous summary."""
    seen=set()
    for receipt in previous['pairs']:
        stem=receipt['stem']
        if stem not in allowed_stems or stem in seen:
            raise ValueError('Unexpected or duplicate previous completion identity')
        seen.add(stem)
        pair=out_root/stem
        for filename,key in [('source_readback.json','readback_sha256'),('ensemble.parquet','output_sha256')]:
            if digest(pair/filename)!=receipt[key]:
                raise ValueError('Previous completion receipt changed: '+stem+'/'+filename)


def write_index(root,state,plan):
    lookup={pair['stem']:pair for pair in plan['pairs']}
    lines=[]
    for result in state['pairs']:
        pair=lookup[result['stem']];stem=html.escape(result['stem'])
        preview=f'<a href="{html.escape(result["preview"])}">View curves</a>' if 'preview' in result else 'Not generated'
        lines.append(f'<tr><td>{html.escape(pair["subject"])}</td><td>{html.escape(pair["environment"])}</td><td>{html.escape(pair["condition"])}</td><td>2 leg averages</td><td>{preview}</td><td><a href="pairs/{stem}/ensemble.parquet">Parquet</a> · <a href="pairs/{stem}/source_readback.json">Source check</a></td></tr>')
    subjects=len({lookup[result['stem']]['subject'] for result in state['pairs']})
    text='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fukuchi ensemble review</title><style>body{font:16px/1.5 system-ui;color:#263345;max-width:1100px;margin:32px auto;padding:0 16px}table{border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #cbd5e1}input{font:inherit;padding:8px}a{color:#334e77}.scroll{overflow:auto}</style><h1>Fukuchi walking: participant-condition averages</h1>'
    text+=f'<p>{len(lines)} of {len(plan["pairs"])} published condition pairs checked · {subjects} participants represented. Scientific review remains open.</p>'
    text+='<p>Each condition has separate left and right means. No raw strides, cycle counts, durations or within-participant standard deviations are reconstructed. Left canonical directions remain unapproved; source components are retained.</p><p>Source: <a href="https://doi.org/10.7717/peerj.4640">Fukuchi, Fukuchi and Duarte (2018)</a>, <a href="https://doi.org/10.6084/m9.figshare.5722711.v6">Figshare version6</a>, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY4.0</a>. Changes: interpolation to150 points, supported right-angle unit and moment-sign conversion.</p>'
    text+='<label>Find a participant or condition <input id="filter" type="search"></label><div class="scroll"><table><thead><tr><th>Participant</th><th>Environment</th><th>Condition code</th><th>Observations</th><th>Preview</th><th>Checked data</th></tr></thead><tbody>'+''.join(lines)+'</tbody></table></div><script>document.getElementById("filter").oninput=function(){const words=this.value.toLowerCase().trim().split(/\\s+/);document.querySelectorAll("tbody tr").forEach(row=>row.hidden=!words.every(word=>row.textContent.toLowerCase().includes(word)));};</script></html>'
    temporary=root/'index.html.tmp';temporary.write_text(text);temporary.replace(root/'index.html')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--previews',action='store_true',help='Also produce one bounded static preview per pair')
    parser.add_argument('--limit-pairs',type=int,help='Explicit pilot subset; never reports full completion')
    args=parser.parse_args()
    if digest(args.plan)!=args.plan_sha256:raise ValueError('Pinned plan hash mismatch')
    plan=json.loads(args.plan.read_text())
    bindings={str(args.plan.resolve()):args.plan_sha256,**plan['input_sha256'],**plan['code_sha256']};verify(bindings)
    run_root=Path(plan['run_root']);source_dir=Path(plan['source_dir']);out_root=Path(plan['output_root'])
    if not run_root.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or source_dir!=run_root/'sources' or out_root!=run_root/'pairs':raise ValueError('Invalid output containment')
    pairs=plan['pairs']
    if args.limit_pairs is not None:
        if args.limit_pairs<1:raise ValueError('Pilot subset must be positive')
        pairs=pairs[:args.limit_pairs]
    if not args.run:
        print(json.dumps({'status':'plan_only','pairs_to_process':len(pairs),'full_inventory_pairs':len(plan['pairs']),'inventory':plan['summary'],'run_root':str(run_root)}));return
    if run_root.exists() and not args.resume:raise FileExistsError('Use a fresh root or explicit verified resume')
    if args.resume and not run_root.exists():raise FileNotFoundError('Resume root does not exist')
    if not run_root.exists():run_root.mkdir(parents=True)
    source_dir.mkdir(exist_ok=True);out_root.mkdir(exist_ok=True)
    import fcntl
    lock=(run_root/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.nice(max(0,19-os.nice(0)))
    guard_path=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py'
    spec=importlib.util.spec_from_file_location('frozen_ensemble_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    state_path=run_root/'summary.json'
    state={'status':'running','scientific_approval':False,'plan_sha256':args.plan_sha256,'pairs':[],'full_inventory_pairs':len(plan['pairs']),'requested_pairs':len(pairs),'network_bytes':0,'preview_requested':args.previews}
    if args.resume:
        previous=json.loads(state_path.read_text())
        if previous['plan_sha256']!=args.plan_sha256:raise ValueError('Resume plan differs')
        verify_previous_receipts(previous,out_root,{pair['stem'] for pair in plan['pairs']})
        state['network_bytes']=previous['network_bytes']
        # Keep receipts for later pairs even if this resumed attempt stops early.
        state['pairs']=previous['pairs']
    write_json(state_path,state)
    last_probe = 0.
    def fetch(start,size):
        nonlocal last_probe
        if time.monotonic()-last_probe>=15:
            guard.check_resources();last_probe=time.monotonic()
        if not 1<=size<=1024**2 or state['network_bytes']+size+1+plan['prior_acquisition_upper_bound_bytes']>16*1024**2:
            raise MemoryError('Range or cumulative acquisition admission exceeded')
        request=urllib.request.Request(plan['archive']['download_url'],headers={'Range':f'bytes={start}-{start+size-1}'})
        # Reserve full request bytes before reading so interrupted downloads remain accounted.
        state['network_bytes']+=size+1;write_json(state_path,state)
        with urllib.request.urlopen(request,timeout=10) as response:
            if response.status!=206 or response.headers.get('Content-Range')!=f"bytes {start}-{start+size-1}/{plan['archive']['size']}":raise ValueError('Unexpected range response')
            raw=response.read(size+1)
        if len(raw)!=size:raise ValueError('Unexpected response length')
        return raw
    def terminate(signum,frame):raise InterruptedError('Runner received signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate)
    try:
        guard.check_resources(prelaunch=True)
        for pair in pairs:
            if (run_root/'STOP_AFTER_CURRENT').exists():
                state['status']='stopped_after_current';break
            verify(bindings)
            stem=pair['stem'];state['active_pair']=stem;write_json(state_path,state)
            evidence_path=source_dir/(stem+'.acquisition.json')
            if evidence_path.exists():
                acquired=json.loads(evidence_path.read_text())
                if acquired['plan_sha256']!=args.plan_sha256 or acquired['stem']!=stem:raise ValueError('Acquisition identity differs')
                verify({str(source_dir/name):e['sha256'] for name,e in acquired['files'].items()})
            else:
                acquired={'stem':stem,'plan_sha256':args.plan_sha256,'source_doi':plan['source_doi'],'archive_url':plan['archive']['download_url'],'whole_archive_md5_verified':False,'files':{}}
                write_json(evidence_path,acquired)
            expected_names={Path(member['name']).name for member in pair['members'].values()}
            if not set(acquired['files'])<=expected_names:raise ValueError('Unexpected acquired source')
            for member in pair['members'].values():
                name=Path(member['name']).name;destination=source_dir/name
                if name in acquired['files']:
                    record=acquired['files'][name]
                    if record['archive_member']!=member['name'] or record['crc32']!=member['crc32'] or record['bytes']!=member['uncompressed_size']:raise ValueError('Member ledger differs from inventory')
                    continue
                if destination.exists():raise FileExistsError('Unledgered partial source exists; reconcile before retry: '+name)
                raw=member_bytes(member,fetch)
                with destination.open('xb') as stream:stream.write(raw)
                acquired['files'][name]={'sha256':digest(destination),'bytes':len(raw),'crc32':member['crc32'],'archive_member':member['name'],'compressed_size':member['compressed_size']}
                write_json(evidence_path,acquired)
            destination=out_root/stem
            if destination.exists():
                if not args.resume:raise FileExistsError('Pair output already exists')
                result=completed_pair(destination)
            else:
                command=['ionice','-c','3','python3',str(ROOT/'contributor_tools/convert_fukuchi_ensemble_pair.py'),'--plan',str(args.plan),'--plan-sha256',args.plan_sha256,'--stem',stem,'--source-dir',str(source_dir),'--output-root',str(out_root)]
                stage={'name':stem}
                guard.guarded_stage(command,run_root/(stem+'.log'),stage)
                result=completed_pair(destination);result['stage']=stage
            if args.previews:
                preview=run_root/'previews'/stem
                if preview.exists():
                    vm=json.loads((preview/'preview_manifest.json').read_text());verify(vm['input_sha256']);verify({str(preview/name):h for name,h in vm['output_sha256'].items()})
                else:
                    command=['ionice','-c','3','python3',str(ROOT/'contributor_tools/build_ensemble_preview.py'),'--input',str(destination/'ensemble.parquet'),'--readback',str(destination/'source_readback.json'),'--output',str(preview)]
                    guard.guarded_stage(command,run_root/(stem+'.preview.log'),{})
                result['preview']='previews/'+stem+'/index.html'
            state['pairs']=[receipt for receipt in state['pairs'] if receipt['stem']!=stem]
            state['pairs'].append(result);write_json(state_path,state)
        else:
            state['status']='all_published_ensemble_pairs_source_checked_unreviewed' if len(pairs)==len(plan['pairs']) else 'explicit_subset_source_checked_unreviewed'
        verify(bindings)
    except BaseException as error:
        state['status']='stopped_incomplete';state['error']=type(error).__name__+': '+str(error);raise
    finally:
        state.pop('active_pair',None)
        state['completed_pairs']=len(state['pairs']);state['completed_observations']=sum(p['observations'] for p in state['pairs']);state['completed_rows']=sum(p['rows'] for p in state['pairs'])
        write_json(state_path,state)
        write_index(run_root,state,plan)
        print(json.dumps({k:v for k,v in state.items() if k!='pairs'}))


if __name__=='__main__':main()
