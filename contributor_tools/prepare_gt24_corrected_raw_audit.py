"""Bind an independent GT24 audit only after actual normalization/admission."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.audit_gt24_corrected_raw_source import digest,admission


def prepare(conversion,output):
    conversion=Path(conversion).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Fresh isolated audit root required')
    cp=json.loads(conversion.read_text());receipt=conversion.parent/'admission.json';summary=conversion.parent/'pilot_summary.json'
    actual=json.loads(summary.read_text())
    if actual.get('status') not in ('unknown_mass_representatives_normalization_checked_unreviewed','two_phase_participant_force_pilot_checked_unreviewed') or actual.get('scientific_approval') is not False or actual.get('plan_sha256')!=digest(conversion):raise ValueError('Actual completed corrected pilot required')
    policy,producer=('gt24_participant_mass_v1','apply_gt24_participant_normalization.py') if actual['status']=='two_phase_participant_force_pilot_checked_unreviewed' else ('gt24_participant_mass_missingness_v2','apply_gt24_participant_normalization_v2.py')
    bindings=dict(cp['bindings'])
    for path in [conversion,receipt,summary,Path(__file__).resolve(),ROOT/'contributor_tools/audit_gt24_corrected_raw_source.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py']:
        value=digest(path)
        if str(path) in bindings and bindings[str(path)]!=value:raise ValueError('Do not refresh frozen code/evidence hashes')
        bindings[str(path)]=value
    plan={'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'records':cp['records'],'producer_policy':policy,'normalization_producer':str(ROOT/'contributor_tools'/producer),'mass_matrix':cp['mass_matrix'],'conversion_plan':str(conversion),'conversion_admission':str(receipt),'worker_limit_mib':768,'limitations':'Partial/unassessed raw fields cannot be promoted to complete source validation; all2421 Parsed/1358 native remain fullscope.'}
    for index,record in enumerate(plan['records']):
        corrected=conversion.parent/f'record_{index}'/'continuous.parquet';prior=conversion.parent/f'record_{index}'/'audit.json';report=json.loads(prior.read_text())
        if report.get('status')!='participant_normalization_independent_readback_checked_unreviewed' or report.get('plan_sha256')!=digest(conversion) or report.get('output_sha256')!=digest(corrected):raise ValueError('Actual corrected output/readback differs')
        admission(plan,output/'plan.json',index,corrected)
        bindings[str(corrected)]=digest(corrected);bindings[str(prior)]=digest(prior)
    for path,expected in bindings.items():
        if digest(path)!=expected:raise ValueError('Bound dependency changed')
    output.mkdir();path=output/'plan.json';path.write_text(json.dumps(plan,indent=2)+'\n')
    return {'plan':str(path),'plan_sha256':digest(path),'records':len(plan['records'])}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--conversion-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.conversion_plan,a.output)))
