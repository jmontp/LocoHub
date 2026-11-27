"""Foot-flat zero (CORE-FOOT-01, decision D-REF-6 = A): per-person foot-angle offset and its application.

In mid-stance the foot lies flat on the surface, so on level ground the foot angle should read 0. Each person's offset is the
median, over that person's matched level-walking strides, of the per-stride median foot angle over 20-35 percent of the stride
(ipsilateral foot, the filtered phase table of the previous package). The offset is a constant per person and dataset.

What changes (and nothing else):
  foot_sagittal_angle_<side>_rad          := foot - offset
  ankle_dorsiflexion_angle_<side>_rad     := ankle - offset            (ankle = foot - shank, so this keeps the composition)
  cop_anterior_<side>_m, cop_vertical_<side>_m := the foot-frame point rotated by the offset inside the leg plane
  cop_lateral_*, every other angle, velocity, moment, power, force, identity and time column stay as they were.

Centre-of-pressure sign. All three datasets build the point the same way (gt23_conventions.foot_frame_point,
gt21_rb_pass.foot_frame_point, run_um21_s02_frame.foot_frame_point): with the leg-plane forward axis f and up axis u,
e_f = cos(th) f + sin(th) u and e_u = -sin(th) f + cos(th) u, anterior = q.e_f - 0.1 m, vertical = q.e_u, for the same foot
angle th that is stored. With a = anterior + 0.1 and v = vertical, (a, v) = R(-th) (q.f, q.u). Replacing th by th - d gives
a' = a cos d - v sin d and v' = a sin d + v cos d (a counterclockwise rotation of (a, v) by +d, d = offset in radians);
lateral = q.e_r does not depend on th. rotate_cop() below is exactly this, and the unit tests recompute samples with each
dataset's own foot-frame function at the shifted angle.

This module needs only numpy (pyarrow is imported lazily); it is loaded by path so that it adds no memory to a capped build.
"""
from __future__ import annotations

import json
import math

import numpy as np

FOOT_ORIGIN_M = 0.1
N = 150
PHASE = np.linspace(0.0, 100.0, N)
MID = (PHASE >= 20.0) & (PHASE <= 35.0)
MID_PERCENT = (20.0, 35.0)
# Coarse limits of the three assessments (identical numbers in GT23-Q01, GT21-Q01 and UM21-Q01)
L1_ANKLE_DEG = (-80.0, 50.0)
L5_BOUNDS_M = {"cop_anterior": (-0.5, 0.5), "cop_vertical": (-0.3, 0.3)}
L2_JUMP_DEG = 30.0
# Channel-state words differ between the assessments (GT21 says passed/failed/missing); each adapter passes its own vocabulary.
VOCAB_GT23 = {"fail": "fail", "pass_ankle": "pass_offset_unverified", "pass_cop": "pass",
              "checked": ("pass", "fail", "pass_offset_unverified")}
VOCAB_GT21 = {"fail": "failed", "pass_ankle": "passed", "pass_cop": "passed", "checked": ("passed", "failed")}
VOCAB_UM21 = {"fail": "fail", "pass_ankle": "pass", "pass_cop": "pass", "checked": ("pass", "fail")}


def checked_columns(entry, vocab, limits):
    """Columns of one existing assessment entry that were checked with L1 (ankle) or L5 (CoP) and are in `limits`."""
    import sys
    out = []
    for st, cols in entry["channel_states"].items():
        if st in vocab["checked"]:
            out += [sys.intern(c) for c in cols if limit_of(c) in limits]
    return sorted(out)


# ------------------------------------------------------------------ offsets
def stride_median_rad(foot_rad_150):
    """Median foot angle over 20-35 percent of one stride (NaN if no finite sample there)."""
    v = np.asarray(foot_rad_150, dtype=float)[MID]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def person_offsets(strides):
    """strides: iterable of (subject, observation_id, foot_rad_150). Returns {subject: {offset_rad, offset_deg, n_strides,
    stride_medians_deg: [[observation_id, deg], ...]}}; a subject with no finite stride median is absent."""
    per = {}
    for subject, oid, foot in strides:
        m = stride_median_rad(foot)
        if math.isfinite(m):
            per.setdefault(subject, []).append((oid, m))
    out = {}
    for s, v in sorted(per.items()):
        off = float(np.median([m for _, m in v]))
        out[s] = {"offset_rad": off, "offset_deg": math.degrees(off), "n_strides": len(v),
                  "stride_median_deg_min": math.degrees(min(m for _, m in v)),
                  "stride_median_deg_max": math.degrees(max(m for _, m in v)),
                  "stride_medians_deg": [[o, math.degrees(m)] for o, m in v]}
    return out


def load_offsets(path, dataset):
    """{subject: offset_rad} from docs/quality/audits/foot-flat-offsets.json (people without an offset are absent)."""
    d = json.loads(open(path).read())["datasets"][dataset]
    return {s: float(v["offset_rad"]) for s, v in d["people"].items() if v.get("offset_rad") is not None}


# ------------------------------------------------------------------ the shift
def rotate_cop(anterior, vertical, offset_rad):
    """Foot-frame (anterior, vertical) after the foot angle changed by -offset_rad (see the module docstring).
    Arrays or scalars; the 0.1 m origin is undone before and reapplied after the rotation."""
    a = np.asarray(anterior, dtype=float) + FOOT_ORIGIN_M
    v = np.asarray(vertical, dtype=float)
    c, s = np.cos(offset_rad), np.sin(offset_rad)
    return a * c - v * s - FOOT_ORIGIN_M, a * s + v * c


def column_plan(names):
    """(foot columns, ankle columns, [(cop_anterior, cop_vertical)]) present in a table."""
    names = list(names)
    foot = [n for n in names if n.startswith("foot_sagittal_angle_") and n.endswith("_rad")]
    ankle = [n for n in names if n.startswith("ankle_dorsiflexion_angle_") and n.endswith("_rad")]
    cop = []
    for n in names:
        if n.startswith("cop_anterior_") and n.endswith("_m"):
            v = "cop_vertical_" + n[len("cop_anterior_"):]
            if v in names:
                cop.append((n, v))
    return foot, ankle, cop


def changed_columns(names):
    foot, ankle, cop = column_plan(names)
    return foot + ankle + [c for pair in cop for c in pair]


def _values(col):
    """(float64 values with NaN, null mask or None) of a pyarrow column; arrow nulls are kept as nulls on the way back."""
    arr = col.combine_chunks() if hasattr(col, "combine_chunks") else col
    mask = arr.is_null().to_numpy(zero_copy_only=False)
    vals = np.array(arr.to_numpy(zero_copy_only=False), dtype=float)
    return vals, (mask if mask.any() else None), arr.type


def _put(t, name, new, mask, typ):
    import pyarrow as pa
    i = t.schema.get_field_index(name)
    return t.set_column(i, t.schema.field(i), pa.array(new, type=typ, mask=mask))


class FootFlat:
    """Part.transform: applies the per-person offset to one pyarrow table (same schema out). Counters are kept for evidence."""

    def __init__(self, offsets_rad):
        self.off = {k: float(v) for k, v in offsets_rad.items()}
        self.rows = 0
        self.rows_shifted = 0
        self.rows_by_subject = {}
        self.cop_partial_rows = 0          # one of anterior/vertical finite, the other not: left unchanged
        self.cop_rotated_samples = 0
        self.cop_rotated_beyond_l5 = 0     # rotated samples outside the coarse CoP limits (reported, not masked)
        self.subjects_seen = set()

    def __call__(self, t):
        subj = t.column("subject").to_pylist()
        self.rows += t.num_rows
        self.subjects_seen.update(set(subj))
        off = np.array([self.off.get(s, 0.0) for s in subj], dtype=float)
        act = off != 0.0
        if not act.any():
            return t
        self.rows_shifted += int(act.sum())
        for s in set(x for x, a in zip(subj, act) if a):
            self.rows_by_subject[s] = self.rows_by_subject.get(s, 0) + sum(1 for x in subj if x == s)
        foot, ankle, cop = column_plan(t.schema.names)
        for name in foot + ankle:
            vals, mask, typ = _values(t.column(name))
            new = vals.copy()
            new[act] = vals[act] - off[act]
            t = _put(t, name, new, mask, typ)
        for an, ve in cop:
            a, ma, ta = _values(t.column(an))
            v, mv, tv = _values(t.column(ve))
            fa, fv = np.isfinite(a), np.isfinite(v)
            both = fa & fv & act
            self.cop_partial_rows += int((((fa != fv)) & act).sum())
            ra, rv = rotate_cop(a[both], v[both], off[both])
            na, nv = a.copy(), v.copy()
            na[both], nv[both] = ra, rv
            self.cop_rotated_samples += int(both.sum())
            self.cop_rotated_beyond_l5 += int(((np.abs(ra) > L5_BOUNDS_M["cop_anterior"][1]) |
                                               (np.abs(rv) > L5_BOUNDS_M["cop_vertical"][1])).sum())
            t = _put(t, an, na, ma, ta)
            t = _put(t, ve, nv, mv, tv)
        return t

    def summary(self):
        return {"rows": self.rows, "rows_shifted": self.rows_shifted, "rows_shifted_by_subject": dict(self.rows_by_subject),
                "cop_samples_rotated": self.cop_rotated_samples, "cop_rows_with_only_one_of_anterior_vertical_finite": self.cop_partial_rows,
                "cop_rotated_samples_beyond_coarse_limit": self.cop_rotated_beyond_l5}


# ------------------------------------------------------------------ re-assessment of L1 (ankle) and L5 (CoP)
def _viol_l1(x_rad):
    d = np.degrees(x_rad)
    return np.isfinite(x_rad) & ((d < L1_ANKLE_DEG[0]) | (d > L1_ANKLE_DEG[1])), d


def _viol_l5(col, x):
    lo, hi = L5_BOUNDS_M[col.split("_")[0] + "_" + col.split("_")[1]]
    return np.isfinite(x) & ((x < lo) | (x > hi))


def limit_of(col):
    if col.startswith("ankle_dorsiflexion_angle_"):
        return "L1"
    if col.startswith(("cop_anterior_", "cop_vertical_")):
        return "L5"
    return None


def reason_text(col, value, l1_decimals):
    if limit_of(col) == "L1":
        lo, hi = L1_ANKLE_DEG
        return f"{col} {value:.{l1_decimals}f} deg outside [{lo:g}, {hi:g}] deg"
    lo, hi = L5_BOUNDS_M[col.split("_")[0] + "_" + col.split("_")[1]]
    return f"{col} {value:.3f} m outside [{lo:g}, {hi:g}] m"


class Reassess:
    """Pre-pass over the table parts: per observation and checked column, the L1/L5 violation counts at offset zero (must equal
    the existing assessment), after the foot-flat shift, and the L2 jump flags of foot/ankle before and after (must be equal).

    checked: {(observation_id, reference_side): [columns the existing assessment checked with L1 or L5]}
    existing: {(observation_id, reference_side): {column: {limit: n}}} (failed_samples of the existing entries)"""

    def __init__(self, offsets_rad, checked, existing, table, list_cap=2000, l1_decimals=3):
        self.off, self.checked, self.existing = offsets_rad, checked, existing
        self.table, self.cap, self.l1d = table, list_cap, l1_decimals
        self.zero = {}      # (key, col) -> count at offset zero (only where >0 or existing >0)
        self.new = {}       # (key, col) -> count after shift
        self.rows = {}      # key -> rows seen (sample index base)
        self.listed = {}    # (key, col) -> [row dicts] of the new violations (capped)
        self.l2_flips = 0
        self.l2_pairs = 0
        self._done = False

    def scan_part(self, part, rp):
        import pyarrow.parquet as pq
        fh = open(part.path, "rb")
        try:
            pf = rp.open_part(fh)
            names = pf.schema_arrow.names
            axis = "time_s" if self.table == "time" else "phase_ipsi"
            foot, ankle, cop = column_plan(names)
            cols = ["observation_id", "reference_side", "subject", "source_recording_id", axis] + foot + ankle + \
                   [c for p in cop for c in p]
            for batch in pf.iter_batches(batch_size=rp.READ_BATCH_ROWS, columns=cols, use_threads=False):
                oids = batch.column("observation_id").to_pylist()
                sides = batch.column("reference_side").to_pylist()
                recs = batch.column("source_recording_id").to_pylist()
                subj = batch.column("subject").to_pylist()
                ax = np.array(batch.column(axis).to_numpy(zero_copy_only=False), dtype=float)
                data = {c: np.array(batch.column(c).to_numpy(zero_copy_only=False), dtype=float)
                        for c in foot + ankle + [c for p in cop for c in p]}
                for key, a, b in rp.batch_runs(oids, sides):
                    if recs[a] in part.drop_recordings:
                        continue
                    base = self.rows.get(key, 0)
                    self.rows[key] = base + (b - a)
                    off = self.off.get(subj[a], 0.0)
                    # L2 flip check on foot and ankle angle columns (constant shift: equal flags expected)
                    for c in foot + ankle:
                        x = data[c][a:b]
                        if b - a > 1:
                            d0 = np.abs(np.degrees(np.diff(x)))
                            d1 = np.abs(np.degrees(np.diff(x - off)))
                            ok = np.isfinite(d0) & np.isfinite(d1)
                            self.l2_pairs += int(ok.sum())
                            self.l2_flips += int((ok & ((d0 > L2_JUMP_DEG) != (d1 > L2_JUMP_DEG))).sum())
                    cols_checked = self.checked.get(key)
                    if not cols_checked:
                        continue
                    for c in cols_checked:
                        if c not in data:
                            continue
                        x = data[c][a:b]
                        if limit_of(c) == "L1":
                            z, _ = _viol_l1(x)
                            n_, d_ = _viol_l1(x - off) if off else (z, None)
                            newx = x - off
                        else:
                            pair = next(p for p in cop if c in p)
                            xa, xv = data[pair[0]][a:b], data[pair[1]][a:b]
                            if off:
                                both = np.isfinite(xa) & np.isfinite(xv)
                                ra, rv = xa.copy(), xv.copy()
                                ra[both], rv[both] = rotate_cop(xa[both], xv[both], off)
                            else:
                                ra, rv = xa, xv
                            newx = ra if c == pair[0] else rv
                            z = _viol_l5(c, x)
                            n_ = _viol_l5(c, newx)
                        if z.any() or self.existing.get(key, {}).get(c):
                            self.zero[(key, c)] = self.zero.get((key, c), 0) + int(z.sum())
                        if n_.any() or z.any() or self.existing.get(key, {}).get(c):
                            self.new[(key, c)] = self.new.get((key, c), 0) + int(n_.sum())
                        if n_.any():
                            lst = self.listed.setdefault((key, c), [])
                            room = self.cap - len(lst)
                            if room > 0:
                                for i in np.flatnonzero(n_)[:room]:
                                    val = float(np.degrees(newx[i])) if limit_of(c) == "L1" else float(newx[i])
                                    lst.append({"observation_id": key[0], "reference_side": key[1], "table": self.table,
                                                "channel": c, "limit": limit_of(c), "sample_index": int(base + i),
                                                ("time_s" if self.table == "time" else "phase_percent"): float(ax[a + i]),
                                                "value": val, "reason": reason_text(c, val, self.l1d)})
        finally:
            fh.close()

    def old_count(self, key, col):
        if self._done:
            return self._old.get((key, col), 0)
        lim = limit_of(col)
        return int(self.existing.get(key, {}).get(col, {}).get(lim, 0))

    def finish(self):
        """Freeze the results and drop the per-observation bookkeeping (a long package keeps this object alive during the build)."""
        ch, mm = self.changes(), self.mismatches()
        old = {(k, c): self.old_count(k, c) for k, cols in ch.items() for c in cols}
        listed = {kc: v for kc, v in self.listed.items() if kc[0] in ch and kc[1] in ch[kc[0]]}
        self._changes, self._mismatches, self._old, self._done = ch, mm, old, True
        self.listed = listed
        self.rows, self.checked, self.existing, self.zero, self.new = {}, {}, {}, {}, {}

    def mismatches(self):
        """(key, col, existing count, recomputed count at offset zero) wherever they differ."""
        if self._done:
            return self._mismatches
        out = []
        keys = set(self.zero) | {(k, c) for k, v in self.existing.items() for c in v if k in self.checked and c in self.checked[k]}
        for key, c in keys:
            if key not in self.rows or c not in self.checked.get(key, ()):
                continue
            if self.old_count(key, c) != self.zero.get((key, c), 0):
                out.append((key, c, self.old_count(key, c), self.zero.get((key, c), 0)))
        return out

    def changes(self):
        """{key: {col: new count}} wherever the shift changed a count against the existing entry."""
        if self._done:
            return self._changes
        out = {}
        for (key, c), n in self.new.items():
            if n != self.old_count(key, c):
                out.setdefault(key, {})[c] = n
        return out


def apply_changes(raw, new_counts, vocab):
    """Update one assessment entry (package form) for new L1/L5 counts {col: n}; returns a modified copy. A channel is in the
    fail state while any limit (L1, L2 or L5) still has a count on it; the entry stays failed while any cause remains."""
    e = dict(raw)
    fs = {c: dict(v) for c, v in e["failed_samples"].items()}
    states = {k: list(v) for k, v in e["channel_states"].items()}
    for c, n in new_counts.items():
        lim = limit_of(c)
        if n > 0:
            fs.setdefault(c, {})[lim] = n
        else:
            fs.get(c, {}).pop(lim, None)
            if c in fs and not fs[c]:
                del fs[c]
        for s_ in list(states):
            if c in states[s_]:
                states[s_].remove(c)
        new_state = vocab["fail"] if fs.get(c) else vocab["pass_ankle" if lim == "L1" else "pass_cop"]
        states.setdefault(new_state, []).append(c)
        states[new_state].sort()
    states = {k: v for k, v in states.items() if v}
    l15 = {lim for v in fs.values() for lim in v if lim in ("L1", "L5")}
    old_causes = list(e["failed_limits"])
    other = [x for x in old_causes if x not in ("L1", "L5")]
    causes = sorted(set(other) | l15)
    if causes:
        status = "failed"
    else:
        status = "failed" if (e["status"] == "failed" and not old_causes) else "no_failure_found"
    e["failed_samples"] = fs
    e["failed_channels"] = sorted(c for c, v in fs.items() if v)
    e["channel_states"] = states
    e["failed_limits"] = causes if status == "failed" else []
    e["status"] = status
    attrs = json.loads(json.dumps(e["attributes"]))
    if isinstance(attrs.get("checks"), dict):
        for lim in ("L1", "L5"):
            if attrs["checks"].get(lim) in ("passed", "failed"):
                attrs["checks"][lim] = "failed" if lim in l15 else "passed"
    e["attributes"] = attrs
    return e


def shift_angle_range_attribute(attrs, off_deg):
    """GT21 assessment attributes carry angle_range_deg per column; shift the foot and ankle ranges by -offset (3 decimals)."""
    r = attrs.get("angle_range_deg")
    if isinstance(r, dict):
        for c, v in r.items():
            if (c.startswith("foot_sagittal_angle_") or c.startswith("ankle_dorsiflexion_angle_")) and v:
                r[c] = [None if x is None else round(x - off_deg, 3) for x in v]   # a range can hold None (no finite sample)
    return attrs
