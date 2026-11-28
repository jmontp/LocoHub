"""Explain why source-curated treadmill cycles fail strict streaming windows."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,resource
from collections import Counter
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
import h5py
ROOT=Path(__file__).resolve().parents[3]


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    curation=ROOT/'converted_datasets/reconversion_v2/um21_tread_full_curation_v2_20261021';coverage=json.loads((curation/'curation_coverage.json').read_text())
    membership=curation/'cycle_membership.jsonl';assert digest(membership)==coverage['membership_sha256']
    source=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Streaming.mat';assert digest(source)==coverage['source_streaming_sha256']
    selected=[json.loads(l) for l in membership.read_text().splitlines() if json.loads(l)['streaming_status']=='excluded_in_original_curation']
    counts=Counter();records=[]
    with h5py.File(source,'r',rdcc_nbytes=1024**2) as h:
        for item in selected:
            events=h[f"Streaming/{item['subject']}/Tread/{item['condition']}/events"]
            cuts=events['cutPoints'][...].T
            labels=[''.join(chr(int(c)) for c in h[ref][...].reshape(-1)) for ref in events['tasks'][...].reshape(-1)]
            assert len(cuts)==len(labels)
            start,end=item['start_frame'],item['end_frame'];overlaps=[]
            for label,(lo,hi) in zip(labels,cuts):
                if max(start,lo)>min(end,hi):continue
                overlaps.append({'label':label,'start_frame':int(lo),'end_frame':int(hi),'overlap_frames':int(min(end,hi)-max(start,lo)+1),'contains_start':bool(lo<=start<=hi),'contains_end':bool(lo<=end<=hi)})
            same=[x for x in overlaps if x['label']==item['original_normalized_task']]
            assert not any(x['contains_start'] and x['contains_end'] for x in same)
            if any(x['contains_start'] for x in same):reason='curated_label_contains_start_but_not_end'
            elif any(x['contains_end'] for x in same):reason='curated_label_contains_end_but_not_start'
            elif same:reason='curated_label_overlaps_inside_cycle'
            else:reason='curated_label_has_no_streaming_window_overlap'
            counts[reason]+=1;records.append({**item,'boundary_reason':reason,'overlapping_streaming_windows':overlaps,'duration_s':(end-start)/100})
    assert len(records)==coverage['totals']['excluded_in_original_curation']
    report={'status':'curated_window_exclusions_explained','scientific_approval':False,'cycles':len(records),'counts':dict(counts),'records':records,'curation_coverage_sha256':digest(curation/'curation_coverage.json'),'streaming_sha256':coverage['source_streaming_sha256'],'probe_sha256':digest(Path(__file__)),'limitations':['Original curated labels and strict streaming windows encode different selection rules','An overlap explains an exclusion but does not establish a constant task or speed across the whole cycle','No source values or existing conversions changed']}
    a.output_root.mkdir(parents=True,exist_ok=False);(a.output_root/'window_edges.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cycles':len(records),'counts':dict(counts)}))


if __name__=='__main__':main()
