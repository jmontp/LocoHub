#!/usr/bin/env python3
"""Build docs/datasets/um21/index.html from the verified local UMich 2021 review bundle.

Reads only small bundle-derived files (manifest.json, dataset_index.json,
exclusions.csv, held_signals.csv, phase_preview.json) and the committed handoffs
UM21-R01.json and UM21-R01-verify.json. It never opens full.parquet or
filtered.parquet. phase_preview.json holds the mean and sample standard deviation
per phase sample, computed from the written cleaned file; this builder pools the
left and right legs from it. Nothing here is published.

Usage: python3 contributor_tools/build_um21_doc_page.py
"""
from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "converted_datasets/reconversion_v2/um21_r01_review_v2"
HANDOFFS = ROOT / "docs/maintainers/handoffs"
OUT = ROOT / "docs/datasets/um21/index.html"
SCOPE = ROOT / "docs/quality/audits/um21-r01-fix-scope.json"
FIGS = ROOT / "docs/datasets/um21/figures"
FIGJSON = FIGS / "figures.json"

CONDITION = {"d10": "10° decline", "d5": "5° decline", "i0": "level", "i5": "5° incline", "i10": "10° incline"}
COLORS = {"d10": "#0072B2", "d5": "#56B4E9", "i0": "#009E73", "i5": "#E69F00", "i10": "#D55E00"}
PANELS = [
    ("decline_walking", "Decline walking", ["d10", "d5"]),
    ("level_walking", "Level walking", ["i0"]),
    ("incline_walking", "Incline walking", ["i5", "i10"]),
    ("transition", "Transitions (belt speed or slope changing)", ["d10", "d5", "i0", "i5", "i10"]),
]
# Plain names and units for each released signal; status comes from the verified handoff.
PLAIN = {
    "pelvis_sagittal_angle_rad": ("Pelvis tilt", "radians"),
    "hip_flexion_angle_ipsi_rad": ("Hip angle", "radians"),
    "knee_flexion_angle_ipsi_rad": ("Knee angle", "radians"),
    "ankle_dorsiflexion_angle_ipsi_rad": ("Ankle angle", "radians"),
    "thigh_sagittal_angle_ipsi_rad": ("Thigh angle (side-view estimate)", "radians"),
    "shank_sagittal_angle_ipsi_rad": ("Shank angle (side-view estimate)", "radians"),
    "pelvis_sagittal_velocity_rad_s": ("Pelvis tilt speed", "radians per second"),
    "thigh_sagittal_velocity_ipsi_rad_s": ("Thigh angle speed", "radians per second"),
    "shank_sagittal_velocity_ipsi_rad_s": ("Shank angle speed", "radians per second"),
    "hip_flexion_moment_ipsi_Nm_kg": ("Hip moment", "newton-metres per kg body mass"),
    "knee_flexion_moment_ipsi_Nm_kg": ("Knee moment", "newton-metres per kg body mass"),
    "ankle_dorsiflexion_moment_ipsi_Nm_kg": ("Ankle moment", "newton-metres per kg body mass"),
    "hip_flexion_power_ipsi_W_kg": ("Hip power", "watts per kg body mass"),
    "knee_flexion_power_ipsi_W_kg": ("Knee power", "watts per kg body mass"),
    "ankle_dorsiflexion_power_ipsi_W_kg": ("Ankle power", "watts per kg body mass"),
}
STATUS_TEXT = {
    "checked": ("Checked", "Checked against impossible angle ranges and sudden jumps."),
    "offset_unverified": ("Checked; zero point not checked", "Checked only against clearly impossible values and sudden jumps. Where the ankle angle is zero has not been checked."),
    "partly_checked": ("Partly checked", "Checked for sudden jumps only; no plausible range exists to check against."),
    "unchecked": ("Not checked", "Values are as published after the sign step; no check was run."),
}
REASON_PLAIN = {
    "t04_2_outside_stride_rule": "Too short or too long to check",
    "c03_2_sudden_jump": "Sudden ankle jumps (AB07, 10° incline, right leg)",
    "q01_limit_failed": "Ankle angle beyond the angle limit (AB08, level, left leg)",
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def cond_name(rec: str) -> str:
    sub, cond = rec.split("/")
    return f"{sub}, {CONDITION[cond]}"


def load_inputs():
    manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((BUNDLE / "dataset_index.json").read_text(encoding="utf-8"))
    with (BUNDLE / "exclusions.csv").open(newline="", encoding="utf-8") as fh:
        excl = list(csv.DictReader(fh))
    with (BUNDLE / "held_signals.csv").open(newline="", encoding="utf-8") as fh:
        held = list(csv.DictReader(fh))
    preview = json.loads((BUNDLE / "phase_preview.json").read_text(encoding="utf-8"))
    r01 = json.loads((HANDOFFS / "UM21-R01.json").read_text(encoding="utf-8"))
    return manifest, index, excl, held, preview, r01


# ---------- phase plots ----------
def pool(groups, column):
    """Pool left and right legs of one condition (weighted mean, pooled sample sd)."""
    n_s = [g["columns"][column]["n"] for g in groups]
    m_s = [g["columns"][column]["mean"] for g in groups]
    s_s = [g["columns"][column]["sd"] for g in groups]
    mean, sd = [], []
    for i in range(150):
        parts = [(n[i], m[i], s[i]) for n, m, s in zip(n_s, m_s, s_s) if n[i] and m[i] is not None]
        N = sum(p[0] for p in parts)
        if N < 2:
            mean.append(None)
            sd.append(None)
            continue
        M = sum(n * m for n, m, _ in parts) / N
        ss = sum((n - 1) * (s or 0.0) ** 2 + n * (m - M) ** 2 for n, m, s in parts)
        mean.append(M)
        sd.append(math.sqrt(ss / (N - 1)))
    return mean, sd


def nice_ticks(lo, hi):
    span = hi - lo or 1.0
    raw = span / 4
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=mag)
    start = math.ceil(lo / step) * step
    ticks, t = [], start
    while t <= hi + 1e-9:
        ticks.append(round(t, 10))
        t += step
    return ticks


def fmt(v):
    s = f"{v:.3g}"
    return "0" if s in ("-0", "0") else s


def panel_svg(title, series, lo, hi, unit):
    W, H, L, R, T, B = 320, 220, 46, 16, 22, 34
    pw, ph = W - L - R, H - T - B

    def X(i):
        return L + pw * i / 149

    def Y(v):
        return T + ph * (1 - (v - lo) / (hi - lo))

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}: mean with spread over the stride, {esc(unit)}" xmlns="http://www.w3.org/2000/svg">',
           f'<text x="{L}" y="14" font-size="12" font-weight="600" fill="currentColor">{esc(title)}</text>']
    for t in nice_ticks(lo, hi):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="currentColor" stroke-opacity=".15"/>')
        out.append(f'<text x="{L - 4}" y="{Y(t) + 4:.1f}" font-size="11" text-anchor="end" fill="currentColor">{fmt(t)}</text>')
    for p in (0, 50, 100):
        x = L + pw * p / 100
        out.append(f'<text x="{x:.1f}" y="{H - 18}" font-size="11" text-anchor="middle" fill="currentColor">{p}</text>')
    out.append(f'<text x="{L + pw / 2:.1f}" y="{H - 4}" font-size="11" text-anchor="middle" fill="currentColor">stride (%)</text>')
    out.append(f'<rect x="{L}" y="{T}" width="{pw}" height="{ph}" fill="none" stroke="currentColor" stroke-opacity=".35"/>')
    for cond, mean, sd in series:
        idx = [i for i in range(150) if mean[i] is not None]
        if len(idx) < 2:
            continue
        up = " ".join(f"{X(i):.1f},{Y(mean[i] + sd[i]):.1f}" for i in idx)
        dn = " ".join(f"{X(i):.1f},{Y(mean[i] - sd[i]):.1f}" for i in reversed(idx))
        line = " ".join(f"{X(i):.1f},{Y(mean[i]):.1f}" for i in idx)
        out.append(f'<polygon points="{up} {dn}" fill="{COLORS[cond]}" fill-opacity=".18" stroke="none"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{COLORS[cond]}" stroke-width="1.6"/>')
    out.append("</svg>")
    return "".join(out)


def phase_section(preview, columns):
    groups = preview["groups"]
    by = {}
    for g in groups:
        by.setdefault((g["task"], g["condition"]), []).append(g)
    parts = []
    for ci, col in enumerate(columns):
        name, unit = PLAIN[col]
        pooled = {}
        lo, hi = math.inf, -math.inf
        for task, _, conds in PANELS:
            for c in conds:
                if (task, c) not in by:
                    continue
                m, s = pool(by[(task, c)], col)
                pooled[(task, c)] = (m, s)
                for a, b in zip(m, s):
                    if a is not None:
                        lo, hi = min(lo, a - b), max(hi, a + b)
        pad = (hi - lo) * 0.05 or 1
        lo, hi = lo - pad, hi + pad
        panels = []
        for task, label, conds in PANELS:
            series = [(c, *pooled[(task, c)]) for c in conds if (task, c) in pooled]
            if series:
                panels.append(f'<figure class="phase-panel">{panel_svg(label, series, lo, hi, unit)}</figure>')
        legend = "".join(f'<span><i style="background:{COLORS[c]}"></i>{CONDITION[c]}</span>' for c in COLORS)
        open_attr = " open" if ci == 0 else ""
        parts.append(
            f'<details class="phase-signal"{open_attr}><summary><strong>{esc(name)}</strong> <span class="phase-unit">{esc(unit)}</span></summary>'
            f'<div class="phase-grid">{"".join(panels)}</div><p class="phase-legend">{legend}</p></details>')
    return "".join(parts)


# ---------- tables ----------
def held_rows(held):
    rows = {}
    for h in held:
        label = cond_name(h["recording"])
        col = h["column"].split("_")[0].capitalize() + " power"
        rows.setdefault(label, []).append(col)
    return rows


def exclusion_table(manifest, excl, held, r01):
    n = manifest["counts"]
    by_code = manifest["counts"]["exclusions_by_reason_code"]
    csv_codes = {}
    for e in excl:
        csv_codes[e["reason_code"]] = csv_codes.get(e["reason_code"], 0) + 1
    assert csv_codes == by_code, "exclusions.csv and manifest disagree"
    short = sum(1 for e in excl if e["reason_code"] == "t04_2_outside_stride_rule" and "below" in e["reason"])
    long_ = sum(1 for e in excl if e["reason_code"] == "t04_2_outside_stride_rule" and "above" in e["reason"])
    held_by = held_rows(held)
    held_text = "; ".join(f"{k}: {', '.join(sorted(v))}" for k, v in held_by.items())
    held_n = len(held)
    rows = [
        (f"Too short or too long to check ({short} under 50 samples, {long_} over 250 samples at 100 per second)",
         by_code["t04_2_outside_stride_rule"], "Neither version",
         "Left out because a stride this short or long cannot be checked against the others."),
        ("Sudden ankle jumps (AB07, 10° incline, right leg)", by_code["c03_2_sudden_jump"], "Neither version",
         "Left out because turning the ankle back by 180° cannot remove a one-sample jump inside these two strides."),
        ("Ankle angle beyond the angle limit (AB08, level, left leg)", by_code["q01_limit_failed"],
         "Full version only, marked failed", "Left out of the cleaned version because six samples fall below the lowest ankle angle we accept; it also has missing samples."),
        ("Whole recordings left out earlier", 6, "Neither version",
         "Left out because the task timing is shifted by 1.7 to 7 s in four of them and cannot be checked in two. They are AB01 10° decline, AB01 5° decline, AB08 10° incline, AB09 10° incline, AB10 level, and AB01 5° incline (an exact copy of its 10° incline recording)."),
        ("AB07 strides that were never converted", 9, "Never part of the converted set",
         "These 9 strides lie in the same 180° stretch, but they are not among the strides the conversion was built from, so they were never released. They are not counted above."),
        ("Foot angle and foot angle speed", 2, "Not released",
         "Left out because the foot angle carries the unchecked ankle zero point."),
        (f"Power channels left empty ({held_n} channels)", held_n, "Present but empty in both versions",
         f"Left empty because we could not settle the sign of the power: {held_text}."),
        ("Kept with an empty ankle (AB08, level, left leg)", 12, "Both versions",
         "These strides stay in, but the ankle angle is missing from the source. Missing is never counted as a pass."),
    ]
    head = "<thead><tr><th>What</th><th>Count</th><th>Where it stands</th><th>Why</th></tr></thead>"
    body = "".join(
        f'<tr><td>{esc(a)}</td><td class="num">{b:,}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>' for a, b, c, d in rows)
    note = (f"<p class=\"note\">Accounting: {n['upstream_observations']:,} strides came in; {n['full']:,} are in the full version "
            f"(15 + 2 left out of both); the cleaned version has {n['filtered']:,} (the AB08 stride is the one difference). "
            "The counts for whole recordings, never-converted strides, foot angles and empty columns are counted in recordings, strides or "
            "columns as stated in each row, not in the strides above.</p>")
    return f'<div class="table-scroll" role="region" aria-label="What we left out" tabindex="0"><table class="plain-table">{head}<tbody>{body}</tbody></table></div>{note}'


def column_table(r01, held):
    held_cols = {}
    for h in held:
        held_cols.setdefault(h["column"], []).append(cond_name(h["recording"]))
    rows = []
    for c in r01["columns"]:
        name, unit = PLAIN[c["column"]]
        label, note = STATUS_TEXT[c["status"]]
        if c["column"] in held_cols:
            label = "Not checked; empty in some recordings"
            note = "No check was run. Empty in: " + "; ".join(held_cols[c["column"]]) + " (sign not settled)."
        rows.append(f'<tr><td>{esc(name)}<br><code>{esc(c["column"])}</code></td><td>{esc(unit)}</td>'
                    f'<td><strong>{esc(label)}</strong><br>{esc(note)}</td></tr>')
    return ('<div class="table-scroll" role="region" aria-label="Columns" tabindex="0"><table class="plain-table">'
            '<thead><tr><th>Column</th><th>Unit</th><th>Status</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


# ---------- fix cards ----------
def fig(src, side, label, alt, cap=""):
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side fix-{side}">{esc(label)}</figcaption>'
            f'<img src="../../quality/fixes/{src}" width="450" height="310" loading="lazy" alt="{esc(alt)}">{c}</figure>')



# ---------- scope blocks (all numbers come from um21-r01-fix-scope.json) ----------
VERDICT_CLASS = {"Also wrong, fixed": "v-fixed", "Checked, not affected": "v-ok", "Left out": "v-left", "Not checked": "v-nc"}


def local_fig(src, label, alt, cap=""):
    import re
    svg = (FIGS / src).read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    w, h = float(m.group(1)), float(m.group(2))
    c = f"<figcaption>{esc(cap)}</figcaption>" if cap else ""
    return (f'<figure class="fix-figure"><figcaption class="fix-side">{esc(label)}</figcaption>'
            f'<img src="figures/{src}" width="{round(w * 100 / 72)}" height="{round(h * 100 / 72)}" loading="lazy" alt="{esc(alt)}">{c}</figure>')


def scope_block(fix):
    t = fix["table"]
    head = "".join(f"<th>{esc(c)}</th>" for c in t["columns"])
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in t["rows"])
    table = (f'<div class="table-scroll" role="region" aria-label="{esc(fix["card"])}: affected recordings" tabindex="0">'
             f'<table class="plain-table scope-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
    if t["fold"]:
        table = f'<details class="scope-fold"><summary>Show all {len(t["rows"])} rows</summary>{table}</details>'
    q = {"clock": "Which recordings have the wrong task timing?", "pelvis_backwards": "Which recordings had a backwards pelvis?",
         "sign_rule": "Which recordings go through the pelvis sign rule?", "thigh_shank": "Which recordings had a wrong thigh and shank?",
         "ankle_180": "Which recordings had an ankle turned by 180°?", "power": "Which recordings have an empty or copied power channel?"}[fix["key"]]
    g = local_fig(f"scope-{fix['key']}.svg", q, f"Grid of participants by task. {fix['grid_caption']}", fix["grid_caption"])
    return (f'<div class="scope-block"><h4>How much was affected</h4><p class="scope-total">{esc(fix["total_line"])}</p>'
            f'<p class="note">{esc(fix["denominator_text"])}</p>'
            f'<div class="fix-figures fix-figures-single">{g}</div>{table}</div>')


def knock_block(fix):
    items = []
    for k in fix["knock_on"]:
        ev = f'<span class="ko-evidence"><em>How we know:</em> {esc(k["evidence"])}</span>' if k["evidence"] else '<span class="ko-evidence"><em>No evidence yet.</em></span>'
        items.append(f'<li class="ko-item"><span class="verdict {VERDICT_CLASS[k["verdict"]]}">{esc(k["verdict"])}</span> '
                     f'<strong>{esc(k["signal"])}.</strong> {esc(k["line"])} {ev}</li>')
    d = f'<p class="ko-direction">{esc(fix["direction"])}</p>' if fix.get("direction") else ""
    return f'<div class="scope-block"><h4>What else this could affect</h4>{d}<ul class="ko-list">{"".join(items)}</ul></div>'


def card(title, wrong, how, did, example, figures="", single=False, scope=None):
    q = ""
    if figures.startswith('<p class="fig-question">'):
        q, figures = figures.split("</p>", 1)
        q += "</p>"
    f = q + (f'<div class="fix-figures{" fix-figures-single" if single else ""}">{figures}</div>' if figures else "")
    return (f'<article class="fix-card"><h3>{esc(title)}</h3>'
            f'<p><strong>What was wrong.</strong> {esc(wrong)}</p><p><strong>How we know.</strong> {esc(how)}</p>'
            f'<p><strong>What we did.</strong> {esc(did)}</p>{f}<p class="fix-evidence"><strong>Example.</strong> {esc(example)}</p>'
            f'{scope_block(scope) if scope else ""}{knock_block(scope) if scope else ""}</article>')


def fix_cards(scope):
    S = {f["key"]: f for f in scope["fixes"]}
    figinfo = json.loads(FIGJSON.read_text(encoding="utf-8"))
    c = []
    c.append(card(
        "Task timing was off in some recordings",
        "The published task intervals (when belt speed or slope changes) were timed on the belt-speed record, not on the motion data. In 4 of 50 treadmill recordings that clock is off by 1.7 to 7 s, and 2 more cannot be checked, so strides near a change can carry the wrong task label.",
        "We lined up the belt-speed record with the belt speed measured from heel and toe markers. 44 recordings agree within the accepted band.",
        "We left the six failing recordings out instead of shifting or estimating any interval.",
        "AB09 at 10° incline: the best shift is 6.85 s, and the belt-speed error drops from 0.67 to 0.07 m/s at that shift, so the recording is left out. AB01 at 5° incline is an exact copy of its 10° incline recording and is also left out.",
        fig("um21-clock.svg", "before", "Before and after, per recording",
            "Shift of the task timing for each of 50 treadmill recordings. Most sit in a narrow band near zero; four sit 1.7 to 7 seconds away and two cannot be checked.",
            "Shift that best lines up the belt-speed record with belt speed from the markers. Crosses at the bottom cannot be checked."), single=True, scope=S["clock"]))
    c.append(card(
        "One recording's pelvis was computed facing backwards",
        "In AB04 level walking the motion-capture software computed the pelvis facing backwards, so its stored tilt has the wrong sign, and so do the thigh and shank angles built on it.",
        "The published tilt is the mirror image of the tilt computed from the pelvis markers.",
        "For that recording only, we flipped the sign of the pelvis tilt using the marker evidence and rebuilt the thigh and shank angles from it.",
        "AB04 level walking, right leg: the pelvis tilt is multiplied by +1 there and by −1 in the other 43 recordings.",
        fig("um21-pelvis-before.svg", "before", "Before: as published", "Published pelvis tilt is the mirror image of tilt computed from the pelvis markers.")
        + fig("um21-pelvis-after.svg", "after", "After: sign flipped", "Published pelvis tilt times minus one overlaps the marker tilt.",
              "Shown with the source sign (forward tilt positive); LocoHub files store pelvis tilt with the opposite sign."), scope=S["pelvis_backwards"]))
    c.append(card(
        "Pelvis tilt direction follows one sign rule",
        "The source reports forward pelvis tilt as positive. LocoHub's rule (counterclockwise is positive) makes forward tilt negative.",
        "We checked the sign of each angle and moment against marker and force-plate evidence.",
        "We multiplied pelvis tilt by −1 in 43 of the 44 recordings (all strides). Hip, knee and ankle angles and the hip, knee and ankle moments keep their published sign.",
        "AB01 level walking, right leg: pelvis tilt is multiplied by −1; hip, knee and ankle are unchanged.",
        '<p class="fig-question">Does the rule flip pelvis tilt, and which way is forward?</p>'
        + local_fig("sign-before.svg", "Before: as the source publishes it (forward tilt is positive)",
                    "One stride of pelvis tilt as the source publishes it; forward tilt is up.")
        + local_fig("sign-after.svg", "After: LocoHub's rule (forward tilt is negative)",
                    "The same stride after multiplying by minus one; forward tilt is down.",
                    f"One stride drawn at random: {figinfo['sign_example']['who']}. The source sign is the released value times −1, since the rule is an exact −1."),
        scope=S["sign_rule"]))
    c.append(card(
        "Thigh and shank angles are rebuilt",
        "Earlier rebuild code added pelvis tilt to the hip angle, but the dataset's authors subtract it, so the thigh angle was off by about twice the pelvis tilt. The older thigh and shank columns are not trusted.",
        "Hip minus pelvis follows the thigh angle computed from the markers within a few degrees; the markers use the bump at the top of the thigh bone, so a small offset is expected.",
        "We rebuilt thigh and shank from the published pelvis, hip and knee angles (after the sign step) and release them as side-view estimates.",
        "AB08 at 5° incline, right leg: the earlier rebuild was about 38° off in the example stride.",
        fig("um21-thigh-before.svg", "before", "Before: the earlier rebuild", "Pelvis plus hip runs far above the thigh angle from markers for the whole stride.")
        + fig("um21-thigh-after.svg", "after", "After: the authors' formula", "Hip minus pelvis follows the thigh angle from markers within a few degrees."), scope=S["thigh_shank"]))
    c.append(card(
        "Part of one ankle recording was turned 180°",
        "For 5,429 frames of one recording's right ankle (AB07, 10° incline) the software reported the ankle in an equivalent but different form that shifts it by about 180°. The strides inside sat near −160°.",
        "After the turn, the strides fall on the strides outside the stretch: −16.2° to 26.8° against −16.6° to 27.0°, and all 20 pass the same angle limits.",
        "We turned 20 strides back by 180° and logged every one of their 3,000 samples. 2 strides with one-sample jumps are left out. The source copy is untouched.",
        "One stride's tenth sample: −159.6° as published becomes 20.4°. Of the 31 strides in the stretch, 20 were turned back, 2 were left out, and 9 were never part of the converted strides, so they were never released.",
        fig("um21-ankle-before.svg", "before", "Before: as published", "Strides inside the stretch sit near minus 160 degrees, far below the strides outside it.")
        + fig("um21-ankle-after.svg", "after", "After: turned back", "Converted strides fall on the strides outside the stretch. The vertical scale differs from the Before figure.",
              "The vertical scale differs from the Before figure. Both figures are drawn from all 31 strides in the stretch; only 20 of them are in the converted set, 2 were left out for jumps, and 9 were never released."), scope=S["ankle_180"]))
    c.append(card(
        "Power sign was unsettled",
        "Power is stored in two ways (8 recordings differ), and its sign could not be settled from the source alone.",
        "We kept the sign for which power equals the published moment times the joint speed, with agreement of at least 0.9 on both legs.",
        "We set the sign that way, and left the power empty where the agreement stays below 0.9.",
        "AB02 at 10° decline: hip power is multiplied by −1, with agreement −1.00. AB03 at 10° incline: hip power agreement is only 0.80 on one leg and 0.67 on the other, so hip power is left empty there.",
        '<p class="fig-question">Does the set sign make power equal moment times joint speed?</p>'
        + local_fig("power-before.svg", "Before: power as the source stores it",
                    "One stride of ankle power as the source stores it is the mirror image of joint moment times joint speed.")
        + local_fig("power-after.svg", "After: sign set by the check",
                    "The same stride after the sign is set; power lies on joint moment times joint speed.",
                    f"One stride drawn at random: {figinfo['power_example']['who']}; agreement after the fix {figinfo['power_example']['agreement_after']}. Joint speed is the slope of the ankle angle."),
        scope=S["power"]))
    return "".join(c)


CSS = """
.um21 section { padding-top: .3rem; }
.um21 h2 { margin-top: 2rem; }
.um21 .lead { max-width: 72ch; }
.um21 .plain-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.um21 .plain-table th, .um21 .plain-table td { text-align: left; vertical-align: top; padding: .45rem .6rem; border-bottom: 1px solid var(--line); }
.um21 .plain-table td.num { text-align: right; white-space: nowrap; }
.um21 .plain-table code { font-size: .74rem; color: var(--muted); word-break: break-all; }
.um21 .table-scroll { overflow-x: auto; }
.um21 .plain-table { min-width: 34rem; }
.um21 .note { color: var(--muted); font-size: .82rem; max-width: 72ch; }
.um21 .checks { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); gap: 1rem 1.5rem; }
.um21 .checks ul { margin: .3rem 0; padding-left: 1.2rem; }
.um21 .checks h3 { margin: .2rem 0; font-size: 1rem; }
.um21 .phase-signal { border-top: 1px solid var(--line); padding: .5rem 0; }
.um21 .phase-signal summary { cursor: pointer; font-size: .95rem; padding: .25rem 0; }
.um21 .phase-unit { color: var(--muted); font-size: .82rem; font-weight: 400; margin-left: .5rem; }
.um21 .phase-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); gap: .8rem 1.2rem; margin: .6rem 0; }
.um21 .phase-panel { margin: 0; min-width: 0; }
.um21 .phase-panel svg { display: block; width: 100%; height: auto; background: var(--page); color: var(--ink); }
.um21 .phase-legend { display: flex; flex-wrap: wrap; gap: .3rem 1rem; font-size: .8rem; color: var(--muted); margin: .2rem 0 .6rem; }
.um21 .phase-legend i { display: inline-block; width: .8rem; height: .25rem; margin-right: .35rem; vertical-align: middle; }
.um21 .fix-card h3 { margin: 0 0 .35rem; font-size: 1.1rem; }
.um21 .scope-block { border-top: 1px solid var(--line); margin-top: .9rem; padding-top: .4rem; }
.um21 .scope-block h4 { margin: .2rem 0 .4rem; font-size: 1rem; }
.um21 .scope-total { max-width: 72ch; font-weight: 600; margin: .2rem 0; }
.um21 .scope-table { min-width: 31rem; }
.um21 .scope-fold > summary { cursor: pointer; font-size: .9rem; padding: .3rem 0; }
.um21 .fig-question { font-weight: 600; margin: .8rem 0 .2rem; max-width: 72ch; }
.um21 .ko-list { list-style: none; margin: .3rem 0; padding: 0; max-width: 80ch; }
.um21 .ko-item { padding: .5rem 0; border-bottom: 1px solid var(--line); font-size: .92rem; }
.um21 .ko-evidence { display: block; color: var(--muted); font-size: .85rem; margin-top: .15rem; }
.um21 .ko-direction { max-width: 72ch; font-size: .92rem; background: var(--soft, transparent); }
.um21 .verdict { display: inline-block; font-size: .78rem; font-weight: 600; padding: .05rem .45rem; border-radius: 3px; border: 1px solid currentColor; margin-right: .3rem; white-space: nowrap; }
.um21 .v-ok { color: #1f6aa5; } .um21 .v-fixed { color: #1b7a43; } .um21 .v-left { color: #8a5a00; } .um21 .v-nc { color: #a3361a; }
@media (prefers-color-scheme: dark) { .um21 .v-ok { color: #6db3e8; } .um21 .v-fixed { color: #5cc98a; } .um21 .v-left { color: #e0a93b; } .um21 .v-nc { color: #f08a6e; } }
@media (max-width: 40rem) { .um21 .scope-table th, .um21 .scope-table td { padding: .35rem .4rem; font-size: .8rem; } }
.um21 .local-box { border: 1px solid var(--warn-line); background: var(--warn); padding: .8rem 1rem; max-width: 72ch; border-radius: 3px; }
"""


def build() -> str:
    manifest, index, excl, held, preview, r01 = load_inputs()
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    n = manifest["counts"]
    recordings = len(index["recordings"])
    subjects = len({r["subject"] for r in index["recordings"]})
    columns = [c["column"] for c in r01["columns"]]
    verified = "2026-11-06"
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="UMich 2021 treadmill walking: what we fixed, what we left out, and what we checked.">
  <meta name="color-scheme" content="light dark">
  <title>Umich 2021 · LocoHub</title>
  <link rel="stylesheet" href="../../stylesheets/site.css">
  <link rel="stylesheet" href="../../stylesheets/dataset-pages.css">
  <link rel="stylesheet" href="../../stylesheets/visual-styles.css">
  <link rel="stylesheet" href="../../stylesheets/fixes.css">
  <script src="../../javascripts/visual-styles.js"></script>
  <script src="../../javascripts/extra.js" defer></script>
  <style>{CSS}</style>
</head>
<body class="dataset-detail">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="wordmark" href="../../index.html" aria-label="LocoHub home">LocoHub</a>
      <nav class="primary-nav" aria-label="Main navigation"><a href="../../index.html" aria-current="page">Data</a>
<a href="../../tutorials/index.html">Tutorials</a>
<a href="../../reference/index.html">File format</a>
<a href="../../quality/index.html">Testing &amp; data quality</a></nav>
      <form class="header-search" role="search" aria-label="Site search" action="../../search/index.html"><label class="visually-hidden" for="header-query">Search documentation</label><input id="header-query" type="search" name="q" placeholder="Search docs" required><button type="submit">Search</button></form>
      <a class="repository-link" href="https://github.com/jmontp/LocoHub">GitHub</a>
    </div>
  </header>
  <div class="page-layout wide-page">
    <main id="main" class="page-content um21" tabindex="-1">
      <div class="page-kicker"><a href="../../index.html">LocoHub</a><span aria-hidden="true">/</span>Umich 2021</div>
      <header class="dataset-heading"><h1 id="umich-2021">Umich 2021</h1>
<p class="dataset-note">Local review version, not yet released. Nothing on this page has been approved scientifically.</p></header>
      <nav class="dataset-section-nav" aria-label="Sections"><a href="#what-this-is">What this is</a><a href="#fixed">What we fixed</a><a href="#left-out">What we left out</a><a href="#checked">What we checked</a><a href="#phase-plots">Phase plots</a><a href="#columns">Columns</a><a href="#downloads">Downloads</a></nav>

      <section id="what-this-is" aria-labelledby="what-h"><h2 id="what-h">What this is</h2>
      <p class="lead">Treadmill walking from {subjects} participants at level, 5° and 10° incline, and 5° and 10° decline, plus the transitions between them: {recordings} recordings. This is a local review version and is not released. The full version has <strong>{n['full']:,} strides</strong>; the cleaned version has <strong>{n['filtered']:,}</strong>. Every stride has exactly 150 samples from 0 to 100 percent of the stride.</p></section>

      <section id="fixed" aria-labelledby="fixed-h"><h2 id="fixed-h">What we fixed (original vs fixed)</h2>
      <p class="note">One card per fix. Each card says what was wrong, how much of the data it touched, and what else it could affect. Before-and-after figures show the published data and the fixed data side by side. Example strides are drawn at random, not hand-picked.</p>
      {fix_cards(scope)}</section>

      <section id="left-out" aria-labelledby="left-h"><h2 id="left-h">What we left out and why</h2>
      {exclusion_table(manifest, excl, held, r01)}</section>

      <section id="checked" aria-labelledby="checked-h"><h2 id="checked-h">What we checked and what we did not</h2>
      <div class="checks"><div><h3>Checked</h3><ul>
        <li>Hip, knee and ankle angles against clearly impossible ranges (the ankle only for impossible values).</li>
        <li>Every angle (pelvis, hip, knee, ankle, thigh, shank) for sudden jumps between neighbouring samples.</li>
        <li>That every stride has 150 samples and that values were not changed except where this page says so.</li></ul></div>
      <div><h3>Not checked</h3><ul>
        <li>Moments, powers and all angle speeds: no check was run.</li>
        <li>Belt speeds.</li>
        <li>Where the ankle angle is zero.</li>
        <li>Plausible ranges for each task: we used only coarse limits, not reviewed ranges.</li>
        <li>Thigh and shank are side-view estimates, not full 3D angles.</li></ul></div></div>
      <p class="note">A stride that passes has not been shown to be right, only not clearly impossible. Missing samples are never counted as a pass: 376 strides have some missing samples.</p></section>

      <section id="phase-plots" aria-labelledby="phase-h"><h2 id="phase-h">Phase plots</h2>
      <p class="note">Mean (line) and spread of one standard deviation (band) of each released signal over the stride, from the cleaned version. Left and right legs are pooled. Colors are the slope. Strides with the power left empty are not in the power plots. These plots show the data as released; they do not mean the signals are correct.</p>
      {phase_section(preview, columns)}</section>

      <section id="columns" aria-labelledby="columns-h"><h2 id="columns-h">Columns</h2>
      {column_table(r01, held)}
      <p class="note">Every column has a value for each stride's own leg only; pelvis has no side. Foot angle and foot angle speed are not released.</p></section>

      <section id="downloads" aria-labelledby="downloads-h"><h2 id="downloads-h">Downloads</h2>
      <div class="local-box"><p><strong>Local review files, not published yet.</strong> The full version, the cleaned version, the list of left-out strides and the log of turned ankle samples exist only on the maintainer's computer. They will get download links when they are released.</p></div>
      <p class="note">Page built from the local review version checked on {verified}.</p></section>
    </main>
  </div>
  <footer class="site-footer"><p>LocoHub</p><nav aria-label="Additional links"><a href="../../contributing/index.html">Contribute data</a><a href="../../maintainers/index.html">Maintainers</a><a href="../../reference/index.html#release-evidence">Download notes</a><a href="https://github.com/jmontp/LocoHub/issues">Report an issue</a></nav></footer>
</body>
</html>
"""
    return page


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
