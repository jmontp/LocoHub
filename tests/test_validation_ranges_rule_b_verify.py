"""Independent CORE-07 verifier checks of range signs under rule B.

Rule B (docs/reference/index.md, "Signs and frames"): joint angles and internal
moments are positive in their named direction; segment angles are counterclockwise
viewed from the right with the person facing +x, so pelvis anterior tilt and toes-down
foot are negative. Each row states a physically known sign and the bound test that an
exact mirror (negate and swap) of the written range would fail. Only range YAML files
are read; no data.
"""

from pathlib import Path

import pytest
import yaml

RANGES = Path(__file__).resolve().parents[1] / "contributor_tools" / "validation_ranges"
PROFILES = ["default_ranges.yaml", "gtech_2024_ranges.yaml"]
PELVIS = "pelvis_sagittal_angle_rad"


def _band(name, task, phase, feature):
    bounds = yaml.safe_load((RANGES / name).read_text())["tasks"][task]["phases"][phase][feature]
    return bounds["min"], bounds["max"]


def _mid(band):
    return (band[0] + band[1]) / 2


# (task, phase, feature, expected sign of the band's centre, physical reason)
KNOWN_SIGNS = [
    ("level_walking", 75, "knee_flexion_angle_ipsi_rad", +1, "mid-swing knee flexion (about 60 deg)"),
    ("run", 75, "knee_flexion_angle_ipsi_rad", +1, "running swing knee flexion (about 90 deg)"),
    ("stand_to_sit", 75, "hip_flexion_angle_ipsi_rad", +1, "near-seated hip flexion (about 80 deg)"),
    ("sit_to_stand", 25, "knee_flexion_angle_ipsi_rad", +1, "knee flexed before seat-off"),
    ("run", 50, "foot_sagittal_angle_ipsi_rad", -1, "early swing after toe-off: toes point down (clockwise)"),
    ("level_walking", 50, "ankle_dorsiflexion_moment_ipsi_Nm_kg", -1, "push-off internal plantarflexor moment"),
    ("decline_walking", 15, "knee_flexion_moment_ipsi_Nm_kg", -1, "loading-response internal knee extensor moment"),
    # Not phase 0: at heel strike the braking force has not developed (gtech band -0.10..+0.14).
    ("run", 15, "grf_anterior_ipsi_BW", -1, "running loading phase braking: force opposes +x"),
    ("level_walking", 50, "grf_anterior_ipsi_BW", +1, "propulsion before toe-off: force along +x"),
    ("run", 0, "thigh_sagittal_angle_ipsi_rad", +1, "initial contact: knee ahead of hip (counterclockwise)"),
]


@pytest.mark.parametrize("name", PROFILES)
@pytest.mark.parametrize("task,phase,feature,sign,reason", KNOWN_SIGNS)
def test_band_centre_has_the_rule_b_sign(name, task, phase, feature, sign, reason):
    band = _band(name, task, phase, feature)
    assert band[0] <= band[1]
    assert _mid(band) * sign > 0, reason


@pytest.mark.parametrize("name", PROFILES)
def test_sit_to_stand_pelvis_reads_counterclockwise(name):
    """Rising: the pelvis tips forward (anterior) after seat-off, which is negative under rule B.

    Diagnostic regardless of the unknown zero: the centre must fall from seated to mid-rise
    and be negative at mid-rise. An anterior-positive band would rise instead.
    """
    seated, mid_rise = (_mid(_band(name, "sit_to_stand", phase, PELVIS)) for phase in (0, 50))
    assert seated > mid_rise and mid_rise < 0


@pytest.mark.parametrize("name", PROFILES)
def test_stand_to_sit_pelvis_reads_counterclockwise(name):
    standing, lowering = (_mid(_band(name, "stand_to_sit", phase, PELVIS)) for phase in (0, 50))
    assert standing > lowering and lowering < 0


@pytest.mark.parametrize("name", PROFILES)
def test_run_pelvis_band_is_mirrored_to_rule_b(name):
    """CORE-07 round 2 mirrored the run band exactly. Running tilts the pelvis forward, which is
    negative under rule B; the band centre must sit below -0.17 rad (about 10 deg anterior) at
    every phase, with no within-cycle signature. The zero remains undocumented.
    """
    centres = [_mid(_band(name, "run", phase, PELVIS)) for phase in (0, 25, 50, 75)]
    assert max(centres) - min(centres) < 0.05
    assert max(centres) < -0.17
