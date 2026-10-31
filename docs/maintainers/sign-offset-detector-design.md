# Sagittal sign and offset detector (CORE-04)

Status: design and synthetic fixtures only. No research dataset has been run.
Module: `contributor_tools/common/sign_offset_detector.py`.
Tests: `tests/test_sign_offset_detector.py` (synthetic).

## Purpose and limits

One dataset-agnostic step that infers, for each sagittal channel of one leg,
the sign that maps the source onto the LocoHub convention, and estimates any
zero offset. The goal is to remove per-dataset sign code from converters.

The target is rule B (decision D-UM21-C03-1, changed from C to B by José,
task DOC-03). The person faces right (+x walking, +y up, +z the person's right
side, out of the page).

- Segment angles (pelvis, thigh, shank, foot, trunk) are counterclockwise
  positive, so pelvis anterior tilt is negative.
- Joint angles and internal moments are positive in their named direction.

In the code, joint = `JOINT_CCW` × (distal − proximal segment), and internal
moment = `JOINT_CCW` × (the counterclockwise moment on the distal segment).
`JOINT_CCW` is +1 for the hip and ankle and −1 for the knee: knee flexion
swings the shank back, which is clockwise.

| Channel | Positive under rule B |
| --- | --- |
| pelvis tilt | posterior tilt (anterior tilt negative) |
| thigh / shank segment | distal end ahead of proximal end |
| foot segment | toes up |
| hip angle | flexion |
| knee angle | flexion |
| ankle angle | dorsiflexion |
| hip / knee / ankle moment (internal, on the distal segment) | flexor / flexor / dorsiflexor |
| joint power | moment x joint angular velocity; generation positive (the same under B and C) |

Rules inherited from AGENTS.md:

- A sign is applied only when independent physical evidence is unambiguous:
  at least two agreeing tests from different evidence families, never a single
  test. Every application is logged with the tests that supported it.
- Offsets are estimated with a confidence interval and flagged for review.
  They are never applied.
- The detector abstains when evidence is weak. Abstaining is a valid outcome.
- Agreement with "typical gait waveforms" is circular. It is weak evidence:
  it never applies a sign. Reference-range pass rates are never used.
- Thresholds are fixed a priori (module `DEFAULTS`, echoed into every report).
  They were not tuned on research data. If a pilot shows that a threshold is
  wrong, the change is logged with its reason. It is not adjusted until the
  pilot agrees.

## Inputs

The detector processes one leg per call. Arrays are `(units, samples)`. A unit
is one stride or cycle, or one fixed block of a continuous recording. Angles
are in rad, moments in N·m/kg and power in W/kg. Positions, CoP and GRF are
`(units, samples, 2)` with components `[forward, up]` in the target frame, and
the GRF acts on the body.

| Input | Needed by |
| --- | --- |
| source channels (logical names: `pelvis_tilt`, `thigh_angle`, `shank_angle`, `foot_angle`, `<joint>_angle`, `<joint>_moment`, `<joint>_power`) | everything |
| marker points (pelvis rear/front, hip, knee, ankle, heel, toe) projected to the sagittal plane | reference-angle test; joint positions for the lever arm |
| vertical GRF on the body, with its unit declared by the adapter (`grf_unit` = `N_per_kg`, `BW` or `N`; optional `body_mass_kg` for N). The declared unit is checked against the data: the median per-unit peak must lie within 0.4–4 body weights in that unit (for N, the declared mass, or a 30–200 kg band when none is declared; no mass is invented). If it fails, every force-plate test abstains (`grf_unit_check`) | stance mask (above 5% of unit peak and above a contact floor of 0.5 N/kg, 0.05 BW or 20 N; no mass needed). An undeclared unit means no stance mask, so the force-plate tests abstain unless a `stance` mask is passed |
| CoP + GRF (anterior optional) + joint centres | lever-arm test |
| `dt` (time data) | power slope magnitude (phase data give sign only) |
| `task` | knee hinge, late-stance and plate-frame checks (abstain or "unknown" outside their task sets) |
| `unit_durations_s` (seconds per unit) | inverse-dynamics-light hip test (accelerations need time) |
| source documentation statements (channel, sign, citation) | conflict check only |
| cited template waveform | weak hint only |

Marker geometry: `forward_axis` takes the median horizontal heel-to-toe vector,
and `project_sagittal` projects onto (forward, up). Given a correct up vector,
the resulting angles do not depend on lab heading or handedness. For example,
GT21 faces lab −Z, and a mirrored lab gives the same angles. An inverted up
vector mirrors every angle. `marker_reference_angles` therefore requires every
upper point (pelvis markers, hip, knee) to be above the foot point (the ankle,
else the heel, else the toe) in at least 90% of the visible frames, and raises
otherwise. Frames with a missing marker are not judged. A failure needs only
one visible frame, but a pass needs at least 50 visible frames (5 units × 10
samples); with fewer, the check is "unknown". The visible-frame count is
reported in `marker_checks`.
This order holds in walking, stairs, deep squats and sit-to-stand, whereas "hip
above knee" fails in a deep squat. When there is no foot point or no upper
point (for example pelvis-only markers), the check is "unknown" and the marker
references are not used. Each angle returned by `marker_reference_angles` is a `MarkerAngle` array that
carries its own vertical-order result. A dict copy, a key selection or a slice
therefore keeps the guard. `detect_leg` checks it on input and drops any marker
reference whose check did not pass, recording this under `marker_checks`.
Only an explicit `np.asarray` conversion removes the guard. A plain array
passed as a reference is treated as a caller-asserted independent reference in
the target frame. The forward axis must be computed per
straight pass (or per unit) for overground out-and-back or turning trials. One
axis for the whole trial mirrors the return passes; the units then split and
the test abstains, which is safe but loses evidence.

Units: an angle channel whose |value| exceeds 2π is refused (`units_check`).
Such values are evidently degrees, and no test runs on that channel. The
detector does not convert the units. The reference-angle test also abstains
when the median |slope| falls outside [0.1, 10], for example small-range
channels stored in degrees. Marker angles carry the zero of their own
definition (for example, the PSIS–ASIS line for the pelvis), so offsets against
them are differences in zero definition, not errors.

## Tests and decision rules

`sign` means target ≈ sign × source. Each test votes once per unit, then
decides only if at least `min_units` = 5 units vote and at least 90% of the
voting units agree. Otherwise it abstains and records the reason.

| Test | Channels | Evidence class | Unit vote | Abstains when |
| --- | --- | --- | --- | --- |
| Reference angle (markers or independent segments) | any angle or segment | strong | sign of slope of source on reference, if \|r\| ≥ 0.8. Source and reference are each re-expressed within ±180° of their robust circular centre first | no reference; low r (e.g. pelvis excursion within marker noise); split units; \|value\| > 2π; median \|slope\| outside [0.1, 10] |
| Plate frame check (prerequisite for the lever arm) | — | gate | CoP progression: stance (CoP − ankle) forward moves heel → toe (last-quarter mean > first-quarter mean). Braking/propulsion: anterior GRF < 0 in the first third and > 0 in the last third of stance. Both run only for forward heel-strike walking (level, incline, decline). CoP within foot (any task): stance CoP forward position lies within the heel–toe marker span ±3 cm in at least 80% of a unit's stance samples. 90% of at least 5 units must agree for pass or fail | progression/braking: any other task, including `None`, backward walking, running and stair descent; no ankle positions; no anterior GRF. CoP within foot: no heel/toe markers. Each such check is unknown |
| Lever arm, quasi-static: M = −`JOINT_CCW` × (r × F)_z, r = CoP − joint, stance only (knee flexor positive) | ankle / knee / hip moment | ankle strong only if CoP progression and CoP within foot both pass, otherwise moderate; knee moderate; hip weak (inertia and segment weight ignored; UM21-C03: hip right in only 8/16 legs) | sign of slope, if \|r\| ≥ 0.6 | no force plate; no joint centres; vertical GRF not upward; CoP progression fails (forward axis reversed); CoP within foot fails (registration). If braking/propulsion fails, the anterior GRF is dropped (vertical-only) |
| Late-stance plantarflexor: after heel-off the CoP is under the forefoot, ahead of the ankle | ankle moment | moderate | mean over the second half of the longest stance run; sign negative ⇒ +1, if \|mean\| ≥ 25% of unit peak | no stance mask; task not forward progression (e.g. backward walking) |
| Knee hinge asymmetry: little hyperextension, so the large walking excursion is flexion (positive under rule B) | knee angle | moderate | excursion on one side of the median ≥ 2× the other, range ≥ 0.5 rad; larger excursion on the positive side ⇒ +1 | task not walking (duty-factor assumption); small range |
| Segment chain: distal = proximal + `JOINT_CCW` × joint (thigh = pelvis + hip, shank = thigh − knee, foot = shank + ankle) | relative signs of three channels | strong relation | best of 4 sign patterns (offset removed) has RMS ≤ 0.5 × second best | any member missing; no clear best |
| Power identity: power ∝ moment × dq/dt | product sign of (moment, angle, power) | strong relation | sign of r if \|r\| ≥ 0.8 | any member missing |
| Template correlation (cited waveform) | any | weak | sign of r if \|r\| ≥ 0.5 | no template |
| Documentation (README, paper, model file) | any | documentation | the stated sign | not supplied |
| 180° branch screen | angles | screening | runs more than 100° (wrapped) from the channel's robust circular centre that begin or end with a one-sample jump above 90°, or fill a whole unit. Continuous excursions (deep knee flexion) are reported as `far_from_median_frames` and not masked. 360° wraps are re-expressed within ±180° of that centre in the fitting copy | n/a |

Cardan triples: `alternate_branch_frames` flags \|c2\| > 90°.
`reexpress_alternate` gives (c1 + 180, 180 − c2, c3 + 180), the same rotation,
as in UM21-C03. It is proposed and never applied. On sagittal channels,
branch frames are masked from every fit, and 360° wraps are re-expressed only
in the fitting copy, since they are the same angle. The source values are not
changed, and the runs (unit, start, stop) are reported.

## Combining evidence into a verdict

Scores are strong = 2, moderate = 1, and weak or documentation = 0. Every
test belongs to one evidence family.

| Test | Family under "fine" (default, by failure mode) | Family under "coarse" (option only) |
| --- | --- | --- |
| reference angle (markers or segments), derived from the segment chain | marker geometry | kinematic |
| knee hinge asymmetry | joint anatomy | kinematic |
| lever arm; inverse-dynamics-light hip (phase 3) | plate geometry | force plate |
| late-stance plantarflexor; hip stance extension, ankle push-off plantarflexion, hip moment timing, power timing (phase 3) | plate timing | force plate |
| derived from the power identity | power identity | power identity |
| template, documentation, unclassified | none | none |

1. If moderate or strong tests disagree, the verdict is `conflict`.
2. If documentation disagrees with the leading data sign, the verdict is
   `conflict`. Documentation can block but never apply (GT24 ankle README
   versus data).
3. **No sign is ever applied from a single test.** `apply` needs agreeing
   moderate or strong tests from at least two different families
   (`min_families` = 2), with a score of 2 or more. Confidence is `high` at a
   score of 4 or more with no weak dissent, and `medium` otherwise.
4. Otherwise any moderate or strong agreement gives `suggest`: flagged, not
   applied. This covers one strong test, or several tests from one family.
   Confidence is `medium` at a score of 2 or more, and `low` otherwise.
5. If nothing decided, or only weak tests did, the verdict is `abstain`. A
   single weak sign is recorded as `weak_hint`.
6. If the reference-angle offset exceeds π/2 in magnitude, the verdict is
   `conflict` ("half-turn offset: branch or zero-definition mismatch"),
   whatever the sign evidence says.
7. **Conflicts are sticky.** No later step, including propagation, may
   replace a `conflict` verdict. A conflicted channel is neither an anchor
   nor a target for derivation.

**What reaches apply.** D-CORE-04-1 was answered C: a sign is applied
automatically when two failure-mode families agree, and phase 3 added
cross-family tests (next section).

Under the default grouping, the synthetic fixture has markers, plates and
stride durations. Its injected source has pelvis anterior tilt positive, knee
flexion negative, knee extensor moment positive and power stored as −(M·ω).
It applies:

- knee angle, from marker geometry + joint anatomy;
- ankle angle, from marker geometry + plate timing;
- hip moment, from plate geometry (ID-light) + plate timing;
- ankle moment, from plate geometry + plate timing;
- ankle power, from the power identity + plate timing.

The fixture's hip is a pure cosine, so it is half-cycle ambiguous and stays
`suggest`; a hip with a second harmonic applies. Pelvis tilt, knee moment, hip
power and knee power stay `suggest` or `abstain` (see the coverage table).
Under the `coarse` option, only the ankle angle applies in this fixture.

Relations (chain, power) are resolved in two steps.

1. **Contradictions.** Every decided relation whose members all carry a sign
   (`apply` or `suggest`) is checked against one snapshot taken before any
   change. Every member of every contradicting relation becomes `conflict`.
2. **Derivation, one hop.** Derivation reads a snapshot taken after step 1.
   When every other member of a relation is still `apply` from direct
   evidence, the remaining member gets derived evidence with the relation's
   strength, and its verdict is recomputed. A channel put in conflict by step
   1 is neither an anchor nor a target.

Because both steps read snapshots, the result does not depend on relation
order. Synthetic tests check both orders and two contradicting relations that
share a member. Derived evidence is never used to derive further. A derived
sign is a single test of its relation's family, so on its own it only gives
`suggest`.

Expected consequences, all of them deliberate:

- Knee moment with force plates is usually `suggest` (lever arm moderate),
  and hip moment usually `abstain`. Upgrading either needs a stronger
  independent test, such as full planar inverse dynamics. That would need
  segment inertia and therefore mass, which must not be invented. It is out of
  scope here.
- The power identity mainly resolves how the power column is stored. One
  example is UM21 layout 1, stored as −(M·ω). It resolves a moment sign only
  when the angle and the power column are both anchored.
- Pelvis tilt is decided only by markers or by the chain. GT23 and GT24 have no
  pelvis channel, so it is absent there.

## Cross-family tests (phase 3, D-CORE-04-1 = C)

These tests give more channels a second, independent family. Every threshold
was fixed before any data were seen. Every test abstains outside its task set,
without a stance mask, and when the plate-to-leg gate fails. Strength is
moderate unless stated otherwise.

**Plate-to-leg gate (`leg_assignment_check`).** In walking, running and stair
ascent, the knee's largest excursion from its median is the swing flexion
peak. If that peak falls inside this plate's stance in at least 90% of 5 or
more units, the plate (or the stride units) belongs to the other leg: the
result is `fail`, and every plate-timed test abstains. If the peak is in swing
in 90% of units, the result is `pass`; otherwise `unknown`, and the tests run.
The gate uses |knee − median|, so the knee channel's own sign does not matter.
Task set: level, incline and decline walking, stair ascent, running. Units with no
stance sample (for example, GRF withheld by the adapter) do not vote; they are
counted as `units_without_stance` (fix from the GT21 pilot, 2026-10-31).

**Plate-timed tests (family plate timing).** Each uses only the vertical-GRF
stance mask and the channel itself: no CoP, no joint positions, no frame. That
makes them independent of marker geometry (up vector, projection, labels) and
of plate geometry (forward axis, CoP registration).

| Test | Channel | Physics | Rule (rule B) | Threshold | Tasks | Failure modes |
| --- | --- | --- | --- | --- | --- | --- |
| hip stance extension | hip angle | Over a planted foot the body progresses forward, so the hip extends from contact to toe-off | mean of the last 5% of stance − mean of the first 5% < 0 ⇒ +1 | \|change\| ≥ 0.20 rad | level/incline/decline walking, stair ascent, run | backward walking or a task mislabelled as forward (votes wrong; synthetic test: conflict with markers, suggest without); contralateral column (gate catches it when the knee column is mislabelled too) |
| ankle push-off plantarflexion | ankle angle | From heel rise to toe-off the foot pivots on the forefoot while the shank rotates forward, so the ankle plantarflexes | change over the last 25% of stance < 0 ⇒ +1 | \|change\| ≥ 0.10 rad | same | toe walking without push-off; immobilised or prosthetic ankles (population not checked: pass `task=None`) |
| hip moment timing | hip moment | Early stance the GRF passes in front of the hip (internal extensor); late stance behind it (internal flexor) | mean of the last 30% of stance − mean of the first 20% > 0 ⇒ +1 | \|contrast\| ≥ 25% of the unit's peak \|moment\| | level/incline/decline walking | weak propulsion, or a trunk-forward posture moving the GRF line; in the synthetic gait with 0.2 BW propulsion the late-stance hip moment was about 0 and the test abstained (the fixture uses 0.15 BW) |
| power timing, ankle | ankle power | Push-off generation (A2) is positive whatever the angle and moment conventions | mean over the last 25% of stance > 0 ⇒ +1 | \|mean\| ≥ 15% of the unit's peak \|power\| | level/incline walking, stair ascent, run | decline walking (reduced A2) is excluded |
| power timing, hip | hip power | Pre-swing / initial-swing flexor generation (H3) | mean over ±10% of stance length around toe-off > 0 ⇒ +1 | same | level walking only (incline removed on 2026-10-31 after UM21 data, see below) | the weakest assumption; the smooth synthetic gait has no distinct H3 and the test casts no vote there (a labelled H3 pattern tests its logic) |

The late-stance plantarflexor moment test now also abstains when the gate
fails.

**Inverse-dynamics-light hip (family plate geometry, `inverse_dynamics_light`).**
This is planar Newton–Euler through the foot (heel→toe), the shank and the
thigh. It uses Winter (2009) Table 4.1 mass, COM and radius-of-gyration
fractions and gives a per-kg internal hip moment (flexor positive) that
includes segment weight and inertia.

- **Inputs.** Sagittal hip, knee, ankle, heel and toe markers (vertical order
  must pass); CoP; GRF per kg (`N_per_kg`, `BW`, or `N` with a declared mass);
  stride durations.
- **Processing.** Markers are detrended (to remove overground translation),
  padded periodically, low-pass filtered at 6 Hz (2nd-order zero-lag
  Butterworth) and differentiated.
- **Decision.** Units vote with the sign of the slope when |r| ≥ 0.6. The test
  abstains if any plate frame check fails.
- **Validation.** It matches an analytic rigid-leg pendulum to 2% of the peak
  over the whole unit, is unchanged by a constant-speed hip translation, and
  matches statics to 1e-6. Both reference formulas are independent of the
  recursion.
- **Independence.** It shares plate geometry with the lever arm, so it is the
  same family. The hip moment therefore applies only together with hip moment
  timing.
- **Failure modes.** Greater-trochanter proxy for the hip centre; Winter
  fractions that do not fit the person (children, amputees); CoP
  registration, which is guarded only above about 11 cm.

**Column from the other leg: half-cycle check (verifier fix, phase 3).** A
left/right column mislabel shifts a channel by half a cycle. For a channel
that is nearly antisymmetric over half a cycle (a near-sinusoidal hip), that
shift looks exactly like negation to every test that reads shape at fixed
timing. The marker test and the hip stance-extension test then flip together,
so two families would agree on a wrong sign. The verifier reproduced this.
The knee-based plate-to-leg gate cannot see it.

The fix combines a lag check with a family rule, and it holds for a pure
sinusoid:

- Every reference-waveform test (marker reference angle, lever arm, ID-light)
  also fits the channel shifted by half a unit. It compares the median |r| at
  lag 0 with the median |r| at the half-cycle lag; the margin is 0.05, fixed
  in advance.
- **Half-cycle lag better by at least the margin:** the test abstains ("column
  from the other leg?").
- **Within the margin (ambiguous):** the evidence is flagged. `combine` then
  counts it and every plate-timed test as one family, `fixed_timing_shape`, so
  that pair can never apply on its own.
- **Lag 0 better by the margin:** the families stay separate.

A pure-cosine hip is therefore at most `suggest`. A hip with a visible second
harmonic (synthetic: 0.12 rad) can still apply, and its other-leg column
cannot.

The synthetic sweep takes each column that can apply (hip, knee and ankle
angles; hip and ankle moments; ankle and hip power) from the other leg, with
both a pure-cosine and an asymmetric hip. No wrong sign is applied in any
case. Why the remaining pairs are safe:

- **Knee:** the knee-range test reads the value distribution, which a time
  shift does not change.
- **Ankle angle, ankle and hip moments:** they are not antisymmetric, so their
  reference tests abstain on the shifted column.
- **Powers:** a power derivation needs applied anchors.

On real data, near-sinusoidal hips will mostly stay `suggest`. The pilot
re-run will show how often.

**Fixture limits (disclosed).** The planar fixture has a fixed hip and no
trunk. It does not produce a physiological hip moment at 0.2 BW propulsion:

- at 0.15 BW the hip moment timing test votes correctly;
- at 0.20 BW it abstains;
- at 0.30 BW it votes wrong, and ID-light and the lever arm disagree with it,
  which gives a conflict (tested).

The timing logic is tested separately on a labelled, normatively shaped hip
moment pattern. Its real-data justification (early extensor, late flexor)
still needs the pilot.

**Coverage after phase 3** (default grouping, all inputs present):

| Channel | Families available | Can apply? |
| --- | --- | --- |
| hip angle | marker geometry, plate timing | yes, only if the hip is not half-cycle ambiguous (lag 0 beats the half-cycle lag by 0.05 in median |r|) |
| knee angle | marker geometry, joint anatomy | yes |
| ankle angle | marker geometry, plate timing | yes |
| pelvis tilt | marker geometry (chain derivations count as marker geometry) | no: suggest only |
| hip moment | plate geometry (ID-light), plate timing | yes |
| knee moment | plate geometry (lever arm) | no: suggest only |
| ankle moment | plate geometry, plate timing | yes |
| ankle power | power identity, plate timing | yes, when the ankle moment and angle are applied |
| hip power | power identity, plate timing (H3) | yes, when H3 votes and the hip moment and angle are applied (so not with a half-cycle-ambiguous hip) |
| knee power | power identity | no |

**Pelvis: no second family adopted.** The candidate "pelvis vs foot-marker
vertical oscillation phase" was rejected for three reasons:

- It uses the same markers, up vector and projection as the marker
  reference, so it is not an independent family.
- The pelvic tilt to vertical-oscillation phase relation is not a physical
  constraint and varies between people.
- The tilt excursion (about ±2°) is close to marker noise.

The only physical route found is the segment chain, pelvis = thigh − hip. It
needs a source thigh segment channel whose sign is applied from two families,
and it would need derived evidence to inherit its anchors' families. Both are
left for a later decision.

**Synthetic tests for phase 3** (`tests/test_sign_offset_detector.py`):

- recovery in both orientations;
- a labelled H3 pattern;
- abstention for `None`, jump, backward walking and stair descent;
- a contralateral plate (shifted half a stride), caught by the gate: every
  plate-timed test abstains and no wrong sign is applied;
- backward walking mislabelled as level: conflict with markers, wrong suggest
  (not applied) without them;
- mirrored markers and plates: angle conflicts, and ID-light abstains on the
  frame check;
- ID-light pendulum, statics and translation invariance;
- ID-light abstains without durations, or with GRF in N and no mass.

None of them applies a wrong sign.

## What is applied and what is flagged

| Item | Applied by `apply_signs`? | Reported |
| --- | --- | --- |
| sign with verdict `apply` | yes, multiply by ±1 | log line naming tests and unit counts |
| sign with `suggest` / `conflict` / `abstain` | no | verdict, reason, evidence |
| offset (any size) | never | estimate, 95% CI, `flag_for_review` |
| 180° branch frames | never (masked from fits only) | counts, runs |
| scale mismatch (reference slope outside 0.8–1.25) | never | `scale_review`; outside [0.1, 10] the reference test abstains |

The offset is reported as median(wrap(sign × source − reference)) per unit,
with the difference wrapped to (−π, π]. A 360° storage wrap is therefore not
an offset. A genuine 180° zero difference is still flagged, and above π/2 it
turns the verdict into `conflict`. Its 95%
CI is a percentile bootstrap of the unit medians (seed 20261030, 2000
resamples). It is flagged when the CI excludes 0 and \|estimate\| > 0.035 rad
(about 2°). Offsets come only from an independent reference angle. The chain
residual mixes the zeros of three channels, so it is reported on the relation
and not attributed to any one channel.

## Output schema (per dataset, per leg)

```json
{
  "schema_version": "sign-offset-detector/0.1",
  "dataset": "...", "leg": "left|right", "task": "...", "index": "time|phase_or_unknown",
  "target_convention": {"rule": "...", "rule_id": "B", "knee_angle": "flexion positive", "...": "..."},
  "scientific_approval": false,
  "parameters": {"min_units": 5, "min_families": 2, "family_grouping": "fine", "...": "..."},
  "marker_checks": {"vertical_order_fraction": 1.0, "required": 0.9, "result": "pass"},
  "plate_frame_check": {"cop_progression": {"result": "pass"}, "braking_propulsion": {"result": "pass"}},
  "channels": {
    "knee_angle": {
      "source_column": "knee_flexion_angle_ipsi_rad or source name",
      "verdict": "apply|suggest|conflict|abstain",
      "sign": -1, "sign_applied": true, "confidence": "high|medium|low|none",
      "reason": "score 3 from families joint_anatomy, marker_geometry",
      "families": ["joint_anatomy", "marker_geometry"], "weak_hint": null,
      "offset": {"estimate": 0.002, "ci95": [-0.001, 0.004], "units": 24,
                 "flag_for_review": false, "applied": false, "reference": "marker ..."},
      "evidence": [{"test": "reference_angle:marker", "strength": "strong", "sign": -1,
                    "units": 24, "units_voting": 24, "units_agreeing": 24,
                    "reason": "", "stats": {"median_abs_slope": 1.0, "scale_review": false}}],
      "branch_screen": {"branch_180_frames": 0, "wrap_360_frames": 0, "runs_unit_start_stop": []}
    }
  },
  "relations": [{"test": "power_identity", "channels": ["ankle_moment", "ankle_angle", "ankle_power"],
                 "product": -1, "strength": "strong", "units_voting": 24, "units_agreeing": 24}],
  "log": ["apply sign -1 to knee_angle: reference_angle:marker(strong, 24/24), ..."]
}
```

The dataset-level record is a list of these leg reports, one per (recording
sample, leg). A converter reads only `sign_applied` channels. Everything else
goes to review.

## Failure modes

- **Lever-arm tests depend on the frame.** The GRF, CoP and joint centres must
  already be in the target frame and on the same origin, which needs
  converter-specific geometry evidence (GT21-C01, GT23 frame audits). A
  reversed forward axis flips every lever-arm vote at once.
  - The plate frame check catches this: the CoP would move toe-to-heel
    relative to the ankle, and the lever arm then abstains.
  - Without ankle positions the check cannot run, so the ankle lever arm drops
    to moderate and cannot apply a sign on its own.
  - The marker angles do not check the plate frame.
  - Heel-to-toe rollover is assumed. In a mirrored frame, backward walking and
    toe walking would pass the check because their true CoP moves toe to heel.
    The check therefore runs only for forward heel-strike walking. For every
    other task, including `task=None`, it is "unknown", and the ankle lever arm
    stays moderate. A forefoot striker labelled as level walking could still
    pass a mirrored frame. Under the two-family rule the lever arm cannot apply
    alone, and the late-stance test, which is independent of the forward axis,
    would dissent and give `conflict`.
  - A reversed origin between CoP and joints that leaves the progression
    intact is not detected. In verifier probes, 0.3–0.6 m origin offsets led
    to abstention or the correct sign.
- **CoP registration.** The lever arm uses the CoP relative to the joint
  centres, so the adapter's rule for putting the plate CoP and the markers on
  one origin sets the lever-arm sign. A constant registration error leaves CoP
  progression intact.
  - In the verifier's independent UMich run, registering the CoP at the heel
    marker at contact put it about 11 cm behind the midpoint rule on AB04/d10.
    The ankle lever arm then voted the wrong sign in both legs. The
    late-stance test dissented, so the pair returned `conflict`.
  - The CoP-within-foot check tests registration whenever heel and toe
    markers exist, but it is coarse. On the verifier's AB04/d10 rerun with
    heel-at-contact registration, it returned "unknown": only 73% and 82% of
    strides fell inside the ±3 cm band, short of the 90% needed to decide.
    The lever arm then voted the wrong sign, and the pair returned `conflict`
    only because the late-stance test disagreed.
  - The check catches CoP registration errors only above about 11 cm. Smaller
    errors rely on the second evidence family. No threshold was retuned after
    this finding.
  - **Adapter requirement:** declare the rule in `cop_registration`; it is
    recorded in the report. The rule must not use the moment channels.
    Without heel and toe markers, the ankle lever arm cannot be strong.
- **Inverted up vector.** It mirrors every marker angle. The vertical-order
  check (pelvis, hip and knee above the foot) refuses it. If the check cannot
  run, the marker references are not used.
- **Angles near ±π.** A reference or source straddling ±π (for example a
  segment measured from a reversed axis) is re-expressed near its robust
  circular centre before fitting. A branch majority, with most units on the
  (π − x) solution, makes the whole-unit branch rule mask the normal units.
  The remaining fit then shows a half-turn offset, which gives `conflict`.
- **Inertia and segment weight are ignored.** Hip votes are unreliable, and
  swing is excluded. Fast running weakens the knee.
- **Population and task assumptions.** The knee hinge and late-stance tests
  assume forward walking with heel-off. Toe walkers, backward walking, stroke
  or prosthetic limbs (no heel-off, hyperextension) can break them. They
  abstain by task, but population is not checked: the caller must pass
  `task=None` for atypical populations.
- **Circularity.** If "independent" segment angles were computed from the same
  IK joint angles, the chain still identifies relative signs but cannot detect
  offsets. Templates are circular and stay weak.
- **Low excursion.** Pelvis tilt (about ±2°) often fails r ≥ 0.8 with noisy
  markers. The detector then abstains; it does not guess. A synthetic test
  covers this.
- **Data artefacts.** Exact zero fill (UM21: 241 of 500 channels) and marker
  label swaps reduce r, which leads to abstention. The caller should mask
  exact (0, 0, 0) fill before calling. Masking stays the caller's step, and
  the detector does not repair data.
- **Mixed storage within a dataset.** UM21 has two power layouts. Running per
  recording sample and comparing reports exposes this as split units or
  inconsistent verdicts. Do not pool recordings with different layouts.
- **Units.** An angle channel above 2π is refused, both in `detect_leg` and
  in `reference_angle_test`. A small-range channel in degrees is caught by the
  slope band of [0.1, 10].
- **Stance.** The adapter must declare the GRF unit (N/kg, BW or N), or pass a
  stance mask. The contact floors need no mass.

## Pilot plan (one dataset at a time, after the guarded launcher is reviewed)

Ground truth is the verified per-signal conventions in
`docs/quality/audits/sign-conventions-source-survey.json` and
`um21-c03-conventions.json`. The expected rule-B signs (target = sign ×
source) are listed below. "?" means unverified, and the detector should
abstain or flag there.

| Dataset | pelvis | hip | knee angle | ankle | hip M | knee M | ankle M | power |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UM21 (clinical, Vicon PiG) | −1 | +1 | +1 | +1 | +1 | +1 | +1 | layout 1: −1; layout 2: +1 |
| GT21 (gait2392) | ? (not sagittal; heading about 90°) | +1 | −1 | +1 | +1 | −1 (inferred) | +1 | not published |
| GT23 (gait2392) | absent | +1 | −1 | +1 | +1 | −1 | +1 | not published |
| GT24 (gait2354) | absent | +1 | −1 | +1 by data / −1 by README | +1 | ? | +1 by data / −1 by README | not published |

Procedure for each dataset, in this order: UM21, GT23, GT21, GT24.

1. Use the source adapter's untransformed channels, so that no prior sign code
   is applied. Draw a seeded sample: 4 recordings and both legs, plus a
   disjoint second seed of 4, reusing the UM21-C03 seeds where possible.
2. Use one numerical worker through the guarded launcher. Bound reads to one
   recording at a time and write nothing under `converted_datasets/`.
3. Run `detect_leg` per recording and leg. Then tabulate the verdicts against
   the table above.
4. Tabulate both applied and suggested signs against the ground truth, so
   that D-CORE-04-1 rests on pilot evidence. The pilot applies nothing to any
   dataset.
5. Acceptance: every `apply` matches the ground truth, and every
   disagreement or `conflict` is explained in the handoff. The GT24 ankle
   should come out as `conflict` when the README statement is supplied. An
   `apply` that contradicts verified ground truth stops the pilot and goes
   back to design, not to threshold tuning.
6. Offsets: compare the UM21 ankle offsets to the unpublished Plug-in Gait
   static offsets noted in UM21-C03, and report them only.

Evidence available per dataset (to confirm against the source in the pilot):
UM21 has markers and force plates. GT21 has markers (`markers`) and force
plates (`fp`). GT23 and GT24 have force plates (GT23 right-leg treadmill NaN),
and their marker access must be checked.

## UM21 pilot result (2026-10-30; re-scored under rule B on 2026-10-31)

The probe ran with the detector targeting rule C. After the rule changed to B,
the pilot builder re-scored the stored results without re-reading data
(`to_rule_b`). Rule B differs from C only in the knee angle and knee moment
targets (B = −C). The detector's knee tests are mirror images under that
change: the marker knee reference is negated, the knee-hinge expectation is
mirrored, and the knee lever arm is multiplied by −1. The vote and agreement
rules are symmetric in sign, and the knee power product is unchanged. So the
verdicts stay the same, while the knee signs, the knee evidence signs and the
knee offsets negate. The ground truth is now the UMich signs under B, which
match the clinical source everywhere except pelvis tilt. Every outcome below
is unchanged.

Evidence: `docs/quality/audits/core04-um21-pilot.json`; builder
`contributor_tools/review_core04_um21_pilot.py`; sheet `review_sheets/CORE-04/`.
The probe was read-only and processed one recording at a time, with a peak
RSS of 203 MiB. It applied nothing to any dataset. The CoP was registered by
the midpoint rule (UM21-C03), which is declared in the report.

Samples: the 8 recordings of the UM21-C03 seeds (20261030 and 20261031),
plus AB01/i0 (level walking) and AB07/i10 (branch episode): 20 legs.

| Outcome | Channel-legs | Notes |
| --- | --- | --- |
| applied, right sign | 36 | knee angle in 16 legs; ankle moment in 20 |
| suggested, right sign | 84 | pelvis, hip and ankle angles, knee moment; knee angle in 4 incline legs |
| wrong sign | 0 | |
| conflict | 0 | |
| abstained | 80 | hip moment (weak lever arm only); all three powers (no joint has both its moment and angle applied) |

- No single test voted for the wrong sign in any leg.
- The power identity recovered the storage slot and sign in all 60
  leg-joints, covering both layouts (UM21 layout 1, −(M·ω) in slot 1, and
  layout 2, +(M·ω) in slot 3). Because derivation needs applied anchors, it
  did not apply any power sign.
- On AB07/i10 right, the branch screen set 30 strides aside. A 31st stride
  (frames 12608–12735) holds a 106° one-frame jump. Resampling to 150 samples
  split it under the 90° jump rule, so the stride was kept; it cast no vote.
- 43 of 80 angle zero offsets were flagged, up to 13°. They are reported but
  not interpreted.

Detector change made before the run: the vertical-order fraction is now
computed only on frames where the compared markers are visible, because a
missing marker is not evidence of an inverted up vector. No threshold was
changed.

After the verifier's review, the CoP-within-foot check and the vertical-order
visible-frame minimum were added and the probe was re-run. Every verdict and
every test vote was unchanged. The CoP-within-foot check passed in all 20
legs, with a median of 87–100% of stance samples inside, and 11,950–20,700
frames were visible for the vertical-order check.

The probe step itself is unchanged by the earlier sheet-only builder edits.
With the same detector, the edited builder reproduced the first probe file
field by field, apart from code hashes and memory figures.

The verifier's independent run covered 5 other recordings and 10 legs, with a
heel-at-contact CoP registration. It also found no wrong sign. It produced 2
conflicts on AB04/d10. In both, the lever arm voted wrong, the CoP-within-foot
check returned "unknown" (73% and 82% of strides inside), and the late-stance
test disagreed (see failure modes).

Follow-up for adapters: run the branch screen on source-rate frames before
resampling.

## UM21 pilot re-run (2026-10-31, detector fb174cf2, rule B, phase-3 tests)

The probe was read-only and ran alone, one recording at a time. Peak RSS was
224 MiB. It used the same 10 recordings and 20 legs. Two inputs were added:
stride durations, and body mass from `ParticipantDetails` `Bodymass` (kg,
source metadata) for the GRF-unit check and the ID-light estimate. Nothing was
applied to any dataset.

Evidence: `docs/quality/audits/core04-um21-pilot-probe-v2.json` and
`core04-um21-pilot.json`. The first run is kept under `history`, and its probe
file is unchanged.

| Outcome | Channel-legs |
| --- | --- |
| applied, right sign | 86: hip angle 13, knee angle 16, ankle angle 18, hip moment 10, ankle moment 18, ankle power 8, hip power 3 |
| suggested, right sign | 85 |
| abstained | 29 (knee power 20, hip power 7, ankle power 2) |
| conflict | 0 |
| wrong sign | 0 |

- **New tests:** no wrong vote; they decided 90 of 120 leg-tests. ID-light
  was right in 20 of 20 legs. Hip stance extension, push-off and hip-moment
  timing were each right in 18 legs and abstained in 2, the AB07/i10 legs.
  Power timing was right in 8 legs and abstained in 12: decline walking is
  outside its assumptions, plus AB07/i10.
- **Half-cycle check:**
  - 7 of 20 real hips are ambiguous, so their hip angle is `suggest` only.
  - ID-light is ambiguous for 9 of 20 hip moments.
  - The weak hip lever arm read "half lag better" in 3 legs although the
    column is that leg's (ID-light was right there). These are false
    alarms, with no effect on verdicts.
- **Plate-to-leg gate:** it failed on both AB07/i10 legs (10% incline). The
  knee's largest excursion fell in stance in about 93% of strides, although the
  plates belong to that leg (frame checks and the ankle lever arm pass). The
  plate-timed tests abstained there, so the ankle moment dropped from apply to
  suggest. The gate's walking assumption does not hold for this subject at 10%
  incline, which is conservative. No threshold was changed.
- **Against the rule-B re-score of the first run:** no decided sign changed.
  82 channel-legs gained a verdict and 2 lost apply (AB07/i10 ankle moment).
  The only old-test vote changes are the 3 hip lever-arm flags and the 2
  AB07/i10 late-stance abstentions. The offsets are identical.

### Record fixes after the v2 verification (2026-10-31; no data read)

- **Pelvis truth varies per recording.** In AB04/i0 (the verifier's run; not
  in the pilot sample), Plug-in Gait computed the pelvis with the walking
  direction reversed: median pelvis rotation 180.2°, against about 0°
  elsewhere. The stored tilt there is therefore flipped, and the detector's +1
  pelvis suggestion is correct for that recording. A blanket dataset truth of
  −1 is wrong for it. The pilot's 10 recordings are unaffected: the pelvis
  marker test agreed with −1 in all 20 legs, and the offsets were within
  0.2°. Ground truth for future pilots must be checked per recording.
- **Plate-to-leg gate message.** A failure now names both causes: the plate
  belongs to the other leg, or the knee pattern is outside the gate's
  assumption (e.g. a steep incline with a flexed stance knee). The threshold
  and scope are unchanged; the AB07/i10 failures remain conservative.
- **Hip push-off power timing is limited to level walking.** This scope
  change was made after seeing UM21 data, and is logged as such. In the
  verifier's run, AB03/i10 R hip power around toe-off was negative in 84 of 90
  strides for a correctly stored column. That gave a wrong vote and pulled
  the hip angle and hip moment into conflict (safe, but evidence lost). A
  labelled synthetic incline pattern now tests the abstention. The v2 probe
  was not re-run. Recombining its stored evidence without the out-of-scope
  votes predicts:
  - AB01/i5 L hip power goes from apply to suggest;
  - 5 incline legs' hip power goes from suggest to abstain;
  - totals become 85 applied, 81 suggested, 34 abstained and 0 wrong.
- **Builder history.** The v2 probe ran with builder e0bf7d46 and the sheet
  was built with 2126c434; only the sheet step changed. Builder e0bf7d46 was
  reconstructed exactly (its sha256 matches the hash recorded in the probe)
  and compared by AST: every probe-step function and module constant except a
  label table is identical.

## GT23 pilot (2026-10-31, detector efd74e73, rule B)

Evidence: `docs/quality/audits/core04-gt23-pilot.json` and
`core04-gt23-pilot-probe.json`; sheet page `review_sheets/CORE-04/gt23.html`;
builder `contributor_tools/review_core04_gt23_pilot.py`.

The probe was read-only and ran alone, one trial at a time. Peak RSS was 230
MiB. Nothing was applied to any dataset.

- **Sample:** seed 20261102 selected AB01, AB13 and AB06. Each subject has
  seven conditions: treadmill level 1.2 m/s; incline 5° and 10° (left leg);
  decline 5° and 10° (right leg, the only treadmill condition with a working
  right plate); stair ascent; stair descent. That gives 20 legs; AB01 has no
  parsed stair-descent strides.
- **Units:** the dataset's own stride segmentation. Stair strides are pooled
  over passes for the leg with more strides.
- **Adapter:**
  - Untransformed OpenSim columns.
  - `.trc` markers and `GroundFrame_GRFs` share the OpenSim ground frame. No
    CoP shift is applied; the CoP-within-foot check tests that registration.
  - GRF in N, with the participant's README mass.
- **Ground truth (rule B):** gait2392, so hip +1, knee angle −1 and ankle +1;
  moments hip +1, knee −1 and ankle +1; powers +1.
- **Moment scale:** GT23 moments are divided by another participant's mass
  for AB06 and AB13 (GT23-C03). Every decision used here is scale-free, and
  slopes are not interpreted.

| Outcome | Channel-legs |
| --- | --- |
| applied, right sign | 85 |
| suggested, right sign | 52 |
| abstained | 43 |
| conflict | 0 |
| wrong sign | 0 |

- **New cross-family tests:** no wrong vote.
- **Half-cycle check:** 3 of 20 hips are ambiguous, all on the 10° inclines,
  so their hip angle is `suggest` only. As in UM21, the weak hip lever arm
  raised "other leg?" false alarms in 3 legs.
- **Gate:** it passed on walking legs. It was unknown for stair descent
  (outside its assumption) and for two legs below 90% in swing (AB06 incline
  10°, AB06 stair ascent).
- **Plate frame checks:** CoP-within-foot failed on AB01 decline 10°, so its
  lever arms abstained.
- **Pelvis:** GT23 publishes no pelvis angle. The marker pelvis heading is
  within 28° of the heel-to-toe axis in every trial and pass; left legs are
  negative and right legs positive, as expected for foot toe-out. No pelvis
  is reversed.
- **Forward axis (corrected in v2):** v1 used the analysed foot's
  heel-to-toe axis. Toe-out rotates that axis 5–28° from the pelvis facing,
  and the offset was not harmless. It leaked frontal forces into the
  sagittal estimate and lowered the decline ID-light correlations (verifier:
  AB01 decline 5° 0.39 → 0.95, AB13 decline 10° 0.25 → 0.54, AB06 decline 5°
  0.74 → 0.85 with the pelvis axis).

### GT23 pilot v2 (2026-10-31, same seed, pelvis-facing axis)

- **Setup:** the same seed, subjects and conditions. Each stride is now
  projected on its pelvis facing (horizontal ASIS-mid minus PSIS-mid). The
  foot axis is a fallback only, used for 3 strides on AB06 incline 5° where
  the pelvis markers were missing.
- **Run:** the process census before the run found no other numerical
  worker. Peak RSS was 240 MiB. The v1 probe and summary are kept as history.
- **Results:** 87 applied, 54 suggested, 39 abstained, 0 conflict, 0 wrong
  (v1: 85 / 52 / 43). ID-light median |r| rose on every walking leg (level and
  incline legs 0.94–0.99).
- **Hip moment on declines:** applied in 4 of 6 legs (v1: 2).
  - AB01 decline 5°: 0.39 → 0.955, suggest → apply.
  - AB13 decline 5°: 0.30 → 0.67, suggest → apply.
  - AB13 decline 10°: 0.25 → 0.535, still suggest (4 votes).
  - AB06 decline 5° and 10°: 0.74 → 0.85 and 0.73 → 0.87, apply in both runs.
  - AB01 decline 10°: still suggest, because the CoP-within-foot check fails.
- **Other changes:** stair-descent hip moments went from abstain to suggest
  (ID-light now votes).
- **Builder history:** v1 ran with builder d99d53ac and its sheet with
  4165840b, which differ only in the sheet step. d99d53ac was reconstructed
  exactly and the probe-step functions compared by AST.

### Pilot builders split (2026-10-31)

Each pilot now has a probe file and a sheet file:

- `contributor_tools/probe_core04_um21.py` and `contributor_tools/probe_core04_gt23.py`
  are the probe steps. They read data under the probe exception.
- `contributor_tools/review_core04_um21_pilot.py` and
  `contributor_tools/review_core04_gt23_pilot.py` are the sheet steps. They read
  no data.

A sheet edit therefore no longer changes the hash recorded in a probe output.
The probe outputs already recorded stay valid:

- UM21: combined builder e0bf7d46 maps to probe file 17846c46.
- GT23: combined builder 97375fa6 maps to probe file 218d5614.

In both cases every probe-step function and constant is identical by AST;
only the command-line dispatcher differs. The GT23 v2 probe ran with builder
97375fa6, and its sheet with 57a9a5c9.

After the mapping, the GT23 probe gained a per-stride check of the angle
between the foot axis and the pelvis facing. A stride more than 90° apart has
its geometry withheld. This version has not been run yet.

## GT24 pilot (2026-10-31, detector efd74e73, rule B)

Evidence: `docs/quality/audits/core04-gt24-pilot.json` and
`core04-gt24-pilot-probe.json`; page `review_sheets/CORE-04/gt24.html`;
builders `contributor_tools/probe_core04_gt24.py` (probe) and
`review_core04_gt24_pilot.py` (sheet).

- **Run:** the census before the run found no other numerical worker. The
  probe was read-only and ran alone, one trial and one zip member at a time.
  Peak RSS was 205 MiB. Nothing was applied to any dataset.
- **Sample:** seed 20261104 selected Phase1And2 BT06, BT07, BT12 and BT16, and
  Phase3 BT01 and BT22. Of these, BT06, BT07 and BT12 have exo-off level
  walking. Conditions were level 1.2 m/s with exo on and off, and incline and
  decline 5° with exo on; both legs. That gives 40 legs. BT12's right leg had
  no strides in its level trials.
- **Geometry:** the Parsed zips hold no markers, so there is no marker
  reference and no pelvis facing. The lab force file is not used. The ankle
  lever arm runs in each foot's calcn frame (insole_sim, generic talus
  position).
- **Documentation:** README lines 90–91 (ankle plantarflexion positive) were
  supplied as documentation.

| Run | Applied | Suggested | Conflict | Abstained | Wrong |
| --- | --- | --- | --- | --- | --- |
| With README documentation | 0 | 162 | 80 | 118 | 0 |
| Data only | 40 (ankle moment) | 202 | 0 | 118 | 0 |

- **README ankle sign:** never applied. Every data test (push-off; ankle
  lever arm; late stance) votes dorsiflexion positive in all 40 legs. That
  agrees with GT24-C02 and conflicts with the README.
- **Without markers:** hip angle, knee angle, hip moment and powers are
  `suggest` at most. The knee moment abstains (no knee position).
- **Checks:** the plate-to-leg gate passed in all 40 legs. The half-cycle
  check (ankle lever arm) was lag0 in all 40.
- **Moment scale:** the normalizing mass is unresolved, but every decision
  used is scale-free.

### Documentation policy (2026-10-31; policy implementation of José's 2026-10-30 instruction)

José, 2026-10-30: "we should just fix both readmes based on the evidence".
The coordinator recorded it verbatim in `docs/maintainers/backlog.json`, in the
handoff checks of tasks GT24-C02 and GT23-C02 (cited by quote and task, not list
position; a test checks the quote is there). Under it, a verified audit
overrides a publisher README.

**Verification source.** A refutation counts only if its task has status
`done` in `docs/maintainers/backlog.json`. Only the coordinator sets `done`, and
only after the independent verifier's `done` verdict, so backlog status is the
single authoritative record. Verify files are not parsed; picking their latest
round by timestamp string was gameable.

**Exact citation keys.** Each documentation statement carries a `citation_id`
of the form `<document>:<locator>`, such as `gt24-readme:L90-91` (a line, line
range or section). Table entries list refuted `citation_ids`, and matching is
exact equality, never substring.

**Enforcement.** A statement is withheld only when an entry lists its channel
and its exact `citation_id`, refutes its sign, and names a done task. Every
matching entry is evaluated, so table order does not matter. Only the refuted
sign is withheld; a statement that agrees with the verified finding is kept. An
unverified refutation keeps the statement and logs why. Malformed input raises
an error: a `citation_id` without a document name or locator, a missing task,
or a statement or refuted sign that is not the integer +1 or -1 (bools, None
and strings fail).

- **What adapters pass:** only documentation statements that no verified
  audit has refuted.
- **What happens to refuted statements:** they are logged with their
  refutation, not passed as evidence. Example: "README lines 90–91: ankle
  plantarflexion is positive: refuted by GT24-C02 (verified, done)".
- **Mechanism:** each dataset has a list of refuted statements in
  `contributor_tools/common/refuted_documentation.json`, read by
  `contributor_tools/common/documentation_policy.py`
  (`split_documentation`).
- **Test:** `tests/test_documentation_policy.py`.

The detector itself is unchanged. Documentation still never applies a sign,
and an unrefuted statement that disagrees with the data still produces a
conflict.

**GT24 re-score:** the stored primary evidence was recombined without the
refuted ankle statements; no data was read. The result equals the data-only
run in 360 of 360 leg-channels: 40 applied (ankle moment +1), 202 suggested,
118 abstained, 0 conflict, 0 wrong. The GT24 probe adapter now applies the
policy itself on its next run.

**GT24 BT12 right leg:** this leg has no strides in either level trial. The
publisher NaN-filled it (insole and moments 0% finite in both level trials,
95% in incline 5°; CORE-04 GT24 verifier), as the README's load-cell note
(line 95) describes.

**Figure 2:** the tests figure now scales to the leg count (it was fixed at 20
legs). The UM21, GT23 and GT24 pages were rebuilt and render at 1100 and 390 px.

### Documentation policy hardening (2026-10-31, coordinator round 5)

The policy refuses a backlog with duplicate task ids, since the status record
would be ambiguous. Citation ids must match the pattern in full, in ASCII, so a
trailing newline or non-ASCII digits fail. A test requires that each refuting
task's backlog record names its citation id or entry id. It is marked strict
xfail because the GT24-C02 record cites "README line 91" but neither key. The
coordinator owns backlog.json; once the key is added there, the marker must be
removed.

## GT21 pilot (2026-10-31, detector ed52fc49, rule B)

**Question.** Does the detector reproduce the GT21 signs on treadmill,
overground, ramps and stairs without a wrong sign? Does it leave the
non-sagittal model pelvis unchecked?

**Design.**

- **Cohort:** seed 20261109; 6 of the 16 local subjects (AB09, AB08, AB18,
  AB30, AB16, AB24); both legs.
- **Conditions:** six per subject (treadmill level, overground level, ramp
  incline and decline, stair ascent and descent), giving 72 legs.
- **Recordings:** seeded per mode and read one at a time until 10
  plate-captured strides per leg and class were reached (capped).
- **Task per stride:** from the mode and the pelvis rise over run, because
  the reader does not admit the conditions tables.
- **Angles:** `ik` (model zero), because the reader does not admit
  `ik_offset`; `id` is in N·m and `jp` in W.
- **Truth (GT21-C01, gait2392):** knee angle and knee moment −1; every other
  joint channel +1.

**Result.** 648 leg-channels: 305 applied, 216 suggested, 127 abstained;
0 conflicts and 0 wrong. No single test voted for a wrong sign.

**Pelvis.** The model heading is near ±90° in 130 of 131 recordings, so
`pelvis_tilt` was not tested.

**Gates and half-cycle.**

- **Leg gate:** 41 pass, 0 fail, 31 not decided. Stair descent is outside
  the gate. On ramps and stair ascent the knee peak was in swing in only
  74–89 % of strides.
- **Half-cycle check:** 450 lag0, 43 ambiguous and 10 half. All 10 "half"
  results are the weak hip lever arm, which uses a thigh-marker hip point; it
  abstained. The hip moment was still applied in 8 of those 10 legs.

**Adapter rules found by the one-subject pilot.**

- The stance-capture rule allows the next stance at the stride end. On stairs,
  plate contact starts before the source heel strike.
- The detector is loaded by file path, because the package `__init__` pulls in
  pandas (85 MiB). Peak RSS is 222 MiB.

**Detector fixes found by the pilot,** each with a synthetic test:

- `grf_unit_check` ignores units whose GRF the adapter withheld. These had
  voted a −inf peak.
- `leg_assignment_check` ignores units without stance. These had voted
  "swing".

The full run was repeated after the gate fix. Verdicts were identical; the
gate result changed from pass to unknown in 5 legs. The earlier pilots are not
re-verified, but their adapters did not withhold GRF for whole strides.

**Not checked.**

- 1 recording was rejected because its plate clock is off the 200 Hz grid;
  the cause was not checked.
- Plates captured the stance in 2239 of 3389 strides.
- The mass unit is unresolved.


## Converter hook (CORE-11, 2026-10-31; design and synthetic fixtures only)

Status: no research data read and nothing launched. Revised after two
verification rounds (back to worker): pilot gate, array types, own family
table, build hashing, publication rule (round 1); pilot-task citation,
committed audited-sign table with per-recording exceptions, provenance
(round 2); explicit-id links, task lists with evidence basis, foot angle in
the AB04/i0 exception, dataset-key check, coordinator's table rulings
(round 3). Module:
`contributor_tools/common/sign_application.py`. Tests (synthetic):
`tests/test_sign_application.py`. GT21 effect:
`contributor_tools/core11_gt21_publication_effect.py` (stored evidence only).

### What the hook does

`run_sign_application(dataset, leg, group_id, recording, unit_ids, channels,
detector_sha256, source_columns, documentation, evidence, mode,
pilot_record_path)` processes one group: one recording (or recording sample)
and one leg. Adapters pass the dataset key and the source recording id, never
signs.

1. **Bound build.** The caller declares the detector build as a full lowercase
   sha256. The hook reads the detector file once, hashes those bytes, refuses
   (`UnboundBuildError`) when no hash is declared, the hash is malformed or the
   file differs, and executes the same bytes. The documentation policy is also
   executed from the bytes it hashed. The refuted-documentation table is read
   once; the policy reads the hook's private copy of those bytes. The hook's
   own bytes are hashed at import. The audited-sign table
   (`contributor_tools/common/audited_signs.json`) is read once. These five
   hashes are the bound build recorded in the log. The backlog is also read
   once per run (the policy gets a private copy), but it is not part of the
   build.
2. **Inputs.** Channels must be plain little-endian float64 `numpy.ndarray`
   (units, samples). Masked arrays, matrices and other subclasses are refused,
   because `np.asarray` would drop their state (a masked value would come out as
   data). Missing samples are NaN. Adapters pass channels at float64 and never
   downcast: the verifier saw borderline verdicts change on float32 copies.
3. **Documentation.** Items `(channel, sign, citation, citation_id)` go through
   `documentation_policy.split_documentation`; a statement refuted by a done
   task is withheld, and every statement's action and reason is logged.
4. **Detection.** `detect_leg` runs with the build's own `DEFAULTS`. `params`
   and any evidence key outside the detector's inputs are refused.
5. **Detector apply.** A detector `apply` counts only if the hook's guard,
   re-reading the stored evidence with the hook's **own frozen family table**
   (`FAMILY_TABLE`, `PLATE_TIMING_TESTS`; a test checks it equals the
   detector's), finds agreeing moderate or strong tests from at least two
   families, no moderate, strong or documentation dissent, and `min_families`
   ≥ 2. A refusal goes to review.
6. **Publication rule** (`publication_rule`; below). The channel is multiplied
   by the resulting sign (exact negation or copy) and nothing else changes.
   Offsets are never applied.
7. **Unchanged check.** The input channels and every evidence array (top level
   and one dict level) are hashed before and after; a change raises. The
   evidence hashes are logged.

### Publication rule (policy application; D-CORE-11-1 withdrawn)

Basis: "José instruction in chat, 2026-10-30, answering D-UM21-C01-2: "all
standardized names (thats the point of the project)"", recorded by the
coordinator in `docs/maintainers/backlog.json`, task UM21-C01, handoff checks,
as a standing preference: release signals under standardized LocoHub names
whenever a verified audit supports the sign; "leave out" is not a neutral
default. A test finds the quote there. This applies an existing preference; it
is not a new decision.

**Audited signs** come only from the committed table
`contributor_tools/common/audited_signs.json`, which is part of the bound
build. Each entry gives a dataset, a channel and a sign (rule B, target =
sign × source). It also records:

- `id`;
- `audit_tasks`, a list;
- `evidence_basis`, for example "one data family + model coordinate
  definition";
- `citation`, the audit file and locator.

An entry is used only when every listed task is `done` in the backlog and
every one of those backlog records cites the entry id explicitly, as a whole
token. A mention of the channel name does not count, because a negative
mention ("knee moment not checked") would otherwise link. A done but unrelated
task therefore cannot publish a sign, and unverified entries fall back to the
detector alone.

The dataset key must be in the table exactly. An unknown or miscased key
(`um21`) raises, because it would skip the dataset's exceptions. Each dataset
declares a `recording_id_pattern`; the adapter's recording id must fully
match it.

**Per-recording exceptions** come from verified audits and are applied before
any sign: their channels are held for that recording, whatever the detector
or audit says. A hold is fail-safe, so it applies even before the backlog
cites it. The table has one exception. UM21-P01 found that Plug-in Gait
computed the AB04/i0 pelvis facing backwards. So that recording's pelvis tilt,
and every segment angle built from it (thigh, shank and foot), are held until
José answers D-UM21-P01-1. Its joint angles and moments are unaffected. A test
fails once that decision is answered, so the table must then be updated.

**Entries** (rule B; coordinator rulings of round 3; no data read):

| Dataset | Entries (sign) | Audit tasks | Evidence basis |
| --- | --- | --- | --- |
| UM21 | pelvis −1; hip, knee, ankle angles +1; knee, ankle moments +1 | UM21-C03 | marker angles, lever-arm moments |
| UM21 | hip moment +1 | UM21-C03, CORE-04 | weak lever arm + pilot ID-light and stance timing |
| GT21 | hip +1, knee −1, ankle +1 angles | GT21-C01, CORE-04 | model coordinate definition + pilot marker and second family |
| GT21 | hip +1, ankle +1 moments | CORE-04, GT21-C01 | pilot data (two families) + model axes |
| GT21 | knee moment −1 | CORE-04, GT21-C01 | one data family (lever arm) + OpenSim coordinate definition (accepted for knee moments) |
| GT23 | ankle moment +1 | GT23-C02 | mass-free lever arm |
| GT23 | hip +1, knee −1, ankle +1 angles; hip moment +1 | CORE-04 | pilot v2 data (two or more families) + gait2392 definition |
| GT23 | knee moment −1 | CORE-04 | one data family (lever arm) + OpenSim coordinate definition |
| GT24 | ankle angle +1, ankle moment +1, hip angle +1, knee angle −1 | GT24-C02 | data checks and exo encoders against the README |

No entry cites SIGN-SURVEY, which is not a verified backlog task. No entry is
verified yet: each needs its tasks' backlog records to cite its id. The
citations are requested in the CORE-11 handoff.

These are omitted, so the detector decides them alone:

- UM21 powers, which are stored in two layouts per recording;
- the GT21 and GT23 pelvis;
- all GT21, GT23 and GT24 powers;
- the GT24 knee moment;
- the GT24 hip moment, removed because its only evidence is one family
  (stance timing) with no model definition behind it;
- segment angles.

A held channel is returned unchanged, in the source convention, and is never
written under a rule-B column name. A recording-level error that no verified
audit lists as an exception is still published under the dataset sign when the
detector abstains. It is held only when the detector suggests, applies or
conflicts against the sign.

**GT21 effect, from stored evidence** (`core11_gt21_publication_effect.py`
over the CORE-04 probe, with the table and the hook's link check; no data
read). The probe has 648 leg-channels; the guard accepts all 305 stored
applies, and 343 are not applied.

- *Backlog as it stands:* no GT21 entry is verified, because no backlog
  record cites the entry ids yet. All 343 non-applied leg-channels are held.
- *After GT21-C01 and CORE-04 cite the six entry ids:* 182 publish with the
  audited sign
  (hip angle 28, knee angle 32, ankle angle 16, hip moment 32, knee moment 72,
  ankle moment 2). 161 are held: hip power 61, knee power 72 and ankle power
  28, because no audit covers the powers.

In both cases no published sign disagrees with the probe's truth.

### Sign-application log (`sign-application/0.3`)

Per group, the log records:

- dataset, leg, group id and unit ids (one per row, in order);
- target rule, the detector's path, sha256, schema and parameters, and the
  bound build;
- mode and pilot facts: the record path and sha256, the receipt sha256 and the
  pilot task;
- the publication policy, the documentation statements (kept or withheld), the
  gate and frame checks, the evidence array hashes and the relations.

Per channel it records:

- source column, dtype, shape;
- verdict, detector sign, confidence and families;
- every test's vote: test, the hook-table family, strength, sign, units voting
  and agreeing, the half-cycle result and the reason;
- `detector_applied`, the guard result, the audit (sign, task, verified);
- `multiplier`, `sign_basis`, `publication`, `hold_reason`;
- the offset (`applied: false`);
- the sha256 of the input and output arrays.

**Undo.** `undo_sign_application(signed, log, expected_log_sha256)` checks
each array against `output_sha256`, multiplies by its multiplier (+1 or −1,
its own inverse) and checks the result against `input_sha256`. A consistently
edited log (multiplier and input hash both changed) passes those checks. The
anchor is therefore the log's sha256: `write_json_exclusive` returns it for the
conversion manifest, and undo with `expected_log_sha256` needs the log file
path and refuses a mismatch.

Documentation withholding and audit verification depend on backlog status at
run time. The backlog is not part of the bound build; the log records each
outcome and its reason.

### Review list

One item per held channel (reason, audit and detector signs). One per channel
with verdict `suggest`, `conflict` or `abstain`. One per guard refusal. One
per offset estimate (`applied: false`). `cross_group_review(logs)` adds an item
when one channel's published sign differs between groups of a dataset, or when
it is published in some groups and held in others (mixed storage: UM21 power
layouts, the UM21 AB04/i0 pelvis).

### How adapters call it

- Group by source recording and leg, never across recordings. Units are the
  adapter's observations (data-contract identities).
- Pass untransformed source channels under the detector's logical names, as
  float64 in radians, N·m/kg and W/kg. Unit conversion happens before the hook.
  Remove the adapter's own sign code for these channels. Their audited signs
  live in the committed table, so the adapter passes only the dataset key and
  the recording id. Frontal and transverse channels are not passed (data
  contract).
- Pass evidence as in the pilots, and declare the detector sha256 in the
  adapter or job spec.
- Write the arrays of published channels to rule-B columns. Write
  `sign_application.json` and `sign_review.json` beside them (exclusive
  create), and record their sha256 in the conversion manifest `outputs`.

### Feeding review sheets and release manifests

- **Review sheets.** A committed builder per dataset reads only logs and
  review lists. Chips: published by basis, held, guard refusals, inconsistent
  groups, flagged offsets, withheld statements; anything unexplained is "not
  checked". Figures: a channel-by-group grid coloured by publication and basis,
  and offsets with their CI.
- **Release manifests.** Proposed, not implemented: a `sign_application`
  block in provenance (bound build, log sha256 values, counts), which
  `build_dataset_release.py` would verify against the logs.

### Per-dataset bound-build pilot (before any full run)

Order: UM21, GT23, GT24, GT21. Each pilot runs through the guarded launcher
(`contributor_tools/guarded_launcher.py`), with the bound build plus the
adapter and probe script as `bindings`, on a seeded sample with
`mode="pilot"`. It passes when:

- no published sign contradicts the per-recording audited truth;
- every hold, conflict and guard refusal is explained;
- undo restores every written output to its logged input hash;
- inputs are unchanged.

The pilot record is a committed file under `docs/quality/audits/`:

```json
{"dataset": "GT21", "outcome": "passed", "pilot_task": "CORE-11-P-GT21",
 "launcher_receipt": {"path": "<committed receipt path>", "sha256": "<64 hex>"},
 "bindings": {"<repo path>": "<64 hex>"}}
```

The pilot task of dataset DS is `CORE-11-P-DS`, created by the coordinator,
with backlog `dataset` equal to DS. When it is marked `done`, its backlog
record must cite three things: the pilot record path, the record's sha256 and
the receipt's sha256. The receipt is committed too.

`mode="full"` refuses (`PilotGateError`) unless all of the following hold:

- the record is under that folder and its bytes equal the HEAD blob;
- its dataset matches and its outcome is `passed`;
- its pilot task is `CORE-11-P-<dataset>`, is `done` in the backlog, has
  that backlog dataset, and its backlog record cites the record path, record
  sha256 and receipt sha256 (this links the independent verification to this
  record; a done but unrelated task or free text does not count);
- the receipt file is committed (bytes equal HEAD) and hashes to the recorded
  value;
- the receipt is `completed` with `clean_success`, its spec binds exactly the
  record's bindings relative to this repository, and every binding matched
  before and after the run;
- the record's bindings include this run's bound build at the same hashes.

Any edit to a bound file invalidates the pilot.

### Synthetic tests

- **Signs and publication.** Applies only two-family detector verdicts with
  the injected sign. Suggestions, conflicts and abstentions are untouched and
  held when there is no audit. Offsets are never applied.
- **Unchanged inputs.** The inputs and evidence are unchanged, and a detector
  that edits its evidence is refused.
- **Input types.** Masked arrays, matrices, float32, big-endian and integer
  arrays are refused.
- **Log and undo.** The log round-trips and undo is bit-exact (including
  NaN). Tampered arrays are refused, and a consistently forged log is refused
  against the manifest hash.
- **Bound build.** Unknown builds, an edited detector file and parameter
  overrides are refused. The logged hashes are of what ran, and the policy
  reads the hook's single copy of the table.
- **Pilot gate.** The full run passes only with a committed pilot record
  whose done `CORE-11-P-SYNTH` task cites it. 18 forgeries are refused,
  plus a record edited after commit:
  - no record, not committed, outside the audits folder;
  - pilot task only in review;
  - the verifier's round-2 attack (an unrelated done task with a
    self-consistent committed receipt);
  - another dataset's pilot task, a backlog dataset that differs, a backlog
    record without the citations;
  - a hand-written uncommitted receipt, a forged receipt hash, a missing
    receipt;
  - other dataset, failed pilot;
  - stale detector or audited-table bindings, receipt bindings that differ,
    an unclean receipt, a binding changed during the run.
- **Documentation.** The policy is honoured in both directions, and
  documentation alone never applies.
- **Guard.** The hook table equals the detector table, and the guard ignores
  a remapped detector table. It refuses single-family, dissenting,
  half-cycle-merged, weak-only and bool-sign applies.
- **Publication rule.**
  - The rule's table cases.
  - With a synthetic table, verified entries publish agreeing and abstaining
    channels with the audited sign, and undo stays exact.
  - Entries against the detector are held, and unverified entries are
    ignored.
  - An unrelated done task that only mentions the channels cannot publish.
  - The link works only by an explicit whole-token id in every listed task,
    and every listed task must be done.
  - An unknown or miscased dataset key raises.
  - A per-recording exception holds even a detector-applied channel for that
    recording only.
  - Recording ids must match the dataset pattern, malformed entries are
    refused, and adapters cannot pass signs.
  - Cross-group inconsistencies are flagged.
- **Committed table.**
  - The table is well formed and bound.
  - No entry cites SIGN-SURVEY and the GT24 hip moment is absent.
  - Every listed task's record must cite each entry. Strict expected
    failures mark the citations requested from the coordinator.
  - The AB04/i0 exception holds the pelvis, thigh, shank and foot until
    D-UM21-P01-1 is answered, and the real table holds AB04/i0 pelvis tilt.
  - José's quote is found under UM21-C01 in the backlog.
