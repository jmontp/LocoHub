"""Local review sheet template: one page José can validate by looking.

Order is fixed: ask, headline, check chips, figures, decision, not shown,
reply, folded details. See AGENTS.md "Decisions and handoffs".
"""
from html import escape
from pathlib import Path
import re

STATES = {'pass': '✓', 'fail': '✗ failed:', 'unchecked': '– not checked:'}
PROSE_BUDGET = 60

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#20252B;--muted:#5b6672;--line:#dde2e7;--ok:#1f7a4d;--okbg:#e5f3eb;
--bad:#a8322d;--badbg:#fbe9e7;--off:#5b6672;--offbg:#eceff2;--ask:#7a4a00;--askbg:#ffefd6;--accent:#24506F}
@media (prefers-color-scheme:dark){:root{--bg:#11161b;--card:#1a2129;--ink:#e6ebf0;--muted:#9aa6b2;--line:#2c3743;
--ok:#5cc28f;--okbg:#14291e;--bad:#f08c84;--badbg:#2e1716;--off:#9aa6b2;--offbg:#222b35;--ask:#f5b55c;--askbg:#2d2213;--accent:#8db8de}
figure img{filter:brightness(.88)}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
padding:20px max(16px,4vw) 48px}
main{max-width:860px;margin:0 auto;display:grid;gap:16px}
.ask{background:var(--askbg);color:var(--ask);border-radius:8px;padding:10px 14px;font-weight:700}
h1{margin:0;font-size:1.45rem;line-height:1.25} h2{margin:0 0 6px;font-size:1.05rem}
.chips{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.chip{padding:6px 11px;border-radius:999px;font-size:.9rem;font-weight:600}
.pass{background:var(--okbg);color:var(--ok)} .fail{background:var(--badbg);color:var(--bad)}
.unchecked{background:var(--offbg);color:var(--off)}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
figure img{width:100%;display:block;background:#fff;border-radius:4px}
.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
figcaption{color:var(--muted);font-size:.9rem;margin-top:6px}
.decision{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--ask);border-radius:8px;padding:14px 16px;display:grid;gap:10px}
.table{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
td.num{font-variant-numeric:tabular-nums}
.muted{color:var(--muted);font-size:.9rem}
details{font-size:.9rem;color:var(--muted)} summary{cursor:pointer;font-weight:600}
@media (max-width:600px){table,tbody,tr,td,th{display:block}thead{display:none}tr{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px}
th,td{border:0;padding:2px 0}td.num{white-space:normal}td::before{content:attr(data-label) ': ';color:var(--muted)}}
code{font:600 .95rem ui-monospace,Consolas,monospace;background:var(--card);border:1px solid var(--line);border-radius:5px;padding:3px 7px}
"""


def words(html):
    return len(re.sub(r'<[^>]+>', ' ', html).split())


def page(path, *, title, ask, headline, chips, figures, not_shown, reply, details=(), decision=None):
    """Write a sheet. chips: [(state, text)]; figures: [(png name or names, question, caption, alt)];
    each PNG is one panel saved at most 4.5 in wide with fonts of at least 10 pt so it stays legible on a phone;
    decision: dict(question, columns, rows=[(key, cells)], recommendation, footnote)."""
    esc = escape
    for state, _ in chips:
        if state not in STATES:
            raise ValueError(f'Unknown chip state {state}')
    if len(chips) > 8 or len(figures) > 3 or len(not_shown) > 3:
        raise ValueError('Sheet exceeds chip, figure or not-shown budget')
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>'
           f'<style>{CSS}</style></head><body><main>',
           f'<div class="ask">{esc(ask)}</div>', f'<h1>{esc(headline)}</h1>',
           '<ul class="chips">' + ''.join(f'<li class="chip {s}">{STATES[s]} {esc(t)}</li>' for s, t in chips) + '</ul>']
    for names, question, caption, alt in figures:
        # One panel per image so text stays legible when panels stack on a phone.
        names = [names] if isinstance(names, str) else names
        images = ''.join(f'<a href="{esc(n)}"><img src="{esc(n)}" alt="{esc(alt)}"></a>' for n in names)
        out.append(f'<figure><h2>{esc(question)}</h2><div class="panels">{images}</div>'
                   f'<figcaption>{esc(caption)}</figcaption></figure>')
    prose = ' '.join([ask, headline] + [c for _, _, c, _ in figures] + list(not_shown))
    if decision:
        head = ''.join(f'<th>{esc(c)}</th>' for c in ['Option'] + decision['columns'])
        rows = ''.join('<tr><th>' + esc(key) + '</th>' + ''.join(f'<td class="num" data-label="{esc(h)}">{esc(c)}</td>'
                       for h, c in zip(decision['columns'], cells)) + '</tr>' for key, cells in decision['rows'])
        out.append(f'<section class="decision"><h2>{esc(decision["question"])}</h2>'
                   f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
                   + (f'<p class="muted">{esc(decision["footnote"])}</p>' if decision.get('footnote') else '')
                   + f'<details><summary>Show agent recommendation (after you choose)</summary><p>{esc(decision["recommendation"])}</p></details></section>')
        prose += ' ' + decision.get('footnote', '')
    out.append('<section><h2>Not shown by this sheet</h2><ul class="muted">' + ''.join(f'<li>{esc(n)}</li>' for n in not_shown) + '</ul></section>')
    out.append(f'<p>Reply in chat: <code>{esc(reply)}</code></p>')
    if details:
        out.append('<details><summary>Details</summary><ul>' + ''.join(f'<li>{esc(d)}</li>' for d in details) + '</ul></details>')
    out.append('</main></body></html>\n')
    if words(prose) > PROSE_BUDGET:
        raise ValueError(f'Sheet prose is {words(prose)} words; budget {PROSE_BUDGET}')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(out), encoding='utf-8')
