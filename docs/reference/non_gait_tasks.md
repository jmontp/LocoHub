---
title: Non-Gait Cyclic Task Definitions
---

# Non-Gait Cyclic Task Definitions

This document describes the segmentation conventions for cyclic activities that are **not** heel-strike-based gait. These tasks follow archetypes that define consistent phase definitions across datasets.

## Task Archetypes

### Standing → Action → Standing

Tasks that begin and end in a stable standing position, with a discrete action in between. The cycle is defined by detecting **stable standing states** (high GRF, low joint velocity) before and after the action.

| Task | Action | Example activities |
|------|--------|-------------------|
| `jump` | Flight phase with both feet leaving ground | Vertical jump, forward/backward hop, lateral jump, rotational jumps |
| `squat` | Descent to depth and return | Bodyweight squat, weighted squat |

### Sitting ↔ Standing Transfers

Tasks that transition between seated and standing states. These use GRF-based state detection combined with joint velocity thresholds to identify motion onset/offset.

| Task | Start state | End state |
|------|-------------|-----------|
| `sit_to_stand` | Stable sitting (GRF < 400N) | Stable standing (GRF > 600N) |
| `stand_to_sit` | Stable standing (GRF > 600N) | Stable sitting (GRF < 400N) |

---

## Jump (`jump`)

### Definition

A jump cycle captures the complete sequence from stable standing through the jump action back to stable standing:

```
Stable Standing → Countermovement → Takeoff → Flight → Landing → Recovery → Stable Standing
```

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Start of segment: stable standing detected (GRF > 600N, joint velocity < 25 deg/s) |
| ~20-40% | Countermovement phase: preparatory knee/hip flexion |
| ~40-50% | Takeoff: GRF increases then drops below flight threshold |
| ~50-60% | Flight phase: GRF < 50N (both feet off ground) |
| ~60-80% | Landing impact: GRF spike as feet contact ground |
| 100% | End of segment: stable standing re-established |

### Segmentation Algorithm

1. **Detect flight phases**: Find intervals where total vertical GRF < 50N for at least 0.05s
2. **Find stable standing before jump**: Search backward from takeoff for GRF > 600N AND joint velocity < 25 deg/s sustained for 0.2s
3. **Find stable standing after landing**: Search forward from landing for same criteria
4. **Create segment**: From stable standing start through stable standing end
5. **Apply IQR filtering**: Remove outlier durations using 1.5× IQR method

### Detection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `FlightThreshold` | 50 N | GRF below which subject is in flight |
| `StandingThreshold` | 600 N | GRF above which subject is standing |
| `VelocityThreshold` | 25 deg/s | Joint velocity below which motion is stable |
| `MinFlightDuration` | 0.05 s | Minimum flight duration to be a valid jump |
| `MinStableDuration` | 0.2 s | Minimum stable standing duration |
| `MinDuration` | 0.5 s | Minimum cycle duration |
| `MaxDuration` | 4.0 s | Maximum cycle duration |

### Expected Patterns

- **Hip flexion**: Increases during countermovement (~40-60°), near-zero during flight, increases during landing absorption
- **Knee flexion**: Similar pattern to hip; deep flexion during countermovement and landing
- **Ankle**: Dorsiflexion during countermovement, plantarflexion during flight, dorsiflexion during landing
- **Vertical GRF**: ~1 BW at start → push peak (~1.5 BW) → flight (~0 BW) → landing impact (~1.5-2 BW) → ~1 BW at end

### Jump Variants

| `task_id` | Description | Notes |
|-----------|-------------|-------|
| `jump_vertical` | Vertical jump in place | Symmetric bilateral |
| `jump_forward_backward` | Forward and backward hops | May have directional asymmetry |
| `jump_lateral` | Side-to-side hops | Mediolateral GRF dominates |
| `jump_hop` | Single-leg hopping | Uses `leading_leg` metadata |
| `jump_90deg`, `jump_180deg` | Rotational jumps | Landing orientation differs from takeoff |

---

## Sit-to-Stand (`sit_to_stand`)

### Definition

A sit-to-stand cycle captures the transition from a stable seated position to a stable standing position:

```
Stable Sitting → Motion Onset → Rising → Motion Offset → Stable Standing
```

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Start of segment: motion onset detected (joint velocity crosses 25 deg/s threshold while seated) |
| ~40-60% | Seat-off: GRF crosses from sitting range (<400N) toward standing range |
| 100% | End of segment: stable standing achieved (GRF > 600N, joint velocity < 25 deg/s) |

### Segmentation Algorithm

1. **Detect GRF state transitions**: Find where GRF crosses from sitting (<400N) to standing (>600N)
2. **Find motion onset**: Search backward from GRF crossing for where joint velocity first exceeds 25 deg/s
3. **Find motion offset**: Search forward from GRF crossing for where joint velocity drops below 25 deg/s
4. **Validate stable states**: Ensure sitting before and standing after are sustained for at least 0.3s
5. **Apply IQR filtering**: Remove outlier durations

### Detection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `StandingThreshold` | 600 N | GRF above which subject is standing |
| `SittingThreshold` | 400 N | GRF below which subject is sitting |
| `VelocityThreshold` | 25 deg/s | Joint velocity threshold for motion onset/offset |
| `MinStableDuration` | 0.3 s | Minimum duration to confirm stable state |
| `MinDuration` | 0.3 s | Minimum transition duration |
| `MaxDuration` | 5.0 s | Maximum transition duration |

### Expected Patterns

- **Hip flexion**: Starts flexed (~80-100°), decreases to near-zero at standing
- **Knee flexion**: Starts deeply flexed (~100-120°), extends to slight flexion (~5-10°)
- **Ankle**: Dorsiflexion throughout, decreases as body rises
- **Vertical GRF**: Starts low (<400N on feet), increases through transition, stabilizes ~1 BW

### Sit-to-Stand Variants

| `task_id` | Description |
|-----------|-------------|
| `sit_stand_short_arm` | Short chair height with armrest use |
| `sit_stand_short_noarm` | Short chair height without armrest |
| `sit_stand_tall_noarm` | Tall chair height without armrest |

---

## Stand-to-Sit (`stand_to_sit`)

### Definition

A stand-to-sit cycle captures the transition from a stable standing position to a stable seated position:

```
Stable Standing → Motion Onset → Lowering → Motion Offset → Stable Sitting
```

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Start of segment: motion onset detected (joint velocity crosses threshold while standing) |
| ~40-60% | Seat-on: GRF crosses from standing range (>600N) toward sitting range |
| 100% | End of segment: stable sitting achieved (GRF < 400N, joint velocity < 25 deg/s) |

### Expected Patterns

- **Hip flexion**: Starts near-zero, increases to deep flexion (~80-100°)
- **Knee flexion**: Starts slightly flexed, increases to deep flexion (~100-120°)
- **Ankle**: Increases in dorsiflexion during controlled descent
- **Vertical GRF**: Starts ~1 BW, decreases as weight transfers to chair

---

## Squat (`squat`)

### Definition

A squat cycle captures the complete descent and ascent from a stable standing position:

```
Stable Standing → Descent → Lowest Depth → Ascent → Stable Standing
```

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Start of segment: stable standing (GRF ~1 BW, joint velocity < threshold) |
| ~50% | Lowest depth: maximum knee/hip flexion |
| 100% | End of segment: stable standing re-established |

### Segmentation Approach

Squats follow the same "standing → action → standing" archetype as jumps, but without a flight phase. Detection uses:

1. **Detect standing phases**: GRF > 600N AND joint velocity < 25 deg/s
2. **Detect squat depth**: Local maximum in knee flexion between standing phases
3. **Segment from standing to standing**: Through the squat depth

### Expected Patterns

- **Hip/Knee flexion**: Starts near-zero, increases to maximum at 50% phase, returns to near-zero
- **Ankle**: Dorsiflexion increases during descent, returns during ascent
- **Vertical GRF**: Relatively constant ~1 BW (no flight phase)

### Squat Variants

| `task_id` | Description |
|-----------|-------------|
| `squat_bodyweight` | No external load |
| `squat_25lbs` | 25 lb external load |

---

## Shared Detection Principles

All non-gait cyclic tasks share these detection principles:

### Kinematic Velocity Bounds

Motion onset and offset are detected using a **25 deg/s joint velocity threshold**. This captures when the subject transitions from static holding to dynamic motion. The velocity is computed as the maximum absolute velocity across hip, knee, and ankle joints for both limbs.

### Stable State Detection

A state is considered "stable" when:
- GRF meets the threshold criteria (standing, sitting, or flight)
- Joint velocity remains below threshold for at least the minimum stable duration
- Both conditions must be sustained, not instantaneous

### IQR-Based Outlier Removal

After initial segmentation, outlier cycles are removed using the interquartile range method:
- Compute Q1 (25th percentile) and Q3 (75th percentile) of cycle durations
- Valid range: `[Q1 - 1.5×IQR, Q3 + 1.5×IQR]` bounded by absolute min/max
- Removes transitions that are unusually fast or slow

### Phase Normalization

All cycles are resampled to **150 samples** spanning 0-100% phase. This enables:
- Cross-subject averaging
- Template-based validation
- Consistent feature extraction across different sampling rates

---

## Implementation Reference

The segmentation functions are located in the Gtech 2023 conversion scripts:

| Task | Segmentation Function |
|------|----------------------|
| `jump` | `segment_jump_cycles.m` |
| `sit_to_stand`, `stand_to_sit` | `segment_sit_stand_transitions.m` |
| `squat` | Uses same approach as `jump` (standing → action → standing) |

Path: `contributor_tools/conversion_scripts/Gtech_2023/utilities/`

---

## Task Metadata

### Common `task_info` Keys

| Key | Description | Example |
|-----|-------------|---------|
| `jump_type` | Type of jump | `vertical`, `forward_backward`, `lateral`, `hop` |
| `chair_height` | Chair height for sit/stand | `short`, `tall` |
| `arm_rest` | Whether armrests were used | `true`, `false` |
| `weight_lbs` | External load weight | `0`, `25` |
| `variant` | Descriptive variant label | `bodyweight`, `weighted` |

### Subject Metadata

For these activities, relevant subject metadata includes:
- `weight_kg`: Body mass (for GRF normalization)
- `height_m`: Body height (affects chair relative height)
- `leg_dominance`: May affect bilateral symmetry
