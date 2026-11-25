#!/usr/bin/env python3
"""Draw the three overview figures of the Georgia Tech 2023 dataset page.

Reads only the small files of the local review package (manifest.json, limitations.json) and the
committed rerun handoff for the before-and-after failure counts. Never opens a table file.
Writes docs/datasets/gt23/figures/page-*.svg (matplotlib, 4.5 in wide, fonts of at least 10 pt).

    python3 contributor_tools/build_gt23_page_figures.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contributor_tools"))
import build_gt23_problems_page as P  # noqa: E402  (shared style only; importing it runs nothing)

BUNDLE = ROOT / "converted_datasets/reconversion_v2/gt23_r01_review_v11"
RERUN = ROOT / "docs/maintainers/handoffs/GT23-PL01.json"
OUT = ROOT / "docs/datasets/gt23/figures"

REASON_TEXT = {
    ("export_exclusion", "shorter_than_0.25_s"): "Stride shorter than 0.25 s",
    ("export_exclusion", "shorter_than_0.3_s"): "Stride shorter than 0.3 s",
    ("export_exclusion", "longer_than_5_s"): "Stride longer than 5 s",
    ("export_exclusion", "last_contact_has_no_following_contact"): "Last foot contact has no next contact",
    ("export_exclusion", "span_boundary_next_to_missing_marker"): "Span edge next to a missing marker",
    ("export_exclusion", "force_not_a_number_inside_stride"): "Force missing inside the stride",
    ("authors_window_not_exported", "no_record_starts_within_tolerance"): "Authors' window: none of ours starts near it",
    ("authors_window_not_exported", "nearest_record_excluded"): "Authors' window: nearest stride left out",
    ("authors_window_not_exported", "no_record_for_this_leg"): "Authors' window: no stride for this leg",
}


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_bytes(buf.getvalue())


def hbar(plt, rows, name, xlabel, colors, height=3.3, label_fmt=lambda v: f"{v:,}"):
    fig, ax = plt.subplots(figsize=(P.WIDTH_IN, height), layout="constrained")
    ys = list(range(len(rows)))[::-1]
    for y, (lab, val), col in zip(ys, rows, colors):
        ax.barh(y, val, color=col, height=.62, zorder=2)
        ax.annotate(label_fmt(val), (val, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, max(r[1] for r in rows) * 1.28)
    ax.grid(axis="x", color=P.GREY, lw=0.4, alpha=0.6, zorder=0)
    save(fig, name)
    plt.close(fig)


def main():
    plt = P.plt_module()
    manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]
    # 1. what was left out
    rows = []
    for kind, reasons in counts["exclusions_by_reason"].items():
        if kind == "assessment_failed":
            continue
        for reason, n in reasons.items():
            rows.append((REASON_TEXT[(kind, reason)], n, kind))
    rows.append(("Failed a coarse limit (cleaned version only)", counts["exclusions_by_stage"]["filtered_variant_only"], "assessment"))
    rows.sort(key=lambda r: -r[1])
    col = {"export_exclusion": P.MUTED, "authors_window_not_exported": P.AFTER, "assessment": P.BEFORE}
    hbar(plt, [(a, b) for a, b, _ in rows], "page-left-out.svg", "Items left out", [col[c] for _, _, c in rows], height=3.6)
    # 2. limitations
    lim = json.loads((BUNDLE / "limitations.json").read_text(encoding="utf-8"))["limitations"]
    short = {"ab03_side_shuffle_1_foot_cop": "AB03 side shuffle: pressure point", "step_up_cop_held": "Step-ups: pressure point held",
             "curb_up_cop_held": "Curb-ups: pressure point held", "ab07_right_foot_offset": "AB07: right-foot marker offset",
             "mass_estimated": "Mass factor estimated", "ab09_divisor": "AB09: mass factor uncertain",
             "nm_rerun_limit": "Mass factor from a local re-run", "window_span_both_legs": "Spans exported for both legs",
             "shuffle_not_steady_walking": "Shuffle filed as level walking", "unlabelled_walking_under_functional_task": "Walking filed as functional task",
             "run_label_check": "Cycles labelled run",
             "power_from_moment_and_speed": "Power recomputed", "other_powers_source_values": "Hip sideways, rotation, subtalar power as published"}
    items = sorted(((short[x["id"]], x.get("observations", x.get("observations_in_recording"))) for x in lim), key=lambda r: -r[1])
    hbar(plt, items, "page-limitations.svg", "Observations touched", [P.MUTED] * len(items), height=3.6)
    # 3. failures before and after
    q = json.loads(RERUN.read_text(encoding="utf-8"))["steps_2_to_4"]["q01_v2"]
    before, after = q["before_old_v1"], q["after"]
    names = [("L5", "Pressure point too far\nfrom the foot"), ("L2", "Angle jumps 30° or\nmore between samples"), ("L1", "Joint angle outside\nthe possible range")]
    fig, ax = plt.subplots(figsize=(P.WIDTH_IN, 3.2), layout="constrained")
    ys = list(range(len(names)))[::-1]
    for y, (k, lab) in zip(ys, names):
        ax.barh(y + .17, before[k], height=.32, color=P.BEFORE, zorder=2)
        ax.barh(y - .17, after[k], height=.32, color=P.AFTER, zorder=2)
        ax.annotate(f"{before[k]:,}", (before[k], y + .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
        ax.annotate(f"{after[k]:,}", (after[k], y - .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([n[1] for n in names])
    ax.set_xlabel("Observations failing the limit")
    ax.set_xlim(0, before["L5"] * 1.2)
    ax.grid(axis="x", color=P.GREY, lw=0.4, alpha=0.6, zorder=0)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=P.BEFORE, label=f"Earlier export ({before['failed']} observations fail)"),
                        plt.Rectangle((0, 0), 1, 1, color=P.AFTER, label=f"This version ({after['failed']} observations fail)")],
               loc="outside lower left", ncols=1)
    save(fig, "page-failures.svg")
    plt.close(fig)
    # 4. power gap (stride files, this leg)
    gap = next(x for x in lim if x["id"] == "power_from_moment_and_speed")["gap_source_power_vs_moment_times_velocity"]
    joints = [("Hip", "hip_flexion_power_ipsi_W_kg"), ("Knee", "knee_flexion_power_ipsi_W_kg"), ("Ankle", "ankle_dorsiflexion_power_ipsi_W_kg")]
    fig, ax = plt.subplots(figsize=(P.WIDTH_IN, 3.2), layout="constrained")
    ys = list(range(3))[::-1]
    for y, (j, c) in zip(ys, joints):
        a, b = 100 * gap[c]["median_nrms"], 100 * gap[c]["p90_nrms"]
        ax.barh(y + .17, a, height=.32, color=P.BEFORE, zorder=2)
        ax.barh(y - .17, b, height=.32, color=P.MUTED, zorder=2)
        ax.annotate(f"{a:.0f}%", (a, y + .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
        ax.annotate(f"{b:.0f}%", (b, y - .17), xytext=(4, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(ys)
    ax.set_yticklabels([j for j, _ in joints])
    ax.set_xlabel("Gap between source power and moment times speed (%)")
    ax.set_xlim(0, 100 * max(gap[c]["p90_nrms"] for _, c in joints) * 1.25)
    ax.grid(axis="x", color=P.GREY, lw=0.4, alpha=0.6, zorder=0)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=P.BEFORE, label="Typical observation (median)"),
                        plt.Rectangle((0, 0), 1, 1, color=P.MUTED, label="Larger gaps (90th percentile)")], loc="outside lower left", ncols=1)
    save(fig, "power-gap.svg")
    plt.close(fig)
    print("wrote 4 figures to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
