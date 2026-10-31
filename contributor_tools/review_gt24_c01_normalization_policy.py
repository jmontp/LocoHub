"""GT24-C01: GT24 channel signs, mass normalization and phase/day/exo mapping, from metadata and audits only.

Steps:
  audit   Writes docs/quality/audits/gt24-c01-normalization-policy.json from the publisher README
          (hash-checked), the GT24 mass matrix (README + Statics metadata only), the GT24-C02 audit,
          and code inspection notes. Reads no GT24 time series.
  sheets  Builds review_sheets/GT24-C01/ (verification) and review_sheets/D-GT24-C01-1/ (decision)
          from that JSON only.

The divisor question needs data; it is planned (contributor_tools/audit_probes/2026_10_31/
probe_gt24_c01_divisors.py, seeded selection embedded here) and not run by this task.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve()
README = Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/readme.txt')
README_SHA256 = 'e896c6b424c45f50f261ade2e40c5f5832065fbcd745c593b7cd72fdeb84026f'
MATRIX = ROOT / 'converted_datasets/reconversion_v2/gt24_source_mass_coverage_v4_20261021/matrix.json'
C02 = ROOT / 'docs/quality/audits/gt24-c02-ankle-sign.json'
GT23_C04 = ROOT / 'docs/quality/audits/gt23-c04-trial-divisors.json'
PROBE = ROOT / 'contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py'
AUDIT = ROOT / 'docs/quality/audits/gt24-c01-normalization-policy.json'
SHEET_V = ROOT / 'review_sheets/GT24-C01'
SHEET_D = ROOT / 'review_sheets/D-GT24-C01-1'
BAND = 0.0488   # GT23-C03 tolerance_v2 lever band half width (log), reused unchanged
INPUTS = ['docs/quality/audits/gt24-c02-ankle-sign.json', 'docs/quality/audits/gt24-unknown-normalization-mass-review.json',
          'docs/quality/audits/gt24-source-companion-scope.json', 'docs/quality/audits/gt24-ankle-evidence-ranking.json',
          'docs/quality/audits/gt23-c03-normalizing-mass.json', 'docs/quality/audits/gt23-c04-trial-divisors.json',
          'docs/quality/audits/gt25-normalization-source-review.json',
          'converted_datasets/reconversion_v2/gt24_source_mass_coverage_v4_20261021/matrix.json',
          'converted_datasets/reconversion_v2/gt24_gt25_source_units_web_20261021/review.json',
          'contributor_tools/DATA_CONTRACT.md', 'docs/reference/index.md', 'docs/datasets/gt24.md',
          'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py',
          'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_time_to_parquet.py',
          'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/metadata.yaml',
          'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/PLAN_add_no_exo_data.md',
          'contributor_tools/gt24_source_mass.py', 'contributor_tools/gt24_mass_field_policy.py',
          'contributor_tools/apply_gt24_participant_normalization_v2.py',
          'contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py', 'tests/test_gt24_c01_divisor_probe.py']
INK, MUTED, BLUE, ORANGE, RED = '#20252B', '#5b6672', '#2a78d6', '#eb6834', '#c0392b'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def readme_line(lines, pattern):
    hits = [i + 1 for i, s in enumerate(lines) if re.search(pattern, s)]
    if not hits:
        raise ValueError(f'README pattern not found: {pattern}')
    return hits[0]


def own_row_fields(row, value):
    """README fields whose printed 2-decimal value equals the Statics model mass (rounded or truncated)."""
    v = Decimal(value)
    shown = {v.quantize(Decimal('.01'), rounding=r) for r in (ROUND_DOWN, ROUND_HALF_UP)}
    return [f for f in ('model_day1_with_exo_kg', 'model_day2_with_exo_kg') if f in row and Decimal(row[f]) in shown]


def probe_module():
    spec = importlib.util.spec_from_file_location('probe_gt24_c01_divisors', PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def units_table(m, probe):
    meta = m['source_metadata']
    rows = meta['readme']['phase_masses']
    units = {}
    for r in m['parsed_recordings']:
        units.setdefault((r['phase'], r['subject']), []).append(r)
    out = []
    for (phase, subject), recs in sorted(units.items()):
        row = rows[phase][subject]
        u = {'phase': phase, 'subject_folder': subject, 'parsed_recordings': len(recs),
             'exo_states': {s: sum(r['exo_state'] == s for r in recs) for s in sorted({r['exo_state'] for r in recs})},
             'readme_line': row['line'], 'readme_row': {k: row[k] for k in row if k.endswith('_kg')}}
        if phase == 'Phase3':
            st = meta['phase3_static_models'][subject]['records']
            groups = {}
            for r in recs:
                key = probe.statics_trial(st, r['recording'])
                value = st[key]['source_model_mass_kg_decimal'] if key else 'no_statics_trial'
                groups.setdefault(value, 0)
                groups[value] += 1
            u['statics_groups'] = []
            for value, n in sorted(groups.items()):
                fields = own_row_fields(row, value) if value != 'no_statics_trial' else []
                other = [] if fields or value == 'no_statics_trial' else [
                    f'{ph} {s} {f}' for ph, rr in rows.items() for s, rw in rr.items() for f in own_row_fields(rw, value)]
                u['statics_groups'].append({'model_mass_kg': value, 'parsed_recordings': n, 'own_row_fields': fields, 'other_rows_matching': other})
            conflict = any(not g['own_row_fields'] for g in u['statics_groups'])
            if conflict:
                u['category'] = 'statics_conflicts_own_readme_row'
                u['participant_mass_rule'] = 'Withheld. Folder model masses equal another subject\'s README row; resolve with the plate-weight estimator (E2) and a decision before binding any body mass.'
                u['divisor_rule'] = 'E1 exact identity per trial; expected (not assumed) to equal the folder Statics mass.'
            elif 'model_day2_with_exo_kg' in row:
                u['category'] = 'phase3_two_mass_rows_bound_by_statics'
                u['participant_mass_rule'] = 'Per trial: the README row (day 1 or day 2) whose w/ exo value equals the trial\'s Statics model mass; body mass = that row\'s w/o exo value.'
                u['divisor_rule'] = 'Statics model mass of the trial, confirmed by E1.'
            else:
                u['category'] = 'single_mass_row'
                u['participant_mass_rule'] = 'README w/o exo (day 1).'
                u['divisor_rule'] = 'Statics model mass of the trial (equals README w/ exo), confirmed by E1.'
        else:
            if 'model_day2_with_exo_kg' in row:
                u['category'] = 'phase12_two_worn_masses_day_unknown'
                u['participant_mass_rule'] = ('Trials whose E1 divisor equals the day-1 w/ exo value: README w/o exo. Trials matching the day-2 w/ exo value: '
                                              'withheld (README reports no day-2 body mass for this collection). Unmatched: withheld.')
                u['divisor_rule'] = 'E1 exact identity per trial (day-1 and day-2 worn masses differ by 0.25-0.8 %, below force-plate precision).'
            else:
                u['category'] = 'single_mass_row'
                u['participant_mass_rule'] = 'README w/o exo.'
                u['divisor_rule'] = 'README w/ exo expected; confirmed by E1 (or E3 within the band when E1 is not exact).'
        out.append(u)
    return out


def c02_evidence(c02, m):
    """Implied divisor from the C02 lever-arm slopes, under each candidate mass. No GT24 data read here."""
    meta = m['source_metadata']
    rows = meta['readme']['phase_masses']
    probe = probe_module()
    trials = []
    for t in c02['trials']:
        slopes = [s['window_slope_source_on_df_prediction'] for s in t['sides'] if s.get('window_slope_source_on_df_prediction')]
        slope = statistics.mean(slopes)
        row = rows[t['phase']][t['subject']]
        cands = {'worn_mass_readme_own_row_day1': float(row['model_day1_with_exo_kg']),
                 'body_mass_readme_own_row_day1': float(row['participant_day1_kg'])}
        if t['phase'] == 'Phase3':
            st = meta['phase3_static_models'][t['subject']]['records']
            key = probe.statics_trial(st, t['condition'])
            cands['worn_mass_statics_trial_model'] = float(st[key]['source_model_mass_kg_decimal'])
        else:
            cands['worn_mass_statics_trial_model'] = cands['worn_mass_readme_own_row_day1']
        # source = M/D, C02 prediction = M_lever/m_used, slope = (M/M_lever) (m_used/D) = b m_used / D
        implied = {k: slope / (t['mass_kg_w_exo'] / v) for k, v in cands.items()}   # = b if D = v
        trials.append({'trial': f"{t['phase']}/{t['subject']} {t['condition']}", 'mass_used_by_c02_kg': t['mass_kg_w_exo'],
                       'mean_slope_two_legs': round(slope, 4), 'candidates_kg': cands, 'slope_over_predicted': {k: round(v, 4) for k, v in implied.items()}})
    gt23 = json.loads(GT23_C04.read_text())
    b = float(gt23['rules']['ankle_bias_centre_ratio'])   # external: calibrated on GT23 trials with known divisors
    for x in trials:
        x['log_dev_from_common_bias'] = {k: round(math.log(v / b), 4) for k, v in x['slope_over_predicted'].items()}
        x['inside_band'] = {k: abs(v) <= BAND for k, v in x['log_dev_from_common_bias'].items()}
    n = len(trials)
    keys = list(trials[0]['inside_band'])
    own = {}
    for k in keys:   # sensitivity only: each hypothesis given its own free bias (the circular variant)
        bk = statistics.median(x['slope_over_predicted'][k] for x in trials)
        own[k] = {'own_median_bias': round(bk, 4),
                  'inside_band': f"{sum(abs(math.log(x['slope_over_predicted'][k] / bk)) <= BAND for x in trials)}/{n}"}
    return {'method': ('From the GT24-C02 audit only (no new reads). C02 slope = source / (lever-arm moment / m_used) = b * m_used / D, '
                       'with D the true divisor and b the lever bias (generic talus, foot inertia). For each candidate D, slope * D / m_used '
                       'should equal b for every trial. b is taken from outside these trials: GT23-C04 rules.ankle_bias_centre_ratio '
                       f'({b}), the same lever method calibrated on GT23 trials with known divisors; band +/-4.9 % (GT23-C03 tolerance_v2, reused). '
                       'One trial per subject, ankle only.'),
            'common_bias_b': b, 'common_bias_source': 'docs/quality/audits/gt23-c04-trial-divisors.json rules.ankle_bias_centre_ratio',
            'common_bias_source_sha256': digest(GT23_C04),
            'assumption': ('The GT23 lever bias transfers to GT24 (different subjects, OpenSim models and an exoskeleton worn). If it does not, '
                           'these 6 slopes cannot separate the worn and body divisors: with a free bias per hypothesis both fit 5-6 of 6 (sensitivity_free_bias).'),
            'band_half_width_log': BAND, 'trials': trials,
            'counts_inside_band': {k: f"{sum(x['inside_band'][k] for x in trials)}/{n}" for k in keys},
            'sensitivity_free_bias': own,
            'reading': ('If the GT23 lever bias transfers: worn model mass (Statics for Phase3, README w/ exo for Phase1And2) fits 6/6 within the band; '
                        'README own-row w/ exo fits 5/6 (BT24 folder about +12 %, where its Statics model mass is BT18\'s README value); body mass w/o exo fits 1/6 '
                        '(BT24, whose own body mass 77.79 kg lies 3.7 % from its folder model mass 74.96 kg). Without that assumption the slopes do not '
                        'separate worn from body mass. Preliminary and conditional; the probe (E1, with E3) is the test.')}


CHANNELS = [
    {'family': 'Sagittal joint angles', 'source': 'angle.csv, angle_filt.csv: hip_flexion_<s>, knee_angle_<s>, ankle_angle_<s> (deg)',
     'canonical': 'hip_flexion_angle, knee_flexion_angle, ankle_dorsiflexion_angle (rad)', 'sign': 'hip +1, knee -1, ankle +1',
     'sign_evidence': 'Hip/knee: README line 91 (hip flexion +, knee extension +) agrees with exo encoders (README line 94 extension +): exo hip vs hip_flexion corr -0.90 to -0.99, exo knee vs knee_angle +0.93 to +0.99 in 12/12 legs (GT24-C02). Ankle: GT24-C02 force-plate evidence, dorsiflexion +; README line 91 is wrong for the ankle.',
     'normalization': 'none (mass-independent)', 'status': 'supported'},
    {'family': 'Sagittal joint velocities and accelerations', 'source': 'velocity.csv (deg/s, central difference of angle_filt, README); acceleration derived by the converter',
     'canonical': '*_velocity_*_rad_s, *_acceleration_*_rad_s2', 'sign': 'same as the angle', 'sign_evidence': 'velocity equals d(angle_filt)/dt (C02: correlation 1.0 for the ankle); signs follow the angle',
     'normalization': 'none', 'status': 'supported'},
    {'family': 'Frontal/transverse angles, velocities and moments', 'source': 'hip_adduction, hip_rotation, subtalar_angle columns',
     'canonical': 'none adopted', 'sign': 'source sign kept (LocoHub frontal/transverse rule not adopted)', 'sign_evidence': 'README line 92 only',
     'normalization': 'as sagittal moments when exported', 'status': 'source_only'},
    {'family': 'Net joint moments', 'source': 'moment.csv, moment_filt.csv: <coord>_<s>_moment (README: Nm/kg, denominator not stated)',
     'canonical': '*_moment_*_Nm_kg', 'sign': 'hip +1, knee -1, ankle +1',
     'sign_evidence': 'OpenSim generalized force shares its coordinate\'s direction (reference sign table); coordinate signs as for angles. Ankle force-plate tested (GT24-C02); hip and knee moment signs not force-plate tested.',
     'normalization': 'canonical = sign * source * D / m_basis, with D the trial\'s exact source divisor (probe E1, net moments checked by E3) and m_basis per D-GT24-C01-1; withheld when D or m_basis is unresolved; published per-kg values kept under source names; never divided again',
     'status': 'supported_after_probe_and_decision'},
    {'family': 'Biological joint moments', 'source': 'moment_filt_bio.csv (README line 520: moment_filt minus exo interaction torque)',
     'canonical': '*_biological_moment_*_Nm_kg', 'sign': 'as net moments', 'sign_evidence': 'as net moments; ankle bio equals net exactly (C02, 12 legs)',
     'normalization': 'as net moments (same D by README line 520 construction; E1 measures it)', 'status': 'supported_after_probe_and_decision'},
    {'family': 'Assistance (exoskeleton) moments', 'source': 'derived: moment_filt - moment_filt_bio; raw exo.csv <joint>_angle_<s>_torque_interaction (units not in README)',
     'canonical': '*_assistance_moment_*_Nm_kg', 'sign': 'hip +1, knee -1 applied to (moment_filt - moment_filt_bio); ankle: the difference is exactly 0 in every C02 leg (no ankle actuator)',
     'sign_evidence': 'README line 520 defines bio = moment_filt - interaction, so total = biological + assistance holds by construction in the bio coordinate convention; no exo sign assumption needed',
     'normalization': 'same D and m_basis as net moments. The raw interaction column stays source-only with unknown units unless E1 shows interaction / (net - bio) is a constant equal to a recorded mass (then N*m). The current converters divide the raw column by the worn mass: unsupported.',
     'status': 'supported_after_probe_and_decision'},
    {'family': 'Joint powers', 'source': 'power.csv, power_bio.csv, power_exo.csv (W/kg)', 'canonical': 'dataset power columns (not exported by the current converters)',
     'sign': 'none (moment x velocity is invariant to the coordinate sign)', 'sign_evidence': 'definition (README lines for power*.csv)',
     'normalization': 'same D / m_basis factor as moments (E1 second identity checks power_exo uses D)', 'status': 'supported_after_probe_and_decision'},
    {'family': 'Vertical ground reaction force', 'source': 'grf.csv fp_<s>_force_y (N, OpenSim global frame, y up; README line 37)',
     'canonical': 'grf_vertical_*_BW', 'sign': '+1 (up)', 'sign_evidence': 'README line 37; stance force > 0 (C02)',
     'normalization': 'canonical = F / (m_basis g) per D-GT24-C01-1; source N kept', 'status': 'supported_after_decision'},
    {'family': 'Horizontal ground reaction force and global CoP', 'source': 'grf.csv fp_<s>_force_x/z, fp_<s>_cop_x/y/z',
     'canonical': 'grf_anterior_*, grf_lateral_*, cop_* (ground frame)', 'sign': 'unresolved: walking heading and anatomical lateral axis per trial not established',
     'sign_evidence': 'none independent; converter already keeps source axes', 'normalization': 'source N/m kept', 'status': 'source_only'},
    {'family': 'Foot-frame insole force and CoP', 'source': 'insole_sim.csv (calcn frames; force N, CoP m)',
     'canonical': 'currently mapped to cop_anterior/cop_lateral by the converters', 'sign': 'x anterior, y up confirmed (C02); z (lateral) sign per leg not checked',
     'sign_evidence': 'C02 frame checks for x and y only', 'normalization': 'none',
     'status': 'unsupported_as_canonical (foot-frame CoP is not the ground-frame CoP the reference defines; left-leg mirror unchecked); source alias only'},
    {'family': 'Exoskeleton sensors and torques', 'source': 'exo.csv encoders (deg, extension +), IMUs, insoles (CoP unitless), torque_estimated (Nm/kg), torque_desired/measured (Nm), torque_interaction (no unit)',
     'canonical': 'none', 'sign': 'exo convention extension + (README line 94; C02 encoder correlations agree)', 'sign_evidence': 'README + C02',
     'normalization': 'none; torque_estimated denominator unknown', 'status': 'source_only'},
    {'family': 'Virtual IMUs and IMU-integrated segment angles', 'source': 'imu_sim.csv (OpenSim body frames); converter integrates gyros with its own initialization',
     'canonical': 'thigh/shank/foot sagittal angles (converter estimate)', 'sign': 'not checked here', 'sign_evidence': 'none in this task',
     'normalization': 'none', 'status': 'not_checked (separate review; not part of this policy)'},
]


def build_audit():
    raw = README.read_bytes()
    if hashlib.sha256(raw).hexdigest() != README_SHA256:
        raise ValueError('README changed')
    lines = raw.decode().splitlines()
    if digest(MATRIX) != '688dec9d45ecf103c43a57740c0fbc019ab3e67b47fd37834a726bdd6062b462':
        raise ValueError('mass matrix changed')
    m = json.loads(MATRIX.read_text())
    c02 = json.loads(C02.read_text())
    probe = probe_module()
    L = lambda p: readme_line(lines, p)
    bindings = {
        'collection_phases': {'lines': [L(r'^Phase1And2 contains'), L(r'^Phase3 contains')], 'text': 'Phase1And2: data phase 1 (BT01-BT12, unpowered all tasks + heuristic controller some tasks) and data phase 2 (BT13-BT17, preliminary model, all powered). Phase3: BT01, BT02, BT13 returned + BT18-BT24, all powered.'},
        'task_name_rule': {'line': L(r'^Note: <task name> is constructed'), 'text': '<base>_<vicon trial>_<on/off>_<descriptor>; vicon trial number not consistent across subjects'},
        'mass_table': {'lines': [L(r'^Masses are presented'), L(r'^BT24: 77\.79')], 'text': 'w/o exo | w/ exo, plus day-2 values for some subjects'},
        'statics': {'line': L(r'Statics\.csv'), 'text': 'exact mass of each OpenSim model used for Phase3 in Statics.csv (complete data)'},
        'sign_statement': {'lines': [L(r'^Biological joint DOFs'), L(r'^\t- Extension is positive')], 'text': 'hip flexion +, knee extension +, ankle plantarflexion + (ankle part wrong: GT24-C02); exo extension +'},
        'invalid_torques': {'line': L(r'^Due to a failure in one of the loadcells')},
        'bt13_day_controllers': {'lines': [L(r'Day 1 commanding'), L(r'Day 2 commanding')]},
        'moment_units': {'line': L(r'^moment\.csv: unfiltered net joint moments'), 'text': 'Nm/kg; denominator not stated'},
        'bio_definition': {'line': L(r'^moment_filt_bio\.csv:'), 'text': 'moment_filt minus exo interaction torque'},
        'power_exo_definition': {'line': L(r'^power_exo\.csv:')},
        'exo_torque_units': {'lines': [L(r'hip_angle_<side>_torque_estimated'), L(r'knee_angle_<side>_torque_measured')], 'text': 'estimated Nm/kg; desired/measured Nm; torque_interaction not listed'},
        'grf_frame': {'line': L(r'_grf\.csv: Measured ground reaction')},
    }
    units = units_table(m, probe)
    rows = m['source_metadata']['readme']['phase_masses']
    diffs = [float(r['model_day1_with_exo_kg']) - float(r['participant_day1_kg']) for ph in rows.values() for r in ph.values()]
    diffs += [float(r['model_day2_with_exo_kg']) - float(r['participant_day2_kg']) for ph in rows.values() for r in ph.values() if 'participant_day2_kg' in r]
    ratios = [float(r[w]) / float(r[b]) for ph in rows.values() for r in ph.values()
              for w, b in (('model_day1_with_exo_kg', 'participant_day1_kg'), ('model_day2_with_exo_kg', 'participant_day2_kg')) if w in r and b in r]
    by_cat = {}
    for u in units:
        c = by_cat.setdefault(u['category'], {'units': [], 'parsed_recordings': 0})
        c['units'].append(f"{u['phase']}/{u['subject_folder']}")
        c['parsed_recordings'] += u['parsed_recordings']
    plan = probe.plan()
    ev = c02_evidence(c02, m)
    doc = {
        'task_id': 'GT24-C01', 'status': 'review', 'scientific_approval': False,
        'question': 'Which GT24 channels can be signed and normalized canonically from independent source evidence, with which masses, and how do collection phases, days and exo conditions map?',
        'scope': f"All {len(m['parsed_recordings'])} Parsed recordings in {len(units)} phase/subject folders; metadata, README and existing audits only. No GT24 time series read by this task.",
        'inputs_sha256': {p: digest(ROOT / p) for p in INPUTS},
        'readme': {'path': str(README), 'sha256': README_SHA256, 'bindings': bindings},
        'answer': {
            'signs': 'Hip +1, knee -1, ankle +1 for sagittal angles, velocities, net/biological/assistance moments (powers unchanged). Ankle: no negation (GT24-C02). Frontal/transverse: source sign kept.',
            'source_divisor': ('Not established. Re-reading the GT24-C02 lever-arm slopes (6 trials) with the externally calibrated GT23-C04 lever bias (0.9942) fits the worn model mass (person + exoskeleton) in 6/6 and body mass in 1/6 (BT24 folder, by coincidence of values); '
                               'this assumes the GT23 bias transfers to GT24. With a free bias the slopes cannot separate worn from body mass. '
                               'the BT24 folder fits its Statics model mass (74.96 kg, BT18\'s README row), not BT24\'s README 84.84 kg. Exact per-trial divisors need the probe (E1 identity).'),
            'normalization_basis': 'Queued: D-GT24-C01-1 (participant body mass vs worn mass vs withhold), held until the divisor probe reports. It sets a convention for exoskeleton datasets, so José decides.',
            'masses': f"README w/ exo exceeds w/o exo by {min(diffs):.2f}-{max(diffs):.2f} kg (ratio {min(ratios):.3f}-{max(ratios):.3f}) in all {len(ratios)} rows.",
            'phase_day_exo': 'Collection from the zip (never from subject IDs); exo state from the _on/_off/_hilo suffix; no no-exoskeleton trials exist; day bound only through an exact model-mass match (Phase3 Statics, or the E1 divisor for Phase1And2).',
        },
        'phase_day_exo_mapping': {
            'collection': 'Phase1And2_Parsed.zip vs Phase3_Parsed.zip is the collection identity. BT01, BT02 and BT13 occur in both with different masses and models; never merge or infer collection from the ID. Within Phase1And2, README line 9 assigns BT01-BT12 to data phase 1 and BT13-BT17 to data phase 2.',
            'exo_state': {'_on': 'powered (914 Phase1And2, 752 Phase3)', '_off': 'worn_unpowered (740 Phase1And2)', '_hilo': 'powered, hilo-inspired controller (15 Phase1And2: BT03, BT07, BT08, BT09, BT11, BT12)',
                          'no_exo': 'does not occur: 0 of 2,421 Parsed recordings. README "w/o exo" values are body masses, not a trial condition; the converters\' _noexo/_bare branch and PLAN_add_no_exo_data.md misread the table.'},
            'controller': 'Phase1And2 data phase 1 _on: heuristic controller (README line 9) except _hilo; data phase 2: preliminary model; BT13 (Phase1And2) day 1 commanded net torque 10 %/8 %, day 2 bio torque 20 %/10 % (README lines 179-180), so BT13 controller per trial is unresolved until its day is bound. Phase3: final deployed model.',
            'day': ('No trial-to-day table exists. Phase3: each native trial\'s Statics model mass equals exactly one README w/ exo value of the folder\'s own row (day 1 or day 2), except BT18/BT24; that binds the mass row, and the body mass of the same row. '
                    'Phase1And2 BT06, BT07, BT13: two worn masses 0.25-0.8 % apart, no trial mapping; only an exact divisor (E1) can bind them; the README gives no day-2 body mass for this collection. '
                    'The converters\' day field (hard-coded 1) and is_day2 name test are invented and must be replaced by null unless bound.'),
            'inclusive_phase_samples': 'Unchanged: phase exports keep 150 samples from 0 to 100 % (converter NUM_POINTS = 150).'},
        'mass_units': units,
        'mass_categories': by_cat,
        'statics_conflict': {'finding': 'BT18 folder Statics.csv lists 84.84/87.15 kg models (README BT24 w/ exo day 1/day 2); BT24 folder lists 74.96/75.23 kg (README BT18 day 1/day 2). The two files, the two folders, or the two README rows are swapped; which one is not known.',
                             'existing_data_evidence': 'GT24-C02 BT24-folder incline trial: lever slope 1.10 with 84.84 kg, i.e. divisor near 75 kg (inside the band for 74.96 kg) if the GT23 lever bias transfers; BT24\'s README body mass 77.79 kg also fits, so this alone does not decide.',
                             'resolution_plan': 'E2 plate weight in both folders separates 75 vs 85 kg; E1 confirms the divisor. Then a decision on whether to bind BT18-row body masses to the BT24 folder (and vice versa) or withhold; not raised before data.',
                             'parsed_recordings_affected': sum(u['parsed_recordings'] for u in units if u['category'] == 'statics_conflicts_own_readme_row')},
        'c02_divisor_evidence': ev,
        'channel_families': CHANNELS,
        'supported_ankle_policy': (
            'GT24 ankle (GT24-C02; supersedes the README sign line and gt24-ankle-evidence-ranking.json proposed_mapping). The published ankle_angle_<side> '
            '(angle.csv, angle_filt.csv), ankle_angle_<side>_velocity (velocity.csv) and ankle_angle_<side>_moment (moment.csv, moment_filt.csv, moment_filt_bio.csv) '
            'are dorsiflexion-positive, with internal moments (plantarflexor negative), as in OpenSim; README line 91 ("ankle plantarflexion is positive") is wrong for the ankle. '
            'LocoHub maps them with sign +1 (no negation): ankle_dorsiflexion_angle = rad(ankle_angle); ankle_dorsiflexion_velocity = rad(ankle_angle_velocity); '
            'ankle_dorsiflexion_moment and ankle_dorsiflexion_biological_moment = +source x D / m_basis (normalization per D-GT24-C01-1; withheld while D or m_basis is unresolved); '
            'ankle_dorsiflexion_assistance_moment = moment_filt - moment_filt_bio (0 in every leg checked; the exoskeleton has no ankle actuator), scaled the same way; ankle powers keep their sign. '
            'Published values stay available under source names. Do not adopt prepare_gt24_ankle_fix.py, adopt_gt24_phase_ankle_sign.py or run_gt24_ankle_converter_pilot.py; '
            'their negation would make ankle_dorsiflexion_* plantarflexion-positive. Evidence covers forward level, incline and decline walking and heel/toe walking (6 subjects, 12 legs); '
            'other tasks use the same coordinate and are not separately tested. Ankle angle zero is the OpenSim model neutral position (not checked).'),
        'required_code_changes': [
            'gt24_mass_field_policy.normalize_sample: sign table is hip +1, knee -1, ankle -1; the ankle must be +1 (GT24-C02). Blocking for any canonical ankle moment (apply_gt24_participant_normalization_v2 uses it).',
            'gt24_mass_field_policy / gt24_source_mass: bind Phase3 body mass per trial through the exact Statics-to-own-README-row match (day-k w/o exo); keep BT18/BT24 as conflict; bind Phase1And2 BT06/BT07/BT13 only through an exact E1 divisor; add an "independent_net_bio_interaction_identity" evidence record per trial from the probe output.',
            "Phase converter get_subject_mass (line 226) tests `'Phase3' in data_source or subject_id in PHASE3_SUBJECTS`, so Phase1And2 BT01, BT02 and BT13 receive Phase3 masses (e.g. BT01 gets 84.28 kg instead of 87.02 kg). The time converter imports this function.",
            'Phase converter get_collection_phase (line 156) treats data_source == \'Parsed\' as Phase3 for shared IDs, but both Parsed zips extract to Parsed/, so collection is inferred from the subject ID, against the collection rule above. Collection must come from the archive (Phase1And2_Parsed.zip vs Phase3_Parsed.zip) carried with each recording.',
            'Phase and time converters: remove the _noexo/_bare and is_day2 logic (no such trials); write day = null unless bound; take D per trial from bound evidence instead of SUBJECT_MASS_*; GRF and moments per D-GT24-C01-1; assistance = moment_filt - moment_filt_bio instead of -torque_interaction / worn mass; Phase3 BT18/BT24 currently get README row masses that disagree with their Statics models.',
            'Converters label foot-frame insole CoP as cop_anterior/cop_lateral: keep as a source alias until a ground-frame CoP mapping is reviewed.',
            'metadata.yaml: citation is wrong (Crossref for 10.1038/s41586-024-08157-7: Molinaro, Scherpereel, Schonhaut, Evangelopoulos, Shepherd, Young, Nature 635, 337-344, 2024; the file names Slade et al.); "clothing-integrated hip exoskeleton" contradicts README (hip and knee actuators); "first 2 and last 1 strides excluded" contradicts SKIP_FIRST/LAST_STRIDES = 0.',
            'PLAN_add_no_exo_data.md (untracked) misreads the README mass table as no-exo trials; mark obsolete when the converter is next changed.'],
        'unsupported': [
            'Canonical kinetics for BT18 and BT24 (Phase3) until the Statics/README swap is resolved (146 recordings).',
            'Body-mass-normalized kinetics for second-day trials of BT06, BT07, BT13 (Phase1And2): no day-2 body mass in the README.',
            'Raw torque_interaction in N*m/kg or as canonical assistance; torque_estimated denominator.',
            'Horizontal GRF, global CoP and foot-frame insole CoP as canonical anatomical axes.',
            'Frontal/transverse canonical signs (rule not adopted).',
            'BT04: README mass row but no Parsed or Complete data (nothing to convert).'],
        'probe_plan': {
            'script': str(PROBE.relative_to(ROOT)), 'script_sha256': digest(PROBE), 'tests': 'tests/test_gt24_c01_divisor_probe.py (synthetic, 7)',
            'status': 'written, not run (numerical slot held by another agent)',
            'caveat': ('E1 gives the divisor used to convert torque_interaction before subtraction (bio = net - interaction / D_x). It equals the net-moment divisor '
                       'only if the authors used the same mass for both. E3 tests that, and E3 carries the same assumption as the C02 re-reading: that the GT23 '
                       'lever bias transfers to GT24. If E3 cannot confirm D_net = D_x, the net/biological moment divisor stays unresolved even when E1 is exact.'),
            'estimators': {'E1': 'exact identity interaction = s D_x (moment_filt - moment_filt_bio), plus interaction x velocity = s D_x power_exo (hip, knee, both sides); D_x is the interaction-torque divisor',
                           'E2': 'plate weight over whole level-walk strides = worn mass', 'E3': 'C02 lever arm in N*m: net ankle moments share the E1 divisor'},
            'selection': plan, 'resource_estimate': 'one worker, one zip member at a time (largest about 5 MB), RLIMIT_AS 1.5 GiB; GT24-C02 read 78 members in 7.3 s at 176 MiB; this reads about 330 members.',
            'launch': 'Through contributor_tools.guarded_launcher (single job, AGENTS.md prefix): python3 contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py pilot',
            'interpretation_rules': [
                'E1 exact and equal (0.05 %) to the trial\'s worn model mass (Statics, or README w/ exo for Phase1And2): D bound for that trial; Phase1And2 repeat-day trials get their mass row from this match.',
                'E1 exact but equal to another value (body mass, another subject, the other day): record as a divisor anomaly; withhold canonical kinetics for that trial pending review.',
                'E1 not exact for both joints/sides: D unbound unless E3 is inside the band of one recorded worn mass that is unique within 8 %; then class "lever_estimate" (not exact).',
                'E3 bias is fixed to the GT23-C04 calibration (0.9942), not re-fitted to the pilot. E3 inside the band of the E1 value: net moments taken to share D_x (conditional on bias transfer). E3 outside: net moments use a different divisor than the interaction subtraction, or the bias does not transfer; stop and report.',
                'E2: worn mass of the person in the folder; BT18/BT24 resolved only if E2 is unique at 2 % and agrees with E1.',
                'If the pilot is all exact, extend E1 (3 members per recording) to all 2,421 recordings as a separate guarded census job; otherwise report and stop.']},
        'other_findings': [
            'GT25 (same lab, same README template): gt25-normalization-source-review.json keeps an ankle negation from its README; GT24-C02 found the GT24 README ankle line wrong, so GT25-C01 should test its ankle sign independently before adopting the negation.',
            'gt24_source_mass.py refuses to bind Phase3 days from model-mass agreement; this policy binds the README mass row (not a calendar day) through exact equality of two publisher documents, which is source evidence, not inference from trial counters.'],
        'readme_mass_spread': {'worn_minus_body_kg': [round(min(diffs), 2), round(max(diffs), 2)], 'worn_over_body': [round(min(ratios), 4), round(max(ratios), 4)], 'rows': len(ratios),
                               'note': 'All README rows, including BT04 (no data)'},
        'decision_candidate': None,
        'limitations': ['No GT24 time series were read by this task; every divisor statement is preliminary until the probe runs.',
                        'C02-derived divisor evidence: 6 trials, one per subject, ankle only, generic talus; the common bias comes from the same trials.',
                        'Hip and knee moment signs follow the OpenSim coordinate definition plus encoder checks; no force-plate test of hip/knee moments.'],
    }
    doc['builder_sha256'] = digest(HERE)
    AUDIT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'audit': str(AUDIT.relative_to(ROOT)), 'categories': {k: (len(v['units']), v['parsed_recordings']) for k, v in by_cat.items()},
                      'c02_inside_band': ev['counts_inside_band'], 'probe_trials': plan['trials'], 'mass_diff_kg': [round(min(diffs), 2), round(max(diffs), 2)],
                      'ratio': [round(min(ratios), 3), round(max(ratios), 3)]}, indent=1))


# ---------------------------------------------------------------- sheets

def fig_divisor(plt, save, ev, path):
    labels = {'worn_mass_statics_trial_model': ('worn mass, trial model', INK, 'o'),
              'worn_mass_readme_own_row_day1': ('worn mass, README row', ORANGE, 's'),
              'body_mass_readme_own_row_day1': ('body mass as divisor', BLUE, 'x')}
    fig, ax = plt.subplots(figsize=(4.5, 3.6), layout='constrained')
    ax.axvspan(math.exp(-BAND), math.exp(BAND), color='#999999', alpha=.15, lw=0)
    ys = list(range(len(ev['trials']), 0, -1))
    for key, (lab, col, mk) in labels.items():
        xs = [math.exp(t['log_dev_from_common_bias'][key]) for t in ev['trials']]
        ax.scatter(xs, ys, color=col, marker=mk, s={'o': 46, 's': 110, 'x': 56}[mk], label=lab, zorder=3,
                   facecolors='none' if mk == 's' else col)
    ax.set_yticks(ys)
    ax.set_yticklabels([t['trial'].split(' ')[0].replace('Phase1And2', 'P1&2').replace('Phase3', 'P3') for t in ev['trials']], fontsize=10)
    ax.axvline(1, color=MUTED, lw=.6)
    ax.set_xlabel('fit to force plates (1 = consistent; grey ±4.9 %)')
    ax.set_xlim(0.8, 1.2)
    fig.legend(fontsize=10, loc='outside lower left', ncols=1)
    save(fig, path); plt.close(fig)


def fig_statics(plt, save, units, path):
    fig, ax = plt.subplots(figsize=(4.5, 3.6), layout='constrained')
    pts = []
    for u in units:
        if u['phase'] != 'Phase3':
            continue
        own = [float(v) for k, v in u['readme_row'].items() if 'with_exo' in k]
        for g in u['statics_groups']:
            if g['model_mass_kg'] == 'no_statics_trial':
                continue
            y = float(g['model_mass_kg'])
            x = min(own, key=lambda v: abs(v - y))
            bad = not g['own_row_fields']
            pts.append((x, y, bad, u['subject_folder']))
    lo, hi = min(min(p[0], p[1]) for p in pts) - 3, max(max(p[0], p[1]) for p in pts) + 3
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=.8)
    for x, y, bad, s in pts:
        ax.scatter(x, y, color=RED if bad else INK, s=40, zorder=3)
    for s in sorted({p[3] for p in pts if p[2]}):
        x, y = next((p[0], p[1]) for p in pts if p[3] == s and p[2])
        ax.annotate(f'{s} folder', (x, y), xytext=(6, -12 if y < x else 6), textcoords='offset points', color=RED, fontsize=10)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel('README w/ exo mass, folder\'s own row (kg)')
    ax.set_ylabel('model mass in folder\'s Statics (kg)')
    ax.set_title('One dot per model mass; line = agreement', fontsize=10, loc='left')
    save(fig, path); plt.close(fig)


def fig_ratio(plt, save, units, path):
    fig, ax = plt.subplots(figsize=(4.5, 3.0), layout='constrained')
    vals = []
    for u in units:
        r = u['readme_row']
        for w, b in (('model_day1_with_exo_kg', 'participant_day1_kg'), ('model_day2_with_exo_kg', 'participant_day2_kg')):
            if w in r and b in r:
                vals.append((float(r[w]) / float(r[b]), u['phase']))
    for i, (v, ph) in enumerate(sorted(vals)):
        ax.scatter(v, 0.5 if ph == 'Phase3' else 1.0, color=INK if ph == 'Phase3' else BLUE, s=30, alpha=.8)
    ax.axvline(1, color=RED, ls='--', lw=1.2)
    ax.text(1.003, 1.25, 'equal masses', color=RED, fontsize=10)
    ax.set_yticks([0.5, 1.0]); ax.set_yticklabels(['Phase3', 'Phase1And2'], fontsize=10)
    ax.set_ylim(0.2, 1.4); ax.set_xlim(0.99, 1.16)
    ax.set_xlabel('worn mass ÷ body mass (README rows)')
    save(fig, path); plt.close(fig)


def build_sheets():
    from contributor_tools.common.review_sheet import page
    from contributor_tools.review_gt24_c02_ankle_sign import save, style
    data = json.loads(AUDIT.read_text())
    ev, units = data['c02_divisor_evidence'], data['mass_units']
    plt = style()
    for d in (SHEET_V, SHEET_D):
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.png'):
            old.unlink()
    for d in (SHEET_V, SHEET_D):
        fig_divisor(plt, save, ev, d / 'fig1_divisor.png')
    fig_statics(plt, save, units, SHEET_V / 'fig2_statics.png')
    fig_ratio(plt, save, units, SHEET_D / 'fig3_ratio.png')
    c = ev['counts_inside_band']
    conflict = data['statics_conflict']['parsed_recordings_affected']
    n_rec = sum(u['parsed_recordings'] for u in units)
    rep = data['mass_categories']['phase12_two_worn_masses_day_unknown']
    sp = data['readme_mass_spread']
    ratios, diffs = sp['worn_over_body'], sp['worn_minus_body_kg']
    chips = [
        ('pass', f'Worn mass fits earlier force-plate trials {c["worn_mass_statics_trial_model"]} with GT23 lever calibration'),
        ('unchecked', 'Worn vs body divisor: holds only if GT23 calibration transfers'),
        ('fail', f'BT18 and BT24 model masses match each other\'s README rows ({conflict} recordings)'),
        ('pass', f'No trials without the exoskeleton: 0 of {n_rec}'),
        ('fail', 'Mass-policy code still negates the ankle; fix before use'),
        ('unchecked', 'Exact divisor per trial: probe written, not run'),
        ('unchecked', f'Day of each trial for BT06, BT07, BT13 (first collection, {rep["parsed_recordings"]} recordings)'),
        ('unchecked', 'Hip and knee moment signs: OpenSim definition, not force-plate tested'),
    ]
    figs = [('fig1_divisor.png', 'Which mass were GT24 moments divided by?', 'Scaled by GT23 lever calibration.',
             'Fit of six earlier force-plate trials under three candidate divisors'),
            ('fig2_statics.png', 'Do model masses match each folder\'s README row?', 'Red: swapped pair.',
             'Statics model mass against the folder\'s own README worn mass')]
    details = [f'Lever bias {ev["common_bias_b"]} from GT23-C04 (external calibration, assumed to transfer to GT24); band ±4.9 % (GT23-C03). Counts inside band: {c}.',
               f'With a free bias per hypothesis (no external calibration) the slopes do not separate the divisors: {json.dumps(ev["sensitivity_free_bias"])}.',
               'Figure 1 contrast: body mass shown as the alternative divisor. BT24 body mass is 3.7 % from its folder model mass, so it fits either way.',
               'Probe caveat: E1 finds the interaction-torque divisor; it is the net-moment divisor only if the same mass was used for both, which E3 checks under the same bias assumption.',
               f'Mass categories: ' + '; '.join(f'{k}: {len(v["units"])} folders, {v["parsed_recordings"]} recordings' for k, v in data['mass_categories'].items()) + '.',
               f'Probe: {data["probe_plan"]["selection"]["trials"]} seeded trials (seed {data["probe_plan"]["selection"]["seed"]}) in {data["probe_plan"]["selection"]["units"]} folders; E1 exact identity, E2 plate weight, E3 lever arm.',
               'Code to fix before use: ankle sign in gt24_mass_field_policy; Phase3 masses given to Phase1And2 BT01/BT02/BT13; collection inferred from subject ID; invented day field and _noexo logic; assistance from raw interaction torque.',
               f'Evidence: {AUDIT.relative_to(ROOT)}; builder {HERE.relative_to(ROOT)}; probe {data["probe_plan"]["script"]}.']
    page(SHEET_V / 'index.html', title='GT24 normalization policy',
         ask='Check the evidence behind the GT24 mass policy.',
         headline='GT24 divisor still open; two folders\' masses are swapped',
         chips=chips, figures=figs,
         not_shown=['New GT24 data (probe not run)', 'Author confirmation', 'CoP, IMU and segment angles'],
         reply='looks right, or what is wrong', details=details)
    options = [
        ('A', 'Leave GT24 kinetics empty', 'All standard GT24 moments, powers and body-weight forces',
         'Published per-kg values only under source names; nothing rescaled. Reversible.'),
        ('B', 'Worn mass (person + exoskeleton)', f'BT18/BT24 ({conflict} recordings) until resolved; trials without an established divisor',
         f'Published values rescaled from their measured divisor to the worn mass; forces in worn-system weights; values {(1 - 1 / min(ratios)) * 100:.0f}-{(1 - 1 / max(ratios)) * 100:.0f} % below body-mass values. Reversible.'),
        ('C', 'Body mass (without exoskeleton)', f'As B, plus second-day trials of BT06, BT07, BT13 (first collection): no body mass reported',
         f'Published values rescaled from their measured divisor to body mass (× {min(ratios):.2f}-{max(ratios):.2f} if the measured divisor is the worn mass, × 1 if it is body mass); comparable with datasets without an exoskeleton; published values kept under source names. Reversible.')]
    rows = [(f'{k} · {lab}', [left, cons]) for k, lab, left, cons in options]
    rows.append(('Defer', ['GT24 standard kinetics', 'The divisor probe and other GT24 work proceed; the adapter cannot finish kinetic columns.']))
    ordering = 'Ordered by the normalizing mass: none, heavier (worn), lighter (body).'
    why = ('LocoHub defines forces in body weights and moments per kg; D-GT23-C03-1 rescaled GT23 to each participant\'s own mass; the task acceptance '
           'forbids substituting exoskeleton model mass for body mass. Source per-kg values stay available, so option B remains recoverable. '
           'Cost: second-day trials of three first-collection subjects lose kinetics.')
    decision = {'question': 'Which mass should standard GT24 moment, power and force columns use?', 'columns': ['Left out', 'Consequence'], 'rows': rows,
                'recommendation': f'C. {why} Confidence: medium.', 'footnote': ordering}
    chips_d = [('unchecked', 'Published divisor: probe not run yet'), chips[2], ('pass', f'Worn mass exceeds body mass by {min(diffs):.1f}-{max(diffs):.1f} kg in every README row')]
    page(SHEET_D / 'index.html', title='GT24 mass basis',
         ask='Queued: answer after the divisor probe reports.',
         headline='Choose a mass basis for standard GT24 kinetics',
         chips=chips_d,
         figures=[('fig3_ratio.png', 'How far apart are the two masses?', 'Dashed: equal masses.', 'Worn mass over body mass for every README row')],
         not_shown=['Exact divisors (probe not run)', 'Other exoskeleton datasets', 'Author confirmation'],
         reply='D-GT24-C01-1: A, B, C or defer', details=[details[2], details[4], 'Options ordered by the normalizing mass: none (A), worn, the heavier (B), body, the lighter (C); the builder writes them in that order.', 'Whatever the probe finds, published per-kg values are first converted back with the measured divisor, then divided by the chosen mass.', details[-1]], decision=decision)
    backlog = {'id': 'D-GT24-C01-1', 'task_id': 'GT24-C01',
               'question': ('GT24 participants wore a 6-8 kg exoskeleton. Which mass should LocoHub\'s standard GT24 moment, power and force columns be per kg of? '
                            'Published per-kg values will first be converted back with the divisor the authors used, once a probe measures it.'),
               'options': [{'key': k, 'label': lab, 'consequence': f'Left out: {left}. {cons}'} for k, lab, left, cons in options],
               'options_order': 'By the normalizing mass: none (withheld), heavier (worn), lighter (body).',
               'recommended': 'C', 'confidence': 'medium', 'why': why,
               'check': f'README subject-mass table: every "w/ exo" mass is {min(diffs):.1f}-{max(diffs):.1f} kg above its "w/o exo" mass.',
               'cost_of_waiting': 'GT24 standard kinetic columns cannot be finalized; the divisor probe and all other GT24 work are unaffected.',
               'decide_before_recommendation': True, 'status': 'open'}
    (SHEET_D / 'decision.json').write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + '\n')
    data['decision_candidate'] = dict(backlog, queued_until='GT24-C01 divisor probe pilot (E1 with E3) reports; re-check the option wording against it before copying into backlog.json.')
    AUDIT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'chips': chips, 'decision': backlog}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['audit', 'sheets'])
    a = ap.parse_args()
    build_audit() if a.step == 'audit' else build_sheets()


if __name__ == '__main__':
    main()
