#!/usr/bin/env python3
"""Prepare a Rajagopal model copy for use in the Gait120 pipeline.

By default this copies `rajagopal_original.osim` to `rajagopal_gait120.osim`
without changing coordinate lock states. Optional locking of secondary knee DOFs
is available via `--lock-secondary-knee-dofs`.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create rajagopal_gait120.osim")
    parser.add_argument(
        "--lock-secondary-knee-dofs",
        action="store_true",
        help="Lock knee_angle_*_beta to zero in the output model",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    src = script_dir / "rajagopal_original.osim"
    dst = script_dir / "rajagopal_gait120.osim"

    if not src.exists():
        raise FileNotFoundError(f"Missing source model: {src}")

    try:
        import opensim as osim  # type: ignore
    except Exception as e:
        print("OpenSim Python API not available.")
        print("Install with: conda install -c opensim-org opensim")
        print(f"Import error: {e}")
        return 1

    model = osim.Model(str(src))
    if args.lock_secondary_knee_dofs:
        coord_set = model.updCoordinateSet()
        for name in ("knee_angle_r_beta", "knee_angle_l_beta"):
            if coord_set.contains(name):
                coord = coord_set.get(name)
                coord.setDefaultValue(0.0)
                coord.setDefaultLocked(True)
                coord.set_locked(True)
        print("Locked knee_angle_*_beta coordinates in output model.")
    else:
        print("Leaving knee_angle_*_beta coordinates unlocked in output model.")

    model.printToXML(str(dst))
    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
