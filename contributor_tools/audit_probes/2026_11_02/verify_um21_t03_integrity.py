"""UM21-T03 verifier part 1: run integrity from the seven launcher receipts (read-only).

Independent of the producer and audit code. Outputs are enumerated only from receipts and
their specs, never by glob. Hashing is chunked.
"""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUD = ROOT / 'docs/quality/audits'
JOBS = [('batch0', 'um21-t03-batch0', 'um21-t03-scope.json', 0),
        ('batch1', 'um21-t03-batch1', 'um21-t03-scope.json', 1)] + \
       [(f'v2-batch{b}', f'um21-t03-v2-batch{b}', 'um21-t03-scope-v2.json', b) for b in range(2, 7)]


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    res = {'schema': 'um21_t03_integrity/1', 'failures': [], 'jobs': []}
    fail = res['failures'].append
    t02 = json.loads((AUD / 'um21-t02-pilot-launcher-receipt.json').read_text())['spec']['bindings']
    key = {'runner': 'contributor_tools/run_um21_t03_full.py',
           'producer': 'contributor_tools/extend_umich_tread_source.py',
           'audit': 'contributor_tools/audit_um21_tread_pilot.py'}
    for k, p in key.items():
        if k != 'runner' and p not in t02:
            fail(f'T02 pilot has no binding for {p}')
    seen_entries = set()
    all_records, obs_total = [], 0
    excl_total = 0
    kept_by_scope = {}
    for name, stem, scope_name, batch in JOBS:
        rec = json.loads((AUD / f'{stem}-launcher-receipt.json').read_text())
        spec = json.loads((AUD / f'{stem}-spec.json').read_text())
        scope = json.loads((AUD / scope_name).read_text())
        job = {'job': name, 'job_id': rec['job_id']}
        ok = (rec['status'] == 'completed' and rec['job_outcome'] == 'completed' and rec['exit_code'] == 0
              and rec['clean_success'] is True and rec['launched'] is True
              and rec['expected_outputs_missing'] == [] and not rec['launcher_errors'] and not rec['finalisation_errors']
              and rec['spec']['bindings'] == spec['bindings'] and rec['spec']['command'][:3] == spec['command'][:3])
        if not ok:
            fail(f'{name}: receipt status/exit/clean')
        if not (rec['checks'] and all(v is True for v in rec['checks'].values())):
            fail(f'{name}: not all checks true {rec["checks"]}')
        if rec['cleanup_proof'].get('proven') is not True:
            fail(f'{name}: cleanup not proven')
        if not all(v['matches'] for v in rec['bindings_before'].values()) or not all(v['matches'] for v in rec['bindings_after'].values()):
            fail(f'{name}: binding mismatch before/after')
        ents = rec['launch_ledger']['entries']
        if len(ents) != 1 or ents[0] in seen_entries:
            fail(f'{name}: ledger entries {ents}')
        seen_entries.update(ents)
        for k, p in key.items():
            if spec['bindings'].get(p) != t02.get(p) and k != 'runner':
                fail(f'{name}: {k} binding differs from T02 pilot')
        job['bindings'] = {k: spec['bindings'][p] for k, p in key.items()}
        # scope version consistent
        cmd = spec['command']
        if cmd[cmd.index('--scope') + 1] != f'docs/quality/audits/{scope_name}' or int(cmd[cmd.index('--batch') + 1]) != batch:
            fail(f'{name}: scope/batch argument')
        if cmd[cmd.index('--scope-sha256') + 1] != sha(AUD / scope_name):
            fail(f'{name}: scope hash')
        out_root = Path(rec['spec']['output_root'])
        if 'INVALID' in ''.join(p.name for p in out_root.iterdir()):
            fail(f'{name}: invalid marker in root')
        # output hashes
        bad = 0
        for o in rec['outputs']:
            p = out_root / o['path']
            if not p.is_file() or p.stat().st_size != o['bytes'] or sha(p) != o['sha256']:
                bad += 1
                fail(f'{name}: output mismatch {o["path"]}')
        job['outputs_checked'] = len(rec['outputs']); job['output_mismatches'] = bad
        job['wall_time_seconds'] = rec['wall_time_seconds']; job['peak_rss_kib_largest'] = rec['peak_rss_kib_largest_process']
        job['peak_group_rss_kib'] = rec['peak_group_rss_kib_sampled']
        # records from scope; check counts via run_summary and output files
        recs = scope['batches'][batch]
        kept = {k['record']: k for k in scope['kept']}
        summ = json.loads((out_root / 'run_summary.json').read_text())
        if summ['status'] != 'batch_passed_unreviewed' or summ['records'] != recs or summ['scope_sha256'] != cmd[cmd.index('--scope-sha256') + 1]:
            fail(f'{name}: run_summary')
        pr = {r['record']: r for r in summ['producer_records']}
        for r in recs:
            sub, cond = r.split('/')
            if summ['audits'][r]['status'] != 'pass' or summ['audits'][r]['checks_failed']:
                fail(f'{name}: audit {r}')
            if pr[r]['observations'] != kept[r]['observations']:
                fail(f'{name}: obs count {r}')
            led = out_root / 'components' / sub / cond / 'candidate_ledger.jsonl'
            lines = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
            ne = sum(1 for l in lines if 'excluded' in l); nw = len(lines) - ne
            if ne != kept[r]['excluded_pairs'] or nw != kept[r]['observations']:
                fail(f'{name}: ledger {r} excl {ne} written {nw}')
            excl_total += ne; obs_total += nw
            all_records.append(r)
        job['records'] = len(recs)
        res['jobs'].append(job)
    # cross-job
    for k in key:
        vals = {j['bindings'][k] for j in res['jobs']}
        if len(vals) != 1:
            fail(f'binding {k} not identical across jobs')
    scope2 = json.loads((AUD / 'um21-t03-scope-v2.json').read_text())
    dropped_obs = sum(d['observations_not_converted'] for d in scope2['dropped'])
    dropped_pairs = sum(d['excluded_pairs_in_baseline'] for d in scope2['dropped'])
    res['totals'] = {'records': len(all_records), 'unique_records': len(set(all_records)), 'observations': obs_total,
                     'interval_exclusions': excl_total, 'dropped_records': len(scope2['dropped']),
                     'dropped_observations': dropped_obs, 'dropped_excluded_pairs': dropped_pairs,
                     'baseline_observations': obs_total + dropped_obs, 'baseline_excluded_pairs': excl_total + dropped_pairs}
    t = res['totals']
    if (t['records'], t['unique_records'], t['observations'], t['interval_exclusions'], t['dropped_records'], t['dropped_observations'],
            t['baseline_observations'], t['baseline_excluded_pairs']) != (44, 44, 7562, 3265, 6, 1064, 8626, 3674):
        fail(f'totals {t}')
    res['bound'] = {k: res['jobs'][0]['bindings'][k] for k in key}
    res['status'] = 'pass' if not res['failures'] else 'fail'
    out = ROOT / 'docs/quality/audits/um21-t03-integrity-check.json'
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(res['status'], t, res['failures'][:10])


if __name__ == '__main__':
    main()
