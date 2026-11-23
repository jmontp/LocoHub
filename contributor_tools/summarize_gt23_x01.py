"""GT23-X01 acceptance-count summary over the twelve finished participant roots (small JSON only; one guarded job).

Creates the new output root, then runs run_gt23_x01.summarize into <output-root>/summary.json.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import run_gt23_x01 as runner  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--events-root', type=Path, required=True)
    p.add_argument('roots', nargs='+', type=Path)
    a = p.parse_args(argv)
    if not a.output_root.resolve().is_relative_to(runner.BASE):
        raise SystemExit('output root must be under converted_datasets/reconversion_v2')
    a.output_root.mkdir(parents=True, exist_ok=False)
    return runner.summarize(argparse.Namespace(out=a.output_root / 'summary.json', roots=a.roots, events_root=a.events_root))


if __name__ == '__main__':
    sys.exit(main())
