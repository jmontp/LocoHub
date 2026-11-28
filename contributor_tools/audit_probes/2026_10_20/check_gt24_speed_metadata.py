"""Check speed metadata against source task families that encode treadmill speeds."""
import ast
import hashlib
import json
from pathlib import Path
import re
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
ROOT=Path(__file__).resolve().parents[3]
CODE=ROOT/'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py'


def main():
    tree=ast.parse(CODE.read_text())
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TASK_MAPPING' for t in n.targets))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='map_task_name')
    # Execute the actual small metadata function without importing numerical code.
    function.returns=None
    scope={'re':re,'TASK_MAPPING':ast.literal_eval(assignment.value)}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(CODE),'exec'),scope)
    base=ROOT/'converted_datasets/reconversion_v2/gt24_task_coverage_review_20261020'
    census=json.loads((base/'source_coverage.json').read_text())
    findings=[]
    for record in census['records']:
        task,task_id,info=scope['map_task_name'](record['recording'])
        if task is not None and 'speed_m_s' in info and record['source_task'] not in {'normal_walk','walk_backward'}:
            findings.append({**record,'emitted_speed_m_s':info['speed_m_s'],
                'reason':'Global digit-hyphen-digit regex treats a non-speed task descriptor as speed'})
    report={'affected_recordings':len(findings),'records':findings,
        'converter_sha256':hashlib.sha256(CODE.read_bytes()).hexdigest(),
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_evidence':'GT24 original readme lists encoded speeds for normal_walk and walk_backward; local jump folders use 90-f/90-s, not numeric speed suffixes',
        'scientific_approval':False}
    with (base/'speed_metadata_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'affected_recordings':len(findings),'emitted_values':sorted({r['emitted_speed_m_s'] for r in findings}),
        'source_tasks':sorted({r['source_task'] for r in findings})}))


if __name__=='__main__':main()
