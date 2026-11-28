"""GT23-M01 mass step: pure functions (no file access).

What this module decides, from José's answers D-GT23-C05-2 and D-GT23-C05-3 (23 Nov 2026):

* Exactly the recordings the hash-bound C05 audit puts in class ``lower_confident`` (52) have their per-kg moments and
  powers multiplied by (mass used / own mass). ``mass used`` is the audit's policy-T divisor: the exact divisor for 7
  recordings (local N*m inverse dynamics) and the README-table mass nearest the force-plate estimate for 45.
* Every other recording keeps the published values, with a note: ``own_mass_confirmed`` (class ``own_mass_only``) or
  ``cannot_be_told``.
* Masses are never refit by error minimisation; the factor is a ratio of two listed masses.
* Body-weight forces use the publisher's README mass table (AB03 = 113.5 kg), never the local rebuilt table.
"""
import re

import numpy as np

G = 9.80665
FACTOR_AUDIT_TOLERANCE = 5e-5        # the audit prints factors to four decimals
RESCALE_CLASS = 'lower_confident'
OWN_CONFIRMED_CLASS = 'own_mass_only'
UNITS = {'moment': 'Nm_kg', 'power': 'W_kg', 'force': 'BW'}
NOTES = {
    'rescaled': 'Per-kg moments and powers multiplied by (mass used / own mass); the publisher divided by another listed mass.',
    'own_mass_confirmed': 'Published per-kg values are consistent with the participant\'s own mass only; kept as published.',
    'cannot_be_told': 'The mass the publisher divided by cannot be told for this recording; kept as published.',
}
README_NOTE = ('The publisher README lists joint moments in N*m and powers in W, but the published values are already per '
               'kilogram; they are labelled Nm_kg and W_kg here and are not divided by mass again.')


class MassError(RuntimeError):
    pass


def parse_readme_masses(text):
    """``AB03: 113.5 kg`` lines of the publisher README -> {subject: kg}; fails if not exactly twelve."""
    table = {m.group(1): float(m.group(2)) for m in re.finditer(r'^(AB\d\d):\s*([0-9.]+)\s*kg\s*$', text, re.M)}
    if len(table) != 12:
        raise MassError(f'README mass table has {len(table)} entries, expected 12')
    return table


def build_plan(trials, masses):
    """Per-recording plan from the C05 audit trials and the README masses.

    Returns {(subject, recording): entry}; entry has action ('rescale' or 'keep'), own_mass_kg, mass_used_kg (None when kept),
    factor (None when kept), how ('exact' / 'estimated' / None), note and the audit facts kept as provenance.
    """
    table_values = sorted(set(masses.values()))
    plan = {}
    for t in trials:
        key = (t['subject'], t['task'])
        if key in plan:
            raise MassError(f'duplicate recording {key}')
        own = masses[t['subject']]
        if abs(t['own_mass_kg'] - own) > 1e-9:
            raise MassError(f'{key}: audit own mass {t["own_mass_kg"]} differs from README {own}')
        entry = {'subject': t['subject'], 'recording': t['task'], 'audit_class': t['class'], 'own_mass_kg': own,
                 'mass_used_kg': None, 'factor': None, 'how': None}
        if t['class'] == RESCALE_CLASS:
            used = t['policy_T']['divisor_kg']
            if used not in table_values:
                raise MassError(f'{key}: mass used {used} is not a README table mass')
            factor = used / own
            if abs(factor - t['policy_T']['factor']) > FACTOR_AUDIT_TOLERANCE:
                raise MassError(f'{key}: factor {factor} differs from the audit {t["policy_T"]["factor"]}')
            how = 'exact' if t['tier'] == 'exact' else 'estimated'
            if how == 'estimated' and t['tier'] != 'validated_gait':
                raise MassError(f'{key}: unexpected tier {t["tier"]}')
            entry.update(action='rescale', mass_used_kg=used, factor=factor, how=how, note=NOTES['rescaled'])
            entry['audit_provenance'] = {k: t.get(k) for k in ('tier', 'lever_kg', 'second_kg', 'loaded_sample_kg', 'rerun_slope_kg',
                                                              'interval_kg', 'plausible_divisors_kg', 'plausible_owners',
                                                              'gait_stances')}
        else:
            note = 'own_mass_confirmed' if t['class'] == OWN_CONFIRMED_CLASS else 'cannot_be_told'
            entry.update(action='keep', note_key=note, note=NOTES[note])
        plan[key] = entry
    return plan


def plan_counts(plan):
    rescaled = [e for e in plan.values() if e['action'] == 'rescale']
    return {'recordings': len(plan), 'rescaled': len(rescaled), 'kept': len(plan) - len(rescaled),
            'rescaled_exact': sum(e['how'] == 'exact' for e in rescaled),
            'rescaled_estimated': sum(e['how'] == 'estimated' for e in rescaled),
            'kept_own_mass_confirmed': sum(e.get('note_key') == 'own_mass_confirmed' for e in plan.values()),
            'kept_cannot_be_told': sum(e.get('note_key') == 'cannot_be_told' for e in plan.values())}


def scale(values, factor):
    """Multiply by the factor; with no factor the same array is returned unchanged."""
    return values if factor is None else values * factor


def to_body_weights(force_n, mass_kg):
    return force_n / (mass_kg * G)


def power_consistency(moment, power, speed, sign):
    """How well power = moment x (sign x speed) holds: least-squares slope through the origin, correlation, residual.

    Finite samples only. ``sign`` converts our speed (flexion / dorsiflexion positive) to the published coordinate.
    """
    x = moment * sign * speed
    ok = np.isfinite(x) & np.isfinite(power)
    out = {'n': int(ok.sum())}
    if ok.sum() < 10 or not np.any(x[ok] != 0):
        return out
    xo, po = x[ok], power[ok]
    out['slope'] = float(xo @ po / (xo @ xo))
    if np.std(xo) > 0 and np.std(po) > 0:
        out['r'] = float(np.corrcoef(xo, po)[0, 1])
    out['rms_power'] = float(np.sqrt(np.mean(po ** 2)))
    out['rms_residual'] = float(np.sqrt(np.mean((po - xo) ** 2)))
    return out


def nm_check(per_kg, inverse_dynamics_nm, mass_kg):
    """Compare per-kg values x mass with N*m inverse dynamics: max abs difference and the least-squares implied mass."""
    ok = np.isfinite(per_kg) & np.isfinite(inverse_dynamics_nm)
    if not ok.any():
        return {'n': 0}
    a, b = per_kg[ok], inverse_dynamics_nm[ok]
    d = np.abs(a * mass_kg - b)
    out = {'n': int(ok.sum()), 'max_abs_nm': float(np.max(d)), 'rms_abs_nm': float(np.sqrt(np.mean(d ** 2))),
           'peak_inverse_dynamics_nm': float(np.max(np.abs(b)))}
    if np.any(a != 0):
        out['implied_mass_kg'] = float(a @ b / (a @ a))
    return out
