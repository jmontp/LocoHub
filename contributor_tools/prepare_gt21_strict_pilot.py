"""Prepare isolated GT21 pilot runners with explicit preservation errors.

Preparation writes Python and metadata only. Running generated pilot plans hashes
source inputs; native execution requires the separately owned serial worker slot.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def once(text,old,new):
 if text.count(old)!=1:raise ValueError('Runner changed: adaptation requires review')
 return text.replace(old,new,1)


def require_assertions():
 # Other independently maintained source auditors still contain assertions.
 if sys.flags.optimize:raise RuntimeError('Source auditors require Python without optimization')


def check_manifest(path):
 path=Path(path);manifest=json.loads(path.read_text())
 if manifest.get('status')!='converted_unreviewed':raise ValueError('Completed native baseline/output required')
 for item in manifest['sources']:
  if digest(item['path'])!=item['sha256']:raise ValueError('Source identity changed')
 names=[item['name'] for item in manifest['outputs']]
 if len(names)!=len(set(names)) or names.count('phase.parquet')!=1:raise ValueError('Unique phase output required')
 for item in manifest['outputs']:
  target=(path.parent/item['name']).resolve()
  if target.parent!=path.parent.resolve() or digest(target)!=item['sha256']:raise ValueError('Output identity changed')
 return digest(path)


def adapt(source,terrain=False):
 if terrain:
  from contributor_tools.prepare_gt21_terrain_pilot_runner import adapt_runner
  source=adapt_runner(source)
 else:
  source=once(source,'ROOT = Path(__file__).resolve().parents[1]',f'ROOT = Path({str(ROOT)!r})')
 source=once(source,'def main():',"from contributor_tools.prepare_gt21_strict_pilot import require_assertions, check_manifest\n\ndef main():\n    require_assertions()")
 source=once(source,'from contributor_tools.prepare_gt21_bilateral_recovery import verify_preserved','from contributor_tools.check_gt21_bilateral_preservation_v2 import verify_preserved')
 source=once(source,"'prepare_gt21_combined_adoption.py', 'prepare_gt21_bilateral_recovery.py',", "'prepare_gt21_combined_adoption.py', 'prepare_gt21_bilateral_recovery.py',\n            'check_gt21_bilateral_preservation_v2.py', 'prepare_gt21_strict_pilot.py',")
 source=once(source,'dependencies += force_dependencies',"dependencies += force_dependencies\n        mass_root = ROOT/'converted_datasets/reconversion_v2/gt21_subject_mass_review_20261021'\n        dependencies += [mass_root/'source_comparison.json', mass_root/'subject_masses.csv']")
 source=once(source,"if plan['baseline_sha256'] != digest(baseline_path):", "if plan['baseline_path'] != str(baseline_path) or plan['recording'] != record or plan['baseline_sha256'] != digest(baseline_path):")
 source=once(source,'    # The Windows launcher independently checks host memory, disk and timeout.', "    plan_sha256 = digest(plan_path)\n    baseline_sha256 = check_manifest(baseline_path)\n    # The Windows launcher independently checks host memory, disk and timeout.")
 source=once(source,"        summary.update(status='combined_pilot_source_checked_unreviewed',", "        if check_manifest(baseline_path) != baseline_sha256 or digest(plan_path) != plan_sha256:\n            raise ValueError('Baseline or plan changed during execution')\n        check_manifest(folder/'conversion_manifest.json')\n        summary.update(status='strict_combined_pilot_source_checked_unreviewed',\n                       full2301scope_checked=False, anatomical_frames_approved=False,\n                       plan_sha256=plan_sha256,")
 ast.parse(source)
 return source


def prepare(out):
 out=Path(out).resolve()
 if not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Use a fresh reconversion_v2 directory')
 original=ROOT/'contributor_tools/run_gt21_combined_pilot.py'
 sources={name:adapt(original.read_text(),terrain) for name,terrain in [('run_level_tread.py',False),('run_ramp_stair.py',True)]}
 dependencies=[Path(__file__).resolve(), original]+[ROOT/'contributor_tools'/name for name in ['check_gt21_bilateral_preservation_v2.py','prepare_gt21_terrain_pilot_runner.py','prepare_gt21_combined_adoption.py']]
 out.mkdir(parents=True,exist_ok=False)
 for name,source in sources.items():(out/name).write_text(source)
 report={'status':'strict_runners_prepared_not_executed','scientific_approval':False,'full2301scope_checked':False,
  'bindings':{str(p):digest(p) for p in dependencies+[out/name for name in sources]},
  'usage':'python3 RUNNER --baseline completed/conversion_manifest.json --output-root NEW_ROOT prepares a hash-bound pilot; append --run only in the authorized exclusive guarded queue. Do not use -O/PYTHONOPTIMIZE.',
  'gates':['Strict exact baseline preservation including cycle intervals','Complete eligible source event pairs','Terrain or treadmill metadata where applicable','Independent joint source readback','All-cycle force/COP including additions','Final baseline/source/output/plan identity closure'],
  'limits':{'python_address_space_MiB':768,'native_memory_MiB':2048,'native_timeout_seconds':300,'serial_slot_required':True},
  'limitations':['Not full 2301 recording coverage','Source annotation agreement does not approve anatomical frames','Original MATLAB aggregate terrain-label admission rule retained','Other source auditors use assertions; optimized execution is explicitly rejected']}
 (out/'preparation_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 return report


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-root',type=Path,required=True)
 args=parser.parse_args();print(json.dumps(prepare(args.output_root)))

if __name__=='__main__':main()
