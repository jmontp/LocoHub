#!/usr/bin/env python3
"""Figures for the Georgia Tech 2021 dataset page (contributor_tools/page_specs/gt21.json).

Every figure is one panel, at most 4.5 in wide, fonts of at least 10 pt, saved as SVG under
docs/datasets/gt21/figures/. Inputs are small evidence JSON files already in the repository
(handoffs, audits, the package's limitations.json and manifest.json); no full dataset table is
opened, so nothing here needs more than a few MiB. Examples are drawn with recorded seeds and
the draw is written to docs/datasets/gt21/figures/page_figures.json.

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
      nice -n 19 ionice -c 3 python3 contributor_tools/figures_gt21_page.py [--only NAME ...]

Not run when it was written (another worker held the guarded launcher). It is read-only apart
from the figure files and page_figures.json, and it stops if its peak memory exceeds 300 MiB.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import resource
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "docs/quality/audits"
HAND = ROOT / "docs/maintainers/handoffs"
PKG = ROOT / "converted_datasets/reconversion_v2/gt21_r01_package_v1"
OUT = ROOT / "docs/datasets/gt21/figures"
MAX_JSON_BYTES = 20 * 1024 * 1024
MAX_RSS_MIB = 300

BLUE, ORANGE, VERMIL, GREEN, SKY, GREY, DARK = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#56B4E9", "#8c8c8c", "#333333"
SEED_EARLY_HS = 20261201
PNG_DIR = None
PROVENANCE: dict = {"script": "contributor_tools/figures_gt21_page.py"}

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "legend.fontsize": 10, "svg.fonttype": "path", "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 100, "axes.grid": False,
})


def load(path: Path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise RuntimeError(f"{path} is larger than {MAX_JSON_BYTES} bytes; this script only reads small evidence files")
    return json.loads(path.read_text(encoding="utf-8"))


def new(height: float):
    fig, ax = plt.subplots(figsize=(4.5, height), layout="constrained")
    return fig, ax


def save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, format="svg")
    if PNG_DIR is not None:  # a look-at-it copy for review; the page uses the SVG
        PNG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(PNG_DIR / (Path(name).stem + ".png"), format="png", dpi=110)
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def plain_signal(ch: str) -> str:
    base = ch.split("_")[0].capitalize()
    side = ("left" if "_left_" in ch else "right" if "_right_" in ch else "this leg" if "_ipsi_" in ch
            else "other leg" if "_contra_" in ch else "")
    return f"{base} angle, {side}" if side else f"{base} angle"


def participant_label(ax, names, rotation=90):
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=rotation)


# ---------- overview figures ----------
def page_failures():
    t = load(AUD / "gt21-q01-summary.json")["totals_per_check"]
    rows = [("Joint range", t["L1"]["failed"]), ("Sudden 30° jump", t["L2"]["failed"]),
            ("Pressure point", t["L5"]["failed"]), ("Left-right side check", t["S5"]["failed"])]
    fig, ax = new(2.3)
    ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1], color=VERMIL)
    for i, v in enumerate([r[1] for r in rows][::-1]):
        ax.text(v, i, f" {v:,}", va="center")
    ax.set_xlabel("Observations that fail the limit")
    ax.set_xlim(0, max(r[1] for r in rows) * 1.2)
    save(fig, "page-failures.svg")


def page_left_out():
    c = load(PKG / "manifest.json")["counts"]["exclusions_by_kind"]
    rows = [("Authors' rule: dropped", c["authors_rule_discard"], DARK),
            ("Authors' rule: no matching case", c["authors_rule_case_not_found"], DARK),
            ("Recording not converted", c["recording_not_converted_in_pass"], DARK),
            ("Too few fitted markers", c["recording_excluded_marker_fit"], DARK),
            ("Failed a limit (cleaned only)", c["assessment_failed"], ORANGE)]
    fig, ax = new(2.6)
    ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1], color=[r[2] for r in rows][::-1])
    ax.set_xscale("log")
    ax.set_xlim(0.7, 2e5)
    for i, r in enumerate(rows[::-1]):
        ax.text(r[1] * 1.15, i, f"{r[1]:,}", va="center")
    ax.set_xlabel("Strides or recordings (log scale)")
    save(fig, "page-left-out.svg")


LIMIT_SHORT = {
    "held_frames_in_angles": "Held frames (angles missing)", "plate_dropout_samples": "Plate dropout flags",
    "early_source_heel_strike_short_left_stance": "Early heel strikes", "left_stance_unavailable_no_toe_off": "No left toe-off",
    "left_treadmill_stance_from_belt_force": "Left toe-off rebuilt", "incomplete_stance_force": "Stance force masked",
    "authors_rule_extended_to_left_leg": "Authors' rule on left leg", "ab27_right_thigh_held_frames": "AB27 right thigh",
    "ab28_pelvis_angle_offset": "AB28 pelvis offset", "p1_unchecked": "Plane glitch not checked",
    "ankle_zero_offset_unreviewed": "Ankle zero unreviewed", "source_is_authors_2024_copy": "Authors' 2024 copy",
    "power_from_moment_and_speed": "Power = moment x speed", "authors_rule_exclusions": "Left out by export",
}


def page_limitations():
    lim = load(PKG / "limitations.json")["limitations"]
    rows = sorted(((LIMIT_SHORT[x["id"]], x["observations"]) for x in lim), key=lambda r: r[1])
    fig, ax = new(4.2)
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=BLUE)
    for i, r in enumerate(rows):
        ax.text(r[1], i, f" {r[1]:,}", va="center")
    ax.set_xlim(0, max(r[1] for r in rows) * 1.3)
    ax.set_xlabel("Observations touched")
    save(fig, "page-limitations.svg")


# ---------- card figures ----------
def toe_off_belt():
    belt = {k: v for k, v in load(AUD / "gt21-rb06-belt-evidence.json").items() if k.startswith("AB")}
    fig, ax = new(3.4)
    ax.plot([0, 1], [0, 1], color=GREY, lw=1, ls="--")
    for side, color, label in (("right", BLUE, "Right foot"), ("left", VERMIL, "Left foot")):
        ax.scatter([v[side]["belt_loaded_fraction_median"] for v in belt.values()],
                   [v[side]["source_toe_off_fraction_median"] for v in belt.values()], color=color, label=label, s=22)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Fraction of the stride the belt is loaded")
    ax.set_ylabel("Source toe-off, fraction of stride")
    ax.legend(loc="lower right", frameon=False)
    save(fig, "gt21-toe-off-belt.svg")


def toe_off_right_check():
    per = load(AUD / "gt21-rb07-right-foot-rule.json")["per_participant"]
    names = sorted(per)
    fig, ax = new(3.2)
    ax.scatter(range(len(names)), [per[k]["p95_abs_error_ms"] for k in names], color=BLUE, label="95th percentile", s=22)
    ax.scatter(range(len(names)), [per[k]["worst_abs_error_ms"] for k in names], color=ORANGE, marker="^", label="Worst stride", s=26)
    participant_label(ax, names)
    ax.set_ylabel("Toe-off error, right foot (ms)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", frameon=False)
    save(fig, "gt21-toe-off-right-check.svg")


def early_heel_strike():
    short = load(AUD / "gt21-rb07-short-left-stances.json")
    excluded = set(load(AUD / "gt21-q01-summary.json")["short_stance_cross_check"]["excluded_in_export"])
    pool = [(p, e) for p, lst in sorted(short.items()) if isinstance(lst, list) for e in lst
            if e["stance_samples"] is not None and e["stance_unavailable"] is None and e["step_id"] not in excluded]
    rng = random.Random(SEED_EARLY_HS)
    drawn = sorted(rng.sample(pool, min(8, len(pool))), key=lambda pe: pe[1]["step_id"])
    PROVENANCE["early_heel_strike"] = {"seed": SEED_EARLY_HS, "pool": len(pool), "drawn": [e["step_id"] for _, e in drawn]}
    fig, ax = new(3.2)
    for i, (_, e) in enumerate(drawn):
        y = [e["force_at_heel_strike_N"]] + list(e["force_next_samples_N"])
        ax.plot(range(len(y)), y, color=BLUE, alpha=.8, lw=1.2, marker="o", ms=3, label="One stride" if i == 0 else None)
    ax.axhline(20, color=VERMIL, ls="--", lw=1.2, label="20 N contact rule")
    ax.set_xlabel("Samples after the source heel strike (200 Hz)")
    ax.set_ylabel("Left belt force (N)")
    ax.legend(loc="upper right", frameon=False)
    save(fig, "gt21-early-heel-strike.svg")


def plate_dropout():
    by = load(AUD / "gt21-q01-summary.json")["plate_dropout"]["by_participant"]
    names = sorted(by)
    fig, ax = new(3.0)
    ax.bar(range(len(names)), [by[k]["samples"] for k in names], color=BLUE)
    participant_label(ax, names)
    ax.set_ylabel("Dropout samples flagged")
    save(fig, "gt21-plate-dropout.svg")


def held_frames():
    text = load(HAND / "GT21-RB02-RB04.json")["held_frames"]
    pairs = re.findall(r"(AB\d{2}) (\d+(?:\.\d+)?)", text)
    if len(pairs) != 22:
        raise RuntimeError(f"expected 22 participants in the held-frame text, found {len(pairs)}")
    fig, ax = new(3.0)
    ax.bar(range(len(pairs)), [float(v) for _, v in pairs], color=[ORANGE if n == "AB27" else BLUE for n, _ in pairs])
    ax.axhline(3.9, color=DARK, ls="--", lw=1, label="All participants: 3.9%")
    participant_label(ax, [n for n, _ in pairs])
    ax.set_ylabel("Leg-frames held (%)")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "gt21-held-frames.svg")


def stance_mask():
    rb05 = load(HAND / "GT21-RB05.json")["results"]
    total = next(x["observations"] for x in load(PKG / "limitations.json")["limitations"] if x["id"] == "incomplete_stance_force")
    counts = dict(rb05["incomplete_stance_force"])
    counts["treadmill"] = total - sum(v for k, v in counts.items() if k != "treadmill")
    if counts["treadmill"] < 0:
        raise RuntimeError("masked-stance counts by mode exceed the package total")
    modes = ["levelground", "ramp", "stair", "treadmill"]
    names = {"levelground": "Level ground", "ramp": "Ramps", "stair": "Stairs", "treadmill": "Treadmill"}
    share = [100 * counts[m] / rb05["phase_observations_by_mode"][m] for m in modes]
    fig, ax = new(2.6)
    ax.bar([names[m] for m in modes], share, color=BLUE)
    for i, (m, s) in enumerate(zip(modes, share)):
        ax.text(i, s + 1.5, f"{s:.1f}%\n({counts[m]:,})", ha="center", va="bottom")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Strides with force masked (%)")
    save(fig, "gt21-stance-mask.svg")


def jumps_by_signal():
    f = load(AUD / "gt21-q01-summary.json")["failed_samples_by_limit_and_channel"]
    rows = sorted(((plain_signal(k.split(":", 2)[2]), v) for k, v in f.items() if k.startswith("time:L2:")), key=lambda r: r[1])
    fig, ax = new(3.6)
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=[VERMIL if "Pelvis" in r[0] else BLUE for r in rows])
    ax.set_xlabel("Samples with a jump of 30° or more")
    save(fig, "gt21-jumps-by-signal.svg")


def ankle_extremes_by_signal():
    f = load(AUD / "gt21-q01-summary.json")["failed_samples_by_limit_and_channel"]
    rows = sorted(((plain_signal(k.split(":", 2)[2]), v) for k, v in f.items() if k.startswith("time:L1:")), key=lambda r: r[1])
    fig, ax = new(2.8)
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=[VERMIL if "Ankle" in r[0] else BLUE for r in rows])
    ax.set_xlabel("Samples outside the joint limit")
    save(fig, "gt21-ankle-extremes-by-signal.svg")


def ankle_worst_values():
    worst = load(AUD / "gt21-q01-summary.json")["worst_examples"]
    vals = [w["value"] for w in worst if w["limit"] == "L1"]
    fig, ax = new(2.2)
    ax.axvspan(-80, 50, color=SKY, alpha=.35, label="Allowed ankle range")
    ax.scatter(vals, [0] * len(vals), color=VERMIL, s=26, label="Ten largest values")
    ax.set_xlim(-100, 190)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Ankle angle (degrees)")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "gt21-ankle-worst-values.svg")


def crossing_steps():
    by = load(HAND / "GT21-RB03.json")["rule_A"]["results"]["by_mode"]
    modes = ["levelground", "ramp", "stair", "treadmill"]
    names = {"levelground": "Level ground", "ramp": "Ramps", "stair": "Stairs", "treadmill": "Treadmill"}
    fig, ax = new(2.8)
    kept = [by[m]["eligible"] for m in modes]
    left = [by[m]["excluded"] for m in modes]
    ax.bar([names[m] for m in modes], kept, color=BLUE, label="Exported")
    ax.bar([names[m] for m in modes], left, bottom=kept, color=ORANGE, label="Left out")
    for i, (k, x) in enumerate(zip(kept, left)):
        ax.text(i, k + x, f"{100 * x / (k + x):.0f}% left out", ha="center", va="bottom")
    ax.set_ylim(0, max(k + x for k, x in zip(kept, left)) * 1.18)
    ax.set_ylabel("Source steps")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "gt21-crossing-steps.svg")


def pelvis_vs_model():
    d = load(AUD / "gt21-rb04-pelvis-vs-ik.json")
    earlier = [r["rms_deg_after_median_removal"] for r in d["c01_recordings"]]
    seeded = [r["rms_deg_after_median_removal"] for r in d["seeded_new_participants"]]
    fig, ax = new(2.8)
    lo, hi = d["summary"]["c01_range_rms_deg"]
    ax.axhspan(lo, hi, color=SKY, alpha=.35, label="Range seen in the earlier review")
    ax.scatter(range(len(earlier)), earlier, color=BLUE, s=24, label="8 recordings, earlier review")
    ax.scatter(range(len(earlier), len(earlier) + len(seeded)), seeded, color=ORANGE, s=24, label="24 recordings drawn with a seed")
    ax.set_xticks([])
    ax.set_xlabel("Recordings")
    ax.set_ylabel("Pelvis angle difference (° RMS)")
    ax.set_ylim(0, 3.4)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    PROVENANCE["pelvis_vs_model"] = {"seed_in_source_file": d["seed"]}
    save(fig, "gt21-pelvis-vs-model.svg")


def power_check():
    lim = next(x for x in load(PKG / "limitations.json")["limitations"] if x["id"] == "power_from_moment_and_speed")
    rows = lim["check"]
    short = {"hip": "Hip", "knee": "Knee", "ankle": "Ankle"}
    label = lambda r: f"{r['table'].capitalize()}: {short[r['power_column'].split('_')[0]]} {r['power_column'].split('_')[-3]}"  # noqa: E731
    fig, ax = new(3.6)
    ax.barh([label(r) for r in rows][::-1], [r["rows_power_finite"] / 1e6 for r in rows][::-1], color=BLUE)
    for i, r in enumerate(rows[::-1]):
        ax.text(r["rows_power_finite"] / 1e6, i, f" {r['rows_deviating']} differ", va="center")
    ax.set_xlim(0, 15)
    ax.set_xlabel("Rows with a power value (millions)")
    save(fig, "gt21-power-check.svg")


def source_compared():
    lim = load(PKG / "limitations.json")["limitations"]
    people = next(x for x in lim if x["id"] == "held_frames_in_angles")["participants"]
    done = set(next(x for x in lim if x["id"] == "source_is_authors_2024_copy")["participants_compared_with_2021_archive"])
    t = load(HAND / "GT21-S02.json")["ab17_acquisition"]["crc_comparison"]["totals"]
    fig, ax = new(2.8)
    for i, p in enumerate(people):
        r, c = divmod(i, 11)
        ax.add_patch(plt.Rectangle((c, 1 - r), .9, .8, color=BLUE if p in done else "#d9d9d9"))
        ax.text(c + .45, 1 - r + .4, p[2:], ha="center", va="center", color="white" if p in done else DARK)
    ax.set_xlim(0, 11)
    ax.set_ylim(-1.3, 2)
    ax.axis("off")
    ax.text(0, -.4, "Blue: compared with the 2021 archive.\nGrey: not compared.\n"
            f"AB17 files: {t['identical_size_and_crc32']:,} identical,\n{t['size_differs']} differ, "
            f"{t['mirror_only']} only in the 2024 copy.", va="top")
    save(fig, "gt21-source-compared.svg")


def checks_run():
    t = load(AUD / "gt21-q01-summary.json")["totals_per_check"]
    order = [("L1", "Joint range"), ("L2", "Sudden 30° jump"), ("L4", "Missing values"), ("L5", "Pressure point"),
             ("P1", "Plane glitch"), ("PD", "Plate dropout"), ("S1", "Grid and clock"), ("S2", "Identity fields"),
             ("S3", "Constant metadata"), ("S4", "Span inside recording"), ("S5", "Left-right side check")]
    states = [("passed", BLUE, "Passed"), ("failed", VERMIL, "Failed"), ("missing", ORANGE, "Missing"), ("unchecked", GREY, "Not checked")]
    fig, ax = new(3.8)
    for row, (code, name) in enumerate(order[::-1]):
        total = sum(t[code].values())
        left = 0.0
        for key, color, label in states:
            v = t[code].get(key, 0)
            if v:
                ax.barh(row, 100 * v / total, left=left, color=color, label=label)
                left += 100 * v / total
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([n for _, n in order[::-1]])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of observations (%)")
    h, l = ax.get_legend_handles_labels()
    uniq = dict(zip(l, h))
    ax.legend(uniq.values(), uniq.keys(), loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=10)
    save(fig, "gt21-checks-run.svg")


FIGURES = {f.__name__: f for f in (
    page_failures, page_left_out, page_limitations, toe_off_belt, toe_off_right_check, early_heel_strike, plate_dropout,
    held_frames, stance_mask, jumps_by_signal, ankle_extremes_by_signal, ankle_worst_values, crossing_steps,
    pelvis_vs_model, power_check, source_compared, checks_run)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--png-dir", type=Path, help="also write PNG copies here, for looking at the figures")
    ap.add_argument("--only", nargs="*", choices=sorted(FIGURES), help="draw only these figures")
    args = ap.parse_args(argv)
    global PNG_DIR
    PNG_DIR = args.png_dir
    for name in args.only or FIGURES:
        FIGURES[name]()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "page_figures.json").write_text(json.dumps(PROVENANCE, indent=1, sort_keys=True), encoding="utf-8")
    rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"peak RSS {rss_mib:.0f} MiB")
    if rss_mib > MAX_RSS_MIB:
        print(f"over the {MAX_RSS_MIB} MiB budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
