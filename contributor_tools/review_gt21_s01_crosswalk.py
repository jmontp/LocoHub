"""GT21-S01: cohort-to-source crosswalk for the 22 Georgia Tech 2021 publisher participants.

Read-only. Reads small publisher manifests and metadata receipts, prior audit
JSONs, the native SubjectInfo export CSV, AB17 recovery receipts and directory
listings (names and sizes) of the local source root. It never opens a motion,
force or other scientific data array and never downloads or extracts an
archive. AB17's ZIP is checked by size only (stat); its SHA-256 comes from the
prior acquisition receipt.

Writes docs/quality/audits/gt21-s01-cohort-crosswalk.json, a plan-only AB14
version 1 equivalence job under converted_datasets/reconversion_v2/ (not run),
and the decision sheet review_sheets/D-GT21-S01-1/.

Decision option order (neutral): by participants releasable with the current
converter (stop at 16: 16; version 1: 16; author 2024 copy: up to 22), ties
broken by download size (none, then the five remaining version 1 archives).
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page

SRC = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET'
CONVERTER = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/convert_gtech_2021_phase_to_parquet.m'
SEGMENTS = ROOT / 'contributor_tools/conversion_scripts/Gtech_2021/utilities/gtech_estimate_segment_lengths.m'
ACQUIRE = ROOT / 'contributor_tools/acquire_gt21_missing_participant.py'
RV2 = ROOT / 'converted_datasets/reconversion_v2'
RECEIPTS = RV2 / 'gt21_participant_repository_receipts_20261021'
FRESH = RV2 / 'gt21_s01_crosswalk_20261031'
EQUIV = RV2 / 'gt21_ab14_v1_equivalence_20261031'
MASS = RV2 / 'gt21_subject_mass_review_20261021'
AB17_ROOT = Path('/mnt/s/locomotion_data/gt21_missing_participants_v1/AB17')
AB17_PLAN = RV2 / 'gt21_ab17_restoration_v4_20261021/plan.json'
AUD = ROOT / 'docs/quality/audits'
OUT = AUD / 'gt21-s01-cohort-crosswalk.json'
SHEET = ROOT / 'review_sheets/D-GT21-S01-1'
PARTS = {'fcgm3chfff': 1, 'k9kvm5tn3f': 2, 'jj3r5f9pnf': 3}
FRESH_MANIFESTS = {'fcgm3chfff': 'fc-v1-files.json', 'k9kvm5tn3f': 'k9-v1-files.json', 'jj3r5f9pnf': 'jj-v1-files.json'}
MODES = ('levelground', 'ramp', 'stair', 'treadmill')
TRIAL_CHANNELS = ('conditions', 'emg', 'fp', 'gcLeft', 'gcRight', 'gon', 'id', 'ik', 'imu', 'jp', 'markers', 'ik_offset')
MISSING = ('AB12', 'AB15', 'AB17', 'AB19', 'AB23', 'AB28')
REFERENCE = 'AB14'  # smallest version 1 archive of a participant already held locally
CONVERTER_READS = {
    'conditions': 'convert_gtech_2021_phase_to_parquet.m 821',
    'ik_offset': 'convert_gtech_2021_phase_to_parquet.m 849 (joint angles); also exported at 73',
    'id': 'convert_gtech_2021_phase_to_parquet.m 860',
    'gcRight': 'convert_gtech_2021_phase_to_parquet.m 871',
    'gcLeft': 'convert_gtech_2021_phase_to_parquet.m 884',
    'fp': 'convert_gtech_2021_phase_to_parquet.m 897',
    'markers': 'convert_gtech_2021_phase_to_parquet.m 908',
    'static/markers': 'gtech_estimate_segment_lengths.m 75-80, called at convert_gtech_2021_phase_to_parquet.m 152; preferred source of segment lengths, with silent fallback to walking-trial markers',
}
DPI = 170
GREEN, RED, AMBER, GREY = '#cfe8da', '#f4cdc9', '#fbe3b5', '#e3e7eb'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def rel(path):
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def load(path, bindings):
    bindings[rel(path)] = sha(path)
    return json.loads(Path(path).read_text())


def manifest_rows(items):
    return {i['filename']: {'size': i['size'], 'sha256': i['content_details']['sha256_hash'],
                            'file_id': i['id'], 'status': i['status']} for i in items}


def session(subject):
    dates = sorted(p.name for p in (SRC / subject).iterdir() if p.is_dir() and p.name != 'osimxml')
    return dates


def local_listing(subject):
    """Directory names and conditions-file counts only; no file is opened."""
    sdir = SRC / subject
    dates = session(subject)
    out = {'session_directories': dates, 'osimxml_present': (sdir / 'osimxml').is_dir()}
    if len(dates) != 1:
        out['note'] = 'not exactly one session directory; counts not computed'
        return out
    sess = sdir / dates[0]
    counts = {m: len(list((sess / m / 'conditions').glob('*.mat'))) for m in MODES}
    out.update({
        'mode_directories': sorted(p.name for p in sess.iterdir() if p.is_dir()),
        'recordings_by_mode_conditions_files': counts,
        'recordings': sum(counts.values()),
        'static_directory_present': (sess / 'static').is_dir(),
        'ik_offset_present_in_all_four_modes': all((sess / m / 'ik_offset').is_dir() for m in MODES),
    })
    return out


def local_files(subject):
    """Relative path -> byte size for every local file of one participant (stat only)."""
    base = SRC / subject
    return {str(p.relative_to(SRC)): p.stat().st_size for p in sorted(base.rglob('*')) if p.is_file()}


def folder_counts_local(files):
    counts = {}
    for path in files:
        parts = path.split('/')
        key = 'osimxml' if parts[1] == 'osimxml' else (f'static/{parts[3]}' if parts[2] == 'static' else parts[3])
        counts[key] = counts.get(key, 0) + 1
    return counts


def folder_counts_v1(plan):
    counts = {}
    for record in plan['records']:
        for channel in record['channels']:
            counts[channel] = counts.get(channel, 0) + 1
    for member in plan['other_members']:
        parts = member['member'].split('/')
        key = 'osimxml' if parts[1] == 'osimxml' else (f'static/{parts[3]}' if parts[2] == 'static' else parts[3])
        counts[key] = counts.get(key, 0) + 1
    return counts


def grid(path, row_labels, col_labels, cells, legend, left=0.22):
    """cells[r][c] = (text, colour). One panel, 4.5 in wide, 10 pt text; the sheet supplies the title."""
    nrow, ncol = len(row_labels), len(col_labels)
    fig_h = 0.27 * nrow + 0.95
    fig, ax = plt.subplots(figsize=(4.5, fig_h), dpi=DPI)
    ax.set_xlim(0, ncol)
    ax.set_ylim(nrow, -1.25)
    for r in range(nrow):
        for c in range(ncol):
            text, colour = cells[r][c]
            ax.add_patch(Rectangle((c + 0.04, r + 0.06), 0.92, 0.88, facecolor=colour, edgecolor='white'))
            ax.text(c + 0.5, r + 0.52, text, ha='center', va='center', fontsize=10)
    for c, label in enumerate(col_labels):
        ax.text(c + 0.5, -0.12, label, ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_yticks([r + 0.5 for r in range(nrow)])
    ax.set_yticklabels(row_labels, fontsize=10)
    ax.set_xticks([])
    for side in ('top', 'right', 'bottom', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(left=False)
    fig.text(0.02, 0.01, legend, fontsize=10, ha='left', va='bottom')
    fig.subplots_adjust(left=left, right=0.99, top=1 - 0.05 / fig_h, bottom=0.45 / fig_h)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def main():
    b = {}
    coverage = load(AUD / 'gt21-participant-source-coverage.json', b)
    phases = load(AUD / 'gt21-all-source-phases.json', b)
    load(AUD / 'gt21-ab17-recovery.json', b)
    load(AUD / 'gt21-ab17-metadata-source-followup.json', b)
    enrich = load(AUD / 'gt21-ab17-native-metadata-enrichment-v2.json', b)
    recipe = load(AUD / 'gt21-ab17-local-processing-recipe.json', b)
    load(AUD / 'queue-recovery-expanded-49-summary.json', b)
    for p in (SRC / 'README.txt', SRC / 'SubjectInfo.mat', CONVERTER, SEGMENTS, ACQUIRE):
        b[rel(p)] = sha(p)

    v1, v2 = {}, {}
    for ds, part in PARTS.items():
        for ver, store in ((1, v1), (2, v2)):
            rows = manifest_rows(load(RECEIPTS / f'{ds}-v{ver}-files.json', b))
            for name, row in rows.items():
                store[name] = dict(row, part=part, dataset_id=ds, doi=f'10.17632/{ds}.{ver}')
    heads = {h['filename']: h for h in load(RECEIPTS / 'head-receipts.json', b)}

    embedded = {}
    for f in sorted(FRESH.glob('*.json')):
        embedded[f.name] = {'sha256': sha(f), 'bytes': f.stat().st_size, 'content': load(f, b)}
    versions = {ds: embedded[f'{ds}-versions.json']['content'] for ds in PARTS}
    licences = {ds: embedded[f'{ds}-v1-meta.json']['content']['data_licence']['short_name'] for ds in PARTS}
    fresh = {}
    for ds, name in FRESH_MANIFESTS.items():
        fresh.update(manifest_rows(embedded[name]['content']))

    with open(MASS / 'subject_masses.csv', newline='') as f:
        weight = {r['Subject']: r['Weight'] for r in csv.DictReader(f)}
    b[rel(MASS / 'subject_masses.csv')] = sha(MASS / 'subject_masses.csv')
    mass_cmp = load(MASS / 'source_comparison.json', b)

    ab17_files = {n: load(AB17_ROOT / n, b) for n in ('acquisition_plan.json', 'acquisition_result.json', 'archive_inspection.json')}
    ab17_zip = AB17_ROOT / f"{ab17_files['acquisition_result.json']['sha256']}.zip"
    ab17_plan = load(AB17_PLAN, b)
    ab17_modes = {}
    for r in ab17_plan['records']:
        ab17_modes[r['mode']] = ab17_modes.get(r['mode'], 0) + 1
    ab17_channels = sorted(set.intersection(*(set(r['channels']) for r in ab17_plan['records'])))
    ab17_dates = sorted({r['date'] for r in ab17_plan['records']})
    ab17_watch = load(RV2 / 'gt21_ab17_after_gt23_pose_20261021/status.json', b)
    meta_watch = load(RV2 / 'gt21_subjectinfo_after_um21_20261021/status.json', b)

    subjects = [n[:-4] for n in sorted(v1) if n.startswith('AB') and n.endswith('.zip')]
    local = sorted(p.name for p in SRC.iterdir() if p.is_dir() and p.name.startswith('AB'))
    v2_containers = {n: r for n, r in v2.items() if n.startswith('Subjects_Part')}

    def v2_container(s):
        num = int(s[2:])
        for name, row in v2_containers.items():
            lo, hi = name.rsplit('_', 1)[1].removesuffix('.zip').split('-')
            if int(lo[2:]) <= num <= int(hi[2:]):
                return {'archive': name, 'doi': row['doi'], 'size': row['size'], 'sha256': row['sha256'],
                        'membership': 'not_checked: assigned from the archive-name range only; member list not fetched'}
        return {'archive': None, 'membership': 'not_checked'}

    rows = []
    local_total = 0
    for s in subjects:
        a = v1[f'{s}.zip']
        f = fresh.get(f'{s}.zip')
        row = {
            'subject': s,
            'publisher_v1_archive': {'doi': a['doi'], 'part': a['part'], 'filename': f'{s}.zip', 'file_id': a['file_id'],
                                     'size': a['size'], 'sha256': a['sha256'], 'status': a['status'],
                                     'recheck_20261031': ('file id, size and SHA-256 unchanged' if f and f['size'] == a['size'] and f['sha256'] == a['sha256'] and f['file_id'] == a['file_id']
                                                          else 'CHANGED' if f else 'not listed in fresh manifest')},
            'publisher_v2_container': v2_container(s),
            'licence': licences[a['dataset_id']],
            'author_2024_mirror': 'not_checked: the saved mirror page does not expose participant folders in plain text',
            'metadata': {
                'source_file': 'SubjectInfo.mat (byte-equal to the publisher v1 and v2 manifest record)',
                'Weight_literal': weight.get(s),
                'Weight_units': 'unresolved (no VariableUnits read; local scripts divide id/jp by it, which supports but does not prove kg)',
                'height_and_other_columns': 'not_checked: the native export read only Subject and Weight',
                'canonical_mass_approved': False,
            },
        }
        if s in local:
            lst = local_listing(s)
            local_total += lst.get('recordings', 0)
            row['local_source'] = dict(lst, root=rel(SRC / s))
            row['local_byte_identity_to_publisher'] = 'not_checked: no publisher archive for this subject was fetched; the local tree carries 2024 static/ik_offset additions absent from the recovered v1 AB17 archive, so it is not the v1 archive as published'
            row['in_local_2301_source_census'] = s in phases['subjects']
            row['converter_inputs_present'] = True
            row['disposition'] = 'local_source_present_publisher_byte_identity_not_checked'
            row['recoverability'] = 'present locally'
        elif s == 'AB17':
            res = ab17_files['acquisition_result.json']
            row['local_source'] = {
                'root': str(AB17_ROOT),
                'archive_bytes_stat_20261031': ab17_zip.stat().st_size,
                'archive_sha256_from_acquisition_receipt': res['sha256'],
                'receipt_sha256_matches_publisher_v1_manifest': res['sha256'] == a['sha256'],
                'receipt_bytes_match_publisher_v1_manifest': res['bytes'] == a['size'] == ab17_zip.stat().st_size,
                'archive_rehashed_this_task': False,
                'zip_directory': {'members': ab17_files['archive_inspection.json']['members'],
                                  'expanded_bytes': ab17_files['archive_inspection.json']['expanded_bytes']},
                'planned_recordings_by_mode': ab17_modes,
                'planned_recordings': len(ab17_plan['records']),
                'session_directories': ab17_dates,
                'channels_in_every_planned_record': ab17_channels,
                'static_directory_present': ab17_files['archive_inspection.json']['version_reconciliation']['archive_static_directory_present'],
                'ik_offset_present': ab17_files['archive_inspection.json']['version_reconciliation']['archive_ik_offset_directory_present'],
                'extracted': (AB17_ROOT / 'extracted_v1_independent_20261021').exists(),
                'extraction_watcher_status': ab17_watch['status'],
                'subjectinfo_unit_watcher_status': meta_watch['status'],
            }
            row['in_local_2301_source_census'] = False
            row['converter_inputs_present'] = False
            row['disposition'] = 'recovered_publisher_v1_archive_verified_not_extracted_not_converted'
            row['recoverability'] = 'bytes held locally; extraction and conversion blocked'
            row['blockers'] = ab17_plan['canonical_blockers'] + [
                'Extraction watcher stopped incomplete; a fresh reviewed launch through the guarded launcher is required (GT21-A01).',
                'SubjectInfo Weight units unresolved; guarded native unit read stopped before launch (GT21-A02).',
                'Source choice for the missing participants is open (D-GT21-S01-1).']
        else:
            h = heads.get(f'{s}.zip', {})
            row['local_source'] = None
            row['publisher_availability'] = {'head_20261021': {'http_status': h.get('http_status'), 'content_length': h.get('content_length')}}
            row['in_local_2301_source_census'] = False
            row['converter_inputs_present'] = False
            row['disposition'] = 'unrecovered_publisher_archive_available_not_fetched'
            row['recoverability'] = 'publisher v1 archive listed COMPLETED with SHA-256; not downloaded'
            row['blockers'] = ['No local bytes. Which source to recover from is open (D-GT21-S01-1).',
                               'Version 1 is expected to lack static and ik_offset like AB17; not checked for this archive.']
        rows.append(row)

    # AB14 local listing and version 1 equivalence plan (plan only, never run here).
    ref_files = local_files(REFERENCE)
    ref_counts = folder_counts_local(ref_files)
    v1_counts = folder_counts_v1(ab17_plan)
    ref = v1[f'{REFERENCE}.zip']
    remaining_v1_bytes = sum(v1[f'{s}.zip']['size'] for s in MISSING if s != 'AB17')
    equivalence_plan = {
        'status': 'plan_only_not_launched',
        'scientific_approval': False,
        'question': 'Did the 2024 author update change the shared trial files (conditions, emg, fp, gcLeft, gcRight, gon, id, ik, imu, jp, markers, osimxml) relative to publisher version 1?',
        'why': 'Settles, for any choice in D-GT21-S01-1, whether version 1 checksums can verify trial files of the 2024 copy and whether the 2024 RUN_OSIM update changed ik/id.',
        'subject': REFERENCE,
        'selection_rule': 'Smallest version 1 archive of a participant already held locally.',
        'archive': {'doi': ref['doi'], 'filename': f'{REFERENCE}.zip', 'file_id': ref['file_id'], 'size': ref['size'],
                    'sha256': ref['sha256'], 'status': ref['status'],
                    'download_url': f"https://data.mendeley.com/public-files/datasets/{ref['dataset_id']}/files/{ref['file_id']}/file_downloaded",
                    'licence': licences[ref['dataset_id']], 'recheck_20261031': rows[subjects.index(REFERENCE)]['publisher_v1_archive']['recheck_20261031']},
        'destination': f'/mnt/s/locomotion_data/gt21_v1_equivalence_reference/{REFERENCE}',
        'local_reference': {'root': rel(SRC / REFERENCE), 'files': len(ref_files), 'bytes': sum(ref_files.values()),
                            'files_by_folder': dict(sorted(ref_counts.items()))},
        'steps': [
            'Download the single archive through the reviewed guarded launcher, one job, after the numerical/I-O slot is free; stream with fixed size and SHA-256 validation; never write into the active source root.',
            'Read only the ZIP central directory (member names, uncompressed sizes, CRC32); do not extract.',
            'For each version 1 member, find the same relative path in the local tree; compare byte size, then CRC32 of the local file bytes (streamed, no MAT decoding).',
            'Report counts per mode and folder: identical, size or CRC differs, version 1 only, local only. Expected local only: 143 ik_offset trial files and 3 static files; anything else is a finding.',
            'Members that differ are listed for a separate decoded comparison task; no array is decoded in this job.',
        ],
        'limits': {'parallel_downloads': 1, 'buffer_bytes': 1048576, 'bandwidth_bytes_per_second': 1048576, 'timeout_seconds': 2700,
                   'disk_reserve_after_download_bytes': 16106127360, 'address_space_mib': 256,
                   'windows_startup_mib': 2816, 'windows_runtime_mib': 2048, 'process_priority': 'nice 19, ionice idle',
                   'local_bytes_read_for_crc': sum(ref_files.values())},
        'prerequisites': [
            'Reviewed guarded launcher (UM21-T02) available; until then launch nothing.',
            'acquire_gt21_missing_participant.py accepts only participants in the missing ledger and writes under gt21_missing_participants_v1; a reviewed reference mode (explicit subject, separate destination) and a CRC comparison script are required before launch.',
            'Fresh disk and memory admission immediately before launch.',
        ],
        'outputs_expected': ['acquisition receipt with SHA-256', 'central-directory listing', 'per-folder identity table', 'list of differing members'],
        'not_claimed': 'CRC32 equality detects change; it is not a cryptographic proof. Equality of trial files would not validate static or ik_offset, which version 1 lacks.',
    }
    EQUIV.mkdir(parents=True, exist_ok=True)
    plan_path = EQUIV / 'plan.json'
    plan_path.write_text(json.dumps(equivalence_plan, indent=2) + '\n')

    decision = {
        'id': 'D-GT21-S01-1',
        'task_id': 'GT21-S01',
        'question': 'Six of the 22 Georgia Tech 2021 participants are missing here. Their checksummed publisher archives (2021) lack the static-pose trials and static-relative joint angles that our converter reads; the authors\' 2024 copy, which the other 16 came from, has them but no publisher checksums. Where should the six come from?',
        'options': [
            {'key': 'A', 'label': 'Stop at 16 participants',
             'consequence': 'The six are documented as unavailable; GT21 is released with 16 of 22; no downloads. Reversible.'},
            {'key': 'B', 'label': 'Publisher version 1 archives (checksummed)',
             'consequence': f'Bytes verified against publisher checksums; the six need a second recipe (model-zero angles, segment lengths from walking markers) or are released without joint angles; about {remaining_v1_bytes / 1e9:.1f} GB more to download. Reversible.'},
            {'key': 'C', 'label': "Authors' 2024 copy",
             'consequence': 'Same folders and recipe as the 16; LocoHub records its own hashes at download; trial files can be checked against version 1 checksums if the planned one-participant comparison shows them unchanged; whether the copy holds all six is not yet checked. Reversible.'},
        ],
        'options_order': f'By participants releasable with the current converter (16, 16, up to 22); ties broken by download size (none, then about {remaining_v1_bytes / 1e9:.1f} GB).',
        'recommended': 'C',
        'confidence': 'medium',
        'why': "The 16 local participants already come from the authors' 2024 update without publisher checksums, so C adds no new trust assumption and keeps one recipe and one angle reference across the cohort. B would mix two angle references in one dataset. C still depends on the copy holding all six, which is not yet checked.",
        'check': 'Sheet, second figure: the version 1 column is red in the ik_offset and static rows, and the 2024 column is green there.',
        'cost_of_waiting': 'The six stay unrecovered. Work on the 16, the AB17 checks and the one-participant comparison can continue; only recovery of the six waits.',
        'decide_before_recommendation': True,
        'status': 'open',
    }

    # Figures.
    SHEET.mkdir(parents=True, exist_ok=True)
    cells, labels = [], []
    for row in rows:
        s = row['subject']
        labels.append(s)
        held = ('2024 copy', GREEN) if s in local else (('v1 zip', AMBER) if s == 'AB17' else ('no', RED))
        inputs = ('yes', GREEN) if row['converter_inputs_present'] else ('no', RED)
        cells.append([('yes', GREEN), held, inputs, ('?', GREY)])
    grid(SHEET / 'fig1_participants.png',
         labels, ['v1\narchive', 'Held\nhere', 'Static +\nik_offset', '2024\nmirror'], cells,
         'Green yes · red no · amber partial · grey ? not checked')
    folder_rows = list(TRIAL_CHANNELS) + ['static/ik', 'static/markers', 'static/ik_offset', 'osimxml']
    fcells, flabels = [], []
    for name in folder_rows:
        flabels.append(f'{name} *' if name in CONVERTER_READS else name)
        row_cells = []
        for counts in (v1_counts, ref_counts):
            n = counts.get(name, 0)
            row_cells.append((str(n) if n else 'none', GREEN if n else RED))
        fcells.append(row_cells)
    grid(SHEET / 'fig2_folders.png',
         flabels, ['v1 archive\n(AB17)', '2024 copy\n(AB14, here)'], fcells,
         '* read by our converter · counts from listings', left=0.36)

    sheet_details = [
        'D-GT21-S01-1 (task GT21-S01). Report: docs/quality/audits/gt21-s01-cohort-crosswalk.json',
        'Builder: contributor_tools/review_gt21_s01_crosswalk.py',
        'Converter reads ik_offset at convert_gtech_2021_phase_to_parquet.m line 849 and prefers static markers for segment lengths (gtech_estimate_segment_lengths.m lines 75-80, falling back to walking-trial markers).',
        'Figure 2 compares two participants: AB17 from its version 1 ZIP directory, AB14 from the local listing. Other version 1 archives are not listed.',
        f'Planned one-participant comparison: {rel(plan_path)} (not run).',
        'Option order: participants releasable with the current converter, ties by download size.',
    ]
    page(SHEET / 'index.html', title='GT21 missing participants source',
         ask='Choose where the six missing Georgia Tech 2021 participants come from.',
         headline='Six participants are missing; their checksummed archives lack folders our converter reads',
         chips=[('pass', '22 publisher archives listed, each with a checksum'),
                ('pass', f'{len(local)} participants here, {local_total:,} recordings, all with static and ik_offset'),
                ('pass', 'AB17 version 1 archive matches its publisher checksum'),
                ('fail', 'version 1 has the static and ik_offset folders the converter reads'),
                ('unchecked', '2024 mirror holds the six missing participants'),
                ('unchecked', 'shared trial files unchanged between version 1 and 2024'),
                ('unchecked', 'origin of the 16 local copies')],
         figures=[('fig1_participants.png', 'Which participants have the folders our converter reads?',
                   'One row per publisher participant.', 'Grid of 22 participants by source availability'),
                  ('fig2_folders.png', 'Which folders does version 1 lack?',
                   'Listings only; two different participants.', 'File counts per folder, version 1 archive versus local 2024 copy')],
         decision={'question': 'Where should the six missing participants come from?',
                   'columns': ['Left out', 'Releasable now', 'Byte check', 'Processing', 'Download'],
                   'rows': [('A · stop at 16', ['6 participants', '16', 'none needed', 'unchanged', 'none']),
                            ('B · version 1', ['static angles and calibration for 6', '16; 6 need a second recipe', 'publisher checksums', 'two recipes', f'{remaining_v1_bytes / 1e9:.1f} GB']),
                            ('C · 2024 copy', ['publisher checksums', 'up to 22, if all six are there', 'our own hashes', 'same as the 16', 'not known']),
                            ('defer', ['6 participants, for now', '16', '—', '—', 'none'])],
                   'footnote': 'Ordered by participants releasable now, then download size.',
                   'recommendation': f"C, medium confidence. {decision['why']}"},
         not_shown=['Data values; folder listings only', 'Weight units'],
         reply='D-GT21-S01-1: A, B, C or defer',
         details=sheet_details)

    report = {
        'task_id': 'GT21-S01',
        'status': 'crosswalk_reconciled_unreviewed_source_decision_open',
        'scientific_approval': False,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'builder': {'path': rel(Path(__file__)), 'sha256': sha(Path(__file__))},
        'resource_class': 'read_only; manifests, receipts and directory listings only; no data arrays opened; no archive downloaded or extracted',
        'publisher': {
            'paper': 'Camargo J, Ramanathan A, Flanagan W, Young A. A comprehensive, open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions. J Biomech 2021:110320. doi:10.1016/j.jbiomech.2021.110320',
            'paper_cohort': '22 able-bodied adults (abstract quoted in the local README)',
            'repository': {ds: {'part': p, 'versions': versions[ds], 'licence_v1': licences[ds]} for ds, p in PARTS.items()},
            'version_note': ('Mendeley lists only versions 1 (2021-02-26) and 2 (2021-10-18) for all three parts on 2026-10-31; '
                             'both predate the README-documented 2024-04-28 static/ik_offset additions. Whether a version 2 '
                             'container includes static trials is not checked (member lists not fetched).'),
            'local_readme_matches_publisher_readme': b[rel(SRC / 'README.txt')] == v1['README.txt']['sha256'],
            'local_readme_note': 'Local README differs from the 4,970-byte README in publisher v1 and v2 and documents the 2024-04-28 additions; exact provenance of the local tree is not recorded.',
            'numbering_gaps': 'AB22, AB26 and AB29 have no publisher archive; no meaning is inferred.',
        },
        'counts': {
            'publisher_v1_subject_archives': len(subjects),
            'publisher_v1_archives_rechecked_20261031': sum(r['publisher_v1_archive']['recheck_20261031'].startswith('file id') for r in rows),
            'local_present': len(local),
            'local_recordings_from_conditions_files': local_total,
            'prior_census_recordings': phases['recordings'],
            'local_recordings_match_prior_census': local_total == phases['recordings'],
            'recovered_not_converted': ['AB17'],
            'unrecovered': [s for s in MISSING if s != 'AB17'],
            'unexpected_local': sorted(set(local) - set(subjects)),
            'missing_matches_prior_audit': sorted(set(subjects) - set(local)) == sorted(coverage['missing_participants']),
        },
        'converter_requirements': {
            'reads': CONVERTER_READS,
            'version1_gap': 'Version 1 (AB17 archive) has no ik_offset and no static folder, so the current converter has no joint-angle input for a version 1 participant and would take segment lengths from walking-trial markers instead of the static pose.',
        },
        'folder_comparison_from_listings': {'v1_AB17_zip_directory': dict(sorted(v1_counts.items())),
                                            'local_2024_AB14': dict(sorted(ref_counts.items())),
                                            'note': 'Different participants; presence and counts only. Byte equality of shared folders is not checked.'},
        'metadata_provenance': {
            'source': rel(SRC / 'SubjectInfo.mat'),
            'publisher_record': f"v1 and v2 manifest SHA-256 {v1['SubjectInfo.mat']['sha256']}",
            'local_matches_publisher': b[rel(SRC / 'SubjectInfo.mat')] == v1['SubjectInfo.mat']['sha256'] == v2['SubjectInfo.mat']['sha256'],
            'rows_exported': len(weight),
            'native_exact_readback': mass_cmp['native_exact_mass_readback'],
            'units': enrich['remaining'],
            'processing_evidence': recipe['mass_recipe']['remaining'],
        },
        'participants': rows,
        'source_decision_draft': decision,
        'next_action': {
            'kind': 'plan_only_source_equivalence',
            'plan_path': rel(plan_path),
            'plan_sha256': sha(plan_path),
            'plan': equivalence_plan,
            'withdrawn': 'The earlier proposal to recover AB15 next is withdrawn: another version 1 archive meets the same ik_offset/static gap, and the source choice is open.',
        },
        'review_sheet': {'path': rel(SHEET / 'index.html'), 'figures': ['fig1_participants.png', 'fig2_folders.png']},
        'not_checked': [
            'Byte identity of the 16 local participant trees to any publisher archive.',
            'Member lists of the version 2 combined archives and of the five unrecovered archives.',
            'Author mirror folders for all six missing participants, including static/ik_offset content.',
            'SubjectInfo columns other than Subject and Weight, and Weight units.',
            'AB17 archive SHA-256 was not recomputed in this task (size only).',
        ],
        'limitations': [
            'Source inventory only. No conversion, readback or scientific approval for any participant.',
            'The 2,301-recording local subtotal is not full-cohort coverage.',
        ],
        'embedded_receipts_20261031': embedded,
        'bindings': dict(sorted(b.items())),
    }
    OUT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts'], indent=2))


if __name__ == '__main__':
    main()
