"""GT24-C01: evaluate the E1 census pilot against CENSUS_PILOT.pass_criteria (fixed in the probe before the run).

Reads JSON only: the census-pilot output, the 58-trial pilot output (for the v1 regression check) and the
launcher receipt. Reads no source data. Writes the verdict exclusively (never overwrites).

Usage:
  python3 check_gt24_c01_census_pilot.py CENSUS_PILOT_OUTPUT FIRST_PILOT_OUTPUT RECEIPT [--out PATH]
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

PROBE = Path(__file__).resolve().parent / 'probe_gt24_c01_divisors.py'
FIRST_PILOT_SHA256 = 'b096d8ff29480fabbecd975fba7b2cf00981a44cd286bd7970ff25ddd0b20f6d'
FULL_CENSUS_TRIALS = 2421
LAUNCHER_MAX_S = 3600
TIME_FRACTION = 0.6
RSS_LIMIT_MIB = 512
REL_TOL = 1e-12


def load_probe():
    spec = importlib.util.spec_from_file_location('probe_gt24_c01_divisors_for_check', PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _key(t):
    return (t['phase'], t['subject'], t['recording'])


def evaluate(doc, first, receipt, census_pilot):
    """Return [{'criterion', 'pass', 'evidence'}] in the order of census_pilot['pass_criteria']."""
    crit = census_pilot['pass_criteria']
    res = {_key(t): t for t in doc['results']}
    old = {_key(t): t for t in first['results']}
    fixed = census_pilot['fixed_trials']
    out = []

    # 1. run integrity and memory
    status_ok = receipt.get('status') == 'completed' and receipt.get('exit_code') == 0
    rss = doc.get('peak_rss_mib')
    out.append({'criterion': crit[0], 'pass': bool(status_ok and doc.get('zips_unchanged') is True and rss is not None and rss < RSS_LIMIT_MIB
                                                and doc.get('stage') == 'census_pilot'),
                'evidence': {'receipt_status': receipt.get('status'), 'exit_code': receipt.get('exit_code'),
                             'clean_success': receipt.get('clean_success'),
                             'failed_receipt_checks': sorted(k for k, v in (receipt.get('checks') or {}).items() if v is False),
                             'zips_unchanged': doc.get('zips_unchanged'), 'peak_rss_mib': rss, 'stage': doc.get('stage'),
                             'trials': len(doc['results'])}})

    # 2. v1-exact regression against the 58-trial pilot
    ev, ok = [], True
    for ph, subj, rec, why in fixed:
        if not why.startswith('v1 exact'):
            continue
        new, prev = res.get((ph, subj, rec)), old.get((ph, subj, rec))
        if new is None or prev is None or prev.get('identity_divisor_kg') is None:
            ok = False
            ev.append({'trial': f'{ph}/{subj}/{rec}', 'problem': 'missing'})
            continue
        rel = abs(new['identity_divisor_kg'] - prev['identity_divisor_kg']) / prev['identity_divisor_kg'] if new.get('identity_divisor_kg') else None
        good = new.get('identity_class') == 'exact' and rel is not None and rel <= REL_TOL
        ok &= good
        ev.append({'trial': f'{ph}/{subj}/{rec}', 'class': new.get('identity_class'), 'divisor_kg': new.get('identity_divisor_kg'),
                   'first_pilot_kg': prev['identity_divisor_kg'], 'rel_diff': rel, 'pass': good})
    out.append({'criterion': crit[1], 'pass': ok and len(ev) == 5, 'evidence': ev})

    # 3. short trials: exact_short or not_exact with a stated reason per column; never exact
    ev, ok = [], True
    for ph, subj, rec, why in fixed:
        if why != 'v1 too_few_samples':
            continue
        t = res.get((ph, subj, rec))
        if t is None:
            ok = False
            ev.append({'trial': f'{ph}/{subj}/{rec}', 'problem': 'missing'})
            continue
        cols = {k: v.get('class') + (':' + v['short_rule_failed'] if 'short_rule_failed' in v else '') for k, v in t['identity'].items()}
        stated = all(v.get('class') in ('exact_short', 'too_few_samples', 'column_absent', 'no_identity', 'proportional_not_exact')
                     or (v.get('class') == 'short_not_exact' and 'short_rule_failed' in v) for v in t['identity'].values())
        good = t['identity_class'] in ('exact_short', 'not_exact') and (t['identity_class'] == 'exact_short' or stated)
        ok &= good
        ev.append({'trial': f'{ph}/{subj}/{rec}', 'class': t['identity_class'], 'divisor_kg': t.get('identity_divisor_kg'),
                   'columns': cols, 'pass': good})
    out.append({'criterion': crit[2], 'pass': ok and len(ev) == 6, 'evidence': ev})

    # 4. BT09: own worn row under own_readme_row, other folder's mass under other_candidates
    ev, ok = [], True
    for ph, subj, rec, why in fixed:
        if subj != 'BT09':
            continue
        s = res.get((ph, subj, rec), {}).get('identity_match_split', {})
        own = [h['field'] for h in s.get('own_readme_row', []) if h['subject'] == 'BT09']
        other = [f"{h['phase']} {h['subject']} {h['field']}" for h in s.get('other_candidates', []) if h['subject'] != 'BT09']
        good = any('with_exo' in f for f in own) and bool(other)
        ok &= good
        ev.append({'trial': f'{ph}/{subj}/{rec}', 'own_readme_row': own, 'other_candidates': other, 'pass': good})
    out.append({'criterion': crit[3], 'pass': ok and len(ev) == 2, 'evidence': ev})

    # 5. BT18/BT24 folders: no own README match, an own Statics match
    ev, ok = [], True
    for ph, subj, rec, why in fixed:
        if 'no own README row match' not in why:
            continue
        s = res.get((ph, subj, rec), {}).get('identity_match_split', {})
        good = s.get('own_readme_row') == [] and bool(s.get('own_statics'))
        ok &= good
        ev.append({'trial': f'{ph}/{subj}/{rec}', 'own_readme_row': len(s.get('own_readme_row', [None])),
                   'own_statics': [h['field'] for h in s.get('own_statics', [])], 'pass': good})
    out.append({'criterion': crit[4], 'pass': ok and len(ev) == 3, 'evidence': ev})

    # 6. projected full-census time
    proj = doc['seconds_per_trial'] * FULL_CENSUS_TRIALS
    limit = TIME_FRACTION * LAUNCHER_MAX_S
    out.append({'criterion': crit[5], 'pass': proj < limit,
                'evidence': {'seconds_per_trial': doc['seconds_per_trial'], 'runtime_seconds': doc.get('runtime_seconds'),
                             'projected_full_census_s': round(proj, 1), 'limit_s': limit,
                             'split_by_phase': proj >= limit}})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('census_pilot_output')
    ap.add_argument('first_pilot_output')
    ap.add_argument('receipt')
    ap.add_argument('--out')
    a = ap.parse_args()
    raw_first = Path(a.first_pilot_output).read_bytes()
    if hashlib.sha256(raw_first).hexdigest() != FIRST_PILOT_SHA256:
        raise SystemExit('first pilot output changed')
    doc = json.loads(Path(a.census_pilot_output).read_text())
    receipt = json.loads(Path(a.receipt).read_text())
    probe = load_probe()
    bound = (receipt.get('spec') or {}).get('bindings', {}).get('contributor_tools/audit_probes/2026_10_31/probe_gt24_c01_divisors.py')
    checks = evaluate(doc, json.loads(raw_first), receipt, probe.CENSUS_PILOT)
    verdict = {'task_id': 'GT24-C01', 'stage': 'census_pilot_check', 'scientific_approval': False,
               'probe_sha256_in_output': doc.get('probe_sha256'), 'probe_sha256_bound': bound,
               'probe_matches_binding': doc.get('probe_sha256') == bound,
               'census_pilot_output_sha256': hashlib.sha256(Path(a.census_pilot_output).read_bytes()).hexdigest(),
               'first_pilot_output_sha256': FIRST_PILOT_SHA256, 'checks': checks,
               'all_pass': all(c['pass'] for c in checks) and doc.get('probe_sha256') == bound}
    text = json.dumps(verdict, indent=1, default=float) + '\n'
    if a.out:
        with open(a.out, 'x') as f:   # never overwrite
            f.write(text)
    print(text)


if __name__ == '__main__':
    main()
