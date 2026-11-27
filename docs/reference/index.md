---
title: Data contract and quality evidence
---

# Data contract and quality evidence

LocoHub releases standardize files and preserve evidence about their origin and processing. Researchers consume these files directly. The current contract is **version 2.0**; historical files in the catalog may follow older conventions and remain **legacy / unreviewed** until their identities and provenance have been established.

## Observation identity

An observation is the unit whose samples must remain together during validation and filtering. Its identity is the combination of:

| Column | Meaning |
|--------|---------|
| `subject` | Participant identifier scoped consistently across the dataset. |
| `source_recording_id` | Original recording or trial identity, preserved across derived observations. |
| `observation_id` | Stable identifier for a cycle, transfer, ensemble curve, or continuous recording. |
| `reference_side` | `left`, `right`, or `none`; identifies the limb defining ipsilateral signals when applicable. Source ensembles may retain `unknown`, with a recorded warning. |

These fields must be explicit, nonempty, and traceable to the source. A legacy `step` label alone does not establish observation identity. Row order and blocks of 150 are not substitutes for source identities. Do not invent a recording identity merely to pass validation.

`observation_type` declares what the observation represents:

| Value | Meaning and analysis implication |
|-------|----------------------------------|
| `individual_cycle` | One segmented cycle. Repeated cycles from a participant are not independent participants. |
| `transfer` | One segmented transfer or action with documented boundaries. |
| `ensemble_curve` | An aggregate curve. Do not count it as an individual stride or treat its samples as independent measurements. |
| `continuous_recording` | A continuous time observation with increasing timestamps. |

Bilateral views may share a source recording. Keep related observations together when defining training/test splits or assessing participant-level uncertainty.

## Metadata

Every observation requires `task`, `task_id`, and `task_info` alongside its identity and observation type. Metadata must remain constant within the observation.

- `task` identifies the activity family, for example `level_walking` or `stair_ascent`.
- `task_id` identifies a specific protocol variant within the dataset.
- `task_info` is a JSON object, serialized as a JSON string in CSV/Parquet when needed: `{"speed_m_s":1.2,"incline_deg":0,"treadmill":true}`.
- Optional `subject_metadata` uses the same JSON representation. Preserve unknown demographic values as unknown; do not infer them.
- Optional `source_start_time_s` and `source_end_time_s` are supplied together and remain constant within the observation. Known boundaries must be finite, with end greater than start. Transfers and ensembles may preserve both boundaries as unknown; one unknown boundary alone is invalid. Never invent durations for normalized source curves.

Older releases may contain comma-separated `key:value` strings. That legacy representation requires explicit conversion and review before a version 2.0 release. Missing values are not zero and are not evidence of a negative finding.

Task definitions live in `contributor_tools/common/task_registry.py`; variable definitions live in `contributor_tools/common/feature_constants.py`. These are internal contributor tools, not a public analysis SDK. Document population and assistance conditions alongside task metadata; a matching task name alone does not make studies comparable.

## Sample indices

| Mode | Index | Required structure |
|------|-------|--------------------|
| Phase | `phase_ipsi` | Exactly 150 distinct samples matching the inclusive grid `linspace(0, 100, 150)` when ordered within each observation. |
| Ensemble | `phase_ipsi` | The same grid, with `observation_type="ensemble_curve"`. |
| Time | `time_s` | At least two distinct finite timestamps, sorted within each observation for analysis. |

The phase grid includes both 0% and 100%; these endpoints describe consecutive boundaries. Event definitions, interpolation, and original durations belong in provenance. For non-gait actions, document what the start and end events mean. Phase normalization changes the sampling representation and does not retain all original time samples.

Time mode supports recordings without defensible cycle boundaries. A continuous recording must not be relabeled as an individual cycle merely to use phase tooling. File rows may be interleaved; checks sort by index within each identity. Phase indices must be unique within an observation; time observations must not repeat timestamps.

## Signals, units, and missing values

Use explicit column names with unit and side tokens. Examples:

| Signal | Example column | Stored unit |
|--------|----------------|-------------|
| Joint angle | `knee_flexion_angle_ipsi_rad` | radians |
| Angular velocity | `knee_flexion_velocity_ipsi_rad_s` | radians/second |
| Mass-normalized moment | `hip_flexion_moment_ipsi_Nm_kg` | Nm/kg |
| Ground reaction force | `grf_vertical_ipsi_BW` | body weights |
| Center of pressure | `cop_anterior_ipsi_m` | meters |
| Segment orientation | `pelvis_sagittal_angle_rad` | radians |

`ipsi` is the reference limb and `contra` is the opposite limb. Contralateral event timing must come from the recorded protocol or a documented derivation; it is not universally a 50% shift. Preserve whether moments represent total, biological, or assistance moments. Signs follow [Signs and frames](#signs-and-frames). Record the source coordinate frame, signs, normalization mass, force-plate assignment, filtering, and derivative method in conversion provenance.

Unavailable signals stay missing. Zero-filled missing features can create false evidence that a signal was measured. A column existing in a file does not establish coverage across every task or observation. Inspect finite-value coverage and required/optional signal declarations before analysis.

UMich 2021 and Georgia Tech 2021 handle low force differently. UMich 2021 writes a force sample under 20 N as 0 body weights, because it has no independent stance timing and cannot tell a lifted foot from a plate that missed a loaded foot. Georgia Tech 2021 marks force missing when stance is expected but the plate reads under 20 N. A 0 in UMich 2021 force means under 20 N, not a measured zero.

## Signs and frames

LocoHub uses one sign rule for every dataset. This section is the authoritative statement; other pages refer to it.

*Changed on 31 October 2026. The rule adopted on 30 October 2026 made every sagittal signal counterclockwise-positive, so knee flexion and the knee flexor moment were negative. The current rule keeps segment angles counterclockwise and makes joint angles and moments positive in their named direction.*

**Decided (current rule, 31 October 2026; sideways force 30 October 2026).**

- **Frame.** View the person from their right side, facing right. +x is the walking direction, +y is up (opposite gravity), and +z = x × y points to the person's right side, out of the page. Both legs use this frame for sagittal signals.
- **Side-view plane (24 November 2026).** Sagittal angles are measured in body-fixed vertical planes, not along the lab or walking direction. Each leg has its own plane: the vertical plane containing that leg's forward direction, taken perpendicular to the knee's flexion axis; that leg's thigh, shank and foot are all measured in it. The pelvis (and trunk) use the pelvis forward direction (mid-PSIS to mid-ASIS, horizontal component). +x in each plane is that segment group's forward direction, +y is up and +z = x × y. This keeps every sagittal angle defined while turning or walking in any direction; joint angles remain differences of segment angles.
- **Segment angles** (pelvis, trunk, thigh, shank, foot) are positive counterclockwise about +z. Pelvis anterior tilt is therefore negative, and trunk leaning back is positive.
- **Joint angles** are positive in their named direction: hip flexion, knee flexion, ankle dorsiflexion. Their velocities and accelerations take the same sign.
- **Moments** are internal (net muscle and tissue) moments acting on the distal segment, as produced by inverse dynamics, and are positive in their named direction: hip flexor, knee flexor, ankle dorsiflexor (ankle plantarflexor negative). An external moment is the negative of the internal moment.
- **Power** is moment × joint angular velocity, both in this convention. Generation is positive; absorption is negative. LocoHub computes power from the published moment and its own joint speeds (24 November 2026), so power, moments and angles are exactly consistent; source power values are not carried over.
- **Sideways force and centre of pressure** are positive outward for each leg: toward +z for the right leg and toward −z for the left leg (mirrored), matching the name `lateral`.
- **Zero references (23 November 2026).** Joint angles are differences of segment angles: hip = thigh − pelvis, knee = thigh − shank, ankle = foot − shank. Segment angles are measured against gravity: thigh and shank from straight down, foot (heel to toe) and pelvis (PSIS to ASIS) from forward horizontal. Defining the segment angles therefore defines the joint angles; there is no separate joint zero such as a static pose or a model's neutral position. Because the PSIS-to-ASIS line normally tilts forward, a person standing straight reads about +10° hip flexion (confirmed 24 November 2026; kept by design).
- **Foot-flat zero (27 November 2026).** In the datasets that carry it (GT23 v12, GT21 v2, UM21 v6), each person's foot angle is shifted so that a foot lying flat on level ground reads 0: the shift is the median, over that person's matched level-walking strides, of the stride's median foot angle at 20 to 35 percent of the stride. The ankle angle shifts by the same amount (ankle = foot − shank), the foot-frame centre of pressure (forward and up) is turned by the same angle in the leg plane, and every other angle, velocity, moment, power and force is unchanged. People with no matched level-walking stride are left unshifted and listed in the dataset's limitations.
- **Centre of pressure frame (23 November 2026; plane clarified 24 November 2026).** The centre of pressure is expressed in the ankle frame, which moves with the foot: within that leg's side-view plane, the foot direction is the leg-plane direction rotated by the foot angle (foot = shank + ankle). The origin is 100 mm forward of the ankle joint centre along that foot direction; forward is along it, up is perpendicular to it within the plane, and sideways is perpendicular to the leg plane, outward from that leg. Toe-out therefore appears as a sideways offset. Ground reaction force stays in the ground frame above.

**LocoHub definitions.** These follow from the decided rule and existing usage; they are not separate decisions.

- **Composition.** Segment and joint angles are related by thigh = pelvis + hip, shank = thigh − knee, foot = shank + ankle. Under the decided zero references these hold exactly. Files converted before 23 November 2026 may use another zero (for example subtraction of a static pose); each dataset's notes say so until it is reconverted. The trunk zero is not yet defined.
- **Ground reaction force** is the force applied by the ground to the person.

!!! warning "Pelvis anterior tilt is negative; knee flexion is positive"
    Segment angles follow the counterclockwise rule, so `pelvis_sagittal_angle_rad` is negative for anterior tilt, although clinical reports often call anterior tilt positive. Joint columns are positive in their named direction: `knee_flexion_angle_*` is positive when the knee flexes (60° of flexion is +1.05 rad) and `knee_flexion_moment_*` is positive for an internal knee flexor moment. OpenSim gait2392 `knee_angle` is flexion-negative, so LocoHub knee = −`knee_angle`.

![Side view of a person facing right with +x forward, +y up and +z out of the page. Curved arrows show the positive direction. Segment angles, counterclockwise: pelvis posterior tilt, trunk leaning back, thigh and shank with the distal end forward, foot toes up. Joint angles, named direction: hip flexion, knee flexion (a clockwise arrow), ankle dorsiflexion.](../assets/sagittal-signs.svg)

| Signal family | Columns | Positive direction | Physical definition | gait2392 equivalent |
|---|---|---|---|---|
| Pelvis tilt | `pelvis_sagittal_angle_rad` | Posterior tilt; **anterior tilt negative** | Angle of the PSIS-to-ASIS line; increases when the front of the pelvis rises. Zero: forward horizontal | `pelvis_tilt` |
| Trunk | `trunk_sagittal_angle_rad` | Leaning back; leaning forward negative | Orientation of the trunk long axis; increases when the shoulders move backward. Zero not yet defined | `pelvis_tilt` + `lumbar_extension` (same sense, up to zero offsets) |
| Thigh | `thigh_sagittal_angle_*_rad` | Knee ahead of hip | Thigh long axis. Zero: straight down | `pelvis_tilt` + `hip_flexion_*` (same sense, up to zero offsets) |
| Shank | `shank_sagittal_angle_*_rad` | Ankle ahead of knee | Shank long axis. Zero: straight down | thigh + `knee_angle_*` (same sense, up to zero offsets) |
| Foot | `foot_sagittal_angle_*_rad` | Toes up | Heel-to-toe line. Zero: forward horizontal | shank + `ankle_angle_*` (same sense, up to zero offsets) |
| Hip angle | `hip_flexion_angle_*_rad` | Flexion | Thigh rotates forward relative to the pelvis | `hip_flexion_r`, `hip_flexion_l` |
| Knee angle | `knee_flexion_angle_*_rad` | Flexion | Shank rotates backward relative to the thigh; a straight knee is 0 | −`knee_angle_r`, −`knee_angle_l` (gait2392 knee is flexion-negative) |
| Ankle angle | `ankle_dorsiflexion_angle_*_rad` | Dorsiflexion | Foot rotates toes-up relative to the shank | `ankle_angle_r`, `ankle_angle_l` |
| Angular velocity and acceleration | `*_velocity_*_rad_s`, `*_acceleration_*_rad_s2` | Same as the angle | First and second time derivatives of the angle | OpenSim coordinate speed and acceleration (negated for the knee) |
| Joint moments: total, biological, assistance | `*_moment_*`, `*_biological_moment_*`, `*_assistance_moment_*` | Named direction: hip flexor, knee flexor, ankle dorsiflexor (ankle plantarflexor negative) | Internal moment on the distal segment; total = biological + assistance | Inverse-dynamics generalized force: `hip_flexion_r_moment`, −`knee_angle_r_moment`, `ankle_angle_r_moment` |
| Joint power | Dataset-specific power columns, where supplied | Generation | Internal moment × joint angular velocity | ID generalized force × coordinate speed (unchanged by the knee negation) |
| Vertical ground reaction force | `grf_vertical_*` | Up (+y) | Force applied by the ground to the person (LocoHub definition); positive while the foot is supported | Ground-frame force y |
| Forward ground reaction force | `grf_anterior_*` | Walking direction (+x) | Negative while braking, positive while propelling | Ground-frame force x |
| Sideways ground reaction force | `grf_lateral_*` | Outward from that leg: +z for the right leg, −z for the left | Pushes the foot away from the body midline | Ground-frame force z (right leg), −z (left leg) |
| Centre of pressure | `cop_anterior_*`, `cop_vertical_*`, `cop_lateral_*` | Forward along the foot, up from the foot, outward from that leg | Position of the centre of pressure in the foot's moving frame; origin 100 mm forward of the ankle joint centre along the heel-to-toe direction | Ground-frame point moved to the foot frame (needs the ankle centre and foot orientation) |
| Frontal and transverse signals | `*_adduction_*`, `*_rotation_*`, `*_frontal_*`, `*_transverse_*` | **Not yet adopted** | Files keep the source sign stated in each dataset's notes; do not combine across datasets until a rule is adopted | — |

The rule applies to files converted after it was adopted. Downloads made earlier may use other signs, for example pelvis anterior tilt positive. Each dataset page states what its current files use; those files remain legacy until reconverted.

## Quality states

| State | Interpretation |
|-------|----------------|
| `passed` | Applicable checks ran and their conditions were satisfied. |
| `failed` | Applicable checks ran and at least one condition was not satisfied. |
| `missing` | Signal data were unavailable; required and optional signals are identified separately. |
| `unchecked` | No applicable profile/check ran, or no mandatory checks were configured. |
| `invalid` | Structural or nonfinite data prevented a trustworthy result. |

Structural integrity, signal coverage, and biomechanical profile conformance are separate evidence. A profile only checks its configured features and phases or time ranges. It does not establish correct source measurements, coordinate transforms, event detection, or clinical applicability.

A profile declares its intended tasks, observation types, required/optional features, thresholds, and supporting rationale. Empirical or manually tuned ranges must be described as such. Call them literature-derived only when traceable sources support the rules. Ensemble curves need a profile that explicitly includes `ensemble_curve`.

Profiles can restrict applicability using recorded metadata such as population or assistance condition. Missing or mismatched applicability metadata leaves an observation unchecked. Profiles without those restrictions disclose that limitation. Whole-waveform diagnostics record missing and infinite values, constant signals, and the largest adjacent-sample change. Optional `waveform_ranges` check bounds across every sample; a configured `max_abs_step` produces a review warning, not an automatic exclusion. See the contributor contract guide in the repository for profile syntax.

No applicable profile means **unchecked**, not passed. A dataset with unchecked observations may retain full converted data and evidence, but those observations are not eligible for the profile-filtered artifact. A low pass rate warrants investigation of both conversion and applicability; increasing thresholds is not itself a correction.

## Release evidence

A prepared release directory contains these artifacts:

| Artifact | Purpose |
|----------|---------|
| `full.parquet` | Byte-identical copy of the admitted converted input file. |
| `filtered.parquet` | Whole observations eligible under the specified profile; may be empty. |
| `quality.json` | Structural checks, signal coverage, observation states, and reasons. |
| `exclusions.parquet` | Identities and reasons for observations excluded from the filtered artifact. |
| `manifest.json` | Release identity, contract version, artifact hashes, counts, and provenance references. |
| `manifest.sha256` | Checksum of the manifest itself. |
| `provenance.json` | Source identifiers/hashes, converter revision, contributor review, and processing notes. |
| `profile.yaml` | Snapshot of the rule profile, when one was supplied. |
| `README.md` | Generated data card describing counts, artifacts, and limitations. |

**Full converted** does not mean original raw data. **Profile-filtered** does not mean universally clean. Report both the selected variant and the profile used. Historical `clean`/`dirty` filenames do not substitute for this evidence.

Building a bundle records checks and contributor review; it does not automatically grant independent maintainer approval. Source URIs and hashes without accessible local source files remain contributor declarations. Reconcile release artifacts with the original study and inspect limitations before publication.

The interactive tuner saves draft profiles with a rationale and an audit sidecar recording hashes, changes, and decision counts. Draft profiles cannot be used to publish a release bundle; review the rules and their evidence before recording an approved profile.

New release directories are immutable: changes to data, profiles, or provenance produce a new directory and identifier. Existing catalog downloads remain legacy / unreviewed unless the corresponding files are explicitly reprocessed and reviewed. This documentation update does not revalidate them.

## Related workflows

- [Load and inspect the complete example](../tutorials/index.md)
- [Find datasets](../datasets/index.md)
- [Prepare a release](../contributing/index.md)
- [Review a release](../maintainers/index.md)
