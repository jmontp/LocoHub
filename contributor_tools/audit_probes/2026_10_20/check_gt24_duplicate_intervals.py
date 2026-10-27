"""Compare duplicate standing intervals against original GT24 GRF/velocity signals."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
import json,subprocess,types,sys,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import load_converter,digest
from contributor_tools.common import stride_segmentation as corrected


def main():
    old_text=subprocess.check_output(['git','show','23df76a:contributor_tools/common/stride_segmentation.py'],cwd=ROOT)
    assert hashlib.sha256(old_text).hexdigest()=='e01434a54aaee082e27455098101b0662e4812b176c05b82aa123664fa984b9b'
    old=types.ModuleType('gt24_original_segmentation');old.__package__='contributor_tools.common';sys.modules[old.__name__]=old
    exec(compile(old_text,'original_stride_segmentation.py','exec'),old.__dict__)
    converter=load_converter(ROOT/'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py')
    base=ROOT/'converted_datasets/reconversion_v2/gt24_phase3_timing_20261020'
    records=[json.loads(line) for line in (base/'recording_results.jsonl').read_text().splitlines()]
    results=[]
    for record in records:
        if record['status']!='quarantined_schema_failure':continue
        subject,recording=record['subject'],record['recording']
        folder=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Phase3_Parsed/Parsed')/subject/recording
        paths={kind:folder/(subject+'_'+recording+'_'+kind+'.csv') for kind in ['angle_filt','grf','velocity']}
        data={k:pd.read_csv(p) for k,p in paths.items()}
        for k in ['grf','velocity']:np.testing.assert_array_equal(data[k].time,data['angle_filt'].time)
        frame=converter.prepare_segmentation_df(data,'l')
        config=corrected.StandingActionConfig(grf_vertical_ipsi_col='grf_vertical_ipsi_N',grf_vertical_contra_col='grf_vertical_contra_N',
            velocity_cols=('hip_flexion_velocity_ipsi_rad_s','hip_flexion_velocity_contra_rad_s','knee_flexion_velocity_ipsi_rad_s','knee_flexion_velocity_contra_rad_s'),
            standing_grf_threshold_N=600,velocity_threshold_rad_s=.436,require_flight_phase=False,use_iqr_filtering=True,iqr_multiplier=1.5)
        before=old.segment_standing_action_cycles(frame,config,'lunge');after=corrected.segment_standing_action_cycles(frame,config,'lunge')
        old_bounds=[(s.start_idx,s.end_idx) for s in before];new_bounds=[(s.start_idx,s.end_idx) for s in after]
        assert len(new_bounds)==len(set(new_bounds))
        results.append({'subject':subject,'recording':recording,'old_candidates':len(before),'old_unique_intervals':len(set(old_bounds)),
            'corrected_intervals':len(after),'merged_candidate_intervals':[{'start':s.start_idx,'end':s.end_idx,'candidates':s.metadata['candidate_count']} for s in after if s.metadata['candidate_count']>1],
            'removed_unique_by_recomputed_iqr':sorted(set(old_bounds)-set(new_bounds)),
            'added_unique_by_recomputed_iqr':sorted(set(new_bounds)-set(old_bounds)),
            'source_sha256':{str(p):digest(p) for p in paths.values()}})
    out=ROOT/'converted_datasets/reconversion_v2/gt24_duplicate_interval_review_20261020';out.mkdir(exist_ok=False)
    report={'recordings':results,'probe_sha256':digest(Path(__file__)),'new_segmentation_sha256':digest(ROOT/'contributor_tools/common/stride_segmentation.py'),
        'scientific_approval':False,'limitations':['Duplicate interval correction does not verify physiological event boundaries','Corrected artifacts still require regeneration']}
    (out/'source_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))


if __name__=='__main__':main()
