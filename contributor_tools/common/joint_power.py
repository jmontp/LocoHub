"""Joint power as moment x joint angular velocity (decision D-REF-5, docs/reference/index.md, "Signs and frames").

LocoHub computes sagittal joint power from the published joint moment and its own joint angular velocity, both in the
LocoHub sign convention (moment positive in the named direction: hip flexor, knee flexor, ankle dorsiflexor; velocity
positive in the same direction). Source power values are not carried over. This module is dataset independent: a dataset
adapter names, for each power column, the moment column and the velocity (one column, or a signed sum of columns such as
thigh velocity minus pelvis velocity for the hip). The release-package builder calls recompute() through Part.transform.

Rules:
  * power is missing wherever the moment or the velocity is missing (not finite); nothing is filled;
  * held CoP or held angle columns do not hold power on their own: power is missing only because a velocity is missing;
  * arithmetic is float64: power = moment * velocity, where velocity = sum(sign * column) in the order given.

Only numpy and pyarrow are used (no pandas), so the module fits the 768 MiB address-space cap.
"""
from __future__ import annotations

import collections
import dataclasses
import json
from typing import Callable, Iterable, Optional

import numpy as np


@dataclasses.dataclass(frozen=True)
class PowerSpec:
    """One recomputed column: power = moment * sum(sign * velocity column)."""
    power: str
    moment: str
    velocity: tuple  # ((column, +1 or -1), ...)

    def inputs(self):
        return (self.moment, *[c for c, _ in self.velocity])


def _col(table, name):
    return table.column(name).to_numpy(zero_copy_only=False).astype(np.float64, copy=False)


def joint_velocity(table, spec):
    v = None
    for name, sign in spec.velocity:
        x = _col(table, name)
        x = x if sign == 1 else -x
        v = x if v is None else v + x
    return v


def power_from(moment, velocity):
    """moment * velocity where both are finite, NaN elsewhere."""
    ok = np.isfinite(moment) & np.isfinite(velocity)
    out = np.full(moment.shape, np.nan)
    out[ok] = moment[ok] * velocity[ok]
    return out, ok


class GapStats:
    """Per observation and per power column: the gap between the source power and moment x velocity, accumulated over batches.

    The normalised RMS difference of one observation is sqrt(sum (source - new)^2 / sum new^2) over the rows where the source
    power and the new power are both finite (the RMS of the difference over the RMS of the new power).
    """

    def __init__(self):
        # (power column, key) -> [rows both finite, sum d2, sum new2, sum src2, rows source finite, rows new finite]
        self.acc = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0, 0])
        self.rows_total = 0

    def add(self, spec, keys_runs, src, new):
        for key, a, b in keys_runs:
            s, n = src[a:b], new[a:b]
            fs, fn = np.isfinite(s), np.isfinite(n)
            both = fs & fn
            r = self.acc[(spec.power, key)]
            d = s[both] - n[both]
            r[0] += int(both.sum()); r[1] += float(np.sum(d * d)); r[2] += float(np.sum(n[both] ** 2))
            r[3] += float(np.sum(s[both] ** 2)); r[4] += int(fs.sum()); r[5] += int(fn.sum())

    def summary(self):
        """{power column: statistics over observations}."""
        by = collections.defaultdict(list)
        for (col, key), r in self.acc.items():
            by[col].append(r)
        out = {}
        for col, rs in sorted(by.items()):
            nr = [np.sqrt(r[1] / r[2]) for r in rs if r[0] > 0 and r[2] > 0]
            tot = [sum(r[i] for r in rs) for i in range(6)]
            out[col] = {
                "observations": len(rs), "observations_compared": len(nr),
                "median_nrms": float(np.median(nr)) if nr else None,
                "p90_nrms": float(np.percentile(nr, 90)) if nr else None,
                "pooled_nrms": float(np.sqrt(tot[1] / tot[2])) if tot[2] > 0 else None,
                "rows_both_finite": int(tot[0]), "rows_source_finite": int(tot[4]), "rows_new_finite": int(tot[5]),
                "rows_source_only_finite": int(tot[4] - tot[0]), "rows_new_only_finite": int(tot[5] - tot[0]),
                "observations_source_finite_new_all_missing": sum(1 for r in rs if r[4] > 0 and r[5] == 0),
                "observations_source_all_missing_new_finite": sum(1 for r in rs if r[4] == 0 and r[5] > 0),
            }
        return out


def runs_of(table):
    """[(key, start, end)] of consecutive rows with the same (observation_id, reference_side)."""
    oids = table.column("observation_id").to_pylist()
    sides = table.column("reference_side").to_pylist()
    runs, i, n = [], 0, len(oids)
    while i < n:
        j = i + 1
        while j < n and oids[j] == oids[i] and sides[j] == sides[i]:
            j += 1
        runs.append(((oids[i], sides[i]), i, j))
        i = j
    return runs


def recompute(table, specs, stats: Optional[GapStats] = None):
    """The table with every spec's power column replaced by moment x joint velocity (float64, NaN where missing).
    A column keeps its Arrow type and name; a null in the source stays a null only if it was null where the result is missing."""
    import pyarrow as pa
    runs = runs_of(table) if stats is not None else None
    for spec in specs:
        idx = table.schema.get_field_index(spec.power)
        if idx < 0:
            raise KeyError(spec.power)
        src = _col(table, spec.power)
        new, _ = power_from(_col(table, spec.moment), joint_velocity(table, spec))
        if stats is not None:
            stats.add(spec, runs, src, new)
        field = table.schema.field(idx)
        arr = pa.array(new, type=field.type)  # NaN stays NaN (not null)
        table = table.set_column(idx, field, arr)
    if stats is not None:
        stats.rows_total += table.num_rows
    return table


# ------------------------------------------------------------------ per-observation presence (assessment bookkeeping)
def scan_presence(path, specs, skip_recordings=frozenset(), expect_recordings=None, batch_rows=3000):
    """{(observation_id, reference_side): {power column: True if any row has a finite new power}} for one table file.
    Reads only the identity and the input columns, in batches, with Arrow threads off."""
    import pyarrow.parquet as pq
    need = ["observation_id", "reference_side", "source_recording_id"]
    for s in specs:
        need += [c for c in (s.power, *s.inputs()) if c not in need]
    out = {}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        cols = [f.name for f in pf.schema_arrow if f.name in need]
        for b in pf.iter_batches(batch_size=batch_rows, columns=cols, use_threads=False):
            import pyarrow as pa
            t = pa.Table.from_batches([b])
            recs = t.column("source_recording_id").to_pylist()
            for key, a, e in runs_of(t):
                if recs[a] in skip_recordings:
                    continue
                d = out.setdefault(key, {s.power: False for s in specs})
                sl = t.slice(a, e - a)
                for s in specs:
                    if not d[s.power]:
                        _, ok = power_from(_col(sl, s.moment), joint_velocity(sl, s))
                        d[s.power] = bool(ok.any())
    return out


def merge_presence(parts):
    """Union of several per-file presence maps (True wins)."""
    out = {}
    for p in parts:
        for key, d in p.items():
            o = out.setdefault(key, {})
            for c, v in d.items():
                o[c] = o.get(c, False) or v
    return out


def adjust_held(held, presence, power_columns, missing_reason, obsolete: Callable[[str], bool] = lambda r: False):
    """Held-signal dict of one observation after power is recomputed.
    A power column with a finite new value somewhere is no longer held. A power column that is missing throughout keeps its
    reason, unless it had none or the reason is obsolete (it described the source power); then missing_reason is the reason.
    Other columns are unchanged. Returns a new dict."""
    out = dict(held)
    for c in power_columns:
        if presence.get(c):
            out.pop(c, None)
        elif c not in out or obsolete(out[c]):
            out[c] = missing_reason
    return out


def adjust_states(states, presence, power_columns, present_state, missing_state):
    """Channel states of one observation after power is recomputed: a power column with a finite new value is in
    present_state, one that is missing throughout is in missing_state. Returns a new dict (lists)."""
    out = {k: [c for c in v if c not in power_columns] for k, v in states.items()}
    for c in power_columns:
        out.setdefault(present_state if presence.get(c) else missing_state, []).append(c)
    return {k: v for k, v in out.items() if v}


def rewrite_held_column(table, power_columns, presence_by_key, missing_reason, dump: Callable[[dict], str],
                        obsolete: Callable[[str], bool] = lambda r: False):
    """Table with held_signals rewritten per observation by adjust_held (same dump format as the source). A row whose held
    text does not change keeps its exact source string. The column keeps its Arrow type."""
    import pyarrow as pa
    idx = table.schema.get_field_index("held_signals")
    field = table.schema.field(idx)
    texts = table.column("held_signals").to_pylist()
    new = list(texts)
    changed = False
    for key, a, b in runs_of(table):
        pres = presence_by_key.get(key)
        if pres is None:
            raise KeyError(f"no power presence for {key}")
        old = json.loads(texts[a]) if texts[a] else {}
        adj = adjust_held(old, pres, power_columns, missing_reason, obsolete)
        if adj != old:
            t = dump(adj)
            for i in range(a, b):
                new[i] = t
            changed = True
    if not changed:
        return table
    arr = pa.array(new, type=pa.string())
    arr = arr.dictionary_encode().cast(field.type) if pa.types.is_dictionary(field.type) else arr
    return table.set_column(idx, field, arr)
