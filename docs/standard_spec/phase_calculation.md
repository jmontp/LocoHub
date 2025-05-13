# Phase Calculation

## 1. Overview
Normalize each gait cycle to **0–100%** phase for consistent comparison.

## 2. Heel-Strike Detection
- Use `vertical_grf_N` with a threshold of **20 N**.
- Mark timestamps where force crosses above threshold from below.
- If the dataset already contains heel-strike event markers or frame indices, these may be used directly instead of detecting from GRF.

## 3. Cycle Segmentation
- Identify consecutive heel strikes.
- Define start (0%) and end (100%) of each cycle.

## 4. Interpolation
- Default `points_per_cycle`: **150**.
- Linearly interpolate intermediate samples to generate `phase_%` values.
- Store `phase_%` as a float 0.0–100.0.

## 5. Configuration
- Allow override of threshold and `points_per_cycle` in conversion scripts.