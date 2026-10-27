"""Prepare a NEW combined terrain runner; never run or alter frozen queued code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Frozen runner structure changed; review adaptation')
    return text.replace(old,new,1)


def combined_terrain_source(source):
    from contributor_tools.prepare_gt21_combined_adoption import combined_source
    text=combined_source(source)
    text=once(text,'\nrun_terrain_clock_fixtures();','\nrun_terrain_clock_fixtures();\nrun_terrain_rounding_fixtures();')
    return text+'''
function run_terrain_rounding_fixtures()
    assert(round(5.25, 1) == 5.3, 'Ramp half-rounding differs');
    assert(round(5.35, 1) == 5.4, 'Ramp decimal rounding differs');
    assert(round(4 * 0.0254, 3) == 0.102, 'Four-inch height conversion differs');
    assert(round(5 * 0.0254, 3) == 0.127, 'Five-inch height conversion differs');
    fprintf('Terrain rounding fixtures: 4 cases passed\\n');
end
'''


def adapt_runner(text):
    text=once(text,'ROOT = Path(__file__).resolve().parents[1]',f'ROOT = Path({str(ROOT)!r})')
    text=once(text,'from contributor_tools.prepare_gt21_combined_adoption import combined_source',
        'from contributor_tools.prepare_gt21_terrain_pilot_runner import combined_terrain_source as combined_source')
    text=once(text,"if record['mode'] not in ('levelground', 'treadmill'):","if record['mode'] not in ('ramp', 'stair'):")
    text=once(text,"raise ValueError('Terrain eligibility ledger is not yet implemented; cannot approve that pilot')", "raise ValueError('This runner requires a ramp/stair recording')")
    text=once(text,'from contributor_tools.audit_gt21_adoption_ledger import check_record as check_ledger',
        'from contributor_tools.audit_gt21_terrain_adoption import check_record as check_ledger')
    text=once(text,"dependencies = [Path(__file__), original, Path(native.__file__), native.GUARD]", "dependencies = [Path(__file__), original, Path(native.__file__), native.GUARD,\n            ROOT/'contributor_tools/run_gt21_combined_pilot.py',\n            ROOT/'contributor_tools/prepare_gt21_terrain_pilot_runner.py',\n            ROOT/'contributor_tools/audit_gt21_terrain_adoption.py',\n            ROOT/'contributor_tools/gt21_terrain_metadata_gate.py']")
    text=once(text,"'Levelground/treadmill pilot only; terrain pipeline remains unverified'", "'Single ramp/stair pilot only; full terrain inventory remains unverified'")
    text=once(text,"        summary['preservation'] = verify_preserved(", "        if 'Terrain rounding fixtures: 4 cases passed' not in (folder/'matlab.log').read_text():\n            raise ValueError('Native terrain rounding fixtures not confirmed')\n        summary['preservation'] = verify_preserved(")
    ast.parse(text)
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args();out=args.output_root.resolve()
    if not out.is_relative_to((ROOT/'converted_datasets/reconversion_v2').resolve()):
        parser.error('Output must stay under reconversion_v2')
    original=ROOT/'contributor_tools/run_gt21_combined_pilot.py'
    text=adapt_runner(original.read_text())
    out.mkdir(parents=True,exist_ok=False)
    target=out/'run_terrain_pilot.py';target.write_text(text)
    paths=[original,Path(__file__).resolve(),ROOT/'contributor_tools/audit_gt21_terrain_adoption.py',ROOT/'contributor_tools/gt21_terrain_metadata_gate.py']
    report={'status':'terrain_runner_prepared_not_executed','scientific_approval':False,
        'runner':str(target),'runner_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'preparation_dependencies':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'usage':'Run this prepared runner WITHOUT --run first to freeze a separate ramp or stair baseline plan. Native execution must be scheduled serially.',
        'gates':['Complete whole-window source terrain event ledger','All-row task identity/transition/geometry metadata','Exact existing observations preserved','Independent joint source readback','All-cycle force/COP readback','Four native rounding fixtures'],
        'limitations':['Near-half raw terrain rounding remains fail-closed pending native reconciliation','Source annotation agreement is not physical/anatomical approval']}
    (out/'preparation_manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
