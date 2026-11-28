"""Inventory original GT23 annotations against the native phase task allowlist.

This checks coverage eligibility, not successful conversion or event semantics.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import json
from pathlib import Path
import re
import sys
from collections import Counter
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest,ensure_storage_headroom
from contributor_tools.prepare_gt23_recording import resolve_recording


def main():
    source=Path('/mnt/s/locomotion_data/Gtech_2023')
    code=ROOT/'contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_phase_to_parquet.m'
    definition=re.search(r'critical_activities\s*=\s*\{(.*?)\};',code.read_text(),re.S).group(1)
    allowed=set(re.findall(r"'([^']+)'",definition))
    records=[];counts=Counter();issues=[]
    for path in sorted((source/'Segmentation').glob('AB*/*_parsing.mat')):
        subject=path.parent.name
        task=re.split(r'_\d+(?:_|$)',path.stem)[0]
        counts[task]+=1
        if path.stat().st_size>4*1024**2:raise MemoryError('Parsing input exceeds 4 MiB')
        parsed=loadmat(path)
        fields={}
        for key,values in parsed.items():
            if key.startswith('_') or not isinstance(values,np.ndarray) or not np.issubdtype(values.dtype,np.number):continue
            if values.ndim!=2 or values.shape[1]!=2 or not values.size:continue
            valid=bool(np.isfinite(values).all() and (values[:,1]>values[:,0]).all())
            fields[key]={'intervals':len(values),'finite_increasing_endpoints':valid}
            if not valid:issues.append({'source':str(path),'field':key,'reason':'invalid_interval'})
        if not fields:issues.append({'source':str(path),'reason':'no_numeric_intervals'})
        if task not in allowed:issues.append({'source':str(path),'reason':'task_omitted_by_phase_allowlist'})
        records.append({'subject':subject,'task':task,'parsing':path.name,'source_sha256':digest(path),
            'recording':resolve_recording(source/'RawData'/subject/'CSV_Data',path.name),
            'phase_task_allowed':task in allowed,'interval_fields':fields})
    out=ROOT/'converted_datasets/reconversion_v2/gt23_task_coverage_review_20261020'
    ensure_storage_headroom(out);out.mkdir(exist_ok=False)
    report={'parsing_windows':len(records),'subjects':len({r['subject'] for r in records}),
        'task_windows':dict(counts),'issues':issues,'records':records,'converter_sha256':digest(code),
        'probe_sha256':digest(Path(__file__)),'scientific_approval':False,
        'limitations':['Allowlist eligibility is not successful reconstruction',
            'Interval validity does not establish physical event meaning or boundary accuracy']}
    (out/'source_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['parsing_windows','subjects','task_windows','issues']}))


if __name__=='__main__':main()
