"""CORE-07: validation range files against the adopted sign rule B.

Rule B (docs/reference/index.html#signs-and-frames; decision D-UM21-C03-1): joint
angles and internal moments are positive in their named direction (hip flexion,
knee flexion, ankle dorsiflexion); segment angles are counterclockwise with the
person facing +x, so pelvis anterior tilt is negative.

CORE-07 classified every feature from the range values in context. Only the run
pelvis_sagittal_angle_rad band disagrees: it is centred near +0.3 rad at every phase,
which reads as anterior tilt positive under every documented zero, while running
tilts the pelvis forward (negative under rule B). Those four entries are mirrored
exactly (negated, bounds swapped) in the two active profiles only. The sit/stand pelvis entries already read
as rule B and the transition entries are near-symmetric, so they are unchanged. The
band's zero is undocumented: the flip fixes the sign, not the zero.

The docs/datasets/*_validation_ranges.yaml snapshots are records of legacy validation
runs under the old pelvis sign; they must stay byte-identical to the baseline commit.

The baseline tests compare against the commit at which CORE-07 started. A later,
deliberate range change must update BASELINE_COMMIT or MIRRORED in this file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from contributor_tools.common.config_manager import ValidationConfigManager

ROOT = Path(__file__).resolve().parents[1]
RANGE_DIR = ROOT / "contributor_tools" / "validation_ranges"

# Commit at which CORE-07 started (2026-10-31); the range files there predate rule B.
BASELINE_COMMIT = "569ee8f4d7cdf83d96d5f74aa6b65354b4a78da4"

PELVIS = "pelvis_sagittal_angle_rad"
RUN_PELVIS = frozenset(("run", phase, PELVIS) for phase in (0, 25, 50, 75))
PROVENANCE_KEY = "sign_rule_conversions"

# Range files with a 'tasks' mapping, loadable by the validation profile loader.
# impaired_ranges.yaml is a copy-paste template without a 'tasks' mapping and is
# not a loadable profile; it holds hip/knee/ankle joint angles only.
PROFILE_FILES = [
    "default_ranges.yaml",
    "gtech_2024_ranges.yaml",
    "example_custom_ranges.yaml",
    "test_custom_phases.yaml",
    "validation_ranges_with_adduction.yaml",
    "strokepig_ranges.yaml",
]

# Legacy per-dataset snapshots: records of past validation runs under the old pelvis
# sign. They are never converted and must equal the baseline commit byte for byte.
SNAPSHOT_FILES = sorted(
    p.relative_to(ROOT).as_posix()
    for p in (ROOT / "docs" / "datasets").glob("*_validation_ranges.yaml")
)

# Tracked range files at the baseline commit, by repository path.
BASELINE_FILES = (
    [f"contributor_tools/validation_ranges/{n}" for n in PROFILE_FILES
     if n != "strokepig_ranges.yaml"]  # untracked: no baseline exists
    + SNAPSHOT_FILES
)

# (task, phase, feature) entries mirrored to rule B (new = -old, bounds swapped).
# Only the two active profiles; nothing else carries a mirror or provenance note.
MIRRORED: dict[str, frozenset] = {
    "contributor_tools/validation_ranges/default_ranges.yaml": RUN_PELVIS,
    "contributor_tools/validation_ranges/gtech_2024_ranges.yaml": RUN_PELVIS,
}

# validation_ranges_with_adduction.yaml (an unreferenced 2025 UMich-derived file)
# has NaN bounds for incline_walking moments; the profile loader already rejected it
# at the baseline commit, so only the other profiles are load-checked.
LOADABLE_FILES = [n for n in PROFILE_FILES
                  if n != "validation_ranges_with_adduction.yaml"]


def mirror(bounds: dict) -> dict:
    """Exact rule-B mirror of one range: negate and swap bounds."""
    return {"min": -bounds["max"], "max": -bounds["min"]}


def _ranges(config: dict) -> dict:
    out = {}
    for task, section in (config.get("tasks") or {}).items():
        for phase, features in ((section or {}).get("phases") or {}).items():
            for feature, bounds in (features or {}).items():
                out[(task, phase, feature)] = bounds
    return out


def _baseline_bytes(path: str) -> bytes:
    """File bytes at BASELINE_COMMIT; a missing commit or file fails the test."""
    try:
        result = subprocess.run(
            ["git", "show", f"{BASELINE_COMMIT}:{path}"],
            cwd=ROOT, capture_output=True, check=False,
        )
    except FileNotFoundError:
        pytest.fail("git is not available; the CORE-07 baseline cannot be checked")
    if result.returncode != 0:
        pytest.fail(f"cannot read {path} at baseline {BASELINE_COMMIT}: "
                    f"{result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def _baseline_text(path: str) -> str:
    return _baseline_bytes(path).decode()


def test_mirror_is_exact_negation_with_swapped_bounds():
    # Values written in the pre-rule run pelvis band.
    assert mirror({"min": -0.05, "max": 0.67}) == {"min": -0.67, "max": 0.05}
    assert mirror(mirror({"min": -0.3, "max": 1.2})) == {"min": -0.3, "max": 1.2}


def test_every_snapshot_is_covered():
    assert len(SNAPSHOT_FILES) == 20


@pytest.mark.parametrize("path", SNAPSHOT_FILES)
def test_legacy_snapshot_is_byte_identical_to_baseline(path):
    assert path not in MIRRORED
    assert (ROOT / path).read_bytes() == _baseline_bytes(path)


@pytest.mark.parametrize("path", BASELINE_FILES)
def test_range_file_matches_baseline_except_mirrored(path):
    baseline = yaml.safe_load(_baseline_text(path))
    current = yaml.safe_load((ROOT / path).read_text())
    old, new = _ranges(baseline), _ranges(current)
    assert set(new) == set(old), "CORE-07 must not add or remove range entries"
    mirrored = MIRRORED.get(path, frozenset())
    assert mirrored <= set(old)
    for key, bounds in old.items():
        expected = mirror(bounds) if key in mirrored else bounds
        assert new[key] == expected, key
    # Task metadata and top-level keys are unchanged, apart from the provenance note.
    for task, section in baseline["tasks"].items():
        old_meta = {k: v for k, v in section.items() if k != "phases"}
        assert {k: v for k, v in current["tasks"][task].items() if k != "phases"} == old_meta
    old_top = {k: v for k, v in baseline.items() if k != "tasks"}
    new_top = {k: v for k, v in current.items() if k not in ("tasks", PROVENANCE_KEY)}
    assert new_top == old_top
    if mirrored:
        (note,) = current[PROVENANCE_KEY]
        assert note["task"] == "CORE-07" and "D-UM21-C03-1" in note["rule"]
        assert "undocumented" in note["zero"]
    else:
        assert PROVENANCE_KEY not in current


@pytest.mark.parametrize("path", BASELINE_FILES)
def test_only_mirrored_bound_lines_and_provenance_differ_textually(path):
    """Every other byte is unchanged: remove the inserted note, then compare lines."""
    old = _baseline_text(path).split("\n")
    new = (ROOT / path).read_bytes().decode().split("\n")
    if PROVENANCE_KEY + ":" in new:
        start = new.index(PROVENANCE_KEY + ":")
        end = new.index("tasks:")
        assert old[start] == "tasks:", "note must be inserted directly before 'tasks:'"
        new = new[:start] + new[end:]
    assert len(new) == len(old)
    changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
    assert len(changed) == 2 * len(MIRRORED.get(path, frozenset()))
    for i in changed:
        assert old[i].strip().split(":")[0] in {"min", "max"}
        assert old[i - (1 if old[i].strip().startswith("min") else 2)].strip() == PELVIS + ":"


def test_run_pelvis_band_now_reads_anterior_negative():
    """After the mirror the run band centres near -0.3 rad (forward tilt, rule B)."""
    for name in ("default_ranges.yaml", "gtech_2024_ranges.yaml"):
        phases = yaml.safe_load((RANGE_DIR / name).read_text())["tasks"]["run"]["phases"]
        centres = [(phases[p][PELVIS]["min"] + phases[p][PELVIS]["max"]) / 2
                   for p in (0, 25, 50, 75)]
        assert max(centres) < -0.17, name


@pytest.mark.parametrize("name", LOADABLE_FILES)
def test_range_file_loads_through_profile_loader(name):
    manager = ValidationConfigManager(RANGE_DIR / name)
    assert manager.get_tasks()


# Independently known sagittal signs, read from the bounds as written. Each row is
# (task, phase, feature, test, physical reason under rule B).
SIGN_SIGNATURES = [
    ("level_walking", 75, "knee_flexion_angle_ipsi_rad", "min>0",
     "knee flexed in swing; knee flexion positive"),
    ("sit_to_stand", 0, "hip_flexion_angle_ipsi_rad", "min>0",
     "seated hip flexed; hip flexion positive"),
    ("sit_to_stand", 0, "thigh_sagittal_angle_ipsi_rad", "min>0",
     "seated thigh points forward; knee ahead of hip is counterclockwise"),
    ("run", 50, "foot_sagittal_angle_ipsi_rad", "max<0",
     "toes down after toe-off; toes up is counterclockwise"),
    ("level_walking", 50, "ankle_dorsiflexion_moment_ipsi_Nm_kg", "mid<0",
     "push-off plantarflexor moment; ankle dorsiflexor positive"),
    ("decline_walking", 15, "knee_flexion_moment_ipsi_Nm_kg", "mid<0",
     "stance knee extensor moment; knee flexor positive"),
    ("level_walking", 0, "hip_flexion_moment_ipsi_Nm_kg", "mid<0",
     "early-stance hip extensor moment; hip flexor positive"),
    ("level_walking", 15, "grf_anterior_ipsi_BW", "mid<0",
     "braking force points backward; walking direction positive"),
]


@pytest.mark.parametrize("name", ["default_ranges.yaml", "gtech_2024_ranges.yaml"])
@pytest.mark.parametrize("task,phase,feature,check,reason", SIGN_SIGNATURES)
def test_rule_b_sign_signatures(name, task, phase, feature, check, reason):
    config = yaml.safe_load((RANGE_DIR / name).read_text())
    bounds = config["tasks"][task]["phases"][phase][feature]
    value = {"min>0": bounds["min"], "max<0": bounds["max"],
             "mid<0": (bounds["min"] + bounds["max"]) / 2}[check]
    assert (value > 0) if check.endswith(">0") else (value < 0), reason
