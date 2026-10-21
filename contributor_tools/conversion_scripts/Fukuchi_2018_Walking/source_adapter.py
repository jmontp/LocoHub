"""Inventory-only scaffold for a pinned Fukuchi Walking source version.

No data conversion, download, or numerical import occurs here. Raw/normalized
observation semantics must be verified before implementing canonical output.
"""
import argparse
import hashlib
import json
from pathlib import Path

PINNED_DOI = '10.6084/m9.figshare.5722711.v6'
MAX_PILOT_DOWNLOAD_BYTES = 16 * 1024**2


def source_plan(inventory_path):
    inventory_path = Path(inventory_path)
    data = json.loads(inventory_path.read_text())
    if data.get('doi') != PINNED_DOI or data.get('version') != 6:
        raise ValueError('Unreviewed source version; re-review evidence before changing the pin')
    if data.get('license', {}).get('name') != 'CC BY 4.0':
        raise ValueError('Source license differs from reviewed evidence')
    files = data.get('files', [])
    if not files or len({f['id'] for f in files}) != len(files):
        raise ValueError('Missing or duplicate source file identity')
    return {'status': 'source_reviewed_conversion_not_implemented',
            'source_doi': PINNED_DOI, 'scientific_approval': False,
            'inventory_sha256': hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
            'files': [{'id': f['id'], 'name': f['name'], 'bytes': f['size'],
                       'source_md5': f['computed_md5'], 'url': f['download_url'],
                       'within_single_file_pilot_budget': 0 < f['size'] <= MAX_PILOT_DOWNLOAD_BYTES}
                      for f in files],
            'blockers': ['51-person v6 metadata versus42-person paper; reconcile participant/recording inventory',
                         'Actual table headers, per-cycle versus average semantics and leg-specific clocks uninspected',
                         'Individual gait event/timing provenance required before150-point cycle export',
                         'Canonical source frames and moment signs require independent bounded source readback'],
            'download_performed': False, 'converted_observations': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, default=Path(__file__).parent/'source_evidence/figshare_v6_inventory.json')
    args = parser.parse_args()
    print(json.dumps(source_plan(args.inventory), indent=2))
