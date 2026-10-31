"""HIST-01: exact source disposition for the twelve retained historical study pages.

Read-only and metadata-only. Reads small JSON/YAML/HTML evidence, the official
AddBiomechanics 1.0 central-directory member ledger (metadata, not B3D bytes) and
byte-hashes only the three small UM24K publisher files. Opens no Parquet, HDF5,
MAT or CSV arrays and downloads nothing. Publisher/DOI facts below were looked up
on 2026-10-31 through the Crossref and DataCite APIs and the existing web receipts
named in each record; anything not looked up is marked not_checked.

Writes docs/quality/audits/hist01-source-dispositions.json, the verification sheet
review_sheets/HIST-01/ and the decision sheet review_sheets/D-HIST-01-1/.
Decision options are ordered by a neutral attribute: total data to download
(none, about 108 GB, about 347 GB). Original-route sizes come from repository
metadata fetched 2026-10-31 (ORIGINAL_ROUTE below); no data files were downloaded.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.common.review_sheet import page

OUT = ROOT / 'docs/quality/audits/hist01-source-dispositions.json'
SHEETS = ROOT / 'review_sheets'
V2 = ROOT / 'converted_datasets/reconversion_v2/swarm_backlog_20261021'
LEDGER = V2 / 'adb_official_release_metadata_20261021/historical_study_member_ledger.json'
ADB_PAGE = V2 / 'adb_official_release_metadata_20261021/official_download.txt'
ADB_ZIP = V2 / 'adb_official_release_metadata_20261021/zip_metadata.json'
LOCAL_SEARCH = V2 / 'adb_local_source_search_20261021.json'
HIST_SCOPE = V2 / 'historical_scope.json'
ADB_DIR = ROOT / 'contributor_tools/conversion_scripts/AddBiomechanics'
UM24K_DIR = ROOT / 'contributor_tools/conversion_scripts/UMich_2024_KneeExo'
UM24K_PUBLISHER = ROOT / 'docs/quality/audits/source_evidence/um24k/publisher-files.json'
AUDITS = ['docs/quality/audits/historical-source-restoration-review.json',
          'docs/quality/audits/tan-falisse-source-identity-review.json',
          'docs/quality/audits/addbiomechanics-source-preservation-review.json',
          'docs/quality/audits/um24k-ensemble-restoration-review.json',
          'docs/quality/audits/um24k-fatigue-restoration-review.json',
          'docs/quality/audits/pm02-job-dispositions.json',
          'docs/quality/audits/queue-recovery-expanded-49-summary.json']
SLUGS = ['ca23', 'fa16', 'fr12', 'ha13', 'ha23', 'mo15', 'ta21', 'ta22', 'ti19', 'um24k', 'vz22', 'wa23']
ADB_SLUGS = [s for s in SLUGS if s != 'um24k']
ADB_YAML = {'ca23': 'carter2023', 'fa16': 'falisse2016', 'fr12': 'fregly2012', 'ha13': 'hamner2013', 'ha23': 'han2023',
            'mo15': 'moore2015', 'ta21': 'tan2021', 'ta22': 'tan2022', 'ti19': 'tiziana2019', 'vz22': 'vanderzee2022',
            'wa23': 'wang2023'}
# Openly licensed original publisher data, sizes from repository metadata fetched 2026-10-31 (metadata only;
# sha256 is of the fetched metadata response). Studies absent here have no openly licensed original confirmed.
ORIGINAL_ROUTE = {
    'ca23': {'bytes': 28882233915, 'files': '50 participant ZIPs plus 3 documentation files', 'size_basis': 'DataCite sizes strings (rounded MB), summed',
             'license': 'CC-BY-4.0 (DataCite)', 'metadata_url': 'https://api.datacite.org/dois/10.15125/BATH-01341',
             'metadata_sha256': 'a584ed060efed3ac1898df4ec57071bcbab948b591d71cc96e8e7a40b2ad9f49'},
    'mo15': {'bytes': 2444992214, 'files': '2 tar.gz raw archives', 'size_basis': 'Zenodo API file sizes, exact',
             'license': 'CC0-1.0 (Zenodo API cc-zero; DataCite CC0 1.0)', 'metadata_url': 'https://zenodo.org/api/records/13030',
             'metadata_sha256': '139dd9b919805d836377c11a76a202fcf96fb2579ed8bb0fa815b8e24b896d94'},
    'ti19': {'bytes': 515231189, 'files': '54 figshare items (50 subject MAT files plus code)', 'size_basis': 'figshare article API file sizes, exact',
             'license': 'items CC0 (figshare API) while DataCite lists the collection CC-BY-4.0; not reconciled',
             'metadata_url': 'https://api.figshare.com/v2/collections/4494755/articles',
             'metadata_sha256': '6b7b704f266ceb35f564785a8ef293239e5c6305e35e61bba2114d4761e74395'},
    'vz22': {'bytes': 15593203562, 'files': '4 figshare items (C3D, CMO and MATLAB levels plus trial table)', 'size_basis': 'figshare article API file sizes, exact',
             'license': 'items CC0 (figshare API) while DataCite lists the collection CC-BY-4.0; not reconciled',
             'metadata_url': 'https://api.figshare.com/v2/collections/5897423/articles',
             'metadata_sha256': '2b5ce467e2382ecbd1887878e9def6a0cdad21daa7812662b9dea7cc0d55cdf3'},
    'wa23': {'bytes': 31012438583, 'files': 'Processed_data.rar and Raw_data.rar', 'size_basis': 'Zenodo API file sizes, exact',
             'license': 'CC BY 3.0 Netherlands (DataCite); Zenodo API shows no license id', 'metadata_url': 'https://zenodo.org/api/records/6457662',
             'metadata_sha256': '6bb5defa6267c70b55e5ab499269eaba21d176790b181d727a7f1d217263b0ed'},
}
FIGSHARE_ARTICLES_SHA256 = 'ad99a5ef257548542485bd29ed7883de837cd72fd61aea57372ff59f48bed096'  # concatenated 58 article responses
ADB_TASKS = ['ADB-P01', 'ADB-C01', 'ADB-F01', 'HIST-02', 'HIST-Q01', 'HIST-R01']
UM24K_TASKS = ['UM24K-F01', 'UM24K-Q01', 'UM24K-R01', 'HIST-02']
LOOKUP = 'Crossref/DataCite API lookup 2026-10-31'

# Curated per-study source facts. Every value is from a named lookup or an existing audit; no inference.
STUDIES = {
    'ca23': dict(
        original_study={'citation': 'Full Body Kinematics and Ground Reaction Forces of Fifty Heterogeneous Runners Completing Treadmill running (University of Bath research data, 2024); original-paper DOI not identified',
                        'doi': None, 'status': 'not_checked'},
        original_data={'repository': 'University of Bath Research Data Archive', 'doi': '10.15125/BATH-01341',
                       'version': '1', 'license': 'CC-BY-4.0', 'participants_stated': 50, 'verified_via': LOOKUP + ' (DataCite)'},
        adb_table={'label': 'Carter et al. 2023', 'subjects': 50, 'link': 'https://doi.org/10.15125/BATH-01341'},
        discrepancies=['Legacy metadata and the AddBiomechanics metadata YAML say University of Colorado and 6 subjects; the publisher record is University of Bath with 50 runners. The page already shows University of Bath; the metadata YAML does not.',
                       'Publisher says running on one force plate; plate number is not anatomical side (prior review).'],
        unknowns=['Which 6 of the 50 runners and which trials the legacy file contained.', 'Original-paper citation, if any, for the Bath dataset.'],
        blockers=['Plate-to-leg assignment must come from source evidence before any force mapping.'],
        size_note='Largest study: two model variants of 50 runners.'),
    'fa16': dict(
        original_study={'citation': 'Falisse A, Van Rossom S, Jonkers I, De Groote F. EMG-Driven Optimal Estimation of Subject-Specific Hill Model Muscle-Tendon Parameters of the Knee Joint Actuators. IEEE Trans Biomed Eng 64(9):2253-2262, 2017',
                        'doi': '10.1109/TBME.2016.2630009', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref); official AddBiomechanics table links PubMed 27875132'},
        original_data=None,
        adb_table={'label': 'Falisse et al. 2016', 'subjects': 11, 'link': 'https://pubmed.ncbi.nlm.nih.gov/27875132/'},
        discrepancies=['Legacy metadata cites DOI 10.1007/s10439-016-1591-9, which resolves to De Groote et al. 2016 (direct collocation for muscle redundancy), a different paper. The page now cites the 2017 TBME paper; the metadata YAMLs do not.',
                       'Archive folder is Falisse2017; legacy label is Falisse2016.',
                       'Legacy converter mapped unknown trial names, including STS_1/STS_2/STS_5, to level walking; corrected converter returns no canonical task (not reconverted).'],
        unknowns=['Per-record task of Gait_* and STS_* trials (needs B3D header and original study evidence).', 'Which of the 11 subjects the 1-subject legacy file held.', 'Original (non-derivative) data location and license.'],
        blockers=['No canonical task may be assigned to Gait_* or STS_* records from names alone.']),
    'fr12': dict(
        original_study={'citation': 'Fregly BJ, Besier TF, Lloyd DG, Delp SL, Banks SA, Pandy MG, D\'Lima DD. Grand challenge competition to predict in vivo knee loads. J Orthop Res 30(4):503-513, 2012',
                        'doi': '10.1002/jor.22023', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'SimTK project kneeloads', 'url': 'https://simtk.org/projects/kneeloads', 'version': None,
                       'license': None, 'status': 'not_checked'},
        adb_table={'label': 'Fregly et al. 2012', 'subjects': 6, 'link': 'https://pubmed.ncbi.nlm.nih.gov/22161745/'},
        discrepancies=['Archive has 6 competition subjects without arms but only 4 (1GC, 2GC, 3GC, 5GC) with arms.', 'Legacy file claims 1 subject.'],
        unknowns=['Which competition subject the legacy file held; implanted side; package license.'],
        blockers=['Measured implant contact force and net inverse-dynamics moment must stay separate.']),
    'ha13': dict(
        original_study={'citation': 'Hamner SR, Delp SL. Muscle contributions to fore-aft and vertical body mass center accelerations over a range of running speeds. J Biomech 46(4):780-787, 2013',
                        'doi': '10.1016/j.jbiomech.2012.11.024', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref); official AddBiomechanics table links PubMed 23246045'},
        original_data={'repository': 'SimTK project nmbl_running', 'url': 'https://simtk.org/projects/nmbl_running', 'version': None,
                       'license': None, 'status': 'not_checked'},
        adb_table={'label': 'Hamner et al. 2013', 'subjects': 10, 'link': 'https://pubmed.ncbi.nlm.nih.gov/23246045/'},
        discrepancies=['Legacy metadata cites DOI 10.1016/j.jbiomech.2012.08.014, which resolves to an unrelated prosthesis-alignment paper (Kobayashi et al. 2012), with the 2010 Hamner title. The page is corrected; both metadata YAMLs are not.',
                       'With-arm archive folder is spelled Hammer2013.'],
        unknowns=['Which of the 10 subjects the 1-subject legacy file held; per-trial speed.'],
        blockers=[]),
    'ha23': dict(
        original_study={'citation': 'Han X, Senderling B, To S, et al. GroundLink: A Dataset Unifying Human Body Movement and Ground Reaction Dynamics. SIGGRAPH Asia 2023 Conference Papers',
                        'doi': '10.1145/3610548.3618247', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref); official table links arXiv 2310.03930'},
        original_data={'repository': 'GroundLink project pages', 'url': 'https://csr.bu.edu/groundlink/', 'version': None,
                       'license': None, 'status': 'not_checked', 'note': 'Prior bounded read found no explicit data license.'},
        adb_table={'label': 'Han et al. 2023', 'subjects': 7, 'link': 'https://arxiv.org/abs/2310.03930'},
        discrepancies=['Page and metadata name KAIST; no checked source supports that institution.',
                       'AddBiomechanics metadata YAML says 22 subjects; archive and official table say 7; legacy file claims 6.',
                       'Archive has 6 empty (zero-byte) members across the two model variants.'],
        unknowns=['Which subject was left out of the legacy file; native data license.'],
        blockers=['Body-model fits and measured force channels must stay distinct.']),
    'mo15': dict(
        original_study={'citation': 'Moore JK, Hnat SK, van den Bogert AJ. An elaborate data set on human gait and the effect of mechanical perturbations. PeerJ 3:e918, 2015',
                        'doi': '10.7717/peerj.918', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'Zenodo record 13030', 'doi': '10.5281/zenodo.13030', 'version': None, 'license': 'CC0-1.0',
                       'verified_via': LOOKUP + ' (DataCite)', 'note': 'Raw original archives; not the processed AddBiomechanics release.'},
        adb_table={'label': 'Moore et al. 2015', 'subjects': 12, 'link': 'https://pubmed.ncbi.nlm.nih.gov/25945311/'},
        discrepancies=['Legacy file claims 11 subjects; archive has 12; the original paper reports 15 participants including pilots (prior ledger).'],
        unknowns=['Which archive subject the legacy file omitted; perturbation intervals and sync per trial.'],
        blockers=['Raw original and AddBiomechanics recordings must not be double-counted.']),
    'ta21': dict(
        original_study={'citation': 'Tan T, Strout ZA, Cheung RTH, Shull PB. Strike index estimation using a convolutional neural network with a single, shoe-mounted inertial sensor. J Biomech 139:111145, 2022',
                        'doi': '10.1016/j.jbiomech.2022.111145', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref); official table row "Tan et al. 2022" links PubMed 35594817'},
        original_data={'repository': 'Author Google Drive folder linked from author page', 'url': 'https://drive.google.com/drive/folders/1ZDy_JIj3j0wsXdHaC1Bpw1vTE-LGwoJ6',
                       'version': None, 'license': None, 'status': 'not_checked', 'note': 'Lists 7 subject folders s1, s4-s9 (prior review).'},
        adb_table={'label': 'Tan et al. 2022', 'subjects': 9, 'link': 'https://pubmed.ncbi.nlm.nih.gov/35594817/'},
        discrepancies=['Folder Tan2021 has 8 subject folders (s1, s3-s9), the official table lists 9 subjects, the author Drive lists 7, and the legacy file claims 7.',
                       'The official page does not state which archive folder belongs to which table row; Tan2021-to-strike-index rests on count and trial-name resemblance only.',
                       'Page and metadata name National University of Singapore and year 2021; no checked source supports either.'],
        unknowns=['Exact folder-to-paper and trial membership (needs B3D header trial names).', 'Which 7 subjects the legacy file held.'],
        blockers=['Do not infer the year crosswalk from folder names.']),
    'ta22': dict(
        original_study={'citation': 'Tan T, Wang D, Shull PB, et al. IMU and Smartphone Camera Fusion for Knee Adduction and Knee Flexion Moment Estimation During Walking. IEEE Trans Ind Inform 19(2):1445-1455, 2023',
                        'doi': '10.1109/TII.2022.3189648', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref); official table row "Tan et al. 2023" links IEEE 9826418'},
        original_data={'repository': 'SimTK project imukinetics', 'url': 'https://simtk.org/projects/imukinetics', 'version': None,
                       'license': None, 'status': 'not_checked', 'note': 'Author README links 17 subjects and says AddBiomechanics processed them (prior review).'},
        adb_table={'label': 'Tan et al. 2023', 'subjects': 17, 'link': 'https://ieeexplore.ieee.org/document/9826418/'},
        discrepancies=['Legacy file claims 16 subjects and 0 historical strides; folder Tan2022 and the official table both have 17.',
                       'Page and metadata name National University of Singapore and year 2022; no checked source supports either.'],
        unknowns=['Which subject the legacy file omitted; joint-moment normalization.'],
        blockers=['Author model inputs are padded stance windows, not bilateral full cycles.']),
    'ti19': dict(
        original_study={'citation': 'Lencioni T, Carpinella I, Rabuffetti M, et al. Human kinematic, kinetic and EMG data during different walking and stair ascending and descending tasks. Sci Data 6:309, 2019',
                        'doi': '10.1038/s41597-019-0323-z', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'figshare collection 4494755', 'doi': '10.6084/m9.figshare.c.4494755.v1', 'version': 'v1',
                       'license': 'CC-BY-4.0 (collection, DataCite); all 54 items CC0 (figshare API 2026-10-31): not reconciled',
                       'verified_via': LOOKUP + ' (DataCite)'},
        adb_table={'label': 'Lencioni et al. 2019', 'subjects': 50, 'link': 'https://www.nature.com/articles/s41597-019-0323-z'},
        discrepancies=['Legacy file claims 43 subjects; the AddBiomechanics YAML says 49; archive and official table say 50.',
                       'Archive has 5 empty members across the two model variants.',
                       'Legacy file holds level walking only; source also has toe/heel walking and stairs.'],
        unknowns=['Which 7 subjects and which tasks were left out of the legacy file.', 'Per-item versus collection license.'],
        blockers=[]),
    'um24k': dict(
        original_study={'citation': 'Divekar NV, Thomas GC, Yerva AR, Frame HB, Gregg RD. A versatile knee exoskeleton mitigates quadriceps fatigue in lifting, lowering, and carrying tasks. Sci Robot 9:eadr8282, 2024',
                        'doi': '10.1126/scirobotics.adr8282', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'Dryad', 'doi': '10.5061/dryad.z34tmpgks', 'version': '6 (Dryad version id 314890, published 2024-09-04)',
                       'license': 'CC0-1.0', 'verified_via': LOOKUP + ' (DataCite); publisher file digests in source_evidence/um24k'},
        adb_table=None,
        discrepancies=['Publisher README introduction swaps the S1/S2 descriptions relative to its detailed field list and the MAT contents (prior review).',
                       'Legacy converter has changed since the commit that added the legacy file.'],
        unknowns=['Anatomical side of knee and segment angles; foot-sensor direction; participant masses (not released).'],
        blockers=[]),
    'vz22': dict(
        original_study={'citation': 'van der Zee TJ, Mundinger EM, Kuo AD. A biomechanics dataset of healthy human walking at various speeds, step lengths and step widths. Sci Data 9:704, 2022',
                        'doi': '10.1038/s41597-022-01817-1', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'figshare collection 5897423', 'doi': '10.6084/m9.figshare.c.5897423.v1', 'version': 'v1',
                       'license': 'CC-BY-4.0 (collection, DataCite); all 4 items CC0 (figshare API 2026-10-31): not reconciled', 'verified_via': LOOKUP + ' (DataCite)', 'note': 'A five-stride subset is separately published (article 16530939 v4, CC BY 4.0, prior review).'},
        adb_table={'label': 'Van der Zee et al. 2022', 'subjects': 10, 'link': 'https://www.nature.com/articles/s41597-022-01817-1'},
        discrepancies=['Legacy file claims 9 subjects; archive and paper have 10.', 'Page names VU Amsterdam; not checked against the paper.'],
        unknowns=['Which subject the legacy file omitted; trial-condition mapping (33 speed/step conditions).'],
        blockers=[]),
    'wa23': dict(
        original_study={'citation': 'Wang H, Basu A, Durandau G, Sartori M. A wearable real-time kinetic measurement sensor setup for human locomotion. Wearable Technol 4:e11, 2023',
                        'doi': '10.1017/wtc.2023.7', 'status': 'checked', 'verified_via': LOOKUP + ' (Crossref)'},
        original_data={'repository': 'Zenodo record 6457662', 'doi': '10.5281/zenodo.6457662', 'version': '1.0',
                       'license': 'CC BY 3.0 Netherlands (DataCite rights)', 'verified_via': LOOKUP + ' (DataCite)'},
        adb_table={'label': 'Wang et al. 2023', 'subjects': 9, 'link': 'https://doi.org/10.1017/wtc.2023.7'},
        discrepancies=['Page and metadata name Stanford University; the checked paper and data record do not support that.',
                       'Legacy file claims 8 subjects; archive, paper and table have 9.'],
        unknowns=['Which subject the legacy file omitted; laboratory versus wearable channel lineage.'],
        blockers=['Laboratory force plate, wearable force estimate and model outputs must stay distinct.']),
}

PAGE_REQUESTS = [
    ('ca23', 'docs/datasets/_metadata/ca23.yaml', 'Institution University of Colorado and 6 subjects contradict the Bath publisher record (50 runners); the rendered page already says University of Bath.'),
    ('fa16', 'docs/datasets/_metadata/fa16.yaml', 'Citation DOI 10.1007/s10439-016-1591-9 is De Groote et al. 2016; replace with 10.1109/TBME.2016.2630009 as the page already does.'),
    ('ha13', 'docs/datasets/_metadata/ha13.yaml', 'Citation DOI 10.1016/j.jbiomech.2012.08.014 is an unrelated paper; replace with 10.1016/j.jbiomech.2012.11.024 as the page already does.'),
    ('ha23', 'docs/datasets/ha23/index.html', 'Institution KAIST is unsupported; cite Han et al. SIGGRAPH Asia 2023, DOI 10.1145/3610548.3618247; no citation DOI is shown.'),
    ('ta21', 'docs/datasets/ta21/index.html', 'Year 2021 and National University of Singapore are unsupported; supported study is Tan et al. J Biomech 2022, DOI 10.1016/j.jbiomech.2022.111145, membership still unproven.'),
    ('ta22', 'docs/datasets/ta22/index.html', 'National University of Singapore is unsupported; cite Tan et al. IEEE TII 2023, DOI 10.1109/TII.2022.3189648.'),
    ('wa23', 'docs/datasets/wa23/index.html', 'Institution Stanford University is unsupported; cite Wang et al. Wearable Technol 2023, DOI 10.1017/wtc.2023.7, data Zenodo 6457662 v1.0.'),
    ('ti19', 'docs/datasets/ti19/index.html', 'Description says 50 subjects while the legacy record counts 43; state that the legacy file covers 43 of 50.'),
    ('vz22', 'docs/datasets/vz22/index.html', 'Institution VU Amsterdam not checked; verify against the paper or remove.'),
    ('all ADB', 'contributor_tools/conversion_scripts/AddBiomechanics/dataset_metadata/*.yaml', 'Same citation/institution/subject errors as above (fa16, ha13, ha23 22 subjects, ti19 49 subjects, ca23); not a docs page but feeds them.'),
]


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def ledger_rows():
    data = json.loads(LEDGER.read_text())
    rows = {}
    for study in data['historical_studies']:
        variants = []
        for v in study['source_variants']:
            subjects = sorted({p.split('/')[3].split('_split')[0] for p in v['member_paths']})
            variants.append({'archive_folder': v['source_folder'], 'members': v['member_count'],
                             'empty_members': v['empty_member_count'], 'subject_folders': len(subjects),
                             'subject_folder_names': subjects, 'compressed_bytes': v['compressed_bytes'],
                             'expanded_bytes': v['expanded_bytes']})
        rows[study['historical_code']] = variants
    return data, rows


def legacy_claims(slug):
    meta = yaml.safe_load((ROOT / f'docs/datasets/_metadata/{slug}.yaml').read_text())
    return {'subjects': int(meta['subjects']), 'tasks': meta.get('tasks'), 'institution': meta.get('institution'),
            'year': meta.get('year'), 'historical_curve_count': meta.get('total_strides'),
            'historical_pass_rate': meta.get('validation_pass_rate'),
            'historical_pass_rate_is_source_evidence': False,
            'remote_legacy_links': {k: v.split('?')[0] for k, v in meta.items() if k.startswith('download_') and k.endswith('_url')},
            'remote_links_fetched_or_hashed': False}


def build():
    ledger, adb = ledger_rows()
    zipmeta = json.loads(ADB_ZIP.read_text())
    search = json.loads(LOCAL_SEARCH.read_text())
    publisher = {f['path']: f for f in json.loads(UM24K_PUBLISHER.read_text())['_embedded']['stash:files']}
    um24k_local = []
    for name in ['dataset_S1.mat', 'dataset_S2.mat', 'dataset.zip']:
        p = UM24K_DIR / name
        row = {'path': rel(p), 'bytes': p.stat().st_size, 'sha256': digest(p)}
        if name in publisher:
            row['publisher_sha256'] = publisher[name]['digest']
            row['publisher_bytes'] = publisher[name]['size']
            row['matches_publisher_version_6'] = row['sha256'] == publisher[name]['digest'] and row['bytes'] == publisher[name]['size']
        else:
            row['note'] = 'Local container of S1, S2 and README; its README member matches publisher README digest (checked in prior review and rechecked by unzip -p).'
        um24k_local.append(row)
    records = []
    for slug in SLUGS:
        s = STUDIES[slug]
        claims = legacy_claims(slug)
        rec = {'slug': slug, 'page': {'path': f'docs/datasets/{slug}/index.html', 'sha256': digest(ROOT / f'docs/datasets/{slug}/index.html')},
               'metadata': {'path': f'docs/datasets/_metadata/{slug}.yaml', 'sha256': digest(ROOT / f'docs/datasets/_metadata/{slug}.yaml')},
               'legacy_metadata_claims': claims, 'original_study': s['original_study'], 'original_data': s['original_data']}
        if slug == 'um24k':
            rec['source_route'] = 'publisher original (Dryad), not AddBiomechanics'
            rec['local_source'] = {'status': 'present_matches_publisher', 'files': um24k_local}
            rec['addbiomechanics_source'] = None
            rec['legacy_artifact'] = {
                'expected_file': 'umich_2024_knee_exo_phase.parquet', 'local_copy': 'absent from converted_datasets/',
                'converter_candidate': {'path': 'contributor_tools/conversion_scripts/UMich_2024_KneeExo/convert_umich_2024_phase_to_parquet.py',
                                        'commit_that_added_dataset': '965a171 (2025-12-20)',
                                        'sha256_at_that_commit': hashlib.sha256(subprocess.run(['git', 'show', '965a171:contributor_tools/conversion_scripts/UMich_2024_KneeExo/convert_umich_2024_phase_to_parquet.py'], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest(),
                                        'sha256_now': digest(ROOT / 'contributor_tools/conversion_scripts/UMich_2024_KneeExo/convert_umich_2024_phase_to_parquet.py'),
                                        'reads': 'dataset_S1.mat exo structure only (torque, thigh/shank/knee angle, foot sensor); no EMG, no S2',
                                        'binding': 'not_bound: no output receipt ties the legacy file to this code or to the local MAT bytes'},
                'count_consistency': '60 historical curves = 6 tasks x 10 participant columns of the exo structure; counts only, not byte-verified'}
            rec['disposition'] = {'source': 'source_available_reconcilable', 'legacy_artifact': 'archive_legacy_unbound',
                                  'summary': 'Local S1/S2 MAT files are byte-identical to Dryad version 6. Rebuild is already in UM24K-F01 scope (120 participant-condition ensembles and 2,260 S2 values); stopped watchers need fresh reviewed plans. Legacy Dropbox file stays legacy.'}
            rec['linked_tasks'] = UM24K_TASKS
            rec['next_bounded_action'] = 'UM24K-F01: write a fresh reviewed S1 plan bound to the local S1 SHA-256 and run one guarded S1 conversion plus independent MAT readback; S2 after S1.'
        else:
            variants = adb[slug]
            rec['source_route'] = 'AddBiomechanics derivative (B3D); original publisher data noted where it exists'
            rec['local_source'] = {'status': 'not_found_in_bounded_search', 'files': [],
                                   'search_evidence': [rel(LOCAL_SEARCH), 'HIST-01 find over /mnt/s/locomotion_data, /mnt/s/scratch_data, /mnt/s/Downloads, /home/jmontp (depth 4) and /mnt/s/workspace (depth 5): 0 .b3d or study-named files'],
                                   'historical_expected_root': search['findings']['historical_source_root'],
                                   'not_a_global_absence_claim': True}
            rec['addbiomechanics_source'] = {
                'release': 'AddBiomechanics 1.0 core archive', 'archive_url': zipmeta['url'], 'etag': zipmeta['etag'],
                'last_modified': zipmeta['last_modified'], 'central_directory_sha256': ledger['central_directory_sha256'],
                'license': 'CC-BY-4.0 stated on official download page; archive has no LICENSE/DATA_CITATIONS member',
                'acquired': False, 'variants': variants,
                'compressed_bytes_total': sum(v['compressed_bytes'] for v in variants),
                'official_table': s['adb_table'],
                'historical_export_equivalence': 'unproven: no historical local B3D hash or manifest survives'}
            rec['legacy_artifact'] = {
                'expected_file': next(iter(claims['remote_legacy_links'].values()), '').rsplit('/', 1)[-1],
                'local_copy': 'absent from converted_datasets/',
                'converter_candidate': {'paths': ['contributor_tools/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py (consolidated, commit cc94be4 2026-01-06)',
                                                  'contributor_tools/conversion_scripts/AddBiomechanics/_archive/ (earlier scripts)'],
                                        'binding': 'not_bound: metadata date_added 2025-12-21 precedes the consolidated commit; no output receipt names code version or input B3D files',
                                        'known_defects': 'Listed in addbiomechanics-source-preservation-review.json concrete_old_defects (70 kg mass fallback, fixed pass slot, root-frame forces as anatomical, invented opposite-leg phase).'},
                'historical_identity_recoverable': False}
            rec['disposition'] = {'source': 'needs_scope_decision', 'legacy_artifact': 'archive_legacy_unbound',
                                  'summary': 'No source found in the searched folders; official derivative members identified by metadata only'
                                             + ('; openly licensed original publisher data also exists' if slug in ORIGINAL_ROUTE else '')
                                             + '; legacy file cannot be traced to any source bytes. Archive-or-rebuild and source route await D-HIST-01-1.',
                                  'decision': 'D-HIST-01-1',
                                  'option_B_route': 'original publisher data' if slug in ORIGINAL_ROUTE else 'AddBiomechanics derivative'}
            rec['original_route'] = ORIGINAL_ROUTE.get(slug) or {'status': 'no openly licensed original confirmed', 'bytes': None}
            rec['linked_tasks'] = ADB_TASKS
            rec['next_bounded_action'] = ('After D-HIST-01-1: if rebuilt, acquire one smallest member through the reviewed member-acquisition tool, '
                                          'read its B3D header trial names and bind them to the legacy page counts before any conversion; otherwise keep the page archived with corrected citation.')
        rec['discrepancies'] = s['discrepancies']
        rec['unknowns'] = s['unknowns']
        rec['blockers'] = s['blockers']
        records.append(rec)
    adb_total = sum(r['addbiomechanics_source']['compressed_bytes_total'] for r in records if r['addbiomechanics_source'])
    mixed_total = sum(ORIGINAL_ROUTE[r['slug']]['bytes'] if r['slug'] in ORIGINAL_ROUTE else r['addbiomechanics_source']['compressed_bytes_total']
                      for r in records if r['addbiomechanics_source'])
    original_total = sum(v['bytes'] for v in ORIGINAL_ROUTE.values())
    free = shutil.disk_usage(ROOT).free
    result = {
        'task_id': 'HIST-01', 'checked_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'status': 'source_dispositions_recorded_not_scientific_approval', 'scientific_approval': False,
        'repository_head': git('rev-parse', '--short', 'HEAD'), 'builder': {'path': rel(Path(__file__)), 'sha256': digest(Path(__file__))},
        'method': 'Metadata only: small JSON/YAML/HTML, official archive central-directory ledger, byte hashes of three small UM24K files, Crossref/DataCite DOI lookups. No scientific arrays opened; nothing downloaded or launched.',
        'scope_reconciliation': {
            'retained_pages': 20, 'active_pages': 8, 'historical_pages': 12,
            'historical_from_addbiomechanics': ADB_SLUGS, 'historical_from_publisher': ['um24k'],
            'addbiomechanics_ledger_studies': [s['historical_code'] for s in ledger['historical_studies']],
            'note': 'The ledger\'s twelve AddBiomechanics studies are not the twelve historical pages: they include sa17 (Santos 2017, converter config only, no LocoHub page) and exclude um24k. sa17 is outside HIST-01 scope and is left unchanged.'},
        'totals': {'adb_compressed_bytes_eleven_studies': adb_total, 'option_B_mixed_route_bytes': mixed_total, 'original_route_bytes_five_studies': original_total,
                   'option_B_route_note': 'Original publisher data for ca23, mo15, ti19, vz22, wa23; AddBiomechanics derivative for fa16, fr12, ha13, ha23, ta21, ta22.',
                   'data_drive_free_bytes_at_check': free, 'data_drive_free_note': 'Decimal GB; the same value is about 153 GiB (df -h shows 154G).',
                   'largest_study': 'ca23', 'ca23_compressed_bytes': next(r for r in records if r['slug'] == 'ca23')['addbiomechanics_source']['compressed_bytes_total']},
        'acceptance_notes': {
            'pass_rates': 'Every historical pass rate is recorded with historical_pass_rate_is_source_evidence=false; none is used as verification.',
            'addbiomechanics_scope': 'Eleven pages derive from AddBiomechanics and no active queue covers them; five also have openly licensed original publisher data. Rebuild scope and source route are D-HIST-01-1.',
            'tan': 'Folder-to-paper mapping recorded as unproven; only counts and author README support it. Trial membership needs B3D header names.',
            'falisse': 'Gait_* and STS_* remain without canonical task; corrected converter withholds tasks; per-record evidence still needed.'},
        'records': records,
        'page_correction_requests': [{'slug': a, 'path': b, 'request': c} for a, b, c in PAGE_REQUESTS],
        'inputs': [{'path': p, 'sha256': digest(ROOT / p)} for p in AUDITS] +
                  [{'path': rel(p), 'sha256': digest(p)} for p in [LEDGER, ADB_PAGE, ADB_ZIP, LOCAL_SEARCH, HIST_SCOPE, UM24K_PUBLISHER]] +
                  [{'path': rel(ADB_DIR / f'dataset_metadata/{ADB_YAML[s]}.yaml'), 'sha256': digest(ADB_DIR / f'dataset_metadata/{ADB_YAML[s]}.yaml')} for s in ADB_SLUGS] +
                  [{'path': rel(ADB_DIR / n), 'sha256': digest(ADB_DIR / n)} for n in ['convert_addbiomechanics_to_parquet.py', 'dataset_configs.py']],
        'not_checked': ['Remote legacy Dropbox files (not fetched, not hashed).', 'B3D bytes or headers of any study.',
                        'Original-data licenses for fr12, ha13, ha23, ta21, ta22, fa16 packages.', 'Institutions shown on pages beyond the corrections listed.'],
    }
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    return result


def figures(result, folder_v, folder_d):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    recs = {r['slug']: r for r in result['records']}
    # Verification figure: legacy participant claim versus source participant count.
    order = sorted(SLUGS, key=lambda s: s)
    src = []
    for s in order:
        a = recs[s]['addbiomechanics_source']
        src.append(max(v['subject_folders'] for v in a['variants']) if a else 10)
    leg = [recs[s]['legacy_metadata_claims']['subjects'] for s in order]
    fig, ax = plt.subplots(figsize=(4.5, 4.2))
    y = range(len(order))
    ax.hlines(y, leg, src, color='#c9ced4', lw=2)
    ax.scatter(src, y, s=36, color='#2a78d6', label='source participants', zorder=3)
    ax.scatter(leg, y, s=36, color='#eb6834', marker='s', label='old LocoHub record', zorder=3)
    ax.set_yticks(list(y), [s.upper() for s in order])
    ax.invert_yaxis()
    ax.set_xscale('log')
    ax.set_xticks([1, 2, 5, 10, 20, 50], ['1', '2', '5', '10', '20', '50'])
    ax.set_xlabel('participants (log scale)')
    ax.legend(loc='lower center', bbox_to_anchor=(0.45, 1.0), ncol=2, frameon=False, handletextpad=0.2, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(folder_v / 'coverage.png', dpi=150)
    plt.close(fig)
    # Decision figure: download size per study and source route, with free-disk line.
    adb = sorted(ADB_SLUGS, key=lambda s: recs[s]['addbiomechanics_source']['compressed_bytes_total'])
    fig, ax = plt.subplots(figsize=(4.5, 4.6))
    h = 0.38
    for i, s in enumerate(adb):
        a = recs[s]['addbiomechanics_source']['compressed_bytes_total'] / 1e9
        ax.barh(i + h / 2, a, height=h, color='#2a78d6', label='AddBiomechanics' if i == 0 else None)
        ax.text(a * 1.12, i + h / 2, f'{a:.1f}' if a < 10 else f'{a:.0f}', va='center', fontsize=10)
        if s in ORIGINAL_ROUTE:
            o = ORIGINAL_ROUTE[s]['bytes'] / 1e9
            ax.barh(i - h / 2, o, height=h, color='#eb6834', label='open publisher original' if s == 'ca23' or 'ca23' not in ORIGINAL_ROUTE else None)
            ax.text(o * 1.12, i - h / 2, f'{o:.1f}' if o < 10 else f'{o:.0f}', va='center', fontsize=10)
    free = result['totals']['data_drive_free_bytes_at_check'] / 1e9
    ax.axvline(free, color='#a8322d', ls='--', lw=1.2)
    ax.text(free * 0.93, 1.3, f'free disk\n{free:.0f} GB\n({free * 1e9 / 2**30:.0f} GiB)', color='#a8322d', fontsize=10, va='center', ha='right')
    ax.set_xscale('log')
    ax.set_xlim(0.05, 1500)
    ax.set_xticks([0.1, 1, 10, 100, 1000], ['0.1', '1', '10', '100', '1000'])
    ax.set_yticks(range(len(adb)), [s.upper() for s in adb])
    ax.set_xlabel('download, GB (log scale)')
    ax.legend(loc='lower center', bbox_to_anchor=(0.45, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(folder_d / 'download.png', dpi=150)
    plt.close(fig)


def sheets(result):
    v, d = SHEETS / 'HIST-01', SHEETS / 'D-HIST-01-1'
    v.mkdir(parents=True, exist_ok=True)
    d.mkdir(parents=True, exist_ok=True)
    figures(result, v, d)
    t = result['totals']
    um = next(r for r in result['records'] if r['slug'] == 'um24k')
    um_ok = all(f.get('matches_publisher_version_6', True) for f in um['local_source']['files'])
    page(v / 'index.html', title='HIST-01 sources',
         ask='Look at one figure; no decision on this sheet.',
         headline='Twelve historical studies: only the knee-exoskeleton source was found in the searched folders.',
         chips=[('pass' if um_ok else 'fail', 'UMich 2024 files match the publisher'),
                ('pass', 'Eleven AddBiomechanics studies located in the official release'),
                ('fail', 'Old files cannot be traced to source files'),
                ('fail', 'Old records list fewer participants in 11 of 12'),
                ('pass', 'Publisher papers confirmed for 11 of 12'),
                ('unchecked', 'Tan and Falisse trial membership'),
                ('unchecked', 'Original-data licenses for six studies'),
                ('unchecked', 'Old download links')],
         figures=[('coverage.png', 'Do the old records hold every published participant?',
                   'Orange squares sit left of blue dots wherever participants are missing.', 'Participants per study: old file versus source')],
         not_shown=['Trial-level membership.', 'Any signal values.', 'License text of each package.'],
         reply='HIST-01 ok',
         details=[f'Audit: {rel(OUT)}', 'Builder: contributor_tools/review_hist01_source_dispositions.py',
                  'Source participants: AddBiomechanics archive subject folders; UMich 2024 uses publisher (10).'])
    gb = lambda key: f'about {t[key] / 1e9:.0f} GB'
    decision = {
        'question': 'From which source, if any, should LocoHub rebuild the eleven AddBiomechanics-derived historical studies?',
        'columns': ['Left out', 'Source', 'Download', 'Consequence'],
        'rows': [('A', ['All eleven', 'none', 'none', 'Pages stay labelled legacy with corrected citations; AddBiomechanics tasks pause. Reversible.']),
                 ('B', ['none', 'Publisher originals for Carter, Moore, Lencioni, van der Zee, Wang; AddBiomechanics for the other six',
                        gb('option_B_mixed_route_bytes'),
                        'Two source families: five new original-format adapters plus the AddBiomechanics adapter. Reversible.']),
                 ('C', ['none', 'AddBiomechanics for all eleven', gb('adb_compressed_bytes_eleven_studies'),
                        'One adapter; Carter alone is 245 GB, more than the free disk; reprocessed derivatives only. Reversible.']),
                 ('defer', ['all for now', 'none', 'none', 'Pages stay legacy; AddBiomechanics tasks stay blocked; active datasets unaffected.'])],
        'footnote': 'Options ordered by total download size.',
        'recommendation': ('B, medium confidence: the publisher originals are the primary records for five studies and cut the total download '
                           'from about 347 to about 108 GB (Carter from 245 to 29 GB). The cost is five new source adapters, each piloted one study at a time.')}
    page(d / 'index.html', title='D-HIST-01-1 rebuild source',
         ask='Choose A, B, C or defer.',
         headline='Eleven studies: no source found in searched folders; all are in AddBiomechanics, five also have open publisher data.',
         chips=[('pass', 'Sizes read from release index and repository metadata'),
                ('unchecked', 'Whether old files equal release files'),
                ('unchecked', 'Licence conflict for Lencioni and van der Zee items')],
         figures=[('download.png', 'How much would each study cost to download, by source?',
                   'Orange bars appear only where open publisher data exists.', 'Download size per study for each source route with free-disk line')],
         not_shown=['Scientific quality of any study.', 'Effort to write each new adapter.'],
         reply='D-HIST-01-1: A | B | C | defer', decision=decision,
         details=[f'Audit: {rel(OUT)}', 'Free disk is in decimal GB (about 153 GiB).'])

if __name__ == '__main__':
    sheets(build())
    print(f'Wrote {rel(OUT)} and review_sheets/HIST-01, review_sheets/D-HIST-01-1')
