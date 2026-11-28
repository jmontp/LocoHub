"""MB24-F01: reconcile the MBLUE rebuild receipts against each other and the source inventory.

Read-only and small. Reads JSON receipts only (4 MiB cap each), hashes those receipts and
the bound code files, and stats (never opens) the large source and output files. It loads
no arrays, opens no MAT or Parquet file, starts no job, and writes nothing under
converted_datasets/. Writes docs/quality/audits/mb24-f01-receipt-reconciliation.json.

The checks are written from the receipts' own fields, not by calling
check_mblue_final_scope.py, so they are a second reading of the same evidence. They
cannot establish that the large files still hold the recorded bytes; that needs the
full-byte job specified in the output.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / 'converted_datasets/reconversion_v2'
AUDITS = ROOT / 'docs/quality/audits'
OUT = AUDITS / 'mb24-f01-receipt-reconciliation.json'
MAX_JSON = 4 * 1024**2
SOURCE_DIR = Path('/mnt/s/workspace/MBLUEAnkleOpenSimProcessing/Subject_Data')

R = {
    'inventory': 'mblue_source_inventory_20261021/source_inventory.json',
    'baseline': 'mblue_full_normalized_v2_20261021/conversion_summary.json',
    'rebuild': 'mblue_pelvis_corrected_full_20261021/conversion_summary.json',
    'readback': 'mblue_pelvis_full_readback_20261021/source_comparison.json',
    'preservation': 'mblue_pelvis_full_preservation_20261021/preservation.json',
    'recovery': 'mblue_stair_reference_review_v3_20261021/reference_recovery.json',
    'correction': 'mblue_reference_corrected_full_20261021/correction_summary.json',
    'scope_gate': 'mblue_final_acceptance_20261021/scope_evidence.json',
    'gate_status': 'mblue_final_acceptance_20261021/status.json',
    'gate_plan': 'mblue_final_acceptance_20261021/plan.json',
    'detour_status': 'mblue_priority_handoff_20261021/status.json',
    'pelvis_queue_plan': 'mblue_pelvis_serial_queue_20261021/plan.json',
    'stair_queue_plan': 'mblue_stair_reference_serial_queue_20261021/plan.json',
    'marker_endpoints': 'mblue_marker_endpoint_review_20261021/marker_endpoints.json',
    'planar': 'mblue_planar_preserved_early_full_20261021/planar_preservation_summary.json',
    'old_readback_main': 'mblue_full_source_audit_v2_20261021/source_comparison.json',
    'old_readback_tail': 'mblue_final_blocks_audit_20261021/source_comparison.json',
    'pelvis_pilot': 'mblue_pelvis_pilot_v2_20261021/conversion_summary.json',
    'pelvis_pilot_readback': 'mblue_pelvis_pilot_readback_v2_20261021/source_comparison.json',
    'pelvis_pilot_preservation': 'mblue_pelvis_preservation_pilot_20261021/preservation.json',
    'stair_pilot': 'mblue_stair_reference_pilot_v2_20261021/correction_summary.json',
}
DOC_AUDITS = ['mblue-complete-scope.json', 'mblue-complete-source-readback.json', 'mblue-pelvis-clock-fix.json',
              'mblue-pelvis-full-preservation.json', 'mblue-pelvis-full-readback.json', 'mblue-stair-reference.json',
              'pm02-job-dispositions.json']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    path = Path(path)
    if path.stat().st_size > MAX_JSON:
        raise ValueError(f'{path} exceeds the 4 MiB JSON cap')
    return json.loads(path.read_text())


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def key(row):
    return (row['subject'], row['source_path'])


def kind(path):
    if '/stairs/' in path:
        return 'stairs'
    if '/STS/' in path:
        return 'sit_stand'
    if path.endswith('/crouch'):
        return 'crouch'
    return 'treadmill'


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    os.nice(max(0, 19 - os.nice(0)))
    paths = {n: V2 / p for n, p in R.items()}
    hashes = {n: sha(p) for n, p in paths.items()}
    d = {n: load(p) for n, p in paths.items() if p.suffix == '.json'}
    doc = {n: load(AUDITS / n) for n in DOC_AUDITS}
    checks = []

    def check(name, ok, detail=''):
        checks.append({'check': name, 'result': 'pass' if ok else 'failed', 'detail': detail})
        return ok

    # ---------------------------------------------------------------- hashes
    recorded = [  # (where recorded, field, receipt name)
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['inventory'], 'inventory'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['baseline'], 'baseline'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['rebuild'], 'rebuild'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['source_audit'], 'readback'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['preservation'], 'preservation'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['recovery'], 'recovery'),
        ('scope gate input_sha256', d['scope_gate']['input_sha256']['correction'], 'correction'),
        ('baseline inventory_sha256', d['baseline']['inventory_sha256'], 'inventory'),
        ('rebuild inventory_sha256', d['rebuild']['inventory_sha256'], 'inventory'),
        ('recovery inventory_sha256', d['recovery']['inventory_sha256'], 'inventory'),
        ('readback summary_sha256', d['readback']['summary_sha256'], 'rebuild'),
        ('preservation baseline_summary_sha256', d['preservation']['baseline_summary_sha256'], 'baseline'),
        ('preservation corrected_summary_sha256', d['preservation']['corrected_summary_sha256'], 'rebuild'),
        ('correction baseline_summary_sha256', d['correction']['baseline_summary_sha256'], 'rebuild'),
        ('correction reference_recovery_sha256', d['correction']['reference_recovery_sha256'], 'recovery'),
        ('marker endpoint recovery_sha256', d['marker_endpoints']['recovery_sha256'], 'recovery'),
        ('planar input correction_summary', next(v for k, v in d['planar']['input_sha256'].items()
                                                  if k.endswith('correction_summary.json')), 'correction'),
        ('planar input scope_evidence', next(v for k, v in d['planar']['input_sha256'].items()
                                              if k.endswith('scope_evidence.json')), 'scope_gate'),
        ('old tail readback summary_sha256', d['old_readback_tail']['summary_sha256'], 'baseline'),
        ('PM-02 pelvis queue plan', doc['mblue-pelvis-clock-fix.json']['queue_plan_sha256'], 'pelvis_queue_plan'),
        ('docs stair-reference queue plan', doc['mblue-stair-reference.json']['queue_plan_sha256'], 'stair_queue_plan'),
        ('docs stair-reference recovery', doc['mblue-stair-reference.json']['recovery_sha256'], 'recovery'),
        ('docs stair-reference pilot summary', doc['mblue-stair-reference.json']['pilot_summary_sha256'], 'stair_pilot'),
        ('docs stair-reference marker report', doc['mblue-stair-reference.json']['marker_endpoint_readback']['report_sha256'],
         'marker_endpoints'),
        ('docs pelvis-clock-fix pilot summary', doc['mblue-pelvis-clock-fix.json']['pilot_summary_sha256'], 'pelvis_pilot'),
        ('docs pelvis-clock-fix pilot readback', doc['mblue-pelvis-clock-fix.json']['source_readback_sha256'],
         'pelvis_pilot_readback'),
        ('docs pelvis-clock-fix pilot preservation', doc['mblue-pelvis-clock-fix.json']['preservation_sha256'],
         'pelvis_pilot_preservation'),
        ('docs pelvis-full-readback evidence', doc['mblue-pelvis-full-readback.json']['evidence_sha256'], 'readback'),
        ('docs pelvis-full-preservation evidence', doc['mblue-pelvis-full-preservation.json']['evidence_sha256'],
         'preservation'),
        ('docs pelvis-full-preservation baseline', doc['mblue-pelvis-full-preservation.json']['baseline_summary_sha256'],
         'baseline'),
        ('docs pelvis-full-preservation corrected', doc['mblue-pelvis-full-preservation.json']['corrected_summary_sha256'],
         'rebuild'),
        ('docs complete-scope evidence', doc['mblue-complete-scope.json']['evidence_sha256'], 'scope_gate'),
        ('docs complete-source-readback summary', doc['mblue-complete-source-readback.json']['summary_sha256'], 'baseline'),
    ]
    for job in d['detour_status']['jobs']:
        name = {'mblue_pelvis_rebuild': 'rebuild', 'mblue_pelvis_readback': 'readback',
                'mblue_pelvis_preservation': 'preservation',
                'mblue_stair_reference_correction': 'correction'}[job['name']]
        recorded.append(('detour status ' + job['name'], job['summary_sha256'], name))
    for job in doc['pm02-job-dispositions.json']['mblue_detour_recheck']['jobs']:
        name = {'mblue_pelvis_rebuild': 'rebuild', 'mblue_pelvis_readback': 'readback',
                'mblue_pelvis_preservation': 'preservation',
                'mblue_stair_reference_correction': 'correction'}[job['job']]
        recorded.append(('PM-02 recheck ' + job['job'], job['recorded_sha256'], name))
    for k, v in doc['mblue-complete-scope.json']['input_sha256'].items():
        recorded.append(('docs complete-scope ' + k, v, {'source_audit': 'readback'}.get(k, k)))
    for path, value in doc['mblue-complete-source-readback.json']['component_audits'].items():
        recorded.append(('docs complete-source-readback component', value,
                         'old_readback_main' if 'full_source_audit_v2' in path else 'old_readback_tail'))
    hash_rows = [{'recorded_in': w, 'receipt': R[n], 'recorded_sha256': v, 'current_sha256': hashes[n],
                  'match': v == hashes[n]} for w, v, n in recorded]
    mismatched = [r for r in hash_rows if not r['match']]
    check('Every recorded receipt hash equals the current receipt bytes', not mismatched,
          f'{len(hash_rows)} recorded references to {len({r["receipt"] for r in hash_rows})} receipts; '
          f'{len(mismatched)} mismatched')

    # ------------------------------------------------------------ code bound
    code_rows = []
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    def code(where, path, value):
        p = Path(path)
        current = sha(p) if p.exists() else None
        row = {'bound_in': where, 'path': rel(p), 'recorded_sha256': value, 'current_sha256': current,
               'match': current == value}
        if not row['match'] and p.is_relative_to(ROOT):
            blob = subprocess.run(['git', 'show', f'HEAD:{rel(p)}'], cwd=ROOT, capture_output=True)
            row['head_sha256'] = hashlib.sha256(blob.stdout).hexdigest() if blob.returncode == 0 else None
            row['recorded_equals_head'] = row['head_sha256'] == value
        code_rows.append(row)
    for plan in ('pelvis_queue_plan', 'stair_queue_plan'):
        for job in d[plan]['jobs']:
            for path, value in job['code_sha256'].items():
                code(f'{plan}:{job["name"]}', path, value)
    for path, value in d['rebuild']['code_sha256'].items():
        code('rebuild summary', path, value)
    code('scope gate plan', d['gate_plan']['probe'], d['gate_plan']['probe_sha256'])
    code('readback probe', ROOT / 'contributor_tools/audit_mblue_normalized.py', d['readback']['probe_sha256'])
    code('preservation probe', ROOT / 'contributor_tools/audit_mblue_pelvis_preservation.py',
         d['preservation']['probe_sha256'])
    code('correction probe', ROOT / 'contributor_tools/correct_mblue_stair_reference.py', d['correction']['probe_sha256'])
    code('inventory probe', ROOT / 'contributor_tools/audit_probes/2026_10_20/check_mblue_source_inventory.py',
         d['inventory']['probe_sha256'])
    code('recovery probe', ROOT / 'contributor_tools/audit_probes/2026_10_20/check_mblue_stair_reference.py',
         d['recovery']['probe_sha256'])
    code('marker endpoint probe', ROOT / 'contributor_tools/audit_probes/2026_10_20/check_mblue_marker_endpoints.py',
         d['marker_endpoints']['probe_sha256'])
    drift = sorted({r['path'] for r in code_rows if not r['match']})
    check('Bound producer/checker code unchanged, or recorded version recoverable from HEAD',
          all(r['match'] or r.get('recorded_equals_head') for r in code_rows),
          f'{len(code_rows)} bindings; changed in working tree: {drift or "none"}')

    # ------------------------------------------------------------- statuses
    expected_status = {'baseline': 'all_normalized_blocks_reconstructed_unreviewed',
                       'rebuild': 'all_normalized_blocks_reconstructed_unreviewed',
                       'readback': 'all_normalized_blocks_source_checked_unreviewed',
                       'preservation': 'pelvis_fix_preservation_checked_unreviewed',
                       'recovery': 'all_stair_reference_windows_recovered_unreviewed',
                       'correction': 'stair_reference_corrected_unreviewed',
                       'scope_gate': 'complete_mblue_scope_evidence_checked_unreviewed',
                       'gate_status': 'complete_mblue_scope_evidence_checked_unreviewed',
                       'detour_status': 'completed_unreviewed',
                       'marker_endpoints': 'all_marker_endpoints_reproduced_unreviewed'}
    bad = {n: d[n].get('status') for n, s in expected_status.items() if d[n].get('status') != s}
    check('Terminal success status in every chain receipt; none claims scientific approval',
          not bad and not any(d[n].get('scientific_approval') for n in expected_status),
          f'unexpected: {bad or "none"}; inventory has no status field (PM-02: no terminal record)')
    check('Readback started at block 0 and correction scope is full_baseline',
          d['readback']['start_index'] == 0 and d['correction']['scope'] == 'full_baseline')

    # --------------------------------------------------------- block scope
    inv = {key(b): b for b in d['inventory']['blocks']}
    idx = {}
    for n in ('baseline', 'rebuild', 'readback', 'preservation', 'correction', 'planar'):
        rows = d[n]['records']
        idx[n] = {key(r): r for r in rows}
        check(f'{n}: 335 unique blocks equal to the inventory block set',
              len(rows) == len(idx[n]) == 335 and idx[n].keys() == inv.keys(), f'{len(rows)} records')
    by_kind = Counter(kind(k[1]) for k in inv)
    sources = {Path(s['path']).name.split('_')[0]: s for s in d['inventory']['sources']}
    check('Inventory names 10 source MAT files, one per subject, and every block subject has one',
          len(sources) == 10 and {k[0] for k in inv} == set(sources))
    check('Every rebuild and baseline record binds its subject source hash from the inventory',
          all(idx[n][k]['source_sha256'] == sources[k[0]]['sha256'] for n in ('baseline', 'rebuild') for k in inv))
    check('Baseline and rebuild agree on subject_info hash, rows and output paths for every block',
          all(idx['baseline'][k]['subject_info_sha256'] == idx['rebuild'][k]['subject_info_sha256']
              and idx['baseline'][k]['rows'] == idx['rebuild'][k]['rows']
              and set(idx['baseline'][k]['outputs']) == set(idx['rebuild'][k]['outputs'])
              == set(idx['correction'][k]['outputs']) for k in inv))
    check('Recovery normalized hashes equal the inventory source hashes',
          all(r['normalized_sha256'] == sources[r['subject']]['sha256'] for r in d['recovery']['records']))

    # ---------------------------------------------------- observation counts
    def inventory_views(k):
        sides = inv[k]['sides']
        if kind(k[1]) in ('sit_stand', 'crouch'):
            return sides['l']['cycles']  # bilateral blocks: one shared clock, exported once
        return sides['l']['cycles'] + sides['r']['cycles']
    per_block = {k: inventory_views(k) for k in inv}
    total = sum(per_block.values())
    fields = [('baseline', 'observations'), ('rebuild', 'observations'), ('readback', 'observations'),
              ('correction', 'observations_before'), ('planar', 'observations')]
    mism = [k for k in inv if not all(idx[n][k][f] == per_block[k] for n, f in fields[:4])]
    check('Per-block views equal inventory cycles in baseline, rebuild, readback and correction (before)',
          not mism, f'total {total}; mismatched blocks {len(mism)}')
    check('Rows are exactly 150 per observation in baseline and rebuild',
          all(idx[n][k]['rows'] == 150 * per_block[k] for n in ('baseline', 'rebuild') for k in inv))
    pres_sum = {k: sum(idx['preservation'][k]['counts'].values()) for k in inv}
    check('Preservation counts per block sum to the block observations',
          all(pres_sum[k] == per_block[k] for k in inv))
    totals = {
        'inventory_views': total,
        'readback_records_sum': sum(r['observations'] for r in d['readback']['records']),
        'readback_reported': d['readback']['observations'],
        'readback_finite_values_sum': sum(r['finite_values_checked'] for r in d['readback']['records']),
        'readback_finite_values_reported': d['readback']['finite_values_checked'],
        'readback_max_error_over_blocks': max(r['maximum_error'] for r in d['readback']['records']),
        'preservation_counts_reported': d['preservation']['counts'],
        'correction_before_reported': d['correction']['observations_before'],
        'correction_after_reported': d['correction']['observations_after'],
        'correction_after_records_sum': sum(r['observations_after'] for r in d['correction']['records']),
        'planar_observations_reported': d['planar']['observations'],
        'planar_records_sum': sum(r['observations'] for r in d['planar']['records']),
        'scope_gate': {k: d['scope_gate'][k] for k in ('blocks', 'observations_before', 'observations_after',
                                                       'retained_stair_windows', 'omitted_nonreference_views')},
    }
    pres_tot = Counter()
    for r in d['preservation']['records']:
        pres_tot.update(r['counts'])
    check('Receipt totals equal the sum of their per-block records',
          totals['readback_records_sum'] == totals['readback_reported'] == total
          and totals['readback_finite_values_sum'] == totals['readback_finite_values_reported']
          and dict(pres_tot) == d['preservation']['counts']
          and totals['correction_before_reported'] == total
          and totals['correction_after_records_sum'] == totals['correction_after_reported']
          and totals['planar_records_sum'] == totals['planar_observations_reported'] == totals['correction_after_reported'])

    # ------------------------------------------------- pelvis/preservation
    pres_by_kind = defaultdict(Counter)
    for k in inv:
        pres_by_kind[kind(k[1])].update(idx['preservation'][k]['counts'])
    left_total = sum(inv[k]['sides']['l']['cycles'] for k in inv)
    right_total = sum(inv[k]['sides']['r']['cycles'] for k in inv if kind(k[1]) in ('treadmill', 'stairs'))
    pres = d['preservation']['counts']
    check('Every left view unchanged and every right view classified (changed or unchanged)',
          pres['left_unchanged'] == left_total and pres['right_changed'] + pres['right_unchanged'] == right_total,
          f'left {left_total}; right {right_total}')
    stair_right = pres_by_kind['stairs'].get('right_unchanged', 0) + pres_by_kind['stairs'].get('right_changed', 0)
    tread_right_unchanged = pres_by_kind['treadmill'].get('right_unchanged', 0)
    unchanged_tread_blocks = sorted(f'{k[0]}/{k[1]}' for k in inv if kind(k[1]) == 'treadmill'
                                    and idx['preservation'][k]['counts'].get('right_unchanged'))
    allowed_prefix = ('pelvis_sagittal_', 'thigh_sagittal_', 'shank_sagittal_', 'foot_sagittal_')
    changed_cols = sorted({c for r in d['preservation']['records'] for c in r['changed_columns']})
    check('Changed columns are only pelvis and pelvis-derived segment columns',
          all(c.startswith(allowed_prefix) for c in changed_cols), f'{len(changed_cols)} distinct columns')
    check('Stairs and bilateral blocks have no changed views (their right clock equals the left clock)',
          all(not pres_by_kind[t].get('right_changed') for t in ('stairs', 'sit_stand', 'crouch')))

    # ------------------------------------------------- stair windows/views
    windows = {}
    rec_counts = Counter()
    for r in d['recovery']['records']:
        matched = [c for c in r['candidates'] if c['status'] == 'all_windows_matched']
        if not (r['status'] == 'unique_source_matched' and len(matched) == 1
                and len(matched[0]['windows']) == r['expected_windows']):
            rec_counts['bad_records'] += 1
            continue
        for w in matched[0]['windows']:
            wk = (r['subject'], w['source_path'], w['source_curve_index'])
            rec_counts['duplicate_windows'] += wk in windows
            windows[wk] = w
            rec_counts[w['reference_side']] += 1
            rec_counts['force_event_endpoints' if w['end_matches_same_side_force_event'] else 'source_marker_endpoints'] += 1
    unresolved = [{'subject': r['subject'], 'condition': r['condition'], 'ik_file': Path(c['ik_path']).name,
                   'session': Path(c['ik_path']).parent.name, 'reason': c.get('reason')}
                  for r in d['recovery']['records'] for c in r['candidates'] if c['status'] != 'all_windows_matched']
    check('Recovery: 20 subject-condition records, each with exactly one fully matched source candidate',
          len(d['recovery']['records']) == 20 and not rec_counts['bad_records'] and not rec_counts['duplicate_windows'],
          f'{len(unresolved)} non-matching candidate sessions retained as unresolved (not used)')
    check('Recovered side and endpoint counts equal the docs stair-reference receipt',
          {k: rec_counts[k] for k in ('right', 'left', 'force_event_endpoints', 'source_marker_endpoints')}
          == doc['mblue-stair-reference.json']['recovered_reference_counts'],
          json.dumps({k: rec_counts[k] for k in ('right', 'left', 'force_event_endpoints', 'source_marker_endpoints')}))
    me = d['marker_endpoints']
    check('Marker-endpoint reproduction covers every marker-derived endpoint',
          me['windows_checked'] == me['windows_matched'] == rec_counts['source_marker_endpoints'])
    stair_blocks = [k for k in inv if kind(k[1]) == 'stairs']
    win_by_block = Counter(wk[:2] for wk in windows)
    check('Every stair block has l and r cycles equal to its recovered window count',
          set(win_by_block) == set(stair_blocks)
          and all(inv[k]['sides']['l']['cycles'] == inv[k]['sides']['r']['cycles'] == win_by_block[k]
                  for k in stair_blocks), f'{len(stair_blocks)} stair blocks, {len(windows)} windows')
    # Independent parse of the observation identities.
    lineage_errors = Counter()
    retained, omitted = set(), set()
    for k in stair_blocks:
        c = idx['correction'][k]
        prefix = f'mblue:{k[0]}_NormalizedStrides.mat:dataOut/{k[1]}:'
        seen_cols = set()
        for oid, bucket in [(o, 'kept') for o in c['retained_stair_observation_ids']] + \
                           [(o, 'omitted') for o in c['omitted_nonreference_views']]:
            if not oid.startswith(prefix):
                lineage_errors['identity_prefix'] += 1
                continue
            side, word, col = oid[len(prefix):].split(':')
            w = windows.get((k[0], k[1], int(col)))
            if word != 'column' or w is None:
                lineage_errors['unknown_window'] += 1
                continue
            ref = w['reference_side'][0]
            if (bucket == 'kept') != (side == ref):
                lineage_errors['wrong_side'] += 1
            seen_cols.add((int(col), side))
            (retained if bucket == 'kept' else omitted).add(oid)
        if seen_cols != {(i, s) for (sub, sp, i) in windows if (sub, sp) == k for s in 'lr'}:
            lineage_errors['window_views_not_exactly_two'] += 1
        if c['observations_after'] != win_by_block[k] or c['observations_before'] != 2 * win_by_block[k]:
            lineage_errors['count'] += 1
    check('Stair lineage: each recovered window keeps exactly its reference view and omits exactly the other view',
          not lineage_errors and len(retained) == len(omitted) == len(windows) == 764 and not retained & omitted,
          f'retained {len(retained)}, omitted {len(omitted)}, errors {dict(lineage_errors) or "none"}')
    nonstair_ok = all(not idx['correction'][k]['retained_stair_observation_ids']
                      and not idx['correction'][k]['omitted_nonreference_views']
                      and idx['correction'][k]['observations_after'] == per_block[k]
                      and idx['correction'][k]['outputs'] == idx['rebuild'][k]['outputs'] for k in inv if k not in win_by_block)
    stair_new_bytes = sum(idx['correction'][k]['outputs'] != idx['rebuild'][k]['outputs'] for k in stair_blocks)
    check('Non-stair blocks: no exclusions and final output hash equals the readback-checked rebuild hash',
          nonstair_ok, f'{335 - len(stair_blocks)} blocks')
    check('Stair blocks: final outputs are new files (hash differs from rebuild) and are not covered by the rebuild readback',
          stair_new_bytes == len(stair_blocks), f'{stair_new_bytes} of {len(stair_blocks)}')
    check('Exclusion accounting: before minus after equals omitted non-reference views',
          total - d['correction']['observations_after'] == len(omitted) == 764
          and d['correction']['observations_after'] == 15061, f'{total} - 15061 = {total - 15061}')
    planar_ok = all(idx['planar'][k]['outputs'][p]['source_sha256'] == h
                    for k in inv for p, h in idx['correction'][k]['outputs'].items())
    check('Downstream planar outputs bind the final correction output hashes (all 335)', planar_ok)

    # ------------------------------------------------------ on-disk (stat)
    def stat_tree(root, outputs):
        missing, sizes, newest = [], 0, 0.0
        for p in outputs:
            f = root / p
            if not f.exists():
                missing.append(p)
                continue
            st = f.stat()
            sizes += st.st_size
            newest = max(newest, st.st_mtime)
        return missing, sizes, newest
    final_root = V2 / 'mblue_reference_corrected_full_20261021'
    rebuild_root = V2 / 'mblue_pelvis_corrected_full_20261021'
    final_outputs = [p for k in inv for p in idx['correction'][k]['outputs']]
    rebuild_outputs = [p for k in inv for p in idx['rebuild'][k]['outputs']]
    f_missing, f_bytes, f_newest = stat_tree(final_root, final_outputs)
    r_missing, r_bytes, r_newest = stat_tree(rebuild_root, rebuild_outputs)
    final_files = sorted(rel(p) for p in final_root.rglob('*') if p.is_file())
    stair_final_bytes = sum((final_root / p).stat().st_size for k in stair_blocks for p in idx['correction'][k]['outputs'])
    stair_rebuild_bytes = sum((rebuild_root / p).stat().st_size for k in stair_blocks for p in idx['rebuild'][k]['outputs'])
    summary_mtime = paths['correction'].stat().st_mtime
    check('All 335 final and 335 rebuild outputs exist; final directory holds only those plus its summary',
          not f_missing and not r_missing and len(final_files) == 336,
          f'final {f_bytes} bytes, rebuild {r_bytes} bytes (stat only, not hashed)')
    check('No final output modified after its correction summary was written (mtime only; not byte evidence)',
          f_newest <= summary_mtime + 1)
    src_stats = []
    for subject, s in sorted(sources.items()):
        p = Path(s['path'])
        info = p.with_name(subject + '_FileInfo.mat')
        src_stats.append({'subject': subject, 'source_exists': p.exists(),
                          'source_bytes_match_inventory': p.exists() and p.stat().st_size == s['bytes'],
                          'source_mtime_utc': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()
                          if p.exists() else None,
                          'fileinfo_exists': info.exists(), 'fileinfo_bytes': info.stat().st_size if info.exists() else None})
    check('All 10 source MAT files exist with the inventory byte size; all 10 FileInfo files exist',
          all(s['source_bytes_match_inventory'] and s['fileinfo_exists'] for s in src_stats))
    mot = []
    for r in d['recovery']['records']:
        for c in r['candidates']:
            if c['status'] == 'all_windows_matched':
                for k2 in ('force', 'ik'):
                    p = Path(c[k2 + '_path'])
                    mot.append({'path': str(p), 'sha256': c[k2 + '_sha256'],
                                'bytes': p.stat().st_size if p.exists() else None})
    check('All 40 matched stair force/IK source files exist', len(mot) == 40 and all(m['bytes'] for m in mot),
          f'{sum(m["bytes"] or 0 for m in mot)} bytes')
    source_bytes = sum(s['bytes'] for s in sources.values())
    info_bytes = sum(s['fileinfo_bytes'] or 0 for s in src_stats)
    mot_bytes = sum(m['bytes'] or 0 for m in mot)

    # ------------------------------------------- side-cycles -> views map
    side_cycles = sum(b['sides'][s]['cycles'] for b in inv.values() for s in b['sides'])
    bilateral = [k for k in inv if kind(k[1]) in ('sit_stand', 'crouch')]
    contra_right = sum(inv[k]['sides']['r']['cycles'] for k in bilateral)
    check('Inventory side-cycles minus right sit-stand/crouch cycles (carried as contra columns) equal the views',
          side_cycles - contra_right == total
          and all(inv[k]['bilateral_clocks_exactly_equal'] for k in bilateral),
          f'{side_cycles} - {contra_right} = {side_cycles - contra_right}; {len(bilateral)} bilateral blocks, '
          'all with exactly equal bilateral clocks')

    # ------------------------------- unchanged right treadmill views pattern
    surplus = {}
    for k in inv:
        if kind(k[1]) == 'treadmill':
            surplus[k] = inv[k]['sides']['r']['cycles'] - inv[k]['sides']['l']['cycles']
    surplus2 = [k for k in surplus if surplus[k] >= 2]
    with_unchanged = [k for k in surplus if idx['preservation'][k]['counts'].get('right_unchanged')]
    surplus_pattern = {
        'treadmill_blocks': len(surplus),
        'blocks_with_right_minus_left_at_least_2': len(surplus2),
        'of_those_with_unchanged_right_views': sum(k in with_unchanged for k in surplus2),
        'blocks_with_right_minus_left_at_most_1_and_unchanged_right_views': sum(
            k in with_unchanged for k in surplus if surplus[k] <= 1),
        'blocks': [{'block': f'{k[0]}/{k[1]}', 'right_minus_left_cycles': surplus[k],
                    'right_unchanged': idx['preservation'][k]['counts'].get('right_unchanged', 0)}
                   for k in sorted(surplus2)],
        'reading': ('Unchanged right views occur only in blocks with at least 2 more right than left cycles. This fits '
                    'right cycles with no left-clock overlap, whose pelvis stayed missing before and after the fix. '
                    'The receipts do not record pre-fix values per view, so this is not established.'),
        'status': 'not_checked',
    }
    checks.append({'check': 'Why 4 right treadmill views were unchanged by the pelvis fix', 'result': 'not_checked',
                   'detail': (f'only in blocks with right-left >= 2 ({surplus_pattern["of_those_with_unchanged_right_views"]} '
                              f'of {len(surplus2)}; 0 of {len(surplus) - len(surplus2)} other treadmill blocks); '
                              'consistent with no left-clock overlap, not established; stage 2 target')})

    # ------------------------------------------------------------ results
    failed = [c for c in checks if c['result'] == 'failed']
    result = {
        'task_id': 'MB24-F01',
        'checked_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'status': 'receipts_reconciled_full_bytes_not_rechecked' if not failed else 'receipt_inconsistency_found',
        'scientific_approval': False,
        'method': ('Read-only. JSON receipts only (4 MiB cap), SHA256 of small JSON receipts and bound code, '
                   'stat (size, mtime) of large source and output files without opening them. No arrays loaded, '
                   'no MAT or Parquet opened, no job started, nothing under converted_datasets/ written.'),
        'repository_head': head,
        'builder': {'path': rel(Path(__file__)), 'sha256': sha(Path(__file__))},
        'receipts_sha256': {R[n]: hashes[n] for n in R},
        'scope_counts': {
            'blocks': len(inv), 'blocks_by_kind': dict(by_kind),
            'observations_before_stair_correction': total,
            'observations_after': d['correction']['observations_after'],
            'stair_windows': len(windows), 'retained_reference_views': len(retained),
            'omitted_nonreference_views': len(omitted),
            'reference_sides': {'right': rec_counts['right'], 'left': rec_counts['left']},
            'endpoint_basis': {'force_event': rec_counts['force_event_endpoints'],
                               'source_marker': rec_counts['source_marker_endpoints']},
            'pelvis_fix_views': dict(pres),
            'pelvis_fix_views_by_kind': {t: dict(c) for t, c in pres_by_kind.items()},
            'right_unchanged_decomposition': {'stairs': pres_by_kind['stairs'].get('right_unchanged', 0),
                                              'treadmill': tread_right_unchanged,
                                              'treadmill_blocks_with_unchanged_right_views': unchanged_tread_blocks,
                                              'right_surplus_pattern': surplus_pattern},
            'pelvis_changed_columns': changed_cols,
            'totals': totals,
        },
        'lineage': {
            'chain': [
                'source MAT (10 subjects) + FileInfo -> inventory (335 blocks, 16,418 side-cycles = 15,825 views; see block_to_observation)',
                'inventory -> pelvis-corrected rebuild (335 outputs; summary binds source and FileInfo hashes per block)',
                'rebuild -> full source readback (re-hashes each rebuild output and each source MAT before comparing values)',
                'baseline v2 + rebuild -> preservation (re-hashes both output sets; only pelvis/segment columns may differ; left views identical)',
                'source MAT + stair force/IK .mot -> reference recovery (20 subject-conditions, 764 windows)',
                'rebuild + recovery -> stair correction (199 outputs copied byte-identical; 136 stair outputs rewritten keeping one view per window plus 4 source-event columns)',
                'all seven summaries -> scope gate (summary consistency only)',
                'correction -> planar relabel (downstream, separate gate)'],
            'block_to_observation': (f'The inventory holds {side_cycles:,} side-cycles. Treadmill and stair blocks emit one view per '
                                     f'side cycle (l + r). The {len(bilateral)} sit-stand and crouch blocks have identical left and '
                                     f'right clocks and emit one observation per left cycle, with the right side as contra columns, '
                                     f'so their {contra_right:,} right cycles are not separate views: '
                                     f'{side_cycles:,} - {contra_right:,} = {total:,} views.'),
            'observation_to_window': ('Stair identity mblue:<subject>_NormalizedStrides.mat:dataOut/<path>:<l|r>:column:<k> maps to '
                                      'recovered window (subject, path, k); the kept view letter equals the recovered reference side.'),
            'nonreference_views': 'Omitted view identities are listed per block in correction_summary.json; none is silently dropped.',
            'unused_recovery_candidates': unresolved,
        },
        'hash_reconciliation': {'recorded_references': len(hash_rows), 'mismatched': len(mismatched), 'rows': hash_rows},
        'code_bindings': {'bindings': len(code_rows), 'changed_in_working_tree': drift, 'rows': code_rows},
        'on_disk_stat': {
            'final_outputs': {'root': rel(final_root), 'files': len(final_outputs), 'missing': f_missing,
                              'bytes': f_bytes, 'stair_bytes': stair_final_bytes},
            'rebuild_outputs': {'root': rel(rebuild_root), 'files': len(rebuild_outputs), 'missing': r_missing,
                                'bytes': r_bytes, 'stair_bytes': stair_rebuild_bytes},
            'source_mat': src_stats, 'source_mat_bytes': source_bytes, 'fileinfo_bytes': info_bytes,
            'stair_force_ik_files': len(mot), 'stair_force_ik_bytes': mot_bytes,
        },
        'checks': checks,
        'failed_checks': len(failed),
    }
    result.update(interpretation(result))
    tmp = OUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, indent=2) + '\n')
    tmp.replace(OUT)
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'failed': len(failed),
                      'hash_refs': len(hash_rows), 'hash_mismatch': len(mismatched), 'code_drift': drift}))


def validate_launcher_spec(spec):
    """Run guarded_launcher.validate_spec in-process with a dummy verifier hash; check receipt bindings resolve."""
    import sys
    sys.path.insert(0, str(ROOT))
    from contributor_tools import guarded_launcher as gl
    dummy = json.loads(json.dumps(spec))
    placeholders = [k for k, v in dummy['bindings'].items() if not str(v).isalnum() or len(v) != 64]
    for k in placeholders:
        dummy['bindings'][k] = '0' * 64
    try:
        normalized = gl.validate_spec(dummy)
        valid, error = True, None
    except gl.SpecError as exc:
        normalized, valid, error = None, False, str(exc)
    receipts = {k: {'exists': (ROOT / k).exists(), 'matches': (ROOT / k).exists() and sha(ROOT / k) == v}
                for k, v in spec['bindings'].items() if k not in placeholders}
    return {'validate_spec_with_dummy_verifier_hash': 'pass' if valid else 'failed', 'error': error,
            'dummy_replaced_bindings': placeholders,
            'placeholder_disclosed': 'TO_BIND_AFTER_REVIEW kept in the spec; validate_spec rejects it as written, as intended',
            'normalized_cwd': rel(Path(normalized['cwd'])) if normalized else None,
            'receipt_bindings_from_repository_root': receipts,
            'all_receipt_bindings_match': all(r['matches'] for r in receipts.values()),
            'launcher_sha256': sha(ROOT / 'contributor_tools/guarded_launcher.py')}


def interpretation(r):
    """Claim status, acceptance assessment and the full-byte job spec (not run)."""
    disk = r['on_disk_stat']
    final_root = disk['final_outputs']['root']
    receipts = r['receipts_sha256']
    read_bytes = (disk['final_outputs']['bytes'] + disk['rebuild_outputs']['stair_bytes']
                  + disk['source_mat_bytes'] + disk['fileinfo_bytes'] + disk['stair_force_ik_bytes'])
    claims = [
        {'claim': 'All 335 blocks and 15,825 source views are reconstructed', 'evidence': 'rebuild summary, inventory, scope gate',
         'basis': 'receipt_exact', 'rests_on_unreviewed': ['inventory has no terminal status record (PM-02 needs_fresh_reviewed_plan)']},
        {'claim': 'Rebuild values agree with the source MAT to at most 1.8e-15 (79,665,196 finite values, tolerance 1e-8)',
         'evidence': 'pelvis-corrected full readback', 'basis': 'receipt_exact; bound to rebuild bytes, not to the final stair files',
         'rests_on_unreviewed': ['readback checker is not independently reviewed; it shares the producer\'s digest helper']},
        {'claim': 'Corrected right pelvis uses the left source clock; missing or conflicting overlap stays missing',
         'evidence': 'readback checker (pelvis expected from left clock; equal_nan comparison); preservation (6,842 right views changed)',
         'basis': 'receipt_exact (checker logic, not a separate count of missing samples)',
         'rests_on_unreviewed': ['no receipt counts the samples left missing by the overlap rule']},
        {'claim': 'Every unrelated column is exactly preserved by the pelvis fix',
         'evidence': 'preservation receipt (check_exact on all non-pelvis/segment columns; left views identical)',
         'basis': 'receipt_exact', 'rests_on_unreviewed': []},
        {'claim': 'Each of 764 stair windows exports exactly its recovered reference view, both legs retained',
         'evidence': 'correction summary identities reconciled here against recovery windows',
         'basis': 'receipt_exact for identities; value preservation of the 136 rewritten stair files rests on the producer self-check only',
         'rests_on_unreviewed': ['no independent readback of the 136 final stair files',
                                 'reference side follows the source force-threshold convention, not physical contact']},
        {'claim': 'No synthetic timing', 'evidence': 'readback: time_s equals the source clock resampled to 150 points; source event times copied from recovery',
         'basis': 'receipt_exact (rebuild); producer self-check (final stair event columns)', 'rests_on_unreviewed': []},
        {'claim': 'Final outputs still hold the recorded bytes', 'evidence': 'none current; recorded hashes date from 2026-10-21',
         'basis': 'not_rechecked', 'rests_on_unreviewed': ['needs the full-byte job below']},
        {'claim': 'Source MAT, FileInfo and stair .mot files still hold the recorded bytes',
         'evidence': 'sizes match; bytes not rehashed here', 'basis': 'not_rechecked',
         'rests_on_unreviewed': ['needs the full-byte job below']},
    ]
    acceptance = [
        {'criterion': 'All 335 blocks accounted for; corrected right pelvis uses left source clock with missing overlap preserved',
         'assessment': 'met_by_receipts', 'gap': 'Byte currency of outputs and sources not rechecked.'},
        {'criterion': 'Every unrelated column exactly preserved; no synthetic timing',
         'assessment': 'met_by_receipts_for_rebuild; stair files by producer self-check',
         'gap': 'Independent check that the 136 stair files equal the rebuild views they keep.'},
        {'criterion': 'Each of 764 stair windows exports exactly its recovered reference view, retaining both legs; dropped views have explicit lineage',
         'assessment': 'met_by_receipts', 'gap': 'Same as above for values; identities fully reconciled.'},
        {'criterion': 'Final source readback bound to final corrected hashes',
         'assessment': 'partly_met',
         'gap': ('Readback is bound to the rebuild hashes. 199 final outputs share those hashes; the 136 rewritten stair outputs '
                 'are bound only through the producer, which compared kept views to the rebuild with check_exact.')},
        {'criterion': 'Do not rerun verified full work merely because old queues stopped',
         'assessment': 'met', 'gap': 'No rerun proposed; only byte currency and the stair-file comparison remain.'},
        {'criterion': 'Scope-specific handoff for profile/limitations review and later release reconciliation',
         'assessment': 'handoff_written', 'gap': 'Profile, anatomy, force/COP lineage and release gates stay open.'},
    ]
    job = {
        'job_id': 'mb24-f01-full-byte-verify-20261031',
        'status': 'specified_not_written_not_run',
        'scheduling': 'PM-01, through the reviewed guarded launcher only after UM21-T02 is reviewed; one numerical worker; no native code.',
        'verifier_to_write': 'contributor_tools/verify_mblue_final_bytes.py (new; Linux Python only; pyarrow for stage 2)',
        'stages': [
            {'stage': 1, 'name': 'byte identity', 'reads': 'streaming SHA256, 1 MiB chunks, no parsing',
             'targets': [
                 f'335 final outputs under {final_root} against correction_summary.json outputs',
                 '136 rebuild stair outputs against the rebuild conversion_summary.json outputs',
                 '10 source MAT files against source_inventory.json sources[].sha256',
                 '10 FileInfo files against the rebuild records subject_info_sha256',
                 '40 matched stair force/IK .mot files against reference_recovery.json candidates'],
             'pass': 'every current hash equals its recorded hash; any mismatch stops stage 2 and is reported, never repaired'},
            {'stage': 2, 'name': 'independent stair-view comparison (136 blocks, 1,528 rebuild views, 764 final views)',
             'reads': 'one stair block at a time, 150-row batches',
             'targets': ['each final stair observation equals the rebuild observation with the same observation_id in every rebuild column (exact)',
                         'the final file holds exactly the retained identities in correction_summary.json and none of the omitted ones',
                         'source_event_start/end_time_s and bases equal the recovery window values',
                         'every row has 150 samples and time_s is unchanged',
                         ('per right treadmill view (140 blocks): from the source time_l/time_r clocks, list the right views whose '
                          'clock window has no left-clock overlap; check that pelvis and derived segment columns are missing exactly '
                          'where no overlap exists, and compare the list with the 4 views the pelvis fix left unchanged '
                          '(AB04/exo/decline_10deg, AB05/bare/decline_5deg, AB11/bare/incline_10deg)')],
             'pass': 'all 764 kept views exact; 764 omitted views absent; the no-overlap list explains the 4 unchanged views or is reported as an open anomaly'}],
        'estimated_read_bytes': read_bytes,
        'launcher_spec': {
            'job_id': 'mb24-f01-full-byte-verify-20261031',
            'command': ['python3', 'contributor_tools/verify_mblue_final_bytes.py',
                        '--correction', 'converted_datasets/reconversion_v2/mblue_reference_corrected_full_20261021/correction_summary.json',
                        '--rebuild', 'converted_datasets/reconversion_v2/mblue_pelvis_corrected_full_20261021/conversion_summary.json',
                        '--inventory', 'converted_datasets/reconversion_v2/mblue_source_inventory_20261021/source_inventory.json',
                        '--recovery', 'converted_datasets/reconversion_v2/mblue_stair_reference_review_v3_20261021/reference_recovery.json',
                        '--output', 'converted_datasets/reconversion_v2/mb24_f01_full_byte_verify_20261031'],
            'output_root': 'converted_datasets/reconversion_v2/mb24_f01_full_byte_verify_20261031',
            'receipt_path': 'converted_datasets/reconversion_v2/mb24_f01_full_byte_verify_20261031.receipt.json',
            'bindings': {
                'contributor_tools/verify_mblue_final_bytes.py': 'TO_BIND_AFTER_REVIEW (script not yet written)',
                'converted_datasets/reconversion_v2/' + R['correction']: receipts[R['correction']],
                'converted_datasets/reconversion_v2/' + R['rebuild']: receipts[R['rebuild']],
                'converted_datasets/reconversion_v2/' + R['inventory']: receipts[R['inventory']],
                'converted_datasets/reconversion_v2/' + R['recovery']: receipts[R['recovery']]},
            'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'address_space_mib': 768,
            'expected_output_names': ['byte_identity.json', 'stair_view_comparison.json'],
            'disk_admission': [{'path': 'converted_datasets/reconversion_v2', 'min_free_mib': 5120}]},
        'notes': [
            'Binding keys are repository-root relative (the launcher hashes them against cwd, which defaults to the repository root); the four receipt keys carry the converted_datasets/reconversion_v2/ prefix and their hashes equal the current files (spec_validation).',
            'The verifier binding is TO_BIND_AFTER_REVIEW: the script is not written, so this spec cannot launch until its reviewed hash replaces the placeholder.',
            'Stage 1 needs no pyarrow. Stage 2 reads the 136 stair files of each set plus, for the overlap target, the 140 rebuild treadmill outputs and the source clocks.',
            'Stage 2 imports pyarrow under the 768 MiB address-space cap; that import hung without single-thread settings in the reviewer test. It must run through the launcher, whose default thread_env sets OPENBLAS/OMP/MKL/ARROW/NUMEXPR_NUM_THREADS=1, and the pilot must confirm it.',
            'The verifier must not import contributor_tools.common.data_contract (changed in the working tree since the rebuild).',
            'A pilot of the same bound code on one treadmill and one stair block is required before the full run (AGENTS.md).'],
    }
    job['spec_validation'] = validate_launcher_spec(job['launcher_spec'])
    remaining = [
        'Run the full-byte job (stage 1 byte identity, stage 2 independent stair-view comparison) under PM-01 after the launcher review; pilot first.',
        'Source inventory has no terminal status record; its source hashes were re-established by the readback (which re-hashes each source MAT), but the inventory run itself is unreviewed.',
        'Docs audits mblue-pelvis-clock-fix.json and mblue-stair-reference.json still say the full rebuild/correction is queued; both completed on 2026-10-21. Owner of docs/quality/audits should mark them superseded by this reconciliation.',
        'docs audit mblue-complete-source-readback.json describes the pre-fix baseline (two partial readbacks, different checker versions); it is superseded for pelvis and segment columns.',
        'contributor_tools/common/data_contract.py differs from the version bound to the rebuild (the bound version equals git HEAD). Existing outputs are unaffected; any rerun must bind the current file.',
        'Not checked: 4 right treadmill views in 3 blocks (AB04/exo/decline_10deg, AB05/bare/decline_5deg, AB11/bare/incline_10deg) were unchanged by the pelvis fix. They occur only in blocks with at least 2 more right than left cycles (3 of 7 such blocks; none in the other 133), consistent with right cycles that have no left-clock overlap. The receipts cannot establish this; stage 2 of the full-byte job lists no-overlap views per view.',
        'Not reconciled here: anatomical/model orientation, force/COP source lineage, raw event exclusions, the planar relabel gate, profile/limitations review and release reconciliation.',
    ]
    return {'claims': claims, 'acceptance_assessment': acceptance, 'full_byte_verification_job': job,
            'remaining': remaining,
            'limitations': ['Receipts, recorded hashes and file stats only; no scientific value was reread.',
                            'Agreement among receipts written by the same pipeline is not independent of that pipeline.',
                            'completed_unreviewed and pass here are not scientific approval.']}


if __name__ == '__main__':
    main()
