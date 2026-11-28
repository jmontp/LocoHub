"""Full GT24 task-eligibility census; never interpret zero output as data approval."""
import ast
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')
CODE=ROOT/'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    tree=ast.parse(CODE.read_text())
    mapping=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='TASK_MAPPING' for target in node.targets))
    output=ROOT/'converted_datasets/reconversion_v2/gt24_task_coverage_review_20261020'
    output.mkdir(exist_ok=False)
    summaries={};records=[];snapshots={}
    for phase in ['Phase3','Phase1And2']:
        source=SOURCE/(phase+'_Parsed')/'Parsed'
        counts=Counter();by_task=defaultdict(Counter);subjects=set()
        observed={}
        name='gt24_phase3_timing_20261020' if phase=='Phase3' else 'gt24_phase1and2_timing_20261020'
        log=ROOT/'converted_datasets/reconversion_v2'/name/'recording_results.jsonl'
        if log.exists():
            # A live writer may have an incomplete final line; retain exact bytes
            # and classify only fully committed JSON lines in this snapshot.
            content=log.read_bytes();snapshot=output/(phase+'_results_snapshot.jsonl');snapshot.write_bytes(content)
            snapshots[phase]={'snapshot_sha256':digest(snapshot),'source_log':str(log)}
            for line in content.splitlines(keepends=True):
                if not line.endswith(b'\n'):continue
                entry=json.loads(line);observed[(entry['subject'],entry['recording'])]=entry
        for subject in sorted(source.glob('BT*')):
            if not subject.is_dir():continue
            subjects.add(subject.name)
            for folder in sorted(subject.iterdir()):
                if not folder.is_dir():continue
                base_task=re.split(r'_\d+(?:_|$)',folder.name)[0]
                match=next(((pattern,value) for pattern,value in mapping.items() if re.search(pattern,folder.name)),None)
                status='unmapped_task' if match is None else ('explicit_task_exclusion' if match[1][0] is None else 'mapped_task')
                counts[status]+=1;by_task[base_task][status]+=1
                entry=observed.get((subject.name,folder.name))
                records.append({'phase':phase,'subject':subject.name,'recording':folder.name,'source_task':base_task,
                    'mapping_status':status,'matched_pattern':match[0] if match else None,
                    'canonical_task':match[1][0] if match else None,
                    'observed_conversion_status':entry.get('status') if entry else None,
                    'observed_rows':entry.get('rows') if entry else None})
        summaries[phase]={'subjects':len(subjects),'recordings':sum(counts.values()),'mapping_counts':dict(counts),
            'by_source_task':{key:dict(value) for key,value in by_task.items()},'observed_results':len(observed)}
    report={'phases':summaries,'records':records,'live_result_snapshots':snapshots,
        'converter_sha256':digest(CODE),'readme_sha256':digest(SOURCE/'readme.txt'),'probe_sha256':digest(Path(__file__)),
        'scientific_approval':False,'limitations':['Mapping eligibility does not prove segmentation or converted data correctness',
            'Result snapshots cover only completed workers at snapshot time; conversions continue separately']}
    (output/'source_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
