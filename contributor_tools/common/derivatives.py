"""
Derivative computation utilities for phase-normalized biomechanical data.

Handles the discontinuities introduced by circular phase shifts (np.roll)
when computing velocities and accelerations. When phase-normalized data is
shifted to align heel strike with phase 0%, the rolled ends meet and create
a discontinuity that causes velocity spikes if computed naively.

This module provides:
- find_discontinuity_index: Detect where a circular shift created a jump
- interpolate_discontinuity: Smooth across the discontinuity with cubic spline
- compute_velocity_from_shifted_angle: Compute velocity handling discontinuities
- compute_acceleration_from_velocity: Compute acceleration handling discontinuities
"""

import numpy as np
from scipy.interpolate import CubicSpline
from typing import Optional


def find_discontinuity_index(data: np.ndarray, threshold_factor: float = 3.0) -> int:
    """
    Find the index where a discontinuity occurs in phase-shifted data.

    Detects the point where the largest jump between adjacent values occurs,
    which indicates where the circular shift created a discontinuity.

    Args:
        data: 1D array that may have a discontinuity from np.roll()
        threshold_factor: Multiplier for detecting discontinuity (default 3.0)
                          A jump > threshold_factor * median_jump is a discontinuity

    Returns:
        Index of the discontinuity (the point AFTER the jump), or -1 if none found

    Example:
        >>> data = np.roll(np.sin(np.linspace(0, 2*np.pi, 100)), 50)
        >>> disc_idx = find_discontinuity_index(data)
        >>> print(f"Discontinuity at index {disc_idx}")  # Should be ~50
    """
    if len(data) < 3:
        return -1

    # Compute absolute differences between adjacent points
    diffs = np.abs(np.diff(data))

    # Find the maximum jump
    max_jump_idx = np.argmax(diffs)
    max_jump = diffs[max_jump_idx]

    # Compare to median jump to determine if it's a true discontinuity
    median_jump = np.median(diffs)

    if max_jump > threshold_factor * median_jump and median_jump > 0:
        # Return index after the jump (where discontinuity starts)
        return max_jump_idx + 1
    else:
        return -1  # No significant discontinuity found


def interpolate_discontinuity(
    data: np.ndarray,
    discontinuity_idx: int,
    window: int = 3
) -> np.ndarray:
    """
    Interpolate across a discontinuity to create smooth data.

    Uses cubic spline interpolation to bridge the gap where a circular
    shift created a discontinuity. Anchor points on each side of the
    discontinuity are used to fit the spline.

    Args:
        data: 1D array with discontinuity
        discontinuity_idx: Index where discontinuity occurs
        window: Number of points on each side to interpolate (default 3)

    Returns:
        Smoothed data array with discontinuity interpolated

    Example:
        >>> data = np.array([1.0, 1.1, 1.2, 5.0, 5.1, 5.2])  # Jump at index 3
        >>> smoothed = interpolate_discontinuity(data, 3, window=1)
        >>> # smoothed[2:4] will be interpolated for smooth transition
    """
    n = len(data)
    if discontinuity_idx < 0 or discontinuity_idx >= n:
        return data.copy()

    smoothed = data.copy()

    # Define the region to interpolate
    # We need points OUTSIDE the discontinuity region to anchor the spline
    left_start = max(0, discontinuity_idx - window - 2)
    left_end = discontinuity_idx - 1
    right_start = discontinuity_idx + 1
    right_end = min(n, discontinuity_idx + window + 3)

    # Get anchor points (outside the interpolation window)
    anchor_indices = list(range(left_start, left_end)) + list(range(right_start, right_end))
    anchor_values = [data[i] for i in anchor_indices]

    if len(anchor_indices) < 4:
        # Not enough points for cubic spline, use linear
        return data.copy()

    # Create cubic spline from anchor points
    try:
        cs = CubicSpline(anchor_indices, anchor_values)

        # Interpolate the discontinuity region
        interp_indices = range(left_end, right_start + 1)
        for idx in interp_indices:
            if 0 <= idx < n:
                smoothed[idx] = cs(idx)
    except Exception:
        # Fall back to linear interpolation if cubic fails
        left_val = data[max(0, discontinuity_idx - window - 1)]
        right_val = data[min(n - 1, discontinuity_idx + window + 1)]
        interp_range = range(max(0, discontinuity_idx - window),
                            min(n, discontinuity_idx + window + 1))
        for i, idx in enumerate(interp_range):
            t = i / max(1, len(interp_range) - 1)
            smoothed[idx] = left_val * (1 - t) + right_val * t

    return smoothed


def smooth_velocity_spikes(
    velocity: np.ndarray,
    discontinuity_idx: int,
    window: int = 5,
    comparison_window: int = 15,
    threshold_std: float = 2.5
) -> np.ndarray:
    """
    Smooth velocity spikes around a known discontinuity location.

    Compares velocity values near the discontinuity to the distribution
    of surrounding values. If values are outliers, interpolates them.

    Args:
        velocity: Velocity array that may have spikes
        discontinuity_idx: Index where discontinuity occurs (e.g., 75 for 50% phase)
        window: Half-window around discontinuity to check for spikes (default 5)
        comparison_window: Window size for computing reference distribution (default 15)
        threshold_std: Number of std deviations to consider as spike (default 2.5)

    Returns:
        Smoothed velocity array
    """
    n = len(velocity)
    if discontinuity_idx < 0 or discontinuity_idx >= n:
        return velocity.copy()

    smoothed = velocity.copy()

    # Define regions
    spike_start = max(0, discontinuity_idx - window)
    spike_end = min(n, discontinuity_idx + window + 1)

    # Get comparison regions (before and after the spike region)
    left_start = max(0, spike_start - comparison_window)
    left_end = spike_start
    right_start = spike_end
    right_end = min(n, spike_end + comparison_window)

    # Collect reference values from surrounding regions
    ref_values = np.concatenate([
        velocity[left_start:left_end],
        velocity[right_start:right_end]
    ])

    if len(ref_values) < 4:
        return velocity.copy()

    # Compute reference statistics
    ref_mean = np.mean(ref_values)
    ref_std = np.std(ref_values)

    if ref_std < 1e-10:
        return velocity.copy()

    # Check for spikes in the discontinuity region
    spike_region = velocity[spike_start:spike_end]
    z_scores = np.abs(spike_region - ref_mean) / ref_std

    # If any values are outliers, interpolate the whole region
    if np.any(z_scores > threshold_std):
        # Get anchor points outside the spike region
        anchor_left = list(range(left_start, left_end))
        anchor_right = list(range(right_start, right_end))
        anchor_indices = anchor_left + anchor_right
        anchor_values = [velocity[i] for i in anchor_indices]

        if len(anchor_indices) >= 4:
            try:
                cs = CubicSpline(anchor_indices, anchor_values)
                for idx in range(spike_start, spike_end):
                    smoothed[idx] = cs(idx)
            except Exception:
                # Linear interpolation fallback
                if len(anchor_left) > 0 and len(anchor_right) > 0:
                    left_val = velocity[anchor_left[-1]]
                    right_val = velocity[anchor_right[0]]
                    for i, idx in enumerate(range(spike_start, spike_end)):
                        t = i / max(1, spike_end - spike_start - 1)
                        smoothed[idx] = left_val * (1 - t) + right_val * t

    return smoothed


def compute_velocity_from_shifted_angle(
    angle_rad: np.ndarray,
    stride_duration_s: float,
    detect_discontinuity: bool = True,
    discontinuity_idx: Optional[int] = None
) -> np.ndarray:
    """
    Compute angular velocity from phase-shifted angle data.

    Handles discontinuities created by circular phase shifts by detecting
    and interpolating across them before computing the gradient.

    Args:
        angle_rad: Joint angle in radians (phase-normalized, possibly shifted)
        stride_duration_s: Duration of the stride in seconds
        detect_discontinuity: If True (default), detect and smooth discontinuities.
                              Set False for non-shifted or non-cyclic data.
        discontinuity_idx: If provided, use this index instead of detecting.
                           For 50% phase shift on 150-point data, use 75.

    Returns:
        Angular velocity in rad/s

    Example:
        >>> # After circular_phase_shift(angle_data, 50.0) on 150-point data
        >>> velocity = compute_velocity_from_shifted_angle(
        ...     angle_shifted, stride_duration_s=1.2, discontinuity_idx=75
        ... )
    """
    if len(angle_rad) < 2 or stride_duration_s <= 0:
        return np.full_like(angle_rad, np.nan)

    dt = stride_duration_s / (len(angle_rad) - 1)

    # Use provided index or detect
    if discontinuity_idx is not None:
        # Step 1: Interpolate angle data at discontinuity
        smoothed_angle = interpolate_discontinuity(angle_rad, discontinuity_idx)
        # Step 2: Compute velocity
        velocity = np.gradient(smoothed_angle, dt)
        # Step 3: Smooth any remaining velocity spikes
        velocity = smooth_velocity_spikes(velocity, discontinuity_idx)
        return velocity
    elif detect_discontinuity:
        # Find and interpolate discontinuity
        disc_idx = find_discontinuity_index(angle_rad)
        if disc_idx >= 0:
            smoothed_angle = interpolate_discontinuity(angle_rad, disc_idx)
            velocity = np.gradient(smoothed_angle, dt)
            velocity = smooth_velocity_spikes(velocity, disc_idx)
            return velocity

    # No discontinuity found or detection disabled
    return np.gradient(angle_rad, dt)


def compute_acceleration_from_velocity(
    velocity_rad_s: np.ndarray,
    stride_duration_s: float,
    detect_discontinuity: bool = True,
    discontinuity_idx: Optional[int] = None
) -> np.ndarray:
    """
    Compute angular acceleration from velocity data.

    Args:
        velocity_rad_s: Angular velocity in rad/s
        stride_duration_s: Duration of the stride in seconds
        detect_discontinuity: If True (default), detect and smooth discontinuities
        discontinuity_idx: If provided, use this index instead of detecting.

    Returns:
        Angular acceleration in rad/s^2
    """
    if len(velocity_rad_s) < 2 or stride_duration_s <= 0:
        return np.full_like(velocity_rad_s, np.nan)

    dt = stride_duration_s / (len(velocity_rad_s) - 1)

    # Use provided index or detect
    if discontinuity_idx is not None:
        # Step 1: Interpolate velocity data at discontinuity
        smoothed_vel = interpolate_discontinuity(velocity_rad_s, discontinuity_idx)
        # Step 2: Compute acceleration
        accel = np.gradient(smoothed_vel, dt)
        # Step 3: Smooth any remaining acceleration spikes
        accel = smooth_velocity_spikes(accel, discontinuity_idx)
        return accel
    elif detect_discontinuity:
        disc_idx = find_discontinuity_index(velocity_rad_s)
        if disc_idx >= 0:
            smoothed_vel = interpolate_discontinuity(velocity_rad_s, disc_idx)
            accel = np.gradient(smoothed_vel, dt)
            accel = smooth_velocity_spikes(accel, disc_idx)
            return accel

    return np.gradient(velocity_rad_s, dt)
