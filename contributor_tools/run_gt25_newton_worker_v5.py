"""Fresh-process wrapper proving the actual imported GT25 segmentation module."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'converted_datasets/reconversion_v2'
FAMILY = Path('contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def inspect_helper(converter, snapshot, expected):
    path = (snapshot / 'contributor_tools/common/stride_segmentation.py').resolve()
    helper = sys.modules.get('common.stride_segmentation')
    if helper is None or Path(helper.__file__).resolve() != path or digest(path) != expected:
        raise ValueError('Actual common.stride_segmentation is not the bound v5 helper')
    for name in ('segment_gait_cycles', 'segment_sit_stand_transfers'):
        if getattr(converter, name) is not getattr(helper, name):
            raise ValueError('Converter callable differs from bound helper: ' + name)
    return {'module': 'common.stride_segmentation', 'path': str(path), 'sha256': expected,
            'callables_identity_checked': ['segment_gait_cycles', 'segment_sit_stand_transfers']}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def storage_guard(worker):
    # Preserve snapshot ROOT for import and code fingerprints. Only authorize the
    # real staging volume in the otherwise byte-identical storage-check function.
    original = worker.ensure_storage_headroom
    scope = dict(original.__globals__, ROOT=ROOT)
    worker.ensure_storage_headroom = types.FunctionType(original.__code__, scope,
                                                       original.__name__, original.__defaults__)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--proposal', type=Path, required=True)
    p.add_argument('--mode', choices=['regular', 'streaming'], required=True)
    a, forwarded = p.parse_known_args()
    proposal = a.proposal.resolve(); snapshot = proposal/'isolated_repo'
    manifest = json.loads((proposal/'preparation_manifest.json').read_text())
    if manifest['status'] != 'explicit_newton_v5_prepared_not_run':
        raise ValueError('Not an explicit-Newton proposal')
    for name, sha in manifest['snapshot_code'].items():
        if digest(snapshot/name) != sha: raise ValueError('Snapshot changed: '+name)
    helper_sha = manifest['snapshot_code']['contributor_tools/common/stride_segmentation.py']
    if 'common.stride_segmentation' in sys.modules or 'contributor_tools.reconvert_recording' in sys.modules:
        raise ValueError('Fresh interpreter required; worker/helper already imported')
    sys.path.insert(0, str(snapshot))
    if a.mode == 'regular':
        module = load(snapshot/FAMILY/'reconvert_recording.py', 'gt25_v5_family_worker')
        owner = module.worker
        if Path(owner.__file__).resolve() != snapshot/'contributor_tools/reconvert_recording.py':
            raise ValueError('Wrong generic worker namespace')
        storage_guard(owner)
    else:
        module = load(snapshot/'contributor_tools/run_gt25_streaming_transfer_newton_v5.py', 'gt25_v5_stream_worker')
        owner = module
    original = owner.load_converter; evidence = []; converters = []
    def checked(path):
        converter = original(path)
        evidence.append(inspect_helper(converter, snapshot, helper_sha)); converters.append(converter)
        return converter
    owner.load_converter = checked
    output = Path(forwarded[forwarded.index('--output-root')+1]).resolve()
    if not output.is_relative_to(BASE) or output.exists(): raise ValueError('Fresh authorized output required')
    sys.argv = [str(module.__file__), *forwarded]
    if a.mode == 'streaming': sys.argv += ['--prepared', str(proposal), '--run']
    module.main()
    if len(evidence) != 1: raise ValueError('Exactly one actual converter load required')
    inspect_helper(converters[0], snapshot, helper_sha)
    if a.mode == 'streaming':
        detector = Path(module.segmentation.__file__).resolve()
        expected = snapshot/'contributor_tools/gt25_streaming_transfers_newton_v5.py'
        if detector != expected or digest(detector) != manifest['snapshot_code'][str(expected.relative_to(snapshot))]:
            raise ValueError('Wrong actual streaming detector')
        evidence[0]['streaming_detector'] = {'path': str(detector), 'sha256': digest(detector)}
    report = {'status': 'actual_v5_imports_checked', 'mode': a.mode, 'helper': evidence[0],
              'wrapper_sha256': digest(__file__), 'proposal_sha256': digest(proposal/'preparation_manifest.json'),
              'storage_guard_policy': 'Only storage-check globals use real repository ROOT; import/code ROOT remains isolated snapshot.'}
    with (output/'runtime_helper.json').open('x') as f: json.dump(report, f, indent=2)

if __name__ == '__main__': main()
