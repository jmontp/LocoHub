"""GT24-C01: summarize the divisor pilot output (reads only the probe output JSON, the launcher receipt and the mass matrix; no source data)."""
import json,math,statistics as st,hashlib
P='converted_datasets/reconversion_v2/gt24_c01_divisor_pilot_20261101/gt24-c01-divisor-probe.json'
REC='docs/quality/audits/gt24-c01-divisor-pilot-receipt.json'
h=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
d=json.load(open(P)); R=d['results']; rc=json.load(open(REC))
m=json.load(open('converted_datasets/reconversion_v2/gt24_source_mass_coverage_v4_20261021/matrix.json'))['source_metadata']['readme']['phase_masses']
trials=[]
for t in R:
    row=m[t['phase']][t['subject']]; D=t['identity_divisor_kg']
    own=[f for f in ('model_day1_with_exo_kg','model_day2_with_exo_kg') if f in row and D and abs(math.log(D/float(row[f])))<=5e-4]
    pl=t.get('plate',{}); lv=t.get('lever',{})
    trials.append({'phase':t['phase'],'folder':t['subject'],'recording':t['recording'],'stage':t['stage'],
      'E1_interaction_divisor_kg':D,'E1_exact':D is not None,'E1_matches':[f"{c['source']} {c['phase']} {c['subject']} {c['field']}" for c in t['identity_matches']],
      'own_readme_worn_row':own,'statics_mass_kg':t.get('statics_mass_kg'),
      'E2_plate_mass_kg':pl.get('mass_kg'),'E2_class':pl.get('class'),'E2_plate_over_D':(pl['mass_kg']/D if pl.get('mass_kg') and D else None),
      'E3_log_ratio_by_side':{s:x.get('log_ratio_to_identity') for s,x in lv.items()},
      'E3_inside_external_band_by_side':{s:x.get('shares_identity_divisor_if_bias_transfers') for s,x in lv.items()}})
ex=[t for t in trials if t['E1_exact']]
lv=[v for t in trials for v in t['E3_log_ratio_by_side'].values() if v is not None]
inb=sum(bool(v) for t in trials for v in t['E3_inside_external_band_by_side'].values() if v is not None)
plates=[t['E2_plate_over_D'] for t in trials if t['E2_plate_over_D']]
lab=lambda t: f"{t['phase']}/{t['folder']} {t['recording']}"
day2=[lab(t) for t in ex if t['phase']=='Phase1And2' and t['own_readme_worn_row']==['model_day2_with_exo_kg']]
rep1=[lab(t) for t in ex if t['phase']=='Phase1And2' and t['folder'] in ('BT06','BT07','BT13') and t['own_readme_worn_row']==['model_day1_with_exo_kg']]
p3=[t for t in ex if t['phase']=='Phase3']
statics_ok=all(abs(t['E1_interaction_divisor_kg']-float(t['statics_mass_kg']))/float(t['statics_mass_kg'])<1e-9 for t in p3)
doc={'task_id':'GT24-C01','stage':'pilot_result','scientific_approval':False,
 'summary_script':{'path':'contributor_tools/audit_probes/2026_10_31/summarize_gt24_c01_pilot.py','note':'reads only the probe output JSON, the launcher receipt and the mass matrix'},
 'probe':{'path':'contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py','sha256':d['probe_sha256']},
 'output':{'path':P,'sha256':h(P)},
 'receipt':{'path':REC,'sha256':h(REC),'status':rc['status'],'exit_code':rc['exit_code'],'clean_success':rc['clean_success'],'checks':rc['checks'],
   'failed_check_explained':("linux_no_new_worker: the only worker seen after the run was another agent's pytest (tests/test_hist05_addbiomechanics_member.py, "
     "tests/test_addbiomechanics_member_acquisition.py, tests/test_backlog_workflow.py) that started as the run ended; not started by this job. Recorded and accepted per "
     "coordinator instruction. All other checks passed (cleanup proven, bindings and envelope unchanged, no orphans, expected output present and hashed)."),
   'wall_time_seconds':rc['wall_time_seconds'],'peak_rss_mib_probe':d['peak_rss_mib'],'members_read':len(d['members_read']),'zips_unchanged':d['zips_unchanged']},
 'trials':trials,
 'E1':{'trials_exact':f"{len(ex)}/{len(trials)}",'not_exact':[lab(t) for t in trials if not t['E1_exact']],
   'not_exact_reason':'all 6 are short stairs trials with 96-176 top-quartile samples, below the pre-registered 200-sample minimum; no identity failure seen',
   'precision':'per-sample ratio robust relative spread <= 6.6e-13; hip/knee/left/right agree within 1.4e-14 per trial; power_exo identity agrees within 1.2e-13 in 204 columns',
   'sign_alignment':'interaction (exo, extension +) = -D (hip_flexion net - bio) in 99/99 columns and +D (knee_angle net - bio) in 97/97; knee_angle is extension-positive, as GT24-C02 found',
   'divisor_is':('In every exact trial the interaction-torque divisor is a worn model mass: Phase1And2 the README "w/ exo" value of the folder\'s own row (day 1 or day 2), '
                 'Phase3 the folder\'s Statics model mass to 1e-9. Never a body ("w/o exo") mass of the own row.'),
   'phase3_equals_statics':statics_ok,'exact_not_matching_own_readme_worn_row':[lab(t) for t in ex if not t['own_readme_worn_row']],
   'raw_interaction_units':'torque_interaction / (moment_filt - moment_filt_bio) is a constant equal to a recorded mass in kg, so the raw interaction column is in N*m.',
   'phase12_repeat_day_trials_matching_day2':day2,'phase12_repeat_day_trials_matching_day1':rep1},
 'E2':{'estimates':len(plates),'plate_over_D_range':[round(min(plates),4),round(max(plates),4)],'median':round(st.median(plates),4),
   'not_estimated':[f"{lab(t)}: {t['E2_class']}" for t in trials if t['stage'].startswith('A') and not t['E2_plate_mass_kg']],
   'reading':('Plate weight is within -2.8 % to +2.1 % of the E1 worn mass in all 30 estimates, so the folder\'s person plus exoskeleton weighs the divisor; body masses are 6-12 % lower. '
              'The pre-registered 2 % uniqueness test is never met because README masses are dense; it is not used for any conclusion.')},
 'E3':{'sides':len(lv),'inside_external_band':f"{inb}/{len(lv)}",'log_ratio_range':[round(min(lv),4),round(max(lv),4)],'median':round(st.median(lv),4),
   'external_centre':round(-math.log(0.9942),4),'implied_gt24_bias_if_shared':round(math.exp(-st.median(lv)),4),
   'reading':('All 66 sides lie between +0.011 and +0.067 (log). If net moments share D_x, the GT24 lever bias is 0.962, 3.2 % below the GT23 calibration (0.9942); '
              '56/66 sides fall inside the pre-registered band around the GT23 centre and the 10 outside are all on the high side (0.055-0.067). '
              'If net moments were divided by body mass, the ratios would sit near log(body/worn) - log(b), about -0.06 to -0.12 for a bias near GT23; none does. '
              'Body mass is excluded unless the GT24 bias were about 0.86-0.91. The bias transfers only approximately (about 3 %), so E3 supports D_net = D_x within a few percent, not exactly.')},
 'BT18_BT24':{'BT18_folder':'E1 divisors 84.8435 kg (normal walk) and 87.1501 kg (stairs) = its Statics models = README BT24 day-1/day-2 worn masses; E2 plate 84.07 kg (-0.9 % of D; 12 % above README BT18 worn 74.96 kg).',
   'BT24_folder':'E1 divisor 74.9573 kg = its Statics model = README BT18 day-1 worn mass; E2 not estimated (non-finite plate force); its stairs trial not exact (too few samples).',
   'reading':'Each folder\'s data, Statics models and (for BT18) measured weight agree with each other and with the other subject\'s README row. The README mass rows (or the folder names) are swapped; the data are internally consistent. Which participant label is right cannot be told from these files.'},
 'conclusions':[
   'Published GT24 per-kg moments, biological moments and exo powers are divided by the worn model mass (person + exoskeleton) of the trial\'s OpenSim model: E1 exact for the interaction torque, E3 consistent for net moments within the ~3 % bias uncertainty, E2 shows the worn mass is the measured weight.',
   'Day-2 models also occur in Phase1And2: 5 of 16 exact BT06/BT07/BT13 trials match the day-2 worn mass, so day must be bound per trial by an E1 census.',
   'BT18/BT24: the swap is between the README rows and the folders; the divisor is the folder Statics mass.',
   'Short stairs trials need a pre-registered census rule for fewer samples.'],
 'proposed_census_rule_change':{'identity_min_samples':50,'why':'the 6 non-exact pilot trials are short stairs with 96-176 top-quartile samples; exactness is decided by spread and correlation, which are unaffected. To be fixed before the census reads data.'}}
json.dump(doc,open('docs/quality/audits/gt24-c01-divisor-pilot-result.json','w'),indent=1)
print(json.dumps({k:doc[k] for k in ('E1','E2','E3')},indent=1)[:2500])
