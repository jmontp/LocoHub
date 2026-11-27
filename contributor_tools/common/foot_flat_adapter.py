"""Adapter mixin for CORE-FOOT-01: applies the foot-flat zero through Part.transform and re-assesses L1 (ankle) and L5 (CoP).

A package adapter (GT23 v12, GT21 v2, UM21 v6) is `class X(FootFlatMixin, PreviousAdapter)`; the mixin only wraps the previous
adapter's methods, so every other value, identity, exclusion and evidence file is what the previous adapter produced.

Before streaming (prepare), one pre-pass over the same table parts reads only the identity, axis, foot, ankle and CoP columns and
counts, per observation and checked column, the L1/L5 violations (a) at offset zero, which must equal the existing assessment
entry exactly, and (b) after the shift. Where (b) differs from the entry, the entry is updated (failed samples, failed channels,
channel states, causes, status). L2 flags of foot and ankle are compared before and after and must not change (a constant shift).
Nothing else in an entry changes except two per-observation limitation flags and the shifted angle ranges stored in attributes.
"""
from __future__ import annotations

import collections
import gc
import json


class FootFlatMixin:
    ff_dataset = None          # 'GT23' | 'GT21' | 'UM21' (key in foot-flat-offsets.json)
    ff_vocab = None            # foot_flat.VOCAB_*
    ff_limits = {"phase": ("L1", "L5"), "time": ("L1", "L5")}
    ff_l1_decimals = 3
    ff_cap = 2000
    ff_failure_fields = ()
    ff_failed_check_ids = {}   # check id of the previous adapter -> 'total' | 'phase' | 'time'
    OFFSETS_PATH = "docs/quality/audits/foot-flat-offsets.json"

    # -- set up (call from __init__ before the previous adapter's prepare) ------------------------------------------------
    def ff_init(self, rp, ff, root):
        self.rp, self.ff, self.ff_root = rp, ff, root
        self.ff_offsets = ff.load_offsets(root / self.OFFSETS_PATH, self.ff_dataset)
        self.ff_tf = {t: ff.FootFlat(self.ff_offsets) for t in self.tables}
        self.ff_changes = {t: {} for t in self.tables}
        self.ff_reassess = {}
        self.ff_flips = {}
        self.ff_causeless_failed = 0        # failed by a structural check with no listed limit (e.g. S5): never changed here
        self.ff_causeless_changed = 0
        self.ff_entries_subject_rows = collections.Counter()
        self.ff_ranges_shifted = 0

    def ff_prepare(self):
        """The re-assessment pre-pass. Call at the end of prepare()."""
        ff = self.ff
        checked = {t: {} for t in self.tables}
        existing = {t: {} for t in self.tables}
        for e in super().assessment_entries():
            key = (e["observation_id"], e["reference_side"])
            cols = ff.checked_columns(e, self.ff_vocab, self.ff_limits.get(e["table"], ()))
            if cols:
                checked[e["table"]][key] = cols
                rel = {c: d for c, d in e["failed_samples"].items() if ff.limit_of(c)}
                if rel:
                    existing[e["table"]][key] = rel
            if e["status"] == "failed" and not e["failed_limits"]:
                self.ff_causeless_failed += 1
        for t in self.tables:
            r = ff.Reassess(self.ff_offsets, checked[t], existing[t], t, self.ff_cap, self.ff_l1_decimals)
            for part in self.table_parts(t):
                r.scan_part(part, self.rp)
                print(f"foot-flat pre-pass {t} {part.label} {part.path.parent.name}", flush=True)
            for (key, c), n in r.new.items():
                if max(n, r.old_count(key, c)) > self.ff_cap and n != r.old_count(key, c):
                    raise self.rp.PackageError(f"{key} {c}: a changed count exceeds the listing cap {self.ff_cap}")
            r.finish()
            gc.collect()
            self.rp.trim_memory()
            self.ff_reassess[t] = r
            self.ff_changes[t] = r.changes()
            print(f"foot-flat {t}: {len(self.ff_changes[t])} observations change L1/L5 counts, "
                  f"{len(r.mismatches())} recount mismatches at offset zero, L2 flips {r.l2_flips} of {r.l2_pairs} pairs", flush=True)

    # -- entries -------------------------------------------------------------------------------------------------------
    def assessment_entries(self):
        ff = self.ff
        for raw in super().assessment_entries():
            key = (raw["observation_id"], raw["reference_side"])
            ch = self.ff_changes.get(raw["table"], {}).get(key)
            e = raw
            if ch:
                e = ff.apply_changes(raw, ch, self.ff_vocab)
                if e["status"] != raw["status"]:
                    self.ff_flips[(key[0], key[1], raw["table"])] = ({"observation_id": key[0], "reference_side": key[1], "table": raw["table"],
                                          "subject": raw["subject"], "task": raw["task"], "type": raw["observation_type"],
                                          "status_before": raw["status"], "status_after": e["status"],
                                          "causes_before": "+".join(raw["failed_limits"]),
                                          "causes_after": "+".join(e["failed_limits"]),
                                          "changed_columns": ";".join(sorted(ch))})
            if raw["status"] == "failed" and not raw["failed_limits"] and e["status"] != "failed":
                self.ff_causeless_changed += 1
            off = self.ff_offsets.get(raw["subject"])
            e = dict(e)
            e["limitations"] = list(e["limitations"]) + ["foot_flat_zero_applied" if off is not None else "foot_flat_zero_not_applied"]
            if off is not None:
                import math
                attrs = json.loads(json.dumps(e["attributes"]))
                if isinstance(attrs.get("angle_range_deg"), dict):
                    ff.shift_angle_range_attribute(attrs, math.degrees(off))
                    self.ff_ranges_shifted += 1
                e["attributes"] = attrs
            yield e

    # -- evidence ------------------------------------------------------------------------------------------------------
    def evidence_tables(self):
        ev = dict(super().evidence_tables())
        name = "assessment_failure_samples.csv"
        fields, base_rows = ev[name]
        changed = {(k[0], k[1], c, self.ff.limit_of(c)) for t, r in self.ff_reassess.items() for k, cols in r.changes().items() for c in cols}
        new_rows = [row for t, r in self.ff_reassess.items() for (key, c), lst in r.listed.items()
                    if (key[0], key[1], c, self.ff.limit_of(c)) in changed for row in lst]

        def rows():
            for row in base_rows:
                if (row.get("observation_id"), row.get("reference_side"), row.get("channel"), row.get("limit")) in changed:
                    continue
                yield row
            for row in new_rows:
                yield {k: row.get(k, "") for k in fields}
        ev[name] = (fields, rows())
        off_rows = [{"dataset": self.ff_dataset, "subject": s, "offset_deg": f"{v * 180 / 3.141592653589793:.6f}", "offset_rad": repr(v)}
                    for s, v in sorted(self.ff_offsets.items())]
        ev["foot_flat_offsets_applied.csv"] = (["dataset", "subject", "offset_deg", "offset_rad"], off_rows)
        chg = []
        for t, r in self.ff_reassess.items():
            for key, cols in sorted(r.changes().items()):
                for c, n in sorted(cols.items()):
                    chg.append({"table": t, "observation_id": key[0], "reference_side": key[1], "channel": c,
                                "limit": self.ff.limit_of(c), "samples_failed_before": r.old_count(key, c), "samples_failed_after": n})
        ev["foot_flat_limit_count_changes.csv"] = (["table", "observation_id", "reference_side", "channel", "limit",
                                                    "samples_failed_before", "samples_failed_after"], chg)
        ev["foot_flat_membership_changes.csv"] = (["observation_id", "reference_side", "table", "subject", "task", "type",
                                                   "status_before", "status_after", "causes_before", "causes_after", "changed_columns"],
                                                  list(self.ff_flips.values()))
        ev["foot_flat_transform_check.csv"] = (["table", "rows", "rows_shifted", "cop_samples_rotated",
                                                "cop_rows_with_only_one_of_anterior_vertical_finite",
                                                "cop_rotated_samples_beyond_coarse_limit", "l2_pairs_compared", "l2_flags_changed",
                                                "recount_mismatches_at_offset_zero"],
                                               [{"table": t, **{k: v for k, v in self.ff_tf[t].summary().items()
                                                                if k not in ("rows_shifted_by_subject",)},
                                                 "l2_pairs_compared": self.ff_reassess[t].l2_pairs,
                                                 "l2_flags_changed": self.ff_reassess[t].l2_flips,
                                                 "recount_mismatches_at_offset_zero": len(self.ff_reassess[t].mismatches())}
                                                for t in self.tables])
        return ev

    # -- limitations, README, checks ----------------------------------------------------------------------------------
    def ff_flip_counts(self):
        up = collections.Counter(f["table"] for f in self.ff_flips.values() if f["status_after"] == "failed")
        down = collections.Counter(f["table"] for f in self.ff_flips.values() if f["status_after"] != "failed")
        return up, down

    def limitations(self, entries):
        import math
        rp = self.rp
        out = list(super().limitations(entries))
        up, down = self.ff_flip_counts()
        people = {s: {"offset_deg": round(math.degrees(v), 3)} for s, v in sorted(self.ff_offsets.items())}
        out.append({"id": "foot_flat_zero_applied", "title": "Foot-flat zero applied to foot angle, ankle angle and foot-frame pressure point",
                    "text": self.ff_text_applied(), "people_offsets": people,
                    "newly_failed_observations_by_table": dict(up), "recovered_observations_by_table": dict(down),
                    **rp.count_flag(entries, "foot_flat_zero_applied")})
        out.append({"id": "foot_flat_zero_not_applied", "title": "People without a foot-flat zero (left uncorrected)",
                    "text": self.ff_text_uncorrected(), **rp.count_flag(entries, "foot_flat_zero_not_applied")})
        return out

    def ff_text_applied(self):
        return ("Foot-flat zero (D-REF-6, 27 November 2026): each person's foot angle was shifted by minus the median, over that "
                "person's matched level-walking strides, of the per-stride median foot angle at 20 to 35 percent of the stride, so that "
                "a foot lying flat on level ground reads 0. The ankle angle shifts by the same amount (ankle = foot - shank), and the "
                "foot-frame pressure point (forward and up) is rotated by the same angle inside the leg plane; its sideways value is "
                "unchanged. Pelvis, thigh, shank, hip and knee angles, all velocities, moments, powers, forces, identities and "
                "time stamps are unchanged. The offsets are in evidence/foot_flat_offsets_applied.csv; the ankle and pressure-point limits "
                "(L1, L5) were re-checked on the shifted values.")

    def ff_text_uncorrected(self):
        return ("People with no matched level-walking stride have no foot-flat offset and keep the foot angle, ankle angle and "
                "foot-frame pressure point as they were measured; their ankle angle is not comparable to the corrected people.")

    def readme_sections(self):
        return list(super().readme_sections()) + [("Foot-flat zero", self.ff_text_applied() + " " + self.ff_text_uncorrected())]

    def extra_checks(self, ctx):
        checks = list(super().extra_checks(ctx))
        up, down = self.ff_flip_counts()
        for i, (cid, d, ex, ob) in enumerate(checks):
            kind = self.ff_failed_check_ids.get(cid)
            if kind:
                delta = (sum(up.values()) - sum(down.values())) if kind == "total" else (up.get(kind, 0) - down.get(kind, 0))
                checks[i] = (cid, d + f" (verified chain total {ex} plus the foot-flat re-assessment change {delta:+d})", ex + delta, ob)
        shifted_expected = {t: sum(e["rows"] for e in ctx["entries"] if e["table"] == t and e["subject"] in self.ff_offsets)
                            for t in self.tables}
        checks += [
            ("FF1", "the L1/L5 recount at offset zero equals the existing assessment entries (checked columns)", {t: 0 for t in self.tables},
             {t: len(self.ff_reassess[t].mismatches()) for t in self.tables}),
            ("FF2", "a constant shift changes no L2 jump flag of any foot or ankle angle", {t: 0 for t in self.tables},
             {t: self.ff_reassess[t].l2_flips for t in self.tables}),
            ("FF3", "rows shifted equal the rows of the assessed observations of people with an offset",
             shifted_expected, {t: self.ff_tf[t].rows_shifted for t in self.tables}),
            ("FF4", "no row has only one of cop anterior and cop vertical finite (they are masked together)", {t: 0 for t in self.tables},
             {t: self.ff_tf[t].cop_partial_rows for t in self.tables}),
            ("FF5", "entries failed by a structural check with no listed limit (e.g. S5 side check) keep their failed status "
                    f"({self.ff_causeless_failed} such entries)", 0, self.ff_causeless_changed),
        ]
        return checks

    def bound_hashes(self):
        h = dict(super().bound_hashes())
        for rel in self.ff_bound_files:
            h[rel] = self.rp.sha256_file(self.ff_root / rel)
        return h
