#!/usr/bin/env python3
"""Draw the figures for docs/datasets/gt21/problems.html.

Writes matplotlib SVGs to docs/datasets/gt21/figures/ in the style of the UMich 2021 figures
(same fonts and colors, 4.5 in wide, fonts at least 10 pt). Reads only
docs/quality/audits/gt21-problem-scope.json: the grids, and the example data that the scope builder
drew with a recorded random seed. Opens no recording.

  scope-<problem>.svg   participant x task grid for every problem card
  force-sign, sideways, pelvis, zero, mass, steps, terrain, plates, heading   one extra figure each
  figures.json          seeds and what each example drew

Usage: python3 contributor_tools/build_gt21_problem_figures.py
"""
from __future__ import annotations

import io
import json
import math
import random
from pathlib import Path

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "docs/quality/audits/gt21-problem-scope.json"
FIG_DIR = ROOT / "docs/datasets/gt21/figures"
INK, MUTED, GREY = "#20252b", "#5b6672", "#b4bcc4"
BEFORE, AFTER = "#c4501a", "#1f6aa5"
W = 4.5
plt.rcParams.update({
    "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "text.color": INK, "axes.labelcolor": INK,
    "axes.edgecolor": INK, "xtick.color": INK, "ytick.color": INK, "legend.frameon": False, "axes.linewidth": 0.7,
    "svg.hashsalt": "locohub-gt21-problems", "svg.fonttype": "path", "figure.facecolor": "white", "axes.facecolor": "white",
    "hatch.linewidth": 0.6})


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None})
    (FIG_DIR / name).write_bytes(buf.getvalue())
    plt.close(fig)


def mix(pct, base_hex):
    t = 0.3 + 0.7 * min(max(pct, 0.0), 100.0) / 100.0
    base = np.array([int(base_hex[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    return tuple((255 * (1 - t) + base * t) / 255)


def grid_figure(prob):
    g = prob["grid"]
    rows, cols, kind = g["rows"], g["cols"], g["kind"]
    base = BEFORE if kind == "affected" else AFTER
    fig, ax = plt.subplots(figsize=(W, 0.255 * len(rows) + 1.75), layout="constrained")
    ax.set_xlim(0, len(cols))
    ax.set_ylim(len(rows), 0)
    used = set()
    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            v = g["cells"][f"{r}/{c}"]
            box = dict(xy=(ci + .06, ri + .06), width=.88, height=.88)
            if v is None:
                ax.add_patch(plt.Rectangle(**box, fill=False, ec=GREY, lw=0.8, ls=(0, (2, 2))))
                used.add("none")
            elif v == "pending":
                ax.add_patch(plt.Rectangle(**box, fc="#dfe3e7", ec=GREY, lw=0.5, hatch="xx"))
                used.add("pending")
            elif v == "nc":
                ax.add_patch(plt.Rectangle(**box, fc="#fff3cf", ec="#d9c27a", lw=0.5))
                ax.text(ci + .5, ri + .52, "?", ha="center", va="center", fontsize=10, color="#7a6200")
                used.add("nc")
            elif v == 0:
                ax.add_patch(plt.Rectangle(**box, fc="#dfe3e7", ec="none"))
                used.add("zero")
            else:
                ax.add_patch(plt.Rectangle(**box, fc=mix(v, base), ec="none"))
                label = f"{v:.0f}" if v >= 1 else "<1"
                ax.text(ci + .5, ri + .52, label, ha="center", va="center", fontsize=10, color="white" if v >= 55 else INK)
                used.add("value")
    ax.set_xticks([i + .5 for i in range(len(cols))])
    ax.set_xticklabels([c.replace(" ", "\n", 1) if c == "Level walking" else c for c in g["cols_plain"]])
    ax.xaxis.tick_top()
    ax.set_yticks([i + .5 for i in range(len(rows))])
    ax.set_yticklabels(["Six more" if r == "SIX" else r for r in rows])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    R = lambda **k: plt.Rectangle((0, 0), 1, 1, **k)  # noqa: E731
    h = []
    if "value" in used:
        h.append(R(fc=mix(100, base), label="Affected (number = % of its recordings)" if kind == "affected" else "Looked at (number = % of its recordings)"))
    if "zero" in used:
        h.append(R(fc="#dfe3e7", label="Checked, not affected" if kind == "affected" else "Not looked at"))
    if "nc" in used:
        h.append(R(fc="#fff3cf", ec="#d9c27a", label="Not checked (?)"))
    if "pending" in used:
        h.append(R(fc="#dfe3e7", ec=GREY, hatch="xx", label="Not converted yet"))
    if "none" in used:
        h.append(R(fill=False, ec=GREY, ls=(0, (2, 2)), label="No such recordings"))
    fig.legend(handles=h, loc="outside lower left", ncols=1, handlelength=1.6)
    save(fig, f"scope-{prob['key']}.svg")


def force_sign(fd):
    rng = random.Random(fd["seed"] + 1)  # horizontal jitter only
    fig, ax = plt.subplots(figsize=(W, 2.5), layout="constrained")
    for y, key, col, lab in ((1, "error_sign_a", BEFORE, "Forward force assumed positive"), (0, "error_sign_b", AFTER, "Forward force assumed negative")):
        xs = [max(d[key], 1e-17) for d in fd["force_sign_draw"]]
        ys = [y + rng.uniform(-.18, .18) for _ in xs]
        ax.scatter(xs, ys, s=26, color=col, alpha=.85, label=lab, linewidths=0)
    ax.set_xscale("log")
    ax.set_xlim(1e-17, 1)
    ax.set_ylim(-.6, 1.6)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Largest error over the leg's stance (body weights)")
    ax.text(1e-17, 1.45, "better match is to the left", fontsize=10, color=MUTED, ha="left", va="center")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handletextpad=.3)
    save(fig, "force-sign.svg")


def sideways(fd):
    p = fd["probe_curve"]
    x = np.linspace(0, 100, 100)
    fig, ax = plt.subplots(figsize=(W, 3.1), layout="constrained")
    ax.axhline(0, color=GREY, lw=.6, zorder=0)
    ax.plot(x, p["right"], color=BEFORE, lw=2.2, label="Right foot (right plate)")
    ax.plot(x, p["left"], color=AFTER, lw=2.2, label="Left foot (left plate)")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Position in stance (%)")
    ax.set_ylabel("Sideways force on the\nlab X axis (N)")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=2.2)
    save(fig, "sideways.svg")


def pelvis(fd):
    rows = fd["pelvis"]
    fig, ax = plt.subplots(figsize=(W, 4.6), layout="constrained")
    y = np.arange(len(rows))[::-1]
    hgt = .26
    for off, key, col, lab in ((hgt, "published_tilt", BEFORE, "Published pelvis tilt"), (0, "minus_list", GREY, "Minus pelvis list"), (-hgt, "heading_removed", AFTER, "Source tilt, heading removed")):
        ax.barh(y + off, [r[key] for r in rows], height=hgt, color=col, label=lab)
    ax.axvline(0, color=INK, lw=.7)
    ax.axvline(1, color=GREY, lw=.7, ls=(0, (3, 3)))
    ax.set_yticks(y)
    ax.set_yticklabels([r["who"].replace(" walking", "") for r in rows])
    ax.set_xlim(-.8, 1.0)
    ax.set_xlabel("Stride-average agreement with marker tilt\n(1 = identical, dashed line)")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=1.4)
    save(fig, "pelvis.svg")


def zero():
    x = np.linspace(0, 100, 150)
    knee = 5 + 28 * np.exp(-((x - 15) / 9) ** 2) + 55 * np.exp(-((x - 72) / 12) ** 2)
    fig, ax = plt.subplots(figsize=(W, 3.1), layout="constrained")
    ax.plot(x, knee, color=INK, lw=2.2, label="Zero at the model's zero")
    ax.plot(x, knee - 12, color=AFTER, lw=2.2, ls="--", label="Zero at a static pose (made-up shift)")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Position in the stride (%)")
    ax.set_ylabel("Knee angle (degrees)")
    ax.text(2, ax.get_ylim()[1] - 2, "MADE-UP EXAMPLE", ha="left", va="top", color=BEFORE, fontsize=10, fontweight="bold")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=2.2)
    save(fig, "zero.svg")


def mass(fd):
    w, six = fd["weights"], set(fd["six"])
    rng = random.Random(7)
    fig, ax = plt.subplots(figsize=(W, 2.6), layout="constrained")
    for sid, v in w.items():
        yy = rng.uniform(-.25, .25)
        if sid in six:
            ax.scatter([v], [yy], s=46, facecolors="white", edgecolors=BEFORE, linewidths=1.4, zorder=3)
        else:
            ax.scatter([v], [yy], s=46, color=AFTER, zorder=3, linewidths=0)
    lo, hi = min(w, key=w.get), max(w, key=w.get)
    ax.annotate(f"{lo}  {w[lo]:.2f}", (w[lo], 0), xytext=(w[lo], .85), ha="left", fontsize=10, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.annotate(f"{hi}  {w[hi]:.2f}", (w[hi], 0), xytext=(w[hi], .85), ha="right", fontsize=10, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_ylim(-.6, 1.3)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Weight number in the subject sheet (no unit stated)")
    h = [plt.Line2D([], [], marker="o", ls="", color=AFTER, label="Local participant"), plt.Line2D([], [], marker="o", ls="", mfc="white", mec=BEFORE, label="Not converted yet")]
    fig.legend(handles=h, loc="outside lower left", ncols=2, handletextpad=.2, columnspacing=1)
    save(fig, "mass.svg")


def stacked(name, labels, series, colors, legend, height, note=None):
    fig, ax = plt.subplots(figsize=(W, height), layout="constrained")
    y = np.arange(len(labels))[::-1]
    left = np.zeros(len(labels))
    for vals, col, lab in zip(series, colors, legend):
        ax.barh(y, vals, left=left, color=col, label=lab, height=.55)
        left += np.array(vals, dtype=float)
    totals = [sum(sr[i] for sr in series) for i in range(len(labels))]
    for yi, i in zip(y, range(len(labels))):
        ax.text(totals[i], yi, "  " + " + ".join(f"{sr[i]:,.0f}" for sr in series if len(series) > 1 or True), va="center", ha="left", fontsize=10, color=INK)
    ax.set_xlim(0, max(totals) * 1.45)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4))
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(note or "")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=1.4)
    save(fig, name)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    P = {p["key"]: p for p in scope["problems"]}
    for p in scope["problems"]:
        grid_figure(p)
    force_sign(P["plate_and_sign"]["figure_data"])
    sideways(P["sideways"]["figure_data"])
    pelvis(P["pelvis"]["figure_data"])
    zero()
    mass(P["mass_unit"]["figure_data"])
    s = P["opposite_leg"]["figure_data"]["steps"]
    stacked("steps.svg", ["36 recordings"], [[s["exported"]], [s["opposite_reference_leg_not_exported"]], [s["outside_complete_eligible_task_window"]]],
            [AFTER, BEFORE, GREY], ["Exported", "Qualifies, not exported (other leg)", "Outside a complete task window"], 2.6, "Source steps")
    t = P["terrain_defaults"]["figure_data"]
    stacked("terrain.svg", ["Ramps", "Stairs"], [[t["ramp"], t["stair"]], [0, 0]], [AFTER, BEFORE], ["Label and size present", "Missing or invalid (0 of 1,680)"], 2.5, "Recordings")
    pl = P["no_plate"]["figure_data"]["plates"]
    modes = [("levelground", "Level walking"), ("ramp", "Ramps"), ("treadmill", "Treadmill")]
    stacked("plates.svg", [m[1] for m in modes], [[pl[m[0]]["assigned"] for m in modes], [pl[m[0]]["no_supported_plate"] for m in modes]], [AFTER, BEFORE],
            ["Leg-step matched to a plate", "No supported plate (force left missing)"], 2.9, "Leg-steps in completed recordings")
    hd = P["forward_direction"]["figure_data"]["heading"]
    stacked("heading.svg", ["Facing −Z", "Facing +Z", "Along X"], [[hd["faces lab -Z"], hd["faces lab +Z"], hd["walks along lab ±X"]]], [AFTER], ["On-plate samples in 8 recordings"], 2.4, "Samples with a foot on a plate")
    (FIG_DIR / "figures.json").write_text(json.dumps({
        "seed": scope["seed"], "script": "contributor_tools/build_gt21_problem_figures.py",
        "how_chosen": "Examples are drawn at random with recorded seeds, never hand-picked.",
        "force_sign": {"seed": scope["seed"], "drew": "24 of 228 legs of one treadmill pilot recording", "indices": [d["index"] for d in P["plate_and_sign"]["figure_data"]["force_sign_draw"]]},
        "sideways": {"seed": P["sideways"]["figure_data"]["probe_curve"]["seed"], "drew": "3 treadmill recordings; the first drawn is plotted", "who": P["sideways"]["figure_data"]["probe_curve"]["who"]},
        "pelvis": {"seed": 20261027, "drew": "8 recordings, 2 per task, drawn by the earlier conventions review"},
        "heading": {"seed": 20261027, "drew": "the same 8 recordings"},
        "zero": "made-up illustration, labelled", "others": "totals from audits, no draw",
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("figures written to", FIG_DIR.relative_to(ROOT))


if __name__ == "__main__":
    main()
