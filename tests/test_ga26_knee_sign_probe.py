"""Synthetic fixtures for the GA26-C01 knee-sign probe (no Gait120 data read).

The curves below are made-up, labeled synthetic shapes with known signs: a
seated start at 90 deg hip flexion and 90 deg knee flexion, and a walking swing
with 60 deg peak knee flexion.
"""
import math

import pytest

from contributor_tools.probe_ga26_knee_sign import classify, parse_mot, select, verdict


def synthetic_mot(hip, knee_r, knee_l, degrees=True):
    head = ["Coordinates", "version=1", f"nRows={len(hip)}", "nColumns=5",
            f"inDegrees={'yes' if degrees else 'no'}", "", "endheader",
            "time\thip_flexion_r\tknee_angle_r\thip_flexion_l\tknee_angle_l"]
    rows = [f"{i/100:.2f}\t{h}\t{kr}\t{h}\t{kl}" for i, (h, kr, kl) in enumerate(zip(hip, knee_r, knee_l))]
    return "\n".join(head + rows) + "\n"


def ramp(a, b, n=50):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def test_seated_start_extension_positive_both_sides():
    cols = parse_mot(synthetic_mot(ramp(90, 0), ramp(-90, 0), ramp(-90, 0)))
    for side in ("r", "l"):
        out = classify("SitToStand", cols, side)
        assert out["call"] == "extension_positive"
        assert out["seated_knee_angle_deg"] == -90


def test_seated_end_flexion_positive_for_stand_to_sit():
    cols = parse_mot(synthetic_mot(ramp(0, 90), ramp(0, 90), ramp(0, 90)))
    assert classify("StandToSit", cols, "r")["call"] == "flexion_positive"


def test_hip_anchor_failure_is_not_a_sign():
    cols = parse_mot(synthetic_mot(ramp(10, 0), ramp(-90, 0), ramp(-90, 0)))
    assert classify("SitToStand", cols, "r")["call"] == "anchor_failed"


def test_walking_swing_signs():
    swing = [-60 * math.sin(math.pi * i / 49) ** 2 for i in range(50)]
    cols = parse_mot(synthetic_mot([20] * 50, swing, [-v for v in swing]))
    assert classify("LevelWalking", cols, "r")["call"] == "extension_positive"
    assert classify("LevelWalking", cols, "l")["call"] == "flexion_positive"


def test_small_excursion_is_indeterminate():
    cols = parse_mot(synthetic_mot([20] * 50, ramp(-10, 10), ramp(-10, 10)))
    assert classify("LevelWalking", cols, "r")["call"] == "indeterminate"


def test_verdict_requires_unanimity():
    assert verdict(["extension_positive"] * 3) == "extension_positive"
    assert verdict(["extension_positive", "indeterminate"]) == "unresolved"
    assert verdict(["extension_positive", "flexion_positive"]) == "unresolved"
    assert verdict([]) == "unresolved"


def test_radians_header_rejected():
    with pytest.raises(ValueError):
        parse_mot(synthetic_mot(ramp(90, 0), ramp(-90, 0), ramp(-90, 0), degrees=False))


def test_selection_is_seeded_bounded_and_one_per_task_subject():
    tasks = ["LevelWalking", "StairAscent", "StairDescent", "SlopeAscent",
             "SlopeDescent", "SitToStand", "StandToSit"]
    recs = [f"S{s:03d}/JointAngle/{t}/Trial0{tr}/step0{st}.mot"
            for s in range(1, 11) for t in tasks for tr in (1, 2) for st in (1, 2)]
    a = select(recs, 3, 7)
    assert a == select(recs, 3, 7)
    assert len(a) == 21 and all(r.endswith("Trial01/step01.mot") for r in a)
    assert len({(r.split("/")[0], r.split("/")[2]) for r in a}) == 21
    with pytest.raises(ValueError):
        select(recs, 4, 7)
