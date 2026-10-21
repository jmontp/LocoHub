"""Create a local static preview of checked ensemble observations, without pooling.

Internal publication preparation only. Does not activate a catalog entry or build
an approved data release. Scientific reads must use the coordinator serial slot.
"""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS = ('Nm_kg', 'N_kg', 'rad', 'deg')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def preview_from_rows(rows):
    if not rows or len(rows) > 3000:
        raise ValueError('Preview requires 1 to 3000 rows')
    groups = {}
    for row in rows:
        if row.get('observation_type') != 'ensemble_curve' or row.get('observation_kind') != 'ensemble':
            raise ValueError('Only explicit ensemble curves are admitted')
        if any(finite(row.get(name)) for name in ('time_s', 'phase_contra', 'source_start_time_s', 'source_end_time_s', 'cycle_duration_s')):
            raise ValueError('This preview does not support invented or shared ensemble timing')
        identity = tuple(row.get(name) for name in ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'task', 'task_id'))
        if any(not isinstance(value, str) or not value.strip() for value in identity):
            raise ValueError('Incomplete ensemble identity')
        if identity[3] not in ('left', 'right'):
            raise ValueError('Explicit anatomical side required')
        groups.setdefault(identity, []).append(row)
    observations, seen_ids = [], set()
    for identity, group in groups.items():
        if identity[2] in seen_ids:
            raise ValueError('Observation ID assigned conflicting metadata')
        seen_ids.add(identity[2])
        if len(group) != 150 or any(not finite(row.get('phase_ipsi')) or abs(row['phase_ipsi']-100*i/149)>1e-8 for i,row in enumerate(group)):
            raise ValueError('Expected complete ordered inclusive 150-point phase grid')
        metadata = [json.loads(row['task_info']) for row in group]
        if any(value != metadata[0] for value in metadata):
            raise ValueError('Changing metadata within ensemble')
        info = metadata[0]
        if info.get('source_grid_samples') != 101 or info.get('export_grid_samples') != 150:
            raise ValueError('Expected explicit source and export grid sizes')
        signals = {}
        for column in group[0]:
            if not (column.startswith('source_') or '_ipsi_' in column) or column.startswith(('source_start_', 'source_end_')):
                continue
            unit = next((unit for unit in UNITS if column.endswith('_'+unit)), None)
            if unit is None:
                continue
            values = [row.get(column) for row in group]
            if any(value is not None and not isinstance(value, (int,float)) for value in values):
                raise ValueError('Nonnumeric signal')
            if any(finite(value) for value in values):
                signals[column] = [value if finite(value) else None for value in values]
        if len(signals)>128:
            raise ValueError('Too many signals for a bounded preview')
        observations.append(dict(zip(('subject','source_recording_id','observation_id','reference_side','task','task_id'),identity),
                                 task_info=info,phase=[row['phase_ipsi'] for row in group],signals=signals))
    columns = sorted({column for observation in observations for column in observation['signals']})
    return {'schema_version':1, 'observation_type':'ensemble_curve', 'scientific_approval':False,
            'subjects':sorted({identity[0] for identity in groups}), 'subject_count':len({identity[0] for identity in groups}),
            'observation_count':len(observations), 'observations':observations,
            'signals':[{'column':column,'label':column.replace('_',' '),
                        'unit':next(unit for unit in UNITS if column.endswith('_'+unit))} for column in columns],
            'note':'Each curve is a source participant-condition mean. Legs and conditions remain separate. Cycle count, duration and within-participant standard deviation are unavailable. No additional averaging is performed.'}


def document(payload, chart_script, preview_script):
    encoded = json.dumps(payload, allow_nan=False, separators=(',',':')).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fukuchi walking ensemble preview</title><style>
body{font:16px/1.5 system-ui;color:#263345;background:#f8fafc;max-width:1200px;margin:32px auto;padding:0 20px}h1{font-size:1.4rem}button,input,select{font:inherit}fieldset{border:1px solid #cbd5e1;margin:16px 0}label{display:inline-block;margin:5px 16px 5px 0}.plots{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}.plot{min-width:0;border-top:1px solid #cbd5e1}svg{width:100%;font:11px system-ui;fill:#526174}.preview-grid{stroke:#e2e8f0}.preview-zero{stroke:#94a3b8}.aggregate-mean{fill:none;stroke:#334155;stroke-width:2}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:6px;border-bottom:1px solid #cbd5e1}.scroll{overflow:auto;max-height:320px}a{color:#334e77}
</style><h1>Fukuchi walking: participant-condition averages</h1>
<p>Source values checked; scientific review remains open. This local pilot is not the complete dataset.</p>
<p id="scope"></p><p id="note"></p><div id="controls"></div><div id="plots" class="plots"></div>
<p>Source: Claudiane A. Fukuchi, Reginaldo K. Fukuchi and Marcos Duarte. <a href="https://doi.org/10.7717/peerj.4640">PeerJ (2018)</a>; <a href="https://doi.org/10.6084/m9.figshare.5722711.v6">Figshare version 6</a>, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Changes: 101 source points interpolated to 150, supported right-angle units and moment signs converted; source-coordinate components retained.</p>
<noscript>Enable JavaScript to explore the embedded small preview. No server or network connection is needed to plot it.</noscript>
<script id="ensemble-data" type="application/json">'''+encoded+'''</script><script>'''+chart_script+'''</script><script>'''+preview_script+'''</script></html>'''


def read_json(path):
    if path.stat().st_size>1024**2:
        raise ValueError('Report exceeds 1 MiB admission')
    return json.loads(path.read_text())


def build(input_path, readback_path, output):
    input_path, readback_path, output = map(lambda p: Path(p).resolve(), (input_path,readback_path,output))
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():
        raise ValueError('Use a new local reconversion preview directory')
    if input_path.stat().st_size>4*1024**2:
        raise ValueError('Pilot Parquet exceeds 4 MiB admission')
    report=read_json(readback_path)
    manifest_path=input_path.parent/'conversion_manifest.json'
    manifest=read_json(manifest_path)
    bindings={str(input_path):manifest['output_sha256'],str(manifest_path):report['manifest_sha256'],str(readback_path):digest(readback_path)}
    if report['status']!='ensemble_source_values_checked_unreviewed' or report['scientific_approval'] is not False:
        raise ValueError('Requires successful independent ensemble readback')
    for name,expected in bindings.items():
        if digest(name)!=expected:raise ValueError('Readback binding changed: '+name)
    import pyarrow.parquet as pq
    with pq.ParquetFile(input_path) as parquet:
        if parquet.metadata.num_rows>3000 or sum(parquet.metadata.row_group(i).total_byte_size for i in range(parquet.metadata.num_row_groups))>16*1024**2:
            raise ValueError('Uncompressed pilot admission exceeded')
        rows=parquet.read(use_threads=False).to_pylist()
    payload=preview_from_rows(rows)
    if len(rows)!=manifest['rows'] or payload['observation_count']!=report['ensembles']:
        raise ValueError('Readback and preview coverage disagree')
    scripts=[ROOT/'docs/javascripts/phase-chart.js',ROOT/'docs/javascripts/ensemble-preview.js']
    bindings.update({str(path):digest(path) for path in scripts})
    rendered=document(payload,*(path.read_text() for path in scripts))
    for name,expected in bindings.items():
        if digest(name)!=expected:raise ValueError('Preview input changed: '+name)
    output.mkdir(parents=True,exist_ok=False)
    (output/'index.html').write_text(rendered)
    (output/'preview.json').write_text(json.dumps(payload,allow_nan=False)+'\n')
    (output/'preview_manifest.json').write_text(json.dumps({'status':'local_ensemble_preview_unreviewed','scientific_approval':False,'input_sha256':bindings,'builder_sha256':digest(__file__),'output_sha256':{name:digest(output/name) for name in ['index.html','preview.json']}},indent=2)+'\n')
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--readback',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    os.nice(max(0,19-os.nice(0)))
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    result=build(args.input,args.readback,args.output)
    print(json.dumps({'subjects':result['subject_count'],'ensemble_observations':result['observation_count']}))


if __name__=='__main__':main()
