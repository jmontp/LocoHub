#!/usr/bin/env python3
"""Figures for the foot-flat zero card on the GT23, GT21 and UM21 pages, and the GT21 knee card.

Two steps, both read only small files (bounded reads, no data tables):

  python3 contributor_tools/build_foot_flat_page_figures.py --extract
      Writes two small evidence files under docs/quality/audits/ from the committed foot-flat offsets
      (foot-flat-offsets.json), the A2 foot-flat sheet summary (ramp check) and the two GT21 knee checks
      (standing pose and knee centre, local comparison.json files):
          foot-flat-page-evidence.json   offsets per person, uncorrected people, ramp check
          gt21-knee-gap-evidence.json    knee gap and what each check removed
  python3 contributor_tools/build_foot_flat_page_figures.py
      Draws docs/datasets/<slug>/figures/foot-flat-offsets.svg and docs/datasets/gt21/figures/gt21-knee-gap.svg
      from those two evidence files only.

Colors and sizes follow the other page figures (4.5 in wide, fonts 10 pt, colour-blind safe palette).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "docs/quality/audits"
RV2 = ROOT / "converted_datasets/reconversion_v2"
OFFSETS = AUD / "foot-flat-offsets.json"
A2 = ROOT / "review_sheets/A2-footflat/summary.json"
FOOT_EVIDENCE = AUD / "foot-flat-page-evidence.json"
KNEE_EVIDENCE = AUD / "gt21-knee-gap-evidence.json"
STATIC = RV2 / "gt21_static_analysis_v1/comparison.json"
CENTRE = RV2 / "gt21_knee_centre_v1/comparison.json"
MAX_BYTES = 2 * 1024 * 1024  # evidence files are small; the offsets file is the largest read (about 0.5 MB)
BLUE, ORANGE, VERMIL, GREEN, SKY, GREY, DARK = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#56B4E9", "#8c8c8c", "#333333"
DATASETS = {"GT23": "gt23", "GT21": "gt21", "UM21": "um21"}


def load(path: Path):
    if path.stat().st_size > MAX_BYTES:
        raise RuntimeError(f"{path} is larger than {MAX_BYTES} bytes; this script only reads small files")
    return json.loads(path.read_text(encoding="utf-8"))


def extract() -> None:
    offsets = load(OFFSETS)["datasets"]
    a2 = load(A2)["slope"]
    out = {"schema": 1, "sources": ["docs/quality/audits/foot-flat-offsets.json", "review_sheets/A2-footflat/summary.json (ramp check)"],
           "datasets": {}}
    for ds, d in offsets.items():
        people = {p: {"offset_deg": v["offset_deg"], "n_strides": v["n_strides"], "lo_deg": v["stride_median_deg_min"], "hi_deg": v["stride_median_deg_max"]}
                  for p, v in d["people"].items()}
        vals = [v["offset_deg"] for v in people.values()]
        ramp = {}
        for cond in ("incline", "decline"):
            ok = [v for v in a2[ds][cond].values() if v["corrected"] is not None and v["raw"] is not None]  # uncorrected people have none
            res = [v["corrected"] for v in ok]
            raw = [v["raw"] for v in ok]
            ramp[cond] = {"people": len(res), "expected_slope_deg": statistics.median(v["expected"] for v in ok),
                          "original_median_deg": statistics.median(raw), "corrected_median_deg": statistics.median(res),
                          "corrected_min_deg": min(res), "corrected_max_deg": max(res)}
        out["datasets"][ds] = {"people": people, "uncorrected_people": d["persons_without_offset"],
                               "offset_median_deg": statistics.median(vals), "offset_min_deg": min(vals), "offset_max_deg": max(vals),
                               "ramp_check_foot_minus_slope": ramp}
    FOOT_EVIDENCE.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    s, c = load(STATIC), load(CENTRE)
    knee = s["by_reference"]["mean_of_both"]["knee"]
    k = {"schema": 1, "sources": ["gt21_static_analysis_v1/comparison.json", "gt21_knee_centre_v1/comparison.json"],
         "people": c["people"], "reference": "mean of the GT23 and UM21 person means (level walking, 20 to 35 percent of the stride)",
         "walking_knee_gap_deg": knee["mean_gap"], "standing_knee_deg": knee["mean_standing"],
         "gap_left_if_standing_is_zero_deg": knee["mean_corrected_gap"],
         "standing_knee_with_marker_knee_centres_deg": c["static"]["knee"]["knee_marker"]["mean"],
         "walking_gap_with_marker_knee_centres_deg": c["walking"]["knee"]["mean_corrected_gap"],
         "knee_centre_verdict": c["verdict"]}
    KNEE_EVIDENCE.write_text(json.dumps(k, indent=1, sort_keys=True), encoding="utf-8")
    print("wrote", FOOT_EVIDENCE.relative_to(ROOT), "and", KNEE_EVIDENCE.relative_to(ROOT))


def plt_module():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
                         "legend.fontsize": 10, "svg.fonttype": "path", "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 100, "axes.grid": False, "svg.hashsalt": "locohub"})
    return plt


def save(plt, fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    print("wrote", path.relative_to(ROOT))


def offsets_figure(plt, ds: str, ev: dict) -> None:
    people = ev["datasets"][ds]["people"]
    names = sorted(people)
    n = len(names)
    fig, ax = plt.subplots(figsize=(4.5, 1.7 + 0.16 * n), layout="constrained")
    ys = list(range(n))[::-1]
    for y, name in zip(ys, names):
        p = people[name]
        ax.plot([p["lo_deg"], p["hi_deg"]], [y, y], color=GREY, lw=1.2, zorder=1)
        ax.scatter([p["offset_deg"]], [y], color=VERMIL, s=22, zorder=3)
    ax.axvline(0, color=DARK, lw=0.8, zorder=0)
    med = ev["datasets"][ds]["offset_median_deg"]
    ax.axvline(med, color=BLUE, lw=1.2, ls="--", zorder=0)
    ax.set_yticks(ys)
    ax.set_yticklabels([x.replace("UM21_", "") for x in names])
    ax.set_xlabel("Foot angle when the foot lies flat (degrees)")
    ax.text(med, 1.0, f" median {med:+.1f}", transform=ax.get_xaxis_transform(), color=BLUE, va="bottom", ha="left")
    ax.scatter([], [], color=VERMIL, s=22, label="Person's offset (the median stride)")
    ax.plot([], [], color=GREY, lw=1.2, label="Range over that person's strides")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18 if n < 15 else -0.1), ncol=1, frameon=False, fontsize=10)
    save(plt, fig, ROOT / "docs/datasets" / DATASETS[ds] / "figures/foot-flat-offsets.svg")


def knee_figure(plt, k: dict) -> None:
    rows = [("Walking knee gap\nas converted", k["walking_knee_gap_deg"], VERMIL),
            ("Standing knee\n(static trial)", k["standing_knee_deg"], BLUE),
            ("Gap left if standing\nwere the zero", k["gap_left_if_standing_is_zero_deg"], SKY),
            ("Standing knee, marker\nknee centres", k["standing_knee_with_marker_knee_centres_deg"], BLUE),
            ("Walking gap, marker\nknee centres", k["walking_gap_with_marker_knee_centres_deg"], VERMIL)]
    fig, ax = plt.subplots(figsize=(4.5, 3.3), layout="constrained")
    ys = list(range(len(rows)))[::-1]
    for y, (label, v, c) in zip(ys, rows):
        ax.barh(y, v, color=c, height=0.6)
        ax.text(v, y, f" {v:.1f}°", va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlim(0, 10)
    ax.set_xlabel(f"Degrees of knee flexion, mean over {k['people']} people")
    save(plt, fig, ROOT / "docs/datasets/gt21/figures/gt21-knee-gap.svg")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract", action="store_true", help="write the two small evidence files from the audit and review files")
    args = ap.parse_args(argv)
    if args.extract:
        extract()
        return 0
    plt = plt_module()
    ev = load(FOOT_EVIDENCE)
    for ds in DATASETS:
        offsets_figure(plt, ds, ev)
    knee_figure(plt, load(KNEE_EVIDENCE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
