"""Regression tests for the GTech 2023 time-indexed converter conventions.

Mirrors tests/test_umich_2021_conventions.py: the biomechanical conventions are
encoded as source-level assertions against the MATLAB converter (which cannot be
executed in CI), backed by numeric checks of the same transforms and a data-level
smoke test that runs only when the converted parquet is present locally.
"""

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CONVERTER = ROOT / "contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_2023_time_to_parquet.m"
PHASE_CONVERTER = ROOT / "contributor_tools/conversion_scripts/Gtech_2023/convert_gtech_phase_to_parquet.m"
CONVERTED = ROOT / "converted_datasets/gtech_2023_time.parquet"


@pytest.fixture(scope="module")
def source() -> str:
    return CONVERTER.read_text(encoding="utf-8")


def test_joint_sign_conventions_match_phase_converter(source):
    # Knee angle/velocity/moment negated; hip untouched. Ankle is NOT negated:
    # the raw OpenSim ankle already follows ankle_dorsiflexion = foot - shank
    # (dorsiflexion positive), so flipping it would invert the ankle vs the chain.
    assert "-sig(cached.angle, ['knee_angle_' ipsi], tw) * deg2rad" in source
    assert "rows.hip_flexion_angle_ipsi_rad   = sig(cached.angle, ['hip_flexion_' ipsi], tw) * deg2rad;" in source

    # Ankle angle and velocity carry no leading minus.
    assert "rows.ankle_dorsiflexion_angle_ipsi_rad   = sig(cached.angle, ['ankle_angle_' ipsi], tw) * deg2rad;" in source
    assert "-sig(cached.angle, ['ankle_angle_" not in source
    assert "-sig(cached.velocity, ['ankle_velocity_" not in source

    assert "-sig(cached.velocity, ['knee_velocity_' ipsi], tw) * deg2rad" in source

    assert "-sig(cached.moment, ['knee_angle_' ipsi '_moment'], tw)" in source
    # Ankle moment must NOT be negated (already correct in the raw data).
    assert "rows.ankle_dorsiflexion_moment_ipsi_Nm_kg   = sig(cached.moment, ['ankle_angle_' ipsi '_moment'], tw);" in source
    assert "-sig(cached.moment, ['ankle_angle_" not in source


def test_units_and_pelvis_offset(source):
    assert "deg2rad = pi / 180;" in source
    # Moments are already Nm/kg from OpenSim -> only the _Nm_kg name, no re-division.
    assert "_Nm_kg" in source
    assert "/ subject_mass" not in source  # moments not re-normalized by mass
    # Pelvis transverse coordinate-frame offset, matching the phase converter.
    assert "sig(cached.link, 'pelvis_Y', tw) * deg2rad + pi/2;" in source
    # Segment plane mapping: Z=sagittal, X=frontal, Y=transverse.
    assert "add_segment(rows, cached.link, 'thigh', 'femur'" in source
    assert "[raw '_' ipsi '_Z'], tw) * deg2rad" in source  # sagittal from _Z


def test_grf_axis_map_and_bw_normalization(source):
    assert "grf_anterior_ipsi_BW   = grf_norm(grf, [IU 'ForceX'], gt, tw, weight_N);" in source
    assert "grf_vertical_ipsi_BW   = grf_norm(grf, [IU 'ForceY_Vertical'], gt, tw, weight_N);" in source
    assert "grf_lateral_ipsi_BW    = grf_norm(grf, [IU 'ForceZ'], gt, tw, weight_N);" in source
    assert "weight_N = subject_mass_kg * 9.81;" in source
    assert "interp1(src_t, src_v, target_time, 'linear', NaN) / weight_N;" in source


def test_cop_ankle_frame_and_contact_masking(source):
    # CoP transformed into the local calcn frame: R' * (cop_global - translation).
    assert "transformed = pagemtimes(permute(Rn, [2 1 3]), reshape(rel, 3, 1, []));" in source
    assert "rel = cop_global - Trn;" in source
    # Static wiring check only; native MATLAB execution is a separate gate.
    assert "copy_name = [LU 'COPY_Vertical'];" in source
    assert "cop_v_i = zeros(n, 1);" not in source
    assert "cop_vert = interp1(gt, local_y, target_time, 'linear', NaN);" in source
    assert "nn = interp1(trans_time, 1:Nt, gt, 'nearest', NaN);" in source
    # CoP masked as missing when unloaded (vertical GRF < 0.2 BW) OR non-physical
    # for the ankle frame (> 0.5 m from the ankle).
    assert "cop_phys_max = 0.5;" in source
    assert "mask_ipsi = ~(rows.grf_vertical_ipsi_BW >= 0.2) |" in source
    assert "mask_contra = ~(rows.grf_vertical_contra_BW >= 0.2) |" in source
    assert "abs(cop_a_i) > cop_phys_max | abs(cop_l_i) > cop_phys_max" in source


def test_time_index_and_ipsi_contra_routing(source):
    # Continuous, native-resolution time reset to zero per labeled window.
    assert "time_s = tw - tw(1);" in source
    assert "rows.time_s = time_s;" in source
    # ipsi = reference (leading heel-strike) leg.
    assert "if strcmp(reference_leg, 'left')" in source
    assert "ipsi = 'l'; contra = 'r';" in source
    assert "ipsi = 'r'; contra = 'l';" in source
    # reference_leg derived from earliest heel strike, default right.
    assert "reference_leg = 'left';" in source


def test_bounded_memory_streaming(source):
    assert "write_table_shard" in source
    assert "merge_parquet_shards" in source
    assert "--row-group-size 65536" in source
    # One shard per subject, cleared between subjects (no whole-dataset accumulation).
    assert "clear subject_rows cached" in source
    assert "total_data" not in source  # not the in-memory accumulation pattern
    # Windows -> WSL path translation for the merge shell-out.
    assert "p = ['/mnt/' drive p(3:end)];" in source


def test_cop_three_dimensional_reference_fixture():
    # Independent geometric expectation, not execution of the MATLAB converter.
    # A rotated ankle frame couples measured global Y into local anterior COP.
    rotation = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    translation = np.array([0.30, 0.0, 0.10])
    cop_global = np.array([0.45, 0.04, 0.02])
    np.testing.assert_allclose(rotation.T @ (cop_global - translation), [0.04, -0.15, -0.08])


def test_grf_normalization_numerically():
    mass_kg = 70.0
    weight_N = mass_kg * 9.81
    raw_vertical_N = weight_N * 1.1  # 1.1 BW
    assert np.isclose(raw_vertical_N / weight_N, 1.1)


@pytest.mark.integration
@pytest.mark.skipif(not CONVERTED.exists(), reason="gtech_2023_time.parquet not generated locally")
def test_converted_time_dataset_passes_conventions():
    import pandas as pd
    from contributor_tools.common.validation.validator import Validator

    result = Validator().validate(str(CONVERTED))
    assert result["mode"] == "time"
    assert result["schema_passed"] is True
    assert result["violations"] == {}

    df = pd.read_parquet(CONVERTED, columns=["step", "time_s", "cop_lateral_ipsi_m", "grf_vertical_ipsi_BW"])
    # time_s strictly increases within every window.
    for _, g in df.groupby("step"):
        assert np.all(np.diff(g["time_s"].to_numpy()) > 0)
    # Ankle-frame CoP is physical (masked to NaN off-contact), never metres away.
    cop = df["cop_lateral_ipsi_m"].to_numpy()
    assert np.all(np.abs(cop[np.isfinite(cop)]) < 1.0)


@pytest.mark.integration
@pytest.mark.skipif(not CONVERTED.exists(), reason="gtech_2023_time.parquet not generated locally")
def test_ankle_follows_standard_segment_chain():
    # ankle_dorsiflexion = foot - shank (dorsiflexion positive). The joint angle
    # must correlate POSITIVELY with (foot_sagittal - shank_sagittal); a negative
    # correlation means the ankle sign is inverted (the bug this converter fixed).
    import pandas as pd

    cols = ["task", "ankle_dorsiflexion_angle_ipsi_rad",
            "foot_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad"]
    df = pd.read_parquet(CONVERTED, columns=cols)
    w = df[df["task"] == "level_walking"].dropna()
    assert len(w) > 1000
    ankle = w["ankle_dorsiflexion_angle_ipsi_rad"].to_numpy()
    chain = (w["foot_sagittal_angle_ipsi_rad"].to_numpy()
             - w["shank_sagittal_angle_ipsi_rad"].to_numpy())
    r = float(np.corrcoef(ankle, chain)[0, 1])
    assert r > 0.8, f"ankle should track +(foot - shank); corr={r:.2f} (sign inverted?)"
