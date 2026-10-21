#!/usr/bin/env python3
"""Build static, artifact-specific audit evidence from reviewed investigation records.

This does not inspect or approve scientific files. Run the referenced audits to
produce new evidence; a page rebuild never upgrades a file's status.
"""
from pathlib import Path
import hashlib
import html
import json

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [('umich', 'Umich 2021'), ('gtech', 'Georgia Tech'), ('remaining', 'Other converted datasets')]
FAMILIES = [('umich_2021','um21','Umich 2021'),('gtech_2021','gt21','Georgia Tech 2021'),
            ('gtech_2023','gt23','Georgia Tech 2023'),('gtech_2024','gt24','Georgia Tech 2024'),
            ('gtech_2025','gt25d','Georgia Tech 2025'),('gait120','ga26','Gait120'),
            ('mblue','mb24','MBLUE Ankle'),('strokepig','sp50','StrokePiG')]
ESC = lambda value: html.escape(str(value), quote=True)


def file_status(findings):
    """A sample pass can never clear an artifact, including when there are zero findings."""
    failures = [f for f in findings if f['severity'] == 'failure' and not f['title'].lower().startswith('needs investigation')]
    if failures:
        return 'Problem found', 'problem'
    if any(f['severity'] in {'warning', 'failure'} for f in findings):
        return 'Needs investigation', 'review'
    return 'Not cleared', 'unknown'


def family(path):
    for prefix, slug, label in FAMILIES:
        if prefix in Path(path).name.lower():
            return slug, label
    return 'other', 'Other'


def evidence_html(directory):
    artifacts = []
    risks = []
    for group, _ in GROUPS:
        report = json.loads((directory / f'{group}.json').read_text())
        risks.extend((group, f) for f in report['findings'] if f['scope'] == 'converter')
        for artifact in report['artifacts']:
            findings = [f for f in report['findings'] if f['scope'] == 'artifact' and artifact['path'] in f['paths']]
            slug, name = family(artifact['path'])
            artifacts.append((slug, name, group, artifact, findings))
    order = {slug: i for i, (_, slug, _) in enumerate(FAMILIES)}
    artifacts.sort(key=lambda r: (order.get(r[0], 99), r[3]['path']))
    text = ['<details class="audit-method"><summary>Audit scope &amp; status definitions</summary>',
            f'<p>{len(artifacts)} local files inspected on 20 October 2026. Checks range from metadata and small source samples to full identity-column scans; no whole-file numerical certification.</p>',
            '<p><strong>Problem found:</strong> observed inconsistency. <strong>Needs investigation:</strong> unresolved anomaly. <strong>Not cleared:</strong> insufficient evidence. A sample pass does not approve a file.</p></details>',
            '<div class="table-scroll audit-table" role="region" tabindex="0" aria-label="Local file audit results"><table><caption>Local file audit — select a file for its evidence and next steps</caption><thead><tr><th scope="col">Dataset / file</th><th scope="col">File status</th><th scope="col">Main finding</th><th scope="col">Recorded findings</th></tr></thead><tbody>']
    details = []
    for slug, name, group, artifact, findings in artifacts:
        path = artifact['path']
        identity = 'audit-' + hashlib.sha256(path.encode()).hexdigest()[:12]
        label, state = file_status(findings)
        ranked = sorted(findings, key=lambda f: 1 if f['title'].lower().startswith('needs investigation') else {'failure':0,'warning':1,'unknown':2,'passed':3}.get(f['severity'], 2))
        lead = ranked[0] if ranked else {'title': 'No source-linked approval recorded', 'check_scope': 'Metadata inspection only'}
        coverage = f'{len(findings)} finding{"s" if len(findings) != 1 else ""}; expand for scope'
        duplicate_name = sum(Path(a[3]['path']).name == Path(path).name for a in artifacts) > 1
        location = f'<small class="audit-file-location">{ESC(Path(path).parent)}</small>' if duplicate_name else ''
        text.append(f'<tr data-audit-dataset="{slug}"><th scope="row"><span class="audit-dataset-name">{ESC(name)}</span><a href="#{identity}">{ESC(Path(path).name)}</a>{location}</th><td><span class="audit-state audit-{state}">{label}</span></td><td>{ESC(lead["title"])}</td><td>{coverage}</td></tr>')
        block = [f'<details class="audit-evidence" id="{identity}" data-audit-dataset="{slug}"><summary>{ESC(name)} · {ESC(Path(path).name)} — {label}</summary>',
                 '<details class="audit-file-metadata"><summary>File identity and audit limits</summary>',
                 f'<p><strong>Exact local path:</strong> <code>{ESC(path)}</code></p>',
                 f'<p>{artifact["rows"]:,} rows · {artifact["cols"]} columns · {artifact["size_bytes"]:,} bytes. File modification timestamp (ns): <code>{artifact["mtime_ns"]}</code>.</p>',
                 '<p class="audit-limitation">Identity is recorded by path, byte size and modification time. No full-file content hash or online-download match was established. These findings must not be transferred to a different version based on its filename.</p></details>']
        for finding in ranked:
            tag = {'failure':'Observed problem','warning':'Review needed','unknown':'Unresolved','passed':'Sample check passed'}.get(finding['severity'],'Unresolved')
            if finding['title'].lower().startswith('needs investigation'):
                tag = 'Numeric anomaly — cause unverified'
            block.extend([f'<details class="audit-finding"><summary>{ESC(tag)}: {ESC(finding["title"])}</summary>',
                          f'<p>{ESC(finding["evidence"])}</p><p><strong>Checked:</strong> {ESC(finding["check_scope"])}</p>',
                          f'<p><strong>Next step:</strong> {ESC(finding["next_step"])}</p></details>'])
        block.append(f'<p><a href="audits/{group}.json">Full investigation record, including positive evidence and limitations (JSON)</a></p></details>')
        details.append('\n'.join(block))
    text.append('</tbody></table></div>')
    text.append('<p data-audit-dataset="gt23" class="audit-limitation"><strong>Georgia Tech 2023 phase:</strong> no local phase export was available to inspect. Its time file was inspected separately. An unavailable file is not a passing file.</p>')
    text.extend(details)
    text.append('<details class="quality-disclosure"><summary>Converter-code risks — not proof every stored file is affected</summary><p>These are paths in current conversion code that need correction or source verification. Historical files may have been produced by different code.</p>')
    for group, finding in risks:
        text.extend([f'<section class="audit-finding"><h3>{ESC(finding["title"])}</h3><p>{ESC(finding["evidence"])}</p>',
                     f'<p><strong>Scope:</strong> {ESC(finding["check_scope"])}</p><p><strong>Next step:</strong> {ESC(finding["next_step"])}</p>',
                     f'<p><a href="audits/{group}.json">Investigation record and code locations</a></p></section>'])
    text.append('</details>')
    text.append('<details class="quality-disclosure"><summary>What about the online downloads?</summary><p>No online download was retrieved and hash-matched during this local audit. Their current status is <strong>Not assessed as exact downloadable files</strong>. Local findings are useful warnings, but are not a hash-bound verdict on those bytes. Select the local file evidence above before making any inference.</p><p><a href="../datasets/index.html">Catalog and download links</a></p></details>')
    return '\n'.join(text)


def main():
    page = ROOT / 'docs/quality/index.html'
    before, rest = page.read_text().split('<!-- AUDIT_EVIDENCE_START -->', 1)
    _, after = rest.split('<!-- AUDIT_EVIDENCE_END -->', 1)
    page.write_text(before + '<!-- AUDIT_EVIDENCE_START -->\n' + evidence_html(ROOT / 'docs/quality/audits') + '\n<!-- AUDIT_EVIDENCE_END -->' + after)


if __name__ == '__main__':
    main()
