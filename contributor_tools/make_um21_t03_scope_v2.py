"""UM21-T03 scope v2 (standard library, small JSON only): keep batches 0..keep-1 of the v1 scope exactly as they
ran and re-partition the remaining records into one batch per subject, in baseline order. The runner
run_um21_t03_full.py is unchanged and reads this file through the same schema."""
import argparse
import hashlib
import json
from pathlib import Path


def repartition(v1, keep, v1_sha256, invalid_note):
    batches = [list(b) for b in v1['batches']]
    head, rest = batches[:keep], [r for b in batches[keep:] for r in b]
    order = []
    for record in rest:
        subject = record.split('/')[0]
        if not order or order[-1][0] != subject:
            order.append((subject, []))
        order[-1][1].append(record)
    tail = [records for _, records in order]
    if [r for b in head + tail for r in b] != [r for b in batches for r in b]:
        raise ValueError('re-partition changed membership or order')
    return {**v1, 'schema': v1['schema'], 'version': 2, 'supersedes_scope_sha256': v1_sha256,
            'batches': head + tail, 'batch_history': {'unchanged_batches': list(range(keep)),
            'repartitioned_batches_from': keep, 'rule': 'one batch per subject in baseline order', 'invalid': invalid_note}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--v1', type=Path, required=True)
    p.add_argument('--keep', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    v1 = json.loads(a.v1.read_text())
    note = ('v1 batch 2 (AB06 d10 .. AB08 d10) failed with ENOMEM under the 768 MiB address-space cap after 5 records; '
            'its output root is invalid and is not reused')
    scope = repartition(v1, a.keep, hashlib.sha256(a.v1.read_bytes()).hexdigest(), note)
    with a.out.open('x') as f:
        json.dump(scope, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
