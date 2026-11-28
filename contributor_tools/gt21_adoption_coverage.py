"""Strict set audit of independently prepared GT21 source-pair evidence.

This pure helper does not derive evidence from source files. A caller must bind
its input ledger to source hashes, independently enumerate windows, and verify
output hashes. Passing this gate alone is not source or force/COP verification.
"""
import math


def pair_key(row):
    side, start, end = row['side'], row['start_s'], row['end_s']
    if side not in ('left','right') or not all(isinstance(x,(float,int)) and not isinstance(x,bool)
            and math.isfinite(x) for x in (start,end)) or end <= start:
        raise ValueError('Invalid source pair identity')
    return side, start, end


def source_exclusion(row):
    windows = row['matching_windows']
    counts = [row[k] for k in ('source_cycle_samples','source_ik_samples','source_id_samples')]
    if not isinstance(windows,int) or isinstance(windows,bool) or windows < 0:
        raise ValueError('Invalid window count')
    if any(not isinstance(n,int) or isinstance(n,bool) or n < 0 for n in counts):
        raise ValueError('Invalid sample counts')
    phase = row['maximum_source_phase']
    if not isinstance(phase,(float,int)) or isinstance(phase,bool) or not math.isfinite(phase) or not 0 <= phase <= 100:
        raise ValueError('Invalid source phase evidence')
    if windows == 0: return 'outside_complete_eligible_task_window'
    if windows > 1: raise ValueError('Ambiguous task windows require reconciliation')
    if counts[0] < 10 or phase < 50: return 'source_cycle_fails_sample_or_phase_rule'
    if min(counts[1:]) < 10: return 'insufficient_source_ik_or_id_samples'
    return None


def audit_complete_pairs(source_pairs, output_pairs):
    expected, known, excluded = set(), set(), []
    for row in source_pairs:
        key = pair_key(row)
        if key in known: raise ValueError('Duplicate source pair')
        known.add(key)
        reason = source_exclusion(row)
        if reason is None: expected.add(key)
        else: excluded.append({'side':key[0],'start_s':key[1],'end_s':key[2],'reason':reason})
    if not known: raise ValueError('Empty source evidence')
    actual = set()
    for row in output_pairs:
        key = pair_key(row)
        if key in actual: raise ValueError('Duplicate output pair')
        actual.add(key)
    if actual != expected:
        raise ValueError(f'Incomplete or unsupported recovery: missing={sorted(expected-actual)}, unexpected={sorted(actual-expected)}')
    return {'eligible_pairs':len(expected),'exported_pairs':len(actual),'exclusions':excluded,
        'scientific_approval':False,'force_cop_checked':False}


def label_segments(clock, labels, target, minimum_samples=50):
    """Proposed per-region rule for review; NOT the adopted converter policy."""
    if len(clock) != len(labels) or not clock or any(not isinstance(x,(float,int))
            or isinstance(x,bool) or not math.isfinite(x) for x in clock):
        raise ValueError('Invalid condition clock')
    if any(b <= a for a,b in zip(clock,clock[1:])):
        raise ValueError('Condition clock must strictly increase')
    if not isinstance(minimum_samples,int) or isinstance(minimum_samples,bool) or minimum_samples < 1:
        raise ValueError('Invalid per-region minimum')
    result=[]; start=None
    for index in range(len(labels)+1):
        hit=index<len(labels) and labels[index]==target
        if hit and start is None: start=index
        if not hit and start is not None:
            end=index-1
            if end-start+1 >= minimum_samples and clock[end]-clock[start] > .05:
                result.append((clock[start],clock[end]))
            start=None
    return result
