#!/usr/bin/env python3
"""Run one GT25 parsed recording through the existing guarded staging worker.

The adapter lives beside its converter so the common worker fingerprints both.
It does not modify the worker used by an already-running GT24 batch.
"""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from contributor_tools import reconvert_recording as worker


def source_paths(args):
    trial = args.source_root / args.subject / args.recording
    if not trial.is_dir():
        raise ValueError('GT25 recording directory does not exist')
    prefix = f'{args.subject}_{args.recording}_'
    kinds = ['angle_filt','moment_filt','grf','velocity','insole_sim',
             'moment_filt_bio','power','power_bio','exo','exo_sim','imu_sim']
    files = [trial/f'{prefix}{kind}.csv' for kind in kinds]
    files = [path for path in files if path.exists()]
    readme = args.source_root.parent/'readme.txt'
    if not readme.is_file():
        raise ValueError('Source README is required for GT25 mass and convention provenance')
    files.append(readme)
    return trial, files, Path(__file__).with_name('convert_gtech_2025_da_to_parquet.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--subject',required=True)
    parser.add_argument('--recording',required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--memory-mib',type=int,default=1536)
    parser.add_argument('--max-source-mib',type=int,default=64)
    parser.add_argument('--ranges',type=Path)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    for value in [args.subject,args.recording]:
        if Path(value).name != value or value in {'.','..'}:
            parser.error('Subject and recording must be single path components')
    if not 1 <= args.max_source_mib <= 512:
        parser.error('Source limit must be between 1 and 512 MiB')
    args.dataset='gt25';args.source='Parsed';args.source_root=args.source_root.resolve()
    original_loader=worker.load_converter
    def load(path):
        module=original_loader(path)
        return SimpleNamespace(process_trial=lambda trial,subject,source,scope:module.process_trial(trial,subject))
    worker.source_paths=source_paths
    worker.load_converter=load
    worker.convert(args)


if __name__=='__main__':main()
