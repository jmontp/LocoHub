"""GT24-C01: summarize the E1 census output into a compact, committed result JSON.

Reads only the census output JSON (hash-checked against the launcher receipt), the receipt, and the README
mass rows in the GT24-C01 policy audit. Reads no source data. Writes the result exclusively (never overwrites).

Usage:
  python3 summarize_gt24_c01_census.py CENSUS_OUTPUT RECEIPT --out docs/quality/audits/gt24-c01-e1-census-result.json
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'docs/quality/audits/gt24-c01-normalization-policy.json'
REPEAT_DAY = ('BT06', 'BT07', 'BT13')   # Phase1And2 folders with two worn masses and no day-2 body mass


def trial_group(t):
    """exact / exact_short, else the not-exact reason from its columns."""
    if t['identity_class'] in ('exact', 'exact_short'):
        return t['identity_class']
    classes = {v.get('class') for v in t['identity'].values()}
    if 'short_not_exact' in classes:
        return 'short_not_exact'
    if classes == {'too_few_samples'}:
        return 'too_few_samples'
    return 'other:' + ','.join(sorted(c for c in classes if c))


def compact(t):
    s = t['identity_match_split']
    return {'phase': t['phase'], 'folder': t['subject'], 'recording': t['recording'], 'group': trial_group(t),
            'divisor_kg': None if t['identity_divisor_kg'] is None else round(t['identity_divisor_kg'], 9),
            'own_readme_fields': sorted({h['field'] for h in s['own_readme_row']}),
            'own_statics': [h['field'] for h in s['own_statics']],
            'other_candidates': [f"{h['source']} {h['phase']} {h['subject']} {h['field']} ({h['relation']})" for h in s['other_candidates']]}


def summarize(doc, readme_rows):
    rows = [compact(t) for t in doc['results']]
    groups = Counter(r['group'] for r in rows)
    col = Counter(v.get('class') + (':' + v['short_rule_failed'] if 'short_rule_failed' in v else '')
                  for t in doc['results'] for v in t['identity'].values())
    with_div = [r for r in rows if r['divisor_kg'] is not None]
    own_body = [r for r in with_div if any(f.startswith('participant_') for f in r['own_readme_fields'])]
    no_readme = Counter(f"{r['phase']}/{r['folder']}" + (' (own Statics match)' if r['own_statics'] else ' (no own match)')
                        for r in with_div if not r['own_readme_fields'])
    flagged = Counter(f"{r['phase']}/{r['folder']} -> {o}" for r in with_div for o in r['other_candidates'])
    rep = {}
    for f in REPEAT_DAY:
        sub = [r for r in rows if r['phase'] == 'Phase1And2' and r['folder'] == f]
        row = readme_rows[('Phase1And2', f)]
        rep[f] = {'recordings': len(sub),
                  'day1_worn': sum('model_day1_with_exo_kg' in r['own_readme_fields'] for r in sub),
                  'day2_worn': sum('model_day2_with_exo_kg' in r['own_readme_fields'] for r in sub),
                  'no_exact_divisor': sum(r['divisor_kg'] is None for r in sub),
                  'other_divisor': sum(r['divisor_kg'] is not None and not ({'model_day1_with_exo_kg', 'model_day2_with_exo_kg'} & set(r['own_readme_fields'])) for r in sub),
                  'readme_has_day2_body_mass': 'participant_day2_kg' in row}
    units = {}
    for r in with_div:
        u = units.setdefault(f"{r['phase']}/{r['folder']}", {})
        e = u.setdefault(f"{r['divisor_kg']:.6f}", {'trials': 0, 'own_readme_fields': r['own_readme_fields'], 'own_statics': r['own_statics']})
        e['trials'] += 1
    spreads = [t['identity_divisor_spread_rel'] for t in doc['results'] if t['identity_divisor_spread_rel'] is not None]
    return rows, {
        'trials': len(rows), 'by_group': dict(sorted(groups.items())), 'column_classes': dict(sorted(col.items())),
        'own_body_mass_matches': [f"{r['phase']}/{r['folder']}/{r['recording']}" for r in own_body],
        'without_own_readme_match_by_folder': dict(sorted(no_readme.items())),
        'flagged_other_candidates_by_folder': dict(sorted(flagged.items())),
        'repeat_day_phase1and2': rep,
        'max_cross_joint_divisor_spread_rel': max(spreads) if spreads else None,
        'units_divisors': units}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('census_output')
    ap.add_argument('receipt')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    raw = Path(a.census_output).read_bytes()
    rc = json.loads(Path(a.receipt).read_text())
    sha = hashlib.sha256(raw).hexdigest()
    if [o['sha256'] for o in rc.get('outputs', [])] != [sha]:
        raise SystemExit('census output does not match the receipt')
    doc = json.loads(raw)
    del raw
    audit = json.loads(AUDIT.read_text())
    readme_rows = {(u['phase'], u['subject_folder']): u['readme_row'] for u in audit['mass_units']}
    rows, summary = summarize(doc, readme_rows)
    result = {'task_id': 'GT24-C01', 'stage': 'e1_census_result', 'scientific_approval': False,
              'summary_script': 'contributor_tools/audit_probes/2026_10_31/summarize_gt24_c01_census.py',
              'probe_sha256': doc['probe_sha256'], 'census_output': {'path': a.census_output, 'sha256': sha},
              'receipt': {'path': a.receipt, 'sha256': hashlib.sha256(Path(a.receipt).read_bytes()).hexdigest(),
                          'status': rc['status'], 'exit_code': rc['exit_code'], 'clean_success': rc['clean_success'],
                          'checks': rc['checks'], 'wall_time_seconds': rc['wall_time_seconds'],
                          'peak_rss_kib_largest_process': rc.get('peak_rss_kib_largest_process')},
              'runtime_seconds': doc['runtime_seconds'], 'seconds_per_trial': doc['seconds_per_trial'],
              'peak_rss_mib_probe': doc['peak_rss_mib'], 'members_read': len(doc['members_read']), 'zips_unchanged': doc['zips_unchanged'],
              'rules': doc['plan']['rules'], 'summary': summary, 'trials': rows}
    with open(a.out, 'x') as f:   # never overwrite
        f.write(json.dumps(result, indent=1, default=float) + '\n')
    print(json.dumps({k: summary[k] for k in summary if k != 'units_divisors'}, indent=1))


if __name__ == '__main__':
    main()
