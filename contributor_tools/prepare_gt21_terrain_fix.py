"""Prepare an isolated GT21 terrain correction; run only in the serial queue.

Requires measured terrain metadata and source task labels. Never assigns a
whole recording to a terrain task merely because no labeled cycles survived.
"""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom


HELPER = '''
function require_terrain_inputs(trial_data, value)
    assert(isnumeric(value) && isscalar(value) && isfinite(value) && value > 0, ...
        'LocoHub:TerrainValue', 'Positive finite source terrain value required');
    assert(isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
        all(ismember({'Header','Label'}, trial_data.conditions.Properties.VariableNames)) && ...
        height(trial_data.conditions) > 0, ...
        'LocoHub:TerrainLabels', 'Source terrain task labels required');
end

function run_terrain_input_fixtures()
    valid.conditions = table([0;1], {'rampascent';'rampascent'}, ...
        'VariableNames', {'Header','Label'});
    require_terrain_inputs(valid, 5.2);
    for value = {NaN, Inf, 0, -1, [], [1 2]}
        caught = false;
        try, require_terrain_inputs(valid, value{1});
        catch problem, caught = strcmp(problem.identifier, 'LocoHub:TerrainValue'); end
        assert(caught, 'Invalid terrain scalar was accepted');
    end
    for invalid = {struct(), struct('conditions', table()), ...
            struct('conditions', table([0;1], 'VariableNames', {'Header'}))}
        caught = false;
        try, require_terrain_inputs(invalid{1}, 5.2);
        catch problem, caught = strcmp(problem.identifier, 'LocoHub:TerrainLabels'); end
        assert(caught, 'Missing terrain labels were accepted');
    end
    fprintf('Terrain input fixtures: 10 cases passed\\n');
end
'''


def terrain_source(source):
    """Patch only reviewed terrain functions, rejecting a changed source shape."""
    for name, value in [('process_ramp', 'ramp_angle'), ('process_stair', 'stair_height_m')]:
        start = source.index('function [rows, trial_count] = '+name+'(')
        # The end of each processing function precedes the next local function.
        end = source.index('\nfunction ', start+1)
        body = source[start:end]
        fallback = body.index('        if ~processed\n')
        suffix = body[fallback:]
        if suffix.count('% FALLBACK PROCESSING:') != 1 or not suffix.rstrip().endswith('    end\nend'):
            raise ValueError('Terrain fallback structure changed; review patch')
        body = body[:fallback]+'    end\nend\n'
        if body.count('        processed = false;') != 1:
            raise ValueError('Terrain processing structure changed')
        body = body.replace('        processed = false;', '        require_terrain_inputs(trial_data, '+value+');')
        body = body.replace('                        processed = true;\n', '')
        if name == 'process_stair':
            old = "            fprintf('  WARNING: No stair height found, using default 0.102 m (4 inches)\\n');\n            stair_height_m = 0.102;"
            if body.count(old) != 1:
                raise ValueError('Stair height default changed')
            body = body.replace(old, "            error('LocoHub:TerrainValue', 'Source stair height required');")
        source = source[:start]+body+source[end:]
    old = "    if isnan(stair_height_m)\n        stair_height_m = 0.102;  % default four-inch step\n    end"
    if source.count(old) != 1:
        raise ValueError('Stair label default changed')
    source = source.replace(old, "    assert(isnumeric(stair_height_m) && isscalar(stair_height_m) && isfinite(stair_height_m) && stair_height_m > 0, ...\n        'LocoHub:TerrainValue', 'Source stair height required');")
    anchor = 'if nargin < 1, options = struct(); end'
    if source.count(anchor) != 1:
        raise ValueError('Converter entry changed')
    return source.replace(anchor, anchor+'\nrun_terrain_input_fixtures();', 1)+HELPER


def verify_identical(baseline, corrected):
    import pandas as pd
    import pyarrow.parquet as pq
    left, right = pq.ParquetFile(baseline), pq.ParquetFile(corrected)
    assert left.metadata.num_rows == right.metadata.num_rows, 'Observation count changed'
    count = 0
    for a, b in zip(left.iter_batches(batch_size=150, use_threads=False),
                    right.iter_batches(batch_size=150, use_threads=False)):
        pd.testing.assert_frame_equal(a.to_pandas(use_threads=False), b.to_pandas(use_threads=False), check_exact=True)
        count += a.num_rows
    assert count == left.metadata.num_rows and count > 0
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    os.nice(max(0, 19-os.nice(0)))
    from contributor_tools import run_gt21_native_batch as native
    baseline = json.loads(args.baseline.read_text())
    assert baseline['status'] == 'converted_unreviewed'
    assert baseline['recording']['mode'] in ('ramp', 'stair')
    for item in baseline['outputs']:
        assert digest(args.baseline.parent/item['name']) == item['sha256']
    for item in baseline['sources']:
        assert digest(Path(item['path'])) == item['sha256']
    out = args.output_root.resolve()
    ensure_storage_headroom(out)
    plan_path = out/'pilot_plan.json'
    if not plan_path.exists():
        out.mkdir(parents=True, exist_ok=False)
        code = out/'isolated_code/Gtech_2021'
        code.mkdir(parents=True)
        original = native.CODE/'convert_gtech_2021_phase_to_parquet.m'
        (code/original.name).write_text(terrain_source(original.read_text()))
        shutil.copytree(native.CODE/'utilities', code/'utilities')
        shutil.copytree(native.CODE.parent/'matlab_common', code.parent/'matlab_common')
        dependencies = [Path(__file__), Path(native.__file__), native.GUARD,
                        ROOT/'contributor_tools/reconvert_recording.py',
                        *sorted((ROOT/'contributor_tools/common').rglob('*.py')),
                        *sorted((out/'isolated_code').rglob('*.m'))]
        native.save(plan_path, {'status': 'prepared_unreviewed', 'scientific_approval': False,
            'baseline_sha256': digest(args.baseline), 'original_converter_sha256': digest(original),
            'recording': baseline['recording'], 'code': native.evidence(dependencies)})
    plan = json.loads(plan_path.read_text())
    assert plan['baseline_sha256'] == digest(args.baseline)
    assert all(digest(Path(x['path'])) == x['sha256'] for x in plan['code'])
    if not args.run:
        print(plan['status'])
        return
    if shutil.disk_usage('/mnt/c').free < 1024**3:
        raise OSError('C free space below 1 GiB')
    summary = {'status': 'running', 'scientific_approval': False}
    try:
        native.CODE = out/'isolated_code/Gtech_2021'
        source_root = next(Path(x['path']).parent for x in baseline['sources'] if Path(x['path']).name == 'SubjectInfo.mat')
        manifest = native.run_record(source_root, baseline['recording'], out/'converted', plan['code'])
        rec = baseline['recording']
        folder = out/'converted'/rec['subject']/rec['date']/rec['mode']/Path(rec['recording']).stem
        assert 'Terrain input fixtures: 10 cases passed' in (folder/'matlab.log').read_text()
        rows = verify_identical(args.baseline.parent/'phase.parquet', folder/'phase.parquet')
        assert all(digest(Path(x['path'])) == x['sha256'] for x in plan['code'])
        summary.update(status='terrain_pilot_preserved_unreviewed', preserved_rows=rows,
                       observations=manifest['checks']['observations'], native_input_fixture_cases=10,
                       output_sha256=digest(folder/'phase.parquet'))
    except Exception as error:
        summary.update(status='failed', reason=str(error))
        raise
    finally:
        native.save(out/'pilot_summary.json', summary)


if __name__ == '__main__':
    main()
