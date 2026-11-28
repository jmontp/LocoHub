"""CORE-11: effect of the publication rule on the GT21 pilot, from stored evidence only.

Reads docs/quality/audits/core04-gt21-pilot-probe.json (no research data) and recombines each stored
leg-channel with ``sign_application.guard_apply`` and ``publication_rule``, taking audited signs from
the committed table contributor_tools/common/audited_signs.json exactly as the hook does
(``load_audited_signs`` against docs/maintainers/backlog.json). Two scenarios: the backlog as it stands,
and the backlog after its audit-task records cite every GT21 table entry (link check assumed). The
probe's ``truth`` is used only to count published signs that disagree with it. Prints JSON. Pelvis
tilt was not tested in the pilot and is absent.
"""
import collections
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'docs/quality/audits/core04-gt21-pilot-probe.json'


def _hook():
    # by path: the contributor_tools.common package __init__ imports pandas
    spec = importlib.util.spec_from_file_location('core11_sign_application', ROOT / 'contributor_tools/common/sign_application.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def effect(probe, assume_linked=False):
    sa = _hook()
    policy, _ = sa._load_policy()
    backlog = sa.BACKLOG_PATH
    records = {t['id']: t for t in json.loads(backlog.read_text())['tasks']}
    table = json.loads(sa.AUDITED_PATH.read_text())
    task_done = lambda t: policy.task_done(t, backlog)
    entries, _, _ = sa.load_audited_signs('GT21', table, records, task_done)
    if assume_linked:
        entries = {k: {**e, 'verified': all(task_done(t)[0] for t in e['audit_tasks'])} for k, e in entries.items()}
    params = probe['detector_parameters']
    rows = []
    for r in probe['records']:
        if 'skipped' in r:
            continue
        for ch, c in r['channels'].items():
            applied = c['verdict'] == 'apply' and sa.guard_apply(c, params['min_families'], params['family_grouping'])[0]
            e = entries.get(ch)
            audit = e['sign'] if e and e['verified'] else None
            mult, basis, publication, hold = sa.publication_rule(c['verdict'], c['sign'], applied, audit)
            rows.append({'leg': f"{r['subject']} {r['condition']} {r['side']}", 'channel': ch, 'verdict': c['verdict'],
                         'detector_applied': applied, 'publication': publication, 'basis': basis, 'hold': hold,
                         'published_sign_matches_truth': None if publication == 'hold' else mult == c['truth']})
    non_applied = [x for x in rows if not x['detector_applied']]
    return {
        'scenario': ('every listed audit task (GT21-C01, CORE-04) cites every GT21 entry id (requested)' if assume_linked else 'backlog as it stands'),
        'gt21_entries_verified': sorted(k for k, e in entries.items() if e['verified']),
        'leg_channels': len(rows),
        'detector_applied': sum(x['detector_applied'] for x in rows),
        'guard_refused_stored_applies': sum(x['verdict'] == 'apply' and not x['detector_applied'] for x in rows),
        'non_applied': len(non_applied),
        'non_applied_published': sum(x['publication'] == 'publish' for x in non_applied),
        'non_applied_held': sum(x['publication'] == 'hold' for x in non_applied),
        'non_applied_by_channel_and_publication': {f'{ch} / {p}': n for (ch, p), n in sorted(collections.Counter(
            (x['channel'], x['publication']) for x in non_applied).items())},
        'held_reasons': dict(collections.Counter(x['hold'] for x in rows if x['publication'] == 'hold')),
        'published_sign_disagrees_with_probe_truth': sum(x['published_sign_matches_truth'] is False for x in rows)}


def main():
    probe = json.loads(PROBE.read_text())
    print(json.dumps({'source': str(PROBE.relative_to(ROOT)),
                      'scenarios': [effect(probe), effect(probe, assume_linked=True)]}, indent=1))


if __name__ == '__main__':
    main()
