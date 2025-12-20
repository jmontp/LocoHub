---
title: Gait Task Definitions
---

# Gait Task Definitions

This document describes the segmentation conventions for cyclic locomotion activities based on **heel-strike-to-heel-strike** gait cycles. These tasks represent the primary use case for phase-normalized biomechanical data.

## The Gait Cycle Archetype

### Heel Strike to Heel Strike

Gait tasks are segmented using ipsilateral heel strikes as cycle boundaries. A complete gait cycle spans from one heel strike of the reference limb to the next heel strike of the same limb.

```
Ipsi Heel Strike → Ipsi Stance → Ipsi Toe Off → Ipsi Swing → Ipsi Heel Strike
       0%              0-60%          ~60%         60-100%         100%
```

### Phase Definition

| Phase (%) | Event | Description |
|-----------|-------|-------------|
| 0% | Ipsilateral heel strike | Initial contact of the reference limb |
| ~10% | Foot flat | Full foot contact, loading response complete |
| ~30% | Midstance | Single-limb support, body passing over stance foot |
| ~50% | Contralateral heel strike | Opposite limb initial contact |
| ~60% | Ipsilateral toe off | Reference limb leaves ground, swing begins |
| ~75% | Mid-swing | Reference limb swinging forward |
| ~85% | Terminal swing | Limb decelerating for next contact |
| 100% | Next ipsilateral heel strike | Cycle complete |

**Note**: Exact phase percentages vary with gait speed, terrain, and individual characteristics. The values above are typical for level walking at self-selected speed.

### Stance vs Swing

- **Stance phase** (~0-60%): Foot in contact with ground, weight-bearing
- **Swing phase** (~60-100%): Foot off ground, limb advancing forward

### Ipsilateral vs Contralateral

- **Ipsilateral (ipsi)**: The limb that defines the phase (heel strike at 0% and 100%)
- **Contralateral (contra)**: The opposite limb (~50% phase offset in symmetric gait)

---

## Heel Strike Detection

### GRF-Based Detection

The primary method uses vertical ground reaction force (GRF) threshold crossings:

```
Heel Strike: GRF crosses upward through threshold (e.g., 20N or 5% body weight)
Toe Off: GRF crosses downward through threshold
```

### Detection Algorithm

1. **Smooth GRF signal**: Apply low-pass filter or moving average to reduce noise
2. **Threshold crossing**: Detect when GRF rises above threshold
3. **Minimum duration**: Ensure stance phase exceeds minimum (e.g., 0.2s) to filter artifacts
4. **Stride duration bounds**: Remove strides outside expected range (e.g., 0.6-2.0s for walking)

### Detection Parameters

| Parameter | Typical Value | Description |
|-----------|---------------|-------------|
| GRF threshold | 20-50 N | Force above which contact is detected |
| Min stance duration | 0.2 s | Minimum time foot must be in contact |
| Min stride duration | 0.6 s | Minimum heel-strike to heel-strike time |
| Max stride duration | 2.0 s | Maximum heel-strike to heel-strike time |
| Smoothing window | 0.01-0.05 s | Filter window for noise reduction |

### Alternative Detection Methods

When GRF is unavailable, heel strikes can be detected from:

- **Foot velocity**: Local minimum in foot forward velocity
- **Shank angle**: Local minimum in shank sagittal angle
- **Acceleration**: Impact spike in foot/shank accelerometer data
- **Kinematic markers**: Foot marker vertical position minima

---

## Level Walking (`level_walking`)

### Definition

Walking on flat, horizontal surfaces at various speeds.

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Ipsilateral heel strike |
| ~50% | Contralateral heel strike |
| ~60% | Ipsilateral toe off |
| 100% | Next ipsilateral heel strike |

### Expected Biomechanical Patterns

**Joint Angles (sagittal plane)**:

| Joint | Heel Strike (0%) | Midstance (~30%) | Toe Off (~60%) | Mid-Swing (~75%) |
|-------|------------------|------------------|----------------|------------------|
| Hip | ~30° flexion | ~0° (neutral) | ~-10° extension | ~25° flexion |
| Knee | ~5° flexion | ~15° flexion | ~40° flexion | ~60° flexion |
| Ankle | ~0° (neutral) | ~10° dorsiflexion | ~-15° plantarflexion | ~0° (neutral) |

**Ground Reaction Forces**:

| Phase | Vertical GRF | Anterior GRF |
|-------|--------------|--------------|
| 0-15% | Loading peak (~1.1 BW) | Braking (posterior) |
| 30% | Midstance valley (~0.8 BW) | ~Zero |
| 45-60% | Push-off peak (~1.1 BW) | Propulsion (anterior) |
| 60-100% | Zero (swing) | Zero |

### Speed Effects

| Speed | Stride Duration | Stance % | Peak GRF |
|-------|-----------------|----------|----------|
| Slow (0.6 m/s) | ~1.4 s | ~65% | ~1.0 BW |
| Normal (1.2 m/s) | ~1.1 s | ~60% | ~1.1 BW |
| Fast (1.8 m/s) | ~0.9 s | ~55% | ~1.2 BW |

### Task Variants

| `task_id` | Description |
|-----------|-------------|
| `level` | Self-selected comfortable speed |
| `level_slow`, `level_0.6ms` | Slow walking (~0.6 m/s) |
| `level_fast`, `level_1.8ms` | Fast walking (~1.8 m/s) |
| `shuffle` | Shuffling gait pattern |
| `skip` | Skipping gait pattern |

---

## Incline Walking (`incline_walking`)

### Definition

Walking uphill on ramps or inclined treadmills.

### Phase Definition

Same as level walking (heel-strike to heel-strike), but with terrain-adapted kinematics.

### Biomechanical Adaptations

Compared to level walking:

- **Hip**: Increased flexion throughout stance (+5-15° at heel strike)
- **Knee**: Increased flexion at heel strike and midstance
- **Ankle**: Increased dorsiflexion during stance
- **Trunk**: Forward lean proportional to grade
- **GRF**: Reduced braking peak, increased propulsion

### Task Variants

| `task_id` | Grade | Notes |
|-----------|-------|-------|
| `incline_5deg` | +5° | Mild incline |
| `incline_10deg` | +10° | Moderate incline |
| `incline_15deg` | +15° | Steep incline |

### Key Metadata

- `incline_deg`: Positive value indicating uphill grade
- `speed_m_s`: Walking speed (typically reduced vs level)
- `surface`: `treadmill` or `overground`

---

## Decline Walking (`decline_walking`)

### Definition

Walking downhill on ramps or declined treadmills.

### Biomechanical Adaptations

Compared to level walking:

- **Hip**: Reduced flexion at heel strike
- **Knee**: Increased flexion at heel strike (shock absorption)
- **Ankle**: Increased plantarflexion at heel strike
- **Trunk**: Backward lean to control descent
- **GRF**: Increased braking peak, eccentric muscle loading

### Task Variants

| `task_id` | Grade | Notes |
|-----------|-------|-------|
| `decline_5deg` | -5° | Mild decline |
| `decline_10deg` | -10° | Moderate decline |

### Key Metadata

- `incline_deg`: Negative value indicating downhill grade

---

## Stair Ascent (`stair_ascent`)

### Definition

Climbing stairs, stepping up from one level to the next.

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Ipsilateral foot contact on current step |
| ~50% | Contralateral foot contact on next step |
| 100% | Ipsilateral foot contact on next step |

### Biomechanical Characteristics

- **Hip**: Large flexion (>60°) to lift body to next step
- **Knee**: Deep flexion (>80°) during pull-up phase
- **Ankle**: Significant dorsiflexion and plantarflexion range
- **GRF**: Single peak pattern, no clear double-hump

### Task Variants

| `task_id` | Description |
|-----------|-------------|
| `stair_ascent` | Standard stair climbing |
| `curb_up` | Single step/curb ascent |
| `step_up_left`, `step_up_right` | Leading leg specified |

### Key Metadata

- `step_height_m`: Height of each step
- `step_number`: Which step in the flight
- `assistance`: `none`, `handrail`, etc.

---

## Stair Descent (`stair_descent`)

### Definition

Descending stairs, stepping down from one level to the next.

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Ipsilateral foot contact on upper step |
| ~50% | Contralateral foot contact on lower step |
| 100% | Ipsilateral foot contact on lower step |

### Biomechanical Characteristics

- **Hip**: Controlled flexion during lowering
- **Knee**: Eccentric loading dominates (>90° flexion common)
- **Ankle**: Plantarflexion for toe contact, then dorsiflexion
- **GRF**: Impact spike at initial contact

### Task Variants

| `task_id` | Description |
|-----------|-------------|
| `stair_descent` | Standard stair descent |
| `curb_down` | Single step/curb descent |

---

## Running (`run`)

### Definition

Locomotion with a flight phase where both feet are off the ground.

### Phase Definition

| Phase (%) | Event |
|-----------|-------|
| 0% | Ipsilateral foot strike |
| ~35-40% | Ipsilateral toe off |
| ~40-50% | First flight phase |
| ~50% | Contralateral foot strike |
| ~85-90% | Second flight phase |
| 100% | Next ipsilateral foot strike |

### Key Differences from Walking

- **Flight phases**: Both feet off ground (~20-30% of cycle)
- **Stance duration**: Shorter (~35-40% vs ~60%)
- **GRF peaks**: Single peak per stance (no midstance valley)
- **Peak forces**: Higher (2-3 BW vs 1.1 BW)

### Task Variants

| `task_id` | Speed | Notes |
|-----------|-------|-------|
| `run_2_5_m_s` | 2.5 m/s | Jogging |
| `run_3_0_m_s` | 3.0 m/s | Running |
| `run_4_0_m_s` | 4.0 m/s | Fast running |

### Key Metadata

- `speed_m_s`: Running speed
- `footwear`: `barefoot`, `shoe`, `minimalist`
- `surface`: `treadmill`, `track`, `overground`

---

## Backward Walking (`backward_walking`)

### Definition

Walking in reverse direction, heel-to-toe contact reversed.

### Phase Definition

Same segmentation as forward walking, but initial contact is typically toe/forefoot rather than heel.

### Biomechanical Characteristics

- **Contact pattern**: Toe-heel instead of heel-toe
- **Joint angles**: Generally mirror-image of forward walking
- **Speed**: Typically slower than forward walking
- **Stability**: Reduced due to lack of visual feedback

### Task Variants

| `task_id` | Speed |
|-----------|-------|
| `backward_0.6ms` | Slow backward |
| `backward_0.8ms` | Moderate backward |
| `backward_1.0ms` | Fast backward |

---

## Phase Normalization

### Resampling to 150 Samples

All gait cycles are resampled to **150 samples** spanning 0-100% phase:

1. **Extract cycle**: Data from heel strike to next heel strike
2. **Interpolate**: Resample to exactly 150 evenly-spaced points
3. **Align**: 0% = heel strike, 100% = next heel strike

### Why 150 Samples?

- **Resolution**: ~0.67% phase per sample, sufficient for gait events
- **Compatibility**: Matches common analysis conventions
- **Efficiency**: Reasonable file size for large datasets

### Interpolation Method

Linear interpolation is typically used. For high-frequency signals (e.g., EMG), consider preserving original timing in time-indexed format.

---

## Quality Checks

### Expected Ranges (Level Walking)

| Feature | Expected Range | Flag if |
|---------|----------------|---------|
| Stride duration | 0.8-1.4 s | Outside 0.6-2.0 s |
| Stance duration | 55-65% | Outside 45-75% |
| Hip flexion ROM | 35-50° | Outside 25-60° |
| Knee flexion ROM | 55-70° | Outside 40-80° |
| Peak vertical GRF | 1.0-1.2 BW | Outside 0.8-1.5 BW |

### Common Issues

| Issue | Possible Cause |
|-------|----------------|
| Asymmetric stride durations | Heel strike detection error, pathology |
| Missing swing phase | GRF threshold too high |
| Double-counted strides | GRF threshold too low, noise |
| Truncated cycles | Trial start/end within stride |

---

## Implementation Reference

Heel strike detection is implemented in dataset-specific conversion scripts. Common utilities include:

| Function | Location | Description |
|----------|----------|-------------|
| `detect_heel_strikes()` | Dataset-specific converters | GRF-based HS detection |
| `phase_detection.py` | `contributor_tools/common/` | Shared phase utilities |

---

## Task Metadata

### Common `task_info` Keys

| Key | Description | Example |
|-----|-------------|---------|
| `speed_m_s` | Walking/running speed | `1.2` |
| `incline_deg` | Grade (+ uphill, - downhill) | `5.0`, `-10.0` |
| `treadmill` | Treadmill vs overground | `true`, `false` |
| `surface` | Walking surface type | `treadmill`, `overground`, `track` |
| `footwear` | Shoe condition | `shoe`, `barefoot` |
| `assistance` | Walking aids used | `none`, `handrail`, `cane` |
| `step_height_m` | Stair step height | `0.18` |
