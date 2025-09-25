"""Canonical task registry for locomotion datasets.

This module centralises the set of valid task names described in
docs/reference/index.md.  Import helpers from here whenever tooling needs to
validate task identifiers (YAML ranges, datasets, CLI utilities, etc.) so that
new task additions only require editing this single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class TaskRecord:
    """Metadata about a canonical task family."""

    name: str
    category: str  # "phase" or "time"
    description: str
    example_ids: List[str]
    notes: str


_TASKS: Dict[str, TaskRecord] = {
    # Phase-friendly families (normalised to 150-point cycles when events exist)
    "level_walking": TaskRecord(
        name="level_walking",
        category="phase",
        description="Steady overground or treadmill walking",
        example_ids=["level", "level_fast", "level_slow"],
        notes="0% ipsilateral heel strike, 50% contralateral heel strike, 100% next ipsilateral heel strike.",
    ),
    "incline_walking": TaskRecord(
        name="incline_walking",
        category="phase",
        description="Uphill ramp or treadmill walking",
        example_ids=["incline_5deg", "incline_10deg"],
        notes="Positive incline_deg metadata; expect increased hip/knee flexion and trunk lean.",
    ),
    "decline_walking": TaskRecord(
        name="decline_walking",
        category="phase",
        description="Downhill ramp or treadmill walking",
        example_ids=["decline_5deg", "decline_10deg"],
        notes="Negative incline metadata with delayed toe-off; monitor eccentric knee control.",
    ),
    "stair_ascent": TaskRecord(
        name="stair_ascent",
        category="phase",
        description="Ascending standard stairs",
        example_ids=["stair_ascent"],
        notes="0% ipsilateral contact on current step, 100% contact on next step.",
    ),
    "stair_descent": TaskRecord(
        name="stair_descent",
        category="phase",
        description="Descending stairs",
        example_ids=["stair_descent"],
        notes="0% upper-step contact, 100% lower-step contact for ipsilateral foot.",
    ),
    "run": TaskRecord(
        name="run",
        category="phase",
        description="Jogging or running with flight phases",
        example_ids=["run_2_5_m_s", "run_3_0_m_s"],
        notes="0% ipsilateral contact, 100% next ipsilateral contact including flight periods.",
    ),
    "transition": TaskRecord(
        name="transition",
        category="phase",
        description="Stride that transitions between gait modes",
        example_ids=["walk_to_run", "stair_to_walk", "turn"],
        notes="0% departing gait event, 100% first event of target gait; store transition metadata.",
    ),
    "sit_to_stand": TaskRecord(
        name="sit_to_stand",
        category="phase",
        description="Chair or box transfer from seated to standing",
        example_ids=["sit_to_stand"],
        notes="0% seated start, 100% stabilized upright; capture chair height and armrest usage.",
    ),
    "stand_to_sit": TaskRecord(
        name="stand_to_sit",
        category="phase",
        description="Chair or box transfer from standing to seated",
        example_ids=["stand_to_sit"],
        notes="0% descent onset, 100% seated contact; capture chair metadata when available.",
    ),
    "squats": TaskRecord(
        name="squats",
        category="phase",
        description="Loaded or bodyweight squats",
        example_ids=["squats", "squat_down", "squat_up"],
        notes="0% upright, 50% lowest depth, 100% back to upright; include load metadata.",
    ),
    "step_up": TaskRecord(
        name="step_up",
        category="phase",
        description="Step-up repetitions on a box or stair",
        example_ids=["step_up"],
        notes="0% initial foot contact on box, 100% full weight on box; record height and lead_leg.",
    ),
    "step_down": TaskRecord(
        name="step_down",
        category="phase",
        description="Step-down repetitions",
        example_ids=["step_down"],
        notes="Mirrors step_up with lower-surface contact; document height and lead_leg.",
    ),
    "jump": TaskRecord(
        name="jump",
        category="phase",
        description="Hops or jumps with identifiable take-off/landing",
        example_ids=["jump_vertical", "jump_lateral", "hop_single"],
        notes="0% preparatory contact, 50% takeoff, 100% same-foot landing.",
    ),
    "weighted_walk": TaskRecord(
        name="weighted_walk",
        category="phase",
        description="Walking with external load/perturbations",
        example_ids=["level"],
        notes="Treat like level walking when heel strikes exist; include variant metadata.",
    ),
    "dynamic_walk": TaskRecord(
        name="dynamic_walk",
        category="phase",
        description="Walking with dynamic perturbations",
        example_ids=["variant:dynamic"],
        notes="Same phase definition as level walking; document perturbation variant.",
    ),
    "walk_backward": TaskRecord(
        name="walk_backward",
        category="phase",
        description="Backward walking variants",
        example_ids=["walk_backward"],
        notes="Heel-strike definitions flipped; ensure consistent event detection.",
    ),

    # Time-indexed (non-cyclic) families
    "agility_drill": TaskRecord(
        name="agility_drill",
        category="time",
        description="Multi-directional drills without steady gait cycles",
        example_ids=["side_shuffle", "tire_run", "dynamic_walk_high_knees"],
        notes="Capture variant, direction, cadence_hz, and surface metadata.",
    ),
    "cutting": TaskRecord(
        name="cutting",
        category="time",
        description="Athletic cuts with large heading changes",
        example_ids=["cutting_left_fast", "cutting_right_slow"],
        notes="Document direction, approach speed, turn angle, and surface.",
    ),
    "free_walk_episode": TaskRecord(
        name="free_walk_episode",
        category="time",
        description="Episodic or exploratory walking segments",
        example_ids=["meander", "start_stop", "obstacle_walk"],
        notes="Used when heel-strike segmentation is unreliable; include start/end timestamps.",
    ),
    "load_handling": TaskRecord(
        name="load_handling",
        category="time",
        description="Asymmetric lifts, carries, or exchanges",
        example_ids=["lift_weight_25lbs_l_c", "ball_toss_center"],
        notes="Record load, hand/side, pickup and drop-off heights.",
    ),
    "perturbation": TaskRecord(
        name="perturbation",
        category="time",
        description="External pushes, pulls, or cooperative force tasks",
        example_ids=["push_forward", "tug_of_war"],
        notes="Distinguish voluntary vs. reactive responses via metadata (initiated_by, support, etc.).",
    ),
    "balance_pose": TaskRecord(
        name="balance_pose",
        category="time",
        description="Static or quasi-static balance holds",
        example_ids=["poses_single_leg", "poses_wide_stance"],
        notes="Include variant, duration, and support keys.",
    ),
    "functional_task": TaskRecord(
        name="functional_task",
        category="time",
        description="Catch-all for non-cyclic behaviours not covered elsewhere",
        example_ids=["variant:custom"],
        notes="Use sparingly; prefer specific families where possible.",
    ),
}


def get_valid_tasks(category: Optional[str] = None) -> List[str]:
    """Return sorted task names, optionally filtered by category."""

    if category is None:
        return sorted(_TASKS.keys())

    category = category.lower()
    return sorted(record.name for record in _TASKS.values() if record.category == category)


def is_valid_task(task_name: str) -> bool:
    """Return True when *task_name* matches a canonical task."""

    if task_name is None:
        return False
    return task_name in _TASKS


def get_task_record(task_name: str) -> Optional[TaskRecord]:
    """Retrieve the TaskRecord for *task_name*, if present."""

    return _TASKS.get(task_name)


def iter_task_records(category: Optional[str] = None) -> Iterable[TaskRecord]:
    """Iterate over TaskRecord entries, optionally filtered by category."""

    if category is None:
        return _TASKS.values()
    category = category.lower()
    return (record for record in _TASKS.values() if record.category == category)

