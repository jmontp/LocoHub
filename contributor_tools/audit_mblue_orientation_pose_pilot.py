"""Bounded source-clock and geometric consistency gate; no anatomical approval.

Default audits existing output. --run explicitly invokes the prepared guarded
native command first; the serial coordinator alone should use that option.
"""
import argparse
import csv
import json
import math
from pathlib import Path, PureWindowsPath
import subprocess

from contributor_tools.prepare_mblue_orientation_pose_pilot import digest

BODIES = ('femur_r', 'tibia_r', 'calcn_r', 'femur_l', 'tibia_l', 'calcn_l')
COLUMNS = ['source_time_s', 'heading_ground_x', 'heading_ground_y', 'heading_ground_z'] + [
    b + suffix for b in BODIES for suffix in
    ('_axis_ground_x', '_axis_ground_y', '_axis_ground_z', '_projected_angle_rad')]


def linux(path):
    p = PureWindowsPath(path)
    if not p.is_absolute() or len(p.drive) != 2:
        raise ValueError('Expected absolute Windows drive path')
    return Path('/mnt') / p.drive[0].lower() / Path(*p.parts[1:])


def recheck(bindings):
    for path, expected in bindings.items():
        if digest(path) != expected:
            raise ValueError('Changed bound input: ' + path)


def source_clock(path, start, end):
    if Path(path).stat().st_size > 64 * 1024**2:
        raise ValueError('Source exceeds admission')
    selected = []
    with Path(path).open() as stream:
        for line_index, line in enumerate(stream):
            if line_index > 100:
                raise ValueError('Missing bounded source header')
            if line.strip().lower() == 'endheader':
                break
        else:
            raise ValueError('Missing source header')
        labels = next(stream).split()
        if labels[0] != 'time' or len(labels) != len(set(labels)):
            raise ValueError('Invalid source labels')
        previous = -math.inf
        for index, line in enumerate(stream):
            if index >= 200000:
                raise ValueError('Source row admission exceeded')
            fields = line.split()
            if len(fields) != len(labels):
                raise ValueError('Malformed source row')
            t = float(fields[0])
            if not math.isfinite(t) or t <= previous:
                raise ValueError('Invalid source clock')
            previous = t
            if start <= t <= end:
                selected.append(t)
                if len(selected) > 2500:
                    raise ValueError('Window admission exceeded')
    if len(selected) < 2:
        raise ValueError('Insufficient source samples')
    return selected


def verify_csv(path, times):
    if Path(path).stat().st_size > 4 * 1024**2:
        raise ValueError('Output admission exceeded')
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError('Output schema differs')
        count = 0
        for count, row in enumerate(reader, 1):
            if count > len(times) or None in row or any(v is None for v in row.values()):
                raise ValueError('Extra or malformed output rows')
            values = [float(row[c]) for c in COLUMNS]
            if not math.isfinite(values[0]) or abs(values[0] - times[count-1]) > 1e-10:
                raise ValueError('Source clock coverage differs')
            h = values[1:4]
            if not all(map(math.isfinite, h)) or abs(math.hypot(*h)-1) > 1e-7 or abs(h[1]) > 1e-12:
                raise ValueError('Invalid horizontal heading')
            for index, body in enumerate(BODIES):
                axis = values[4+4*index:7+4*index]
                angle = values[7+4*index]
                if not all(map(math.isfinite, axis)) or abs(math.hypot(*axis)-1) > 1e-7:
                    raise ValueError('Invalid body axis')
                forward = sum(a*b for a, b in zip(axis, h))
                vertical = axis[1]
                if math.hypot(forward, vertical) < 1e-8:
                    if not math.isnan(angle):
                        raise ValueError('Undefined projection must be missing')
                else:
                    expected = math.atan2(vertical, forward) if body.startswith('calcn') else math.atan2(forward, -vertical)
                    if not math.isfinite(angle) or abs(math.remainder(angle-expected, 2*math.pi)) > 1e-7:
                        raise ValueError('Projection angle differs')
        if count != len(times):
            raise ValueError('Missing output samples')
    return count


def audit(plan_path, run=False):
    plan_path = Path(plan_path).resolve()
    root = plan_path.parent
    output = root/'pose_audit.json'
    if output.exists() or (run and any((root/n).exists() for n in ('native_status.json', 'body_axes.csv', 'pose_attempt.json'))):
        raise ValueError('Existing attempt or audit; use a fresh prepared pilot')
    plan = json.loads(plan_path.read_text())
    if plan.get('status') != 'prepared_not_executed':
        raise ValueError('Expected prepared pilot')
    bindings = dict(plan['inputs_sha256'])
    bindings[str(plan_path)] = digest(plan_path)
    if str(Path(__file__).resolve()) not in bindings:
        raise ValueError('Auditor must be bound by prepared plan')
    recheck(bindings)
    options_path = root/'options.json'
    options = json.loads(options_path.read_text())
    if linux(options['output_path']).resolve() != root/'body_axes.csv':
        raise ValueError('Output must match prepared root')
    for key in ('ik_path', 'model_path'):
        if str(linux(options[key]).resolve()) not in bindings:
            raise ValueError('Unbound native input')
    if run:
        (root/'pose_attempt.json').write_text(json.dumps({'status':'started', 'plan_sha256':bindings[str(plan_path)]})+'\n')
        with (root/'guard.log').open('x') as log:
            subprocess.run(plan['command'], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=360)
    recheck(bindings)
    status_path = root/'native_status.json'
    status = json.loads(status_path.read_text(encoding='utf-8-sig'))
    if status.get('status') != 'completed' or status.get('exit_code') != 0:
        raise ValueError('Native execution did not complete successfully')
    if linux(status.get('options', '')).resolve() != options_path:
        raise ValueError('Native status options mismatch')
    result_path = root/'body_axes.csv'
    evidence = {str(p): digest(p) for p in (status_path, result_path)}
    times = source_clock(linux(options['ik_path']), options['start_s'], options['end_s'])
    count = verify_csv(result_path, times)
    recheck(bindings); recheck(evidence)
    result = {'status':'source_clock_and_projection_consistency_checked_unreviewed',
              'scientific_approval':False, 'rows_checked':count, 'body_axes_per_row':6,
              'inputs_sha256':bindings, 'outputs_sha256':evidence,
              'limitations':['Native model transformations are not independently recomputed by this audit.',
                            'Body-axis/anatomical conventions require review; no normalized interpolation or canonical publication is approved.']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.plan, args.run)))


if __name__ == '__main__':
    main()
