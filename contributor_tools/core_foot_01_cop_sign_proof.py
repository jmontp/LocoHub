"""CORE-FOOT-01: CoP sign proof from each dataset's own foot-frame function (synthetic points, no dataset is read).

For each dataset's own foot_frame_point (GT23 conventions, GT21 pass, UM21 S02 frame), a few random synthetic points are placed
in the lab frame with random leg-plane geometry, the foot-frame point is computed at the foot angle and again at the foot angle
minus the offset, and the second result is compared with foot_flat.rotate_cop() of the first. The wrong sign is shown as well.
Writes docs/quality/audits/core-foot-01-cop-sign-proof.json (seed recorded).

  OMP_NUM_THREADS=1 nice -n 19 ionice -c 3 python3 contributor_tools/core_foot_01_cop_sign_proof.py
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261127


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    ff = load("foot_flat_proof", "contributor_tools/common/foot_flat.py")
    sources = (("GT23 (gt23_conventions.foot_frame_point, used by run_gt23_c06.py)", load("gt23c", "contributor_tools/gt23_conventions.py"), [0, 1, 0], ("R", "L")),
               ("GT21 (gt21_rb_pass.foot_frame_point)", load("gt21p", "contributor_tools/gt21_rb_pass.py"), [0, 1, 0], ("right", "left")),
               ("UM21 (run_um21_s02_frame.foot_frame_point)", load("um21f", "contributor_tools/run_um21_s02_frame.py"), [0, 0, 1], ("right", "left")))
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "synthetic": True, "formula": "a' = (a+0.1) cos d - v sin d - 0.1 ; v' = (a+0.1) sin d + v cos d ; d = offset (rad); foot angle' = foot angle - d",
           "datasets": {}}
    for label, mod, up, legs in sources:
        rows, worst, worst_wrong = [], 0.0, 1e9
        for leg in legs:
            n = 25
            ankle = rng.normal(0, 0.3, (n, 3))
            point = ankle + rng.normal(0, 0.15, (n, 3))
            foot = rng.uniform(-0.6, 0.5, n)
            fwd = np.tile(np.array([1.0, 0, 0]), (n, 1)) if "um21" not in mod.__name__ else np.array([1.0, 0, 0])
            for deg in (-11.75, -6.72, 1.2, 5.2):
                d = math.radians(deg)
                r0 = mod.foot_frame_point(point, ankle, fwd, foot, leg)
                r1 = mod.foot_frame_point(point, ankle, fwd, foot - d, leg)
                get = (lambda r, k: r[k]) if isinstance(r0, dict) else (lambda r, k: r[("anterior", "vertical", "lateral").index(k)])
                a0, v0, l0 = (np.asarray(get(r0, k)) for k in ("anterior", "vertical", "lateral"))
                a1, v1, l1 = (np.asarray(get(r1, k)) for k in ("anterior", "vertical", "lateral"))
                ra, rv = ff.rotate_cop(a0, v0, d)
                wa, wv = ff.rotate_cop(a0, v0, -d)
                dev = max(float(np.abs(ra - a1).max()), float(np.abs(rv - v1).max()), float(np.abs(l0 - l1).max()))
                wrong = max(float(np.abs(wa - a1).max()), float(np.abs(wv - v1).max()))
                worst, worst_wrong = max(worst, dev), min(worst_wrong, wrong)
                if len(rows) < 3:
                    i = 0
                    rows.append({"leg": leg, "offset_deg": deg, "foot_angle_rad": float(foot[i]),
                                 "before_anterior_vertical_lateral_m": [float(a0[i]), float(v0[i]), float(l0[i])],
                                 "dataset_function_at_shifted_foot_angle_m": [float(a1[i]), float(v1[i]), float(l1[i])],
                                 "rotate_cop_m": [float(ra[i]), float(rv[i])], "wrong_sign_m": [float(wa[i]), float(wv[i])]})
        out["datasets"][label] = {"max_abs_deviation_m_over_200_cases": worst,
                                  "wrong_sign_smallest_max_deviation_m": worst_wrong, "samples": rows}
    path = ROOT / "docs/quality/audits/core-foot-01-cop-sign-proof.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=1) + "\n")
    print({k: (v["max_abs_deviation_m_over_200_cases"], v["wrong_sign_smallest_max_deviation_m"]) for k, v in out["datasets"].items()})


if __name__ == "__main__":
    main()
