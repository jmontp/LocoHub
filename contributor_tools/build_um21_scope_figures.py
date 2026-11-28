#!/usr/bin/env python3
"""Draw the figures for the UMich 2021 fix cards that the fixes page does not have.

Writes SVGs to docs/datasets/um21/figures/ (matplotlib, same fonts, colors and 4.5 in width as
docs/quality/fixes/um21-*.svg, fonts at least 10 pt):
  scope-<fix>.svg   grid of participants x tasks shaded by the share of strides affected
                    (data: docs/quality/audits/um21-r01-fix-scope.json)
  sign-before.svg, sign-after.svg   one stride of pelvis tilt as published and after the flip
  power-before.svg, power-after.svg one stride of ankle power against moment x joint speed,
                                    before and after the sign is set
  figures.json      the seed and the stride each example drew (examples are drawn at random
                    with a recorded seed, never hand-picked)

The two example stride pairs read ONE stride each from the local review bundle's full.parquet,
row group by row group (3,000 rows each; pyarrow system pool, no threads, no read buffer).
Run alone at nice 19 / ionice idle. Nothing is written under converted_datasets/.

Usage: ARROW_DEFAULT_MEMORY_POOL=system nice -n 19 ionice -c 3 python3 contributor_tools/build_um21_scope_figures.py
"""
from __future__ import annotations

import io
import json
import os
import random

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_review_v2"
SCOPE = ROOT / "docs/quality/audits/um21-r01-fix-scope.json"
FIG_DIR = ROOT / "docs/datasets/um21/figures"
SEED = 20261106
INK, MUTED, GREY = "#20252b", "#5b6672", "#b4bcc4"
BEFORE, AFTER = "#c4501a", "#1f6aa5"
WIDTH_IN = 4.5
CONDITION = {"d10": "10°\ndecline", "d5": "5°\ndecline", "i0": "level", "i5": "5°\nincline", "i10": "10°\nincline"}


def plt_module():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.labelsize": 10, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "axes.spines.top": False, "axes.spines.right": False,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK,
        "xtick.color": INK, "ytick.color": INK, "legend.frameon": False,
        "axes.linewidth": 0.7, "svg.hashsalt": "locohub-um21-scope", "svg.fonttype": "path",
        "figure.facecolor": "white", "axes.facecolor": "white"})
    return plt


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None})
    (FIG_DIR / name).write_bytes(buf.getvalue())


def mix(pct):
    """White to orange; any affected cell gets at least a visible tint."""
    t = 0.3 + 0.7 * min(max(pct, 0.0), 100.0) / 100.0
    base = np.array([int(BEFORE[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    return tuple((255 * (1 - t) + base * t) / 255)


def grid_figure(plt, fix):
    g = fix["grid"]
    rows, cols = g["rows"], g["cols"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.1), layout="constrained")
    ax.set_xlim(0, len(cols))
    ax.set_ylim(len(rows), 0)
    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            v = g["cells"].get(f"{r}/{c}")
            if v is None:
                ax.add_patch(plt.Rectangle((ci + .06, ri + .06), .88, .88, fill=False, ec=GREY, lw=0.8, ls=(0, (2, 2))))
                continue
            if v == 0:
                ax.add_patch(plt.Rectangle((ci + .06, ri + .06), .88, .88, fc="#dfe3e7", ec="none"))
                continue
            col = mix(v)
            ax.add_patch(plt.Rectangle((ci + .06, ri + .06), .88, .88, fc=col, ec="none"))
            label = f"{v:.0f}" if v >= 1 else "<1"
            ax.text(ci + .5, ri + .52, label, ha="center", va="center", fontsize=10, color="white" if v >= 55 else INK)
    ax.set_xticks([i + .5 for i in range(len(cols))])
    ax.set_xticklabels([CONDITION[c] for c in cols])
    ax.xaxis.tick_top()
    ax.set_yticks([i + .5 for i in range(len(rows))])
    ax.set_yticklabels(rows)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=mix(100), label="Affected (number = % of its strides)"),
               plt.Rectangle((0, 0), 1, 1, fc="#dfe3e7", label="Not affected"),
               plt.Rectangle((0, 0), 1, 1, fill=False, ec=GREY, ls=(0, (2, 2)), label="No such recording")]
    fig.legend(handles=handles, loc="outside lower left", ncols=1, handlelength=1.6)
    save(fig, f"scope-{fix['key']}.svg")
    plt.close(fig)


def pick_strides(fix_pool):
    """Draw one stride per example at random (recorded seed) from the bundle, one row group at a time."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(BUNDLE / "full.parquet", buffer_size=0)
    cols = ["observation_id", "reference_side", "source_start_time_s", "source_end_time_s", "phase_ipsi",
            "pelvis_sagittal_angle_rad", "ankle_dorsiflexion_angle_ipsi_rad", "ankle_dorsiflexion_moment_ipsi_Nm_kg",
            "ankle_dorsiflexion_power_ipsi_W_kg", "ankle_reexpressed"]
    rng = random.Random(SEED)
    order = rng.sample(range(pf.num_row_groups), pf.num_row_groups)
    found = {}
    for rg in order:
        t = pf.read_row_group(rg, columns=cols).to_pydict()
        ids = t["observation_id"]
        for start in range(0, len(ids), 150):
            if start + 150 > len(ids) or ids[start] != ids[start + 149]:
                continue
            oid = ids[start]
            rec = oid.split(":")[1].split("/")
            rec = f"{rec[1]}/{rec[3]}"
            sl = slice(start, start + 150)
            row = {k: np.array(t[k][sl], dtype=float) for k in cols[2:9]}
            row["id"], row["rec"], row["side"] = oid, rec, t["reference_side"][start]
            row["ankle_reexpressed"] = bool(t["ankle_reexpressed"][start])
            for name, ok in fix_pool.items():
                if name not in found and ok(row):
                    found[name] = row
        if len(found) == len(fix_pool):
            break
    return found


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    plt = plt_module()
    for fix in scope["fixes"]:
        grid_figure(plt, fix)

    # recordings whose ankle power sign was set by the moment-times-speed check with multiplier -1
    import re
    q01 = json.loads((ROOT / "docs/maintainers/handoffs/UM21-Q01.json").read_text(encoding="utf-8"))
    phys = set()
    for line in q01["t04_v2_power_summary"]["per_record"]:
        rec, rest = line.split(": ", 1)
        m = re.search(r"ankle physics r=([+-]\d\.\d\d)/([+-]\d\.\d\d)", rest)
        if m and float(m.group(1)) < -0.99 and float(m.group(2)) < -0.99:
            phys.add(rec)
    finite = lambda r, *k: all(np.isfinite(r[x]).all() for x in k)  # noqa: E731
    pool = {
        "sign": lambda r: r["rec"] != "AB04/i0" and finite(r, "pelvis_sagittal_angle_rad"),
        "power": lambda r: r["rec"] in phys and finite(r, "ankle_dorsiflexion_angle_ipsi_rad", "ankle_dorsiflexion_moment_ipsi_Nm_kg", "ankle_dorsiflexion_power_ipsi_W_kg"),
    }
    found = pick_strides(pool)
    ph = np.linspace(0, 100, 150)
    LOCO = "Position in the stride (%)"

    def who(r):
        s, c = r["rec"].split("/")
        cond = {"i0": "level", "d5": "5° decline", "d10": "10° decline", "i5": "5° incline", "i10": "10° incline"}[c]
        return f"{s}, {cond}, {r['side']} leg"

    # ---- sign rule: one stride, source sign and LocoHub sign
    r = found["sign"]
    tilt = np.degrees(r["pelvis_sagittal_angle_rad"])
    src = -tilt  # published by the source (forward tilt +); the rule multiplies by -1
    lim = (min(tilt.min(), src.min()) - 3, max(tilt.max(), src.max()) + 3)
    for name, y, col, lab, arrow_up in (("sign-before.svg", src, INK, "Pelvis tilt as the source publishes it", True),
                                         ("sign-after.svg", tilt, AFTER, "Pelvis tilt after the rule (−1)", False)):
        fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.1), layout="constrained")
        ax.axhline(0, color=GREY, lw=0.6, zorder=0)
        ax.plot(ph, y, color=col, lw=2.2, label=lab)
        ax.set_xlim(0, 100)
        ax.set_ylim(*lim)
        ax.set_xlabel(LOCO)
        ax.set_ylabel("Pelvis tilt (degrees)")
        ytxt = lim[1] - 0.12 * (lim[1] - lim[0]) if arrow_up else lim[0] + 0.12 * (lim[1] - lim[0])
        yarr = lim[1] - 0.02 * (lim[1] - lim[0]) if arrow_up else lim[0] + 0.02 * (lim[1] - lim[0])
        ax.annotate("forward tilt", xy=(98, yarr), xytext=(98, ytxt), ha="right", va="top" if arrow_up else "bottom", fontsize=10, color=MUTED,
                    arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2), annotation_clip=False)
        fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=2.2)
        save(fig, name)
        plt.close(fig)

    # ---- power sign: one stride of ankle power against moment x joint speed
    r = found["power"]
    dur = float(r["source_end_time_s"][0] - r["source_start_time_s"][0])
    dt = dur / 149.0
    mom = r["ankle_dorsiflexion_moment_ipsi_Nm_kg"]
    speed = np.gradient(r["ankle_dorsiflexion_angle_ipsi_rad"], dt)
    ref = mom * speed
    rel = r["ankle_dorsiflexion_power_ipsi_W_kg"]
    pub = -rel  # the source stores this recording's power with the opposite sign; the check multiplies by -1
    lim = (min(ref.min(), pub.min(), rel.min()) - 0.4, max(ref.max(), pub.max(), rel.max()) + 0.4)
    for name, y, col, lab, rcol in (("power-before.svg", pub, INK, "Ankle power as the source stores it", BEFORE),
                                     ("power-after.svg", rel, INK, "Ankle power after the sign is set", AFTER)):
        fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.1), layout="constrained")
        ax.axhline(0, color=GREY, lw=0.6, zorder=0)
        ax.plot(ph, y, color=col, lw=2.2, label=lab)
        ax.plot(ph, ref, color=rcol, lw=1.8, ls="--", label="Joint moment × joint speed")
        ax.set_xlim(0, 100)
        ax.set_ylim(*lim)
        ax.set_xlabel(LOCO)
        ax.set_ylabel("Ankle power (watts per kg)")
        fig.legend(*ax.get_legend_handles_labels(), loc="outside lower left", ncols=1, handlelength=2.2)
        save(fig, name)
        plt.close(fig)

    corr = float(np.corrcoef(rel, ref)[0, 1])
    (FIG_DIR / "figures.json").write_text(json.dumps({
        "seed": SEED, "script": "contributor_tools/build_um21_scope_figures.py",
        "how_chosen": "row groups of the full version in a seeded random order; the first stride that fits each pool",
        "sign_example": {"stride": r_id(found["sign"]), "who": who(found["sign"]), "pool": "any stride except AB04 level (43 recordings)"},
        "power_example": {"stride": r_id(found["power"]), "who": who(found["power"]), "agreement_after": round(corr, 3),
                          "pool": "ankle power set by the moment-times-speed check with a sign flip, agreement −0.99 or better on both legs",
                          "note": "joint speed is the slope of the released ankle angle over the stride's source time span"},
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("figures written to", FIG_DIR.relative_to(ROOT))


def r_id(r):
    return r["id"]


if __name__ == "__main__":
    main()
