#!/usr/bin/env python3
"""Run quick validation in a Linux systemd scope with a hard memory ceiling."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_command(args, validation_args):
    quick_check = Path(__file__).with_name('quick_validation_check.py')
    validation = [sys.executable, str(quick_check), *validation_args]
    if sys.platform.startswith('linux') and shutil.which('systemd-run'):
        return [
            'systemd-run', '--user', '--scope', '--quiet',
            '-p', f'MemoryHigh={args.memory_high_mb}M',
            '-p', f'MemoryMax={args.memory_max_mb}M',
            '-p', f'MemorySwapMax={args.memory_swap_max_mb}M',
            *validation,
        ]
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='All arguments after -- are passed to quick_validation_check.py.',
    )
    parser.add_argument('--memory-high-mb', type=int, default=3072)
    parser.add_argument('--memory-max-mb', type=int, default=4096)
    parser.add_argument('--memory-swap-max-mb', type=int, default=1024)
    args, validation_args = parser.parse_known_args()
    if validation_args and validation_args[0] == '--':
        validation_args = validation_args[1:]
    if not validation_args:
        parser.error('provide quick-validation arguments after --')
    if args.memory_high_mb > args.memory_max_mb:
        parser.error('--memory-high-mb cannot exceed --memory-max-mb')

    command = build_command(args, validation_args)
    if command[0] != 'systemd-run':
        print(
            'Warning: systemd-run is unavailable; running without an OS-enforced '
            'memory ceiling.',
            file=sys.stderr,
        )
    return subprocess.run(command, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
