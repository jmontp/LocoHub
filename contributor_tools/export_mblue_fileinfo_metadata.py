"""Prepare or explicitly export bounded FileInfo date/task metadata only.

The optional read uses subject_info from small FileInfo MATs, never normalized
signals. Execute --run only when assigned the shared serial numerical slot.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_text(value):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError('Nonempty scalar source text required')
    if Path(value).name != value or '\\' in value or value in ('.', '..'):
        raise ValueError('Unsafe metadata path component')
    return value


def select_fields(subject, info, tasks):
    if scalar_text(info['subject']) != subject:
        raise ValueError('FileInfo subject identity mismatch')
    date = scalar_text(info['date'])
    if not re.fullmatch(r'\d{8}', date):
        raise ValueError('Expected explicit eight-digit source date')
    result = {'date': date, 'tasks': {}}
    for condition, task in sorted(tasks):
        if condition not in ('bare', 'exo'):
            raise ValueError('Unknown source condition')
        key = 'vicon_filename' if condition == 'bare' else 'filename_suffix'
        result['tasks'].setdefault(condition, {})[task] = {
            key: scalar_text(info[condition][task][key])}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    rebuilt = json.loads(args.rebuild.read_text())
    if rebuilt['status'] != 'all_normalized_blocks_reconstructed_unreviewed':
        raise ValueError('Complete rebuilt source lineage required')
    subjects = {}
    for record in rebuilt['records']:
        subject = scalar_text(record['subject'])
        condition, task, *_ = record['source_path'].split('/')
        item = subjects.setdefault(subject, {'sha256': record['subject_info_sha256'], 'tasks': set()})
        if item['sha256'] != record['subject_info_sha256']:
            raise ValueError('Inconsistent FileInfo source hashes')
        item['tasks'].add((condition, task))
    if not 1 <= len(subjects) <= 10:
        raise ValueError('FileInfo subject admission exceeded')
    sources = []
    for subject, item in sorted(subjects.items()):
        path = args.source_root/(subject+'_FileInfo.mat')
        if path.stat().st_size > 1024**2:
            raise MemoryError('FileInfo metadata source exceeds 1 MiB admission')
        if digest(path) != item['sha256']:
            raise ValueError('FileInfo source differs from rebuild lineage')
        sources.append({'subject': subject, 'path': str(path.resolve()), 'sha256': item['sha256'],
                        'tasks': [list(pair) for pair in sorted(item['tasks'])]})
    plan = {'status':'prepared_metadata_export_not_executed','scientific_approval':False,
            'rebuild_sha256':digest(args.rebuild),'exporter_sha256':digest(Path(__file__)), 'sources':sources}
    plan_path = args.output_root/'plan.json'; output = args.output_root/'fileinfo_metadata.json'
    if output.exists():
        raise FileExistsError('Preserve existing metadata receipt')
    if plan_path.exists():
        if json.loads(plan_path.read_text()) != plan:
            raise ValueError('Prepared metadata dependencies changed')
    else:
        args.output_root.mkdir(parents=True,exist_ok=False)
        plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    if not args.run:
        print(json.dumps({'status':plan['status'],'subjects':len(sources)})); return
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)))
    from scipy.io import loadmat
    result = {'status':'fileinfo_metadata_exported_unreviewed','scientific_approval':False,
              'plan_sha256':digest(plan_path),'rebuild_sha256':plan['rebuild_sha256'],
              'exporter_sha256':plan['exporter_sha256'],'subjects':{}}
    for source in sources:
        info = loadmat(source['path'],variable_names=['subject_info'],simplify_cells=True)['subject_info']
        selected = select_fields(source['subject'],info,[tuple(t) for t in source['tasks']])
        selected.update(source_fileinfo_path=source['path'],source_fileinfo_sha256=source['sha256'])
        result['subjects'][source['subject']]=selected
        if digest(source['path'])!=source['sha256']:
            raise ValueError('Source metadata changed during extraction')
    if digest(args.rebuild)!=plan['rebuild_sha256'] or digest(Path(__file__))!=plan['exporter_sha256']:
        raise ValueError('Metadata export lineage changed')
    with output.open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':result['status'],'subjects':len(result['subjects'])}))


if __name__=='__main__':
    main()
