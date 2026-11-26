#!/usr/bin/env python3
"""Figures for the new time-table and ground-force cards on the UMich 2021 page (page_specs/um21.json, extra_cards).

One panel per image, at most 4.5 in wide, fonts of at least 10 pt, SVG under docs/datasets/um21/figures/.
Inputs are small files only: the package's manifest.json and two small evidence CSVs, plus numbers quoted
from docs/maintainers/handoffs/UM21-T05-verify.json (hard-coded below with their source named). No parquet
table is opened. The under-20-N figure is a labelled made-up example, not data.

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg \
      prlimit --as=$((600*1024*1024)) -- nice -n 19 ionice -c 3 python3 contributor_tools/figures_um21_t05_page.py
"""
from __future__ import annotations

import csv
import json
import resource
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "converted_datasets/reconversion_v2/um21_r01_package_v5"
OUT = ROOT / "docs/datasets/um21/figures"
BLUE, ORANGE, VERMIL, GREY = "#0072B2", "#E69F00", "#D55E00", "#8c8c8c"

plt.rcParams.update({"font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "legend.fontsize": 10, "svg.fonttype": "path", "axes.spines.top": False, "axes.spines.right": False})


def new(h):
    return plt.subplots(figsize=(4.5, h), layout="constrained")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, format="svg")
    plt.close(fig)
    print("wrote", name)


def tables():
    c = json.loads((PKG / "manifest.json").read_text())["counts"]
    fig, ax = new(2.4)
    labels = ["Phase, full", "Phase, cleaned", "Time, full", "Time, cleaned"]
    vals = [c["full"]["phase_rows"], c["filtered"]["phase_rows"], c["full"]["time_rows"], c["filtered"]["time_rows"]]
    ax.barh(labels[::-1], [v / 1e6 for v in vals[::-1]], color=[ORANGE, ORANGE, BLUE, BLUE])
    for i, v in enumerate(vals[::-1]):
        ax.text(v / 1e6 + 0.02, i, f"{v:,}", va="center")
    ax.set_xlim(0, 1.8)
    ax.set_xlabel("Rows (millions of samples)")
    save(fig, "um21-time-tables.svg")


def under20():
    t = np.linspace(0, 0.8, 400)
    f = 700 * np.sin(np.pi * t / 0.8) ** 1.5 + 6 * np.sin(40 * t)  # made-up stance force, newtons
    fig, ax = new(2.8)
    ax.plot(t, f, color=GREY, lw=3, alpha=0.4, label="Made-up plate signal")
    um = np.where(f < 20, 0.0, f)
    ax.plot(t, um, color=ORANGE, lw=1.6, label="UMich 2021: 0 under 20 N")
    gt = np.where(f < 20, np.nan, f)
    ax.plot(t, gt + 6, color=BLUE, lw=1.6, label="Georgia Tech 2021: empty (shifted up 6 N)")
    ax.axhline(20, color="k", lw=0.8, ls="--")
    ax.text(0.605, 26, "20 N")
    ax.set_xlim(0.6, 0.81)
    ax.set_ylim(-8, 150)
    ax.set_xlabel("Time (s), end of stance; made-up example, not data")
    ax.set_ylabel("Force (N)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=1)
    save(fig, "um21-under-20n.svg")


def force_held():
    rows = list(csv.DictReader((PKG / "evidence/time_force_and_cop_legs.csv").open()))
    pub = sum(r["force_published"] == "True" for r in rows)
    pend = sum("held-back" in r["force_reason"] for r in rows)
    load = sum("fewer than 95" in r["force_reason"] for r in rows)
    assert pub + pend + load == len(rows) == 88
    fig, ax = new(2.2)
    ax.barh(["Published", "Held: pending ruling\n(5 recordings)", "Held: plate loaded\nat under 95% of steps\n(AB04, 5° incline)"][::-1],
            [pub, pend, load][::-1], color=[VERMIL, ORANGE, BLUE])
    for i, v in enumerate([load, pend, pub]):
        ax.text(v + 1, i, str(v), va="center")
    ax.set_xlim(0, 95)
    ax.set_xlabel("Legs (of 88)")
    save(fig, "um21-force-held.svg")


def time_jump():
    rows = list(csv.DictReader((PKG / "evidence/time_l2_jumps.csv").open()))
    fig, ax = new(2.6)
    names = [f"{'Foot' if r['channel'].startswith('foot') else 'Ankle'} angle, sample {r['frame']}" for r in rows]
    ax.barh(names[::-1], [abs(float(r["value_deg"])) for r in rows][::-1], color=VERMIL)
    ax.axvline(30, color="k", ls="--", lw=0.8)
    ax.text(30.5, -0.45, "limit 30°", va="bottom")
    ax.set_xlim(0, 55)
    ax.set_xlabel("Jump to the next sample (degrees)")
    save(fig, "um21-time-jump.svg")


def cop_noise():
    # Quoted from UM21-T05-verify.json tolerance_choices.T05-H: frame-to-frame noise, anterior, in mm.
    fig, ax = new(2.0)
    ax.barh(["AB04, 10° incline,\nright leg", "Four other legs\n(0.06 to 0.11 mm)"], [3.0, 0.11], color=[VERMIL, BLUE])
    ax.set_xlabel("Sample-to-sample noise (mm)")
    ax.text(3.05, 0, "3.0", va="center")
    ax.set_xlim(0, 3.6)
    save(fig, "um21-cop-noise.svg")


def shortfall():
    # Quoted from UM21-T05-verify.json force.units_and_frame: two-leg vertical sum, body weights.
    names = ["Median of 38 recordings", "10th percentile", "AB03, 10° decline", "AB10, 10° decline", "AB03, 5° decline"]
    vals = [0.994, 0.949, 0.912, 0.923, 0.931]
    fig, ax = new(2.5)
    ax.barh(names[::-1], vals[::-1], color=[VERMIL, VERMIL, VERMIL, GREY, GREY])  # recordings with a shortfall (orange-red) vs the spread of all recordings (grey)
    ax.axvline(1.0, color="k", ls="--", lw=0.8)
    for i, v in enumerate(vals[::-1]):
        ax.text(0.8 + 0.005, i, f"{v:.3f}", va="center", color="white")
    ax.set_xlim(0.8, 1.02)
    ax.set_xlabel("Two-leg vertical force (body weights)")
    save(fig, "um21-plate-shortfall.svg")


def left_out():
    byr = json.loads((PKG / "manifest.json").read_text())["counts"]["exclusions_by_reason"]
    rows = [("Pressure point too far\nfrom foot (strides)", byr["assessment_failed"]["L5"], VERMIL),
            ("Stride too short or\ntoo long (strides)", byr["upstream_stride_rule"]["t04_2_outside_stride_rule"], GREY),
            ("Sudden ankle jump\n(strides)", byr["upstream_sudden_jump"]["c03_2_sudden_jump"], GREY),
            ("Ankle outside possible\nrange (stride)", byr["assessment_failed"]["L1"], VERMIL),
            ("Sudden jump in a time\nrecording (recording)", byr["assessment_failed"]["L2"], VERMIL)]
    fig, ax = new(3.0)
    ax.barh([r[0] for r in rows][::-1], [r[1] for r in rows][::-1], color=[r[2] for r in rows][::-1])
    for i, r in enumerate(rows[::-1]):
        ax.text(r[1] + 0.3, i, str(r[1]), va="center")
    ax.set_xlim(0, 25)
    ax.set_xlabel("Items left out")
    save(fig, "um21-left-out-v5.svg")


if __name__ == "__main__":
    for fn in (left_out, tables, under20, force_held, time_jump, cop_noise, shortfall):
        fn()
    print("peak RSS MiB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
