"""Text/synthetic tests: no native execution or scientific source reads."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import pytest
from contributor_tools import prepare_gt21_strict_pilot as tool


@pytest.mark.parametrize('terrain',[False,True])
def test_real_runner_composition_retains_adoption_gates(terrain):
 source=tool.adapt((tool.ROOT/'contributor_tools/run_gt21_combined_pilot.py').read_text(),terrain)
 tree=ast.parse(source)
 imports={(n.module,alias.name) for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) for alias in n.names}
 assert ('contributor_tools.check_gt21_bilateral_preservation_v2','verify_preserved') in imports
 assert ('contributor_tools.prepare_gt21_bilateral_recovery','verify_preserved') not in imports
 assert ('contributor_tools.audit_gt21_added_cycle_forces','audit_record') in imports
 assert ('contributor_tools.audit_gt21_terrain_adoption' if terrain else 'contributor_tools.audit_gt21_adoption_ledger','check_record') in imports
 for gate in ['require_complete_ledger(ledger)','all_pilot_cycles_force_checked_unreviewed','check_manifest(baseline_path)','check_manifest(folder/','full2301scope_checked=False','require_assertions()','check_gt21_bilateral_preservation_v2.py','subject_masses.csv']:
  assert gate in source
 assert ('Terrain rounding fixtures: 4 cases passed' in source)==terrain


def test_unrecognized_runner_fails_closed():
 with pytest.raises(ValueError,match='requires review'):tool.adapt('def main(): pass')


def test_optimized_execution_refused_before_source_reads():
 result=subprocess.run([sys.executable,'-O','-c','from contributor_tools.prepare_gt21_strict_pilot import require_assertions; require_assertions()'],cwd=tool.ROOT,capture_output=True,text=True,timeout=10)
 assert result.returncode!=0 and 'without optimization' in result.stderr


def test_manifest_closure_detects_source_and_output_changes(tmp_path):
 source=tmp_path/'synthetic.txt';source.write_text('source')
 output=tmp_path/'phase.parquet';output.write_bytes(b'synthetic-not-parquet')
 manifest=tmp_path/'conversion_manifest.json'
 data={'status':'converted_unreviewed','sources':[{'path':str(source),'sha256':tool.digest(source)}],'outputs':[{'name':output.name,'sha256':tool.digest(output)}]}
 manifest.write_text(json.dumps(data));assert tool.check_manifest(manifest)==tool.digest(manifest)
 source.write_text('changed')
 with pytest.raises(ValueError,match='Source'):tool.check_manifest(manifest)
 source.write_text('source');output.write_bytes(b'changed')
 with pytest.raises(ValueError,match='Output'):tool.check_manifest(manifest)


def test_prepare_new_paths_and_hashes_only(tmp_path,monkeypatch):
 # Real adapter composition, temporary metadata-only destination.
 out=tmp_path/'converted_datasets/reconversion_v2/new'
 root=tool.ROOT
 monkeypatch.setattr(tool,'ROOT',tmp_path)
 (tmp_path/'contributor_tools').symlink_to(root/'contributor_tools',target_is_directory=True)
 report=tool.prepare(out)
 assert all(tool.digest(path)==sha for path,sha in report['bindings'].items())
 assert report['scientific_approval'] is False
 with pytest.raises(FileExistsError):tool.prepare(out)
