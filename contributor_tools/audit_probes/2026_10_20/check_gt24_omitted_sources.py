"""Check native clocks and actual joint samples in representative omitted GT24 tasks."""
import csv
import hashlib
import json
import math
from pathlib import Path
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    evidence=ROOT/'converted_datasets/reconversion_v2/gt24_task_coverage_review_20261020'
    census=json.loads((evidence/'source_coverage.json').read_text())
    selected={}
    for record in census['records']:
        if record['mapping_status']!='mapped_task':
            selected.setdefault((record['phase'],record['source_task'],record['mapping_status']),record)
    results=[]
    for record in selected.values():
        folder=SOURCE/(record['phase']+'_Parsed')/'Parsed'/record['subject']/record['recording']
        path=folder/(record['subject']+'_'+record['recording']+'_angle_filt.csv')
        before=path.stat()
        previous=None;start=None;rows=0;bad_clock=0
        columns=['hip_flexion_l','hip_flexion_r','knee_angle_l','knee_angle_r']
        finite={col:0 for col in columns}
        with path.open(newline='') as f:
            reader=csv.DictReader(f)
            assert {'time',*columns}.issubset(reader.fieldnames)
            for row in reader:
                t=float(row['time'])
                if not math.isfinite(t) or (previous is not None and t<=previous):bad_clock+=1
                if start is None:start=t
                previous=t;rows+=1
                for col in columns:
                    finite[col]+=int(math.isfinite(float(row[col])))
        after=path.stat()
        assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        results.append({**record,'source_file':str(path),'source_sha256':digest(path),'rows':rows,
            'start_s':start,'end_s':previous,'nonincreasing_or_nonfinite_clock_samples':bad_clock,'finite_joint_samples':finite})
    report={'representative_files':len(results),'results':results,'probe_sha256':digest(Path(__file__)),
        'census_sha256':digest(evidence/'source_coverage.json'),'scientific_approval':False,
        'limitations':['One representative per phase/source-task/exclusion category',
            'Finite samples and ordered clocks do not establish gait boundaries or physical conventions']}
    target=evidence/'omitted_source_samples.json'
    with target.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'files':len(results),'rows':sum(r['rows'] for r in results),
        'invalid_clock_samples':sum(r['nonincreasing_or_nonfinite_clock_samples'] for r in results),
        'files_with_no_finite_joint_samples':sum(not any(r['finite_joint_samples'].values()) for r in results)}))


if __name__=='__main__':main()
