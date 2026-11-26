"""Merge the per-job outputs of compare_training_vs_locohub.py and write docs/datasets/training-vs-locohub-columns.html.

Reads only the small CSV/JSON outputs under docs/quality/audits/training-compare-*. Every number on the page is a sum, weighted
mean or order statistic of those outputs; nothing is recomputed from the data tables. Descriptive only; no approval is claimed.

Pooling rules (stated on the page): n, coverage, bias, RMS and the share past the reporting size are exact pooled values over
participants (weighted by matched samples). Correlation and the 95th percentile cannot be pooled from per-participant summaries, so for
GT21 (several jobs) the page shows the median and range over participants of each participant's own value. UM21 ran as one job and
its values are pooled directly.
"""
import base64
import csv
import html
import io
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / 'docs/quality/audits'
OUT = ROOT / 'docs/datasets/training-vs-locohub-columns.html'
# participant -> job directory (the last, current run of that participant; superseded runs are left in place, not used)
GT21_SRC = {'AB06': 'j1', 'AB07': 'j1', 'AB08': 'p-AB08', 'AB09': 'j2c', 'AB10': 'j2', 'AB11': 'j3', 'AB13': 'j3', 'AB14': 'j4',
            'AB16': 'j4', 'AB18': 'j5', 'AB20': 'j5', 'AB21': 'j6', 'AB24': 'j6', 'AB25': 'j7b', 'AB30': 'j7b'}
UM21_DIR = AUD / 'training-compare-um21-all'
COLS = [  # name, plain label, unit, reporting size
    ('ankle_angle', 'Ankle angle', 'deg', 2.0), ('shank_angle', 'Shank angle', 'deg', 2.0), ('foot_angle', 'Foot angle', 'deg', 2.0),
    ('ankle_velocity', 'Ankle velocity', 'deg/s', 20.0), ('ankle_moment', 'Ankle moment', 'Nm/kg', 0.05),
    ('vertical_force', 'Vertical force', 'BW', 0.05), ('cop_anterior', 'Centre of pressure, forward', 'm', 0.02)]
LABEL = {c[0]: c[1] for c in COLS}
UNIT = {c[0]: c[2] for c in COLS}
SIZE = {c[0]: c[3] for c in COLS}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def read(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh))


def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '&ndash;'
    if x == 0:
        return '0'
    if abs(x) < 1e-3 or abs(x) >= 1e5:
        return f'{x:.2e}'
    return f'{x:.{nd}g}'


def pct(x):
    return '&ndash;' if not math.isfinite(x) else (f'{100 * x:.1f}%' if x >= 0.0005 or x == 0 else f'{100 * x:.3f}%')


def load_subject_rows(dataset):
    """subject-scope and subject_task-scope rows from the current run of each participant."""
    subj, task = [], []
    if dataset == 'gt21':
        for s, j in GT21_SRC.items():
            for r in read(AUD / f'training-compare-gt21-{j}/comparison.csv'):
                if r['subject'] == s and r['scope'] == 'subject':
                    subj.append(r)
                elif r['subject'] == s and r['scope'] == 'subject_task':
                    task.append(r)
    else:
        for r in read(UM21_DIR / 'comparison.csv'):
            if r['scope'] == 'subject':
                subj.append(r)
            elif r['scope'] == 'subject_task':
                task.append(r)
    return subj, task


def load_align(dataset):
    al, um = [], []
    if dataset == 'gt21':
        for s, j in GT21_SRC.items():
            d = AUD / f'training-compare-gt21-{j}'
            al += [r for r in read(d / 'alignment.csv') if r['subject'] == s]
            um += [r for r in read(d / 'unmatched.csv') if r['subject'] == s]
    else:
        al, um = read(UM21_DIR / 'alignment.csv'), read(UM21_DIR / 'unmatched.csv')
    return al, um


def pool(rows, col):
    rs = [r for r in rows if r['column'] == col]
    n_pos = sum(int(r['n_positions']) for r in rs)
    n = sum(int(r['n_matched']) for r in rs)
    his = sum(f(r['coverage_his']) * int(r['n_positions']) for r in rs)
    lh = sum(f(r['coverage_lh']) * int(r['n_positions']) for r in rs)
    out = {'n_pos': n_pos, 'n': n, 'cov_his': his / n_pos if n_pos else math.nan, 'cov_lh': lh / n_pos if n_pos else math.nan,
           'subjects': len(rs), 'subjects_with_n': sum(1 for r in rs if int(r['n_matched']) > 0)}
    ok = [r for r in rs if int(r['n_matched']) > 0]
    if n:
        out['bias'] = sum(f(r['bias']) * int(r['n_matched']) for r in ok) / n
        out['rms'] = math.sqrt(sum(f(r['rms']) ** 2 * int(r['n_matched']) for r in ok) / n)
        out['exceed'] = sum(f(r['frac_exceed']) * int(r['n_matched']) for r in ok) / n
        cs = [f(r['corr']) for r in ok if math.isfinite(f(r['corr']))]
        ps = [f(r['p95_abs']) for r in ok if math.isfinite(f(r['p95_abs']))]
        out['corr'] = (statistics.median(cs), min(cs), max(cs)) if cs else None
        out['p95'] = (statistics.median(ps), min(ps), max(ps)) if ps else None
    return out


def dataset_row_um21(col):
    r = [x for x in read(UM21_DIR / 'comparison.csv') if x['scope'] == 'dataset' and x['column'] == col][0]
    return r


def main_table(dataset, rows):
    h = ['Column (unit)', 'Matched samples', 'Coverage: training / LocoHub', 'Mean difference', 'RMS difference',
         '95th percentile of |difference|', 'Correlation', 'Past the reporting size']
    out = ['<table><thead><tr>' + ''.join(f'<th>{x}</th>' for x in h) + '</tr></thead><tbody>']
    data = {}
    for name, label, unit, size in COLS:
        p = pool(rows, name)
        data[name] = p
        if p['n'] == 0:
            out.append(f'<tr><td>{label} ({unit})</td><td class="n">0</td><td class="n">{pct(p["cov_his"])} / {pct(p["cov_lh"])}</td>'
                       f'<td colspan="5" class="muted">no LocoHub values to compare</td></tr>')
            continue
        if dataset == 'um21':
            d = dataset_row_um21(name)
            corr, p95 = fmt(f(d['corr'])), fmt(f(d['p95_abs']))
        else:
            c, q = p['corr'], p['p95']
            corr = f'{fmt(c[0])} <span class="muted">({fmt(c[1])} to {fmt(c[2])})</span>'
            p95 = f'{fmt(q[0])} <span class="muted">({fmt(q[1])} to {fmt(q[2])})</span>'
        out.append(f'<tr><td>{label} ({unit})</td><td class="n">{p["n"]:,}</td><td class="n">{pct(p["cov_his"])} / {pct(p["cov_lh"])}</td>'
                   f'<td class="n">{fmt(p["bias"])}</td><td class="n">{fmt(p["rms"])}</td><td class="n">{p95}</td><td class="n">{corr}</td>'
                   f'<td class="n">{pct(p["exceed"])} <span class="muted">(&gt; {SIZE[name]:g} {unit})</span></td></tr>')
    out.append('</tbody></table>')
    return '\n'.join(out), data


def fig_bytes(fig):
    b = io.BytesIO()
    fig.savefig(b, format='png', dpi=200, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    return b.getvalue()


def img(png, alt):
    return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{base64.b64encode(png).decode()}">'


def fig_bias(gt, um):
    fig, ax = plt.subplots(figsize=(3.9, 3.4))
    names = [c[0] for c in COLS]
    ys = range(len(names))
    for off, data, lab, col in ((-0.18, gt, 'GT21', '#1f77b4'), (0.18, um, 'UM21', '#d95f02')):
        xs = [(data[n]['bias'] / SIZE[n]) if data[n]['n'] else math.nan for n in names]
        ax.barh([y + off for y in ys], xs, height=0.34, color=col, label=lab)
    ax.axvline(0, color='k', lw=0.8)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([LABEL[n].replace('Centre of pressure, forward', 'CoP forward') for n in names], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel('Mean difference / reporting size\n(training minus LocoHub)', fontsize=10)
    ax.tick_params(axis='x', labelsize=10)
    ax.legend(fontsize=10, loc='lower left', frameon=False)
    ax.set_title('How far apart are the averages?', fontsize=10)
    return fig_bytes(fig)


def fig_subject(rows_by_ds, col, title):
    fig, axs = plt.subplots(1, 2, figsize=(4.1, 3.3), gridspec_kw={'width_ratios': [15, 10]}, sharey=False)
    fig.suptitle(title, fontsize=10)
    for ax, (ds, rows), color in zip(axs, rows_by_ds.items(), ('#1f77b4', '#d95f02')):
        rs = sorted([r for r in rows if r['column'] == col and int(r['n_matched']) > 0], key=lambda r: r['subject'])
        ax.barh(range(len(rs)), [f(r['bias']) for r in rs], color=color)
        ax.set_yticks(range(len(rs)))
        ax.set_yticklabels([r['subject'] for r in rs], fontsize=10)
        ax.invert_yaxis()
        ax.axvline(0, color='k', lw=0.8)
        ax.set_xlabel(f'{ds}: mean diff (deg)', fontsize=10)
        ax.tick_params(axis='x', labelsize=10)
    fig.tight_layout()
    return fig_bytes(fig)


def per_participant_table(rows, dataset):
    names = [c[0] for c in COLS]
    h = ['Participant'] + [f'{LABEL[n].replace("Centre of pressure, forward", "CoP forward")}<br><span class="muted">bias / RMS ({UNIT[n]})</span>' for n in names]
    out = ['<table class="small"><thead><tr>' + ''.join(f'<th>{x}</th>' for x in h) + '</tr></thead><tbody>']
    for s in sorted({r['subject'] for r in rows}):
        cells = []
        for n in names:
            r = [x for x in rows if x['subject'] == s and x['column'] == n]
            if not r or int(r[0]['n_matched']) == 0:
                cells.append('<td class="muted">&ndash;</td>')
            else:
                cells.append(f'<td class="n">{fmt(f(r[0]["bias"]), 3)} / {fmt(f(r[0]["rms"]), 3)}</td>')
        out.append(f'<tr><td>{s}</td>{"".join(cells)}</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def top_table(task_rows, dataset, k=10, min_n=1000):
    cand = []
    for r in task_rows:
        n = int(r['n_matched'])
        if n < min_n:
            continue
        rms = f(r['rms'])
        cand.append((rms / SIZE[r['column']], r))
    cand.sort(key=lambda t: -t[0])
    h = ['Participant', 'Task (training label)', 'Column', 'Matched samples', 'Mean difference', 'RMS difference', 'RMS / reporting size']
    out = ['<table><thead><tr>' + ''.join(f'<th>{x}</th>' for x in h) + '</tr></thead><tbody>']
    for ratio, r in cand[:k]:
        c = r['column']
        out.append(f'<tr><td>{r["subject"]}</td><td>{html.escape(r["task"])}</td><td>{LABEL[c]} ({UNIT[c]})</td><td class="n">{int(r["n_matched"]):,}</td>'
                   f'<td class="n">{fmt(f(r["bias"]))}</td><td class="n">{fmt(f(r["rms"]))}</td><td class="n">{ratio:.1f}</td></tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def align_block(dataset, al, um):
    st = Counter(a['status'] for a in al)
    rows_match = sum(int(a['his_rows']) for a in al if a['status'] == 'matched' and a['his_rows'])
    rows_all = sum(int(a['his_rows']) for a in al if a['his_rows'])
    matched = [a for a in al if a['status'] == 'matched']
    legs = Counter(a['leg'] for a in matched)
    signs = Counter(a['sign_of_best_fit'] for a in matched)
    mx = max((f(a['align_rms_Nm_kg']) for a in matched), default=math.nan)
    reasons = Counter()
    for u in um:
        if u['side'] == 'training':
            r = u['reason']
            reasons['alignment failed (moment difference above 0.10 Nm/kg)' if r.startswith('alignment failed') else r] += 1
    lh_un = Counter(u['reason'] for u in um if u['side'] == 'locohub')
    li = [f'<li>Training recordings found in the files: {sum(1 for a in al if a["his_recording"]):,}; matched to a LocoHub recording: '
          f'<b>{st["matched"]:,}</b> ({100 * rows_match / rows_all:.1f}% of training rows).</li>']
    li.append(f'<li>Largest moment difference among matched pairs: {fmt(mx)} Nm/kg (alignment tolerance 0.10 Nm/kg). '
              f'Sign of best fit: {dict(signs)}.</li>')
    if dataset == 'gt21':
        li.append(f'<li>Reference leg chosen by best fit (the training file does not keep it): {dict(legs)}.</li>')
    else:
        li.append(f'<li>Right-leg strides used throughout (the converter wrote right for every row): {dict(legs)}.</li>')
    for r, c in reasons.most_common():
        li.append(f'<li>Training recordings not compared: {c:,} &ndash; {html.escape(r)}.</li>')
    for r, c in lh_un.most_common():
        li.append(f'<li>LocoHub recordings not compared: {c:,} &ndash; {html.escape(r)}.</li>')
    if dataset == 'um21' and st.get('strides_not_in_a_matched_segment'):
        n = sum(int(a['strides']) for a in al if a['status'] == 'strides_not_in_a_matched_segment')
        li.append(f'<li>LocoHub strides with no matched training segment: {n:,}.</li>')
    return '<ul>' + ''.join(li) + '</ul>'


def failures_table(al):
    bad = [a for a in al if a['status'] == 'alignment_failed']
    if not bad:
        return '<p>None.</p>'
    h = ['Participant', 'Training recording', 'Best moment RMS (Nm/kg)', 'Overlap (samples)', 'Training rows']
    out = ['<table class="small"><thead><tr>' + ''.join(f'<th>{x}</th>' for x in h) + '</tr></thead><tbody>']
    for a in sorted(bad, key=lambda a: -f(a['align_rms_Nm_kg'])):
        out.append(f'<tr><td>{a["subject"]}</td><td>{html.escape(a["his_recording"].split("|")[-1])}</td><td class="n">{f(a["align_rms_Nm_kg"]):.3f}</td>'
                   f'<td class="n">{a["align_overlap_n"]}</td><td class="n">{a["his_rows"]}</td></tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1d2330;--mut:#5d6677;--line:#d6dbe4;--card:#f5f7fa;--acc:#1b5fb0}
@media (prefers-color-scheme:dark){:root{--bg:#14171d;--fg:#e4e8ef;--mut:#9aa4b5;--line:#2c3340;--card:#1c212b;--acc:#7db3f0}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:1rem 1.2rem 4rem}
h1{font-size:1.6rem}h2{margin-top:2.2rem;border-bottom:1px solid var(--line);padding-bottom:.2rem}h3{margin-top:1.6rem}
table{border-collapse:collapse;width:100%;margin:.8rem 0;font-size:.92rem;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:.3rem .5rem;text-align:left;vertical-align:top}th{background:var(--card)}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.small{font-size:.82rem}.muted{color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.7rem 1rem;margin:1rem 0}
img{max-width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:6px}
.figs{display:flex;flex-wrap:wrap;gap:1rem}code{background:var(--card);padding:0 .2rem;border-radius:3px}
"""


def main():
    g_subj, g_task = load_subject_rows('gt21')
    u_subj, u_task = load_subject_rows('um21')
    g_al, g_um = load_align('gt21')
    u_al, u_um = load_align('um21')
    g_tab, g_data = main_table('gt21', g_subj)
    u_tab, u_data = main_table('um21', u_subj)
    figs = [img(fig_bias(g_data, u_data), 'Mean difference per column in units of the reporting size, GT21 and UM21'),
            img(fig_subject({'GT21': g_subj, 'UM21': u_subj}, 'ankle_angle', 'Ankle angle: mean difference per participant'),
                'Ankle angle mean difference per participant')]
    summ = json.load(open(AUD / 'training-compare-gt21-j1/summary.json'))
    unm = [u['column'] for u in summ['mapping']['training_unmapped']]
    notes = {u['column']: u['role'] for u in summ['mapping']['training_unmapped']}
    un_rows = ''.join(f'<tr><td><code>{html.escape(c)}</code></td><td>{html.escape(notes[c])}</td></tr>' for c in unm)
    mapping = ''.join(f'<tr><td>{LABEL[m["name"]]}</td><td><code>{m["training_column"]}</code></td><td><code>{m["locohub_column"]}</code></td>'
                      f'<td>{m["reporting_size"]:g} {m["unit"]}</td></tr>' for m in summ['mapping']['columns'])
    lh_unmapped_note = ('LocoHub columns not compared (hip, knee, thigh, pelvis, power, lateral and anterior forces, held signals) are listed in each '
                        '<code>summary.json</code> under <code>mapping.locohub_unmapped</code>.')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Training files vs LocoHub rebuilds, column by column</title><style>{CSS}</style></head><body>
<h1>Training files vs LocoHub rebuilds, column by column</h1>
<div class="card"><b>What this is.</b> For each signal the ankle model reads, how far the number in the training file is from the same sample
in the rebuilt LocoHub data. Descriptive only: the &ldquo;reporting sizes&rdquo; (2&deg;, 20&deg;/s, 0.05 Nm/kg, 0.05 BW, 0.02 m) only decide which
differences are counted in the last column. They are not quality limits, and nothing here approves or rejects either file.
Differences are <i>training minus LocoHub</i>. Unreviewed.</div>
<h2>Headline</h2>
<ul>
<li><b>Ankle moment and vertical force match.</b> GT21 ankle moment: RMS difference {fmt(g_data['ankle_moment']['rms'])} Nm/kg over {g_data['ankle_moment']['n']:,} samples;
GT21 vertical force RMS {fmt(g_data['vertical_force']['rms'])} BW. UM21 ankle moment RMS {fmt(u_data['ankle_moment']['rms'])} Nm/kg (the training value is read between 100 Hz frames).</li>
<li><b>Angles differ, and for some participants by whole turns.</b> GT21 ankle angle averages {fmt(g_data['ankle_angle']['bias'])}&deg; apart (RMS {fmt(g_data['ankle_angle']['rms'])}&deg;),
shank {fmt(g_data['shank_angle']['bias'])}&deg; (RMS {fmt(g_data['shank_angle']['rms'])}&deg;), foot {fmt(g_data['foot_angle']['bias'])}&deg; (RMS {fmt(g_data['foot_angle']['rms'])}&deg;).
Where the RMS is far above the mean (for example AB24, AB07, AB16), a read-only look at AB24 found training angles near &plusmn;350&deg; against LocoHub angles within &plusmn;30&deg; (section 3). UM21 angles are much closer: {fmt(u_data['ankle_angle']['bias'])}&deg;, {fmt(u_data['shank_angle']['bias'])}&deg;, {fmt(u_data['foot_angle']['bias'])}&deg; mean difference.</li>
<li><b>Velocity and centre of pressure</b> differ by method and origin (see caveats).</li>
</ul>
<h2>1. GT21 (training time file against rb07 exports)</h2>
<p>{len(GT21_SRC)} participants. Pooling: counts, coverage, mean, RMS and share past the reporting size are exact over all matched samples. Correlation and 95th percentile
are shown as the median over participants of each participant's own value, with the range in brackets (they cannot be pooled from per-participant summaries).</p>
{g_tab}
<h3>Per participant, mean difference / RMS</h3>{per_participant_table(g_subj, 'gt21')}
<h2>2. UM21 (training time file against package v4 phase file)</h2>
<p>{len(set(r['subject'] for r in u_subj))} participants, treadmill only, right leg; samples are LocoHub phase samples (150 per stride) with the training series read at the same source-time positions. Pooled directly (one job).</p>
{u_tab}
<h3>Per participant, mean difference / RMS</h3>{per_participant_table(u_subj, 'um21')}
<h2>Figures</h2>
<div class="figs">{figs[0]}{figs[1]}</div>
<p class="muted">Figure 1: mean difference divided by each column's reporting size (training minus LocoHub). Figure 2: ankle angle mean difference per participant, same sign convention.</p>
<h2>3. Biggest differences by participant and task</h2>
<p>Ranked by RMS divided by the reporting size, among participant-and-task groups with at least 1,000 matched samples. Task is the training file's own label.</p>
<div class="card"><b>Why AB24 tops the list.</b> A read-only probe of AB24 (output: <code>docs/quality/audits/training-compare-probe-ab24-angle-range.txt</code>) compared the eight AB24
recordings with the largest ankle-angle RMS and two typical ones. In the eight, the training ankle angle lies in roughly &minus;445 to &minus;343&deg; or 286 to 395&deg; while the LocoHub angle lies in about &minus;26 to 24&deg;;
foot angle is similarly out by about 180&deg; or 360&deg; in most of them. The two typical recordings differ by about 13&deg; (ankle) and 19&deg; (foot) with both series in a normal range.
This probe covers AB24 only; the pooled tables above do not separate such recordings, and I did not check the other participants recording by recording.</div>
<h3>GT21</h3>{top_table(g_task, 'gt21')}
<h3>UM21</h3>{top_table(u_task, 'um21')}
<h2>4. Alignment</h2>
<p>Training and LocoHub clocks are not assumed equal. Each training recording is matched to a LocoHub recording by name, then shifted in time by cross-correlating the ankle moment
(exact moment difference over all shifts, both signs); a pair counts only if the best moment RMS is at most 0.10 Nm/kg over at least 100 samples (and 30% of the training moment samples). The tolerance only decides
whether two recordings are the same recording.</p>
<h3>GT21</h3>{align_block('gt21', g_al, g_um)}
<h3>UM21</h3>{align_block('um21', u_al, u_um)}
<h3>Alignment failures</h3><p>16 of the 19 UM21 failures are the short <code>d0x5</code> segments (about 550 training rows each) 2 are <code>a0x5</code> and 1 is <code>d0x2</code>; they have the least moment data to align on. They are left out of the statistics, not forced to match.</p><p><b>GT21:</b></p>{failures_table(g_al)}<p><b>UM21:</b></p>{failures_table(u_al)}
<h2>5. Columns compared and not compared</h2>
<table class="small"><thead><tr><th>Column</th><th>Training</th><th>LocoHub</th><th>Reporting size</th></tr></thead><tbody>{mapping}</tbody></table>
<p>Training columns not compared (same list for both files):</p><table class="small"><tbody>{un_rows}</tbody></table>
<p>{lh_unmapped_note} LocoHub UM21 package v4 (phase only) has no ankle velocity or vertical force column, so those two rows have no matched samples.</p>
<h2>6. Caveats</h2>
<ul>
<li><b>Velocity</b> in the training file is its own backward difference of the sampled angle; LocoHub uses the source or stride slope. The difference is a method difference.</li>
<li><b>Centre of pressure</b>: the LocoHub value has the 0.100 m origin shift added back before comparing, so the mean difference also contains any difference between the two ankle-centre definitions. It is only present where force was measured.</li>
<li><b>UM21 package v4, the one compared here, has no LocoHub force and no time table</b>; comparisons use LocoHub phase samples only. Package v5 adds a time table with force and was not compared.</li>
<li><b>Angles</b>: the training UM21 shank/foot values include its own &minus;2&times; pelvis tilt correction; the training GT21 values were built on the old pelvis tilt, and the angle zero differs between the two (static pose vs gravity).</li>
<li><b>Coverage</b> is the fraction of compared positions with a value in each series; a missing value in either series removes that sample from every statistic of that column.</li>
<li>Training recordings with too little finite ankle moment to align are listed, not compared; every skipped recording is counted in section 4.</li>
<li>GT21 jobs were run two participants at a time to stay under the memory cap; pooled values merge those jobs. Reconstructed from <code>docs/quality/audits/training-compare-*</code>.</li>
</ul></body></html>"""
    OUT.write_text(page)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
