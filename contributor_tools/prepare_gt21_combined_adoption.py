"""Compose isolated GT21 fixes; never execute MATLAB or change production code.

Native validation, source eligibility and force/COP readback remain adoption gates.
The existing contiguous-label sample policy is deliberately unchanged pending review.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


CLOCK_GUARD = """    clock = trial_data.conditions.Header;
    assert(isnumeric(clock) && isreal(clock) && iscolumn(clock) && ...
        numel(clock) == height(trial_data.conditions) && all(isfinite(clock)) && ...
        all(diff(clock) > 0), ...
        'LocoHub:TerrainClock', 'Finite strictly increasing scalar condition timestamps required');
"""
CLOCK_FIXTURES = """
function run_terrain_clock_fixtures()
    valid.conditions = table([0;1;2], {'rampascent';'rampascent';'rampascent'}, ...
        'VariableNames', {'Header','Label'});
    require_terrain_inputs(valid, 5.2);
    bad_clocks = {[0;NaN;2], [0;Inf;2], [0;0;2], [0;2;1], ...
        {'0';'1';'2'}, [0 0;1 1;2 2], [0;1i;2]};
    for idx = 1:numel(bad_clocks)
        invalid = valid;
        invalid.conditions.Header = bad_clocks{idx};
        caught = false;
        try, require_terrain_inputs(invalid, 5.2);
        catch problem, caught = strcmp(problem.identifier, 'LocoHub:TerrainClock'); end
        assert(caught, 'Malformed terrain clock accepted');
    end
    fprintf('Terrain clock fixtures: 8 cases passed\\n');
end
"""


def combined_source(source):
    # Lazy imports keep source inspection/AST checks free of numerical imports.
    from contributor_tools.prepare_gt21_bilateral_recovery import bilateral_source
    from contributor_tools.prepare_gt21_terrain_fix import terrain_source
    first = terrain_source(bilateral_source(source))
    second = bilateral_source(terrain_source(source))
    if first != second:
        raise ValueError('Fix composition depends on order; review before adoption')
    anchor = "        'LocoHub:TerrainLabels', 'Source terrain task labels required');\n"
    if first.count(anchor) != 1:
        raise ValueError('Terrain guard changed; review composition')
    first = first.replace(anchor, anchor + CLOCK_GUARD, 1)
    invocation = '\nrun_terrain_input_fixtures();'
    if first.count(invocation) != 1:
        raise ValueError('Native fixture entry changed')
    return first.replace(invocation, invocation+'\nrun_terrain_clock_fixtures();', 1)+CLOCK_FIXTURES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='NEW proposal directory')
    args = parser.parse_args()
    source = args.source.read_text()
    proposal = combined_source(source)
    args.output.mkdir(parents=True, exist_ok=False)
    target = args.output/args.source.name
    target.write_text(proposal)
    evidence = {'status':'isolated_combined_source_prepared_not_executed',
        'scientific_approval':False,'source_path':str(args.source.resolve()),
        'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'proposal_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'preparation_code_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [Path(__file__).resolve(),
                ROOT/'contributor_tools/prepare_gt21_bilateral_recovery.py',
                ROOT/'contributor_tools/prepare_gt21_terrain_fix.py']},
        'label_segment_policy':'Unchanged; min_samples currently applies across disjoint regions',
        'remaining_gates':['Native positive and negative pipeline fixtures',
            'Exact old-observation preservation', 'Complete independently eligible pair recovery',
            'Independent force/COP readback on added cycles',
            'Reviewed per-region label eligibility policy', 'Preserved production plan handoff']}
    (args.output/'proposal.json').write_text(json.dumps(evidence,indent=2)+'\n')


if __name__ == '__main__':
    main()
