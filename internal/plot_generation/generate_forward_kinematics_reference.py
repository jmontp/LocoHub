#!/usr/bin/env python3
"""
Generate a reference image for the planar forward kinematic chain.

This script creates a diagram showing:
- The world reference frame (origin and axes) in the bottom-left corner
- An ipsilateral leg (blue), offset from the origin for clarity
- A contralateral leg (orange) in the same pose
- A torso segment (green) above the ipsilateral hip
- Vertical dashed lines as global reference directions at key joints
- Angle arcs:
  - Joint angles θ_hip, θ_knee, θ_ankle on the ipsilateral leg
  - Global segment angles φ_thigh, φ_shank, φ_foot on the contralateral leg

The geometry and conventions match the visualization logic in
``forward_kinematics_plots.KinematicPoseGenerator``.

Usage (from repository root):

    python3 -m internal.plot_generation.generate_forward_kinematics_reference \\
        --output forward_kinematics_reference.png
"""

from __future__ import annotations

import argparse
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np


def _draw_axes(
    ax: plt.Axes,
    origin: Tuple[float, float] = (0.0, 0.0),
    length: float = 1.0,
) -> None:
    """Draw world reference frame axes at a given origin."""
    x0, y0 = origin

    # X axis (forward)
    ax.arrow(
        x0,
        y0,
        length,
        0.0,
        head_width=0.08,
        head_length=0.12,
        length_includes_head=True,
        color="black",
    )
    ax.text(x0 + length * 1.05, y0, "x", fontsize=12, va="center")

    # Y axis (up)
    ax.arrow(
        x0,
        y0,
        0.0,
        length,
        head_width=0.08,
        head_length=0.12,
        length_includes_head=True,
        color="black",
    )
    ax.text(x0, y0 + length * 1.05, "y", fontsize=12, ha="center")

    ax.scatter([x0], [y0], color="black", s=30, zorder=5)
    ax.text(
        x0 + 0.25,
        y0 - 0.12,
        "world origin",
        fontsize=10,
        ha="left",
        va="top",
    )

    # Indicate z-axis (out of the page) at the world origin using the standard
    # circle-with-dot notation.
    z_circle_radius = 0.08
    z_circle = plt.Circle((x0, y0), z_circle_radius, fill=False, color="black", linewidth=1.2)
    ax.add_patch(z_circle)
    ax.scatter([x0], [y0], color="black", s=10, zorder=6)
    ax.text(x0 + 0.12, y0 - 0.10, "z", fontsize=11, va="center", ha="left")


def _draw_leg(
    ax: plt.Axes,
    hip: np.ndarray,
    knee: np.ndarray,
    ankle: np.ndarray,
    foot: np.ndarray,
    color: str,
) -> None:
    """Draw the thigh, shank, and foot segments and mark joints."""
    # Segments
    ax.plot(
        [hip[0], knee[0]],
        [hip[1], knee[1]],
        color=color,
        linewidth=3,
    )
    ax.plot(
        [knee[0], ankle[0]],
        [knee[1], ankle[1]],
        color=color,
        linewidth=3,
    )
    ax.plot(
        [ankle[0], foot[0]],
        [ankle[1], foot[1]],
        color=color,
        linewidth=3,
    )

    # Joints
    joint_kwargs = dict(s=25, color=color, edgecolors="black", zorder=6)
    ax.scatter([hip[0]], [hip[1]], **joint_kwargs)
    ax.scatter([knee[0]], [knee[1]], **joint_kwargs)
    ax.scatter([ankle[0]], [ankle[1]], **joint_kwargs)
    ax.scatter([foot[0]], [foot[1]], **joint_kwargs)


def _angle_annotation(
    ax: plt.Axes,
    position: Tuple[float, float],
    label: str,
    offset: Tuple[float, float],
) -> None:
    """Simple text-only angle label near a joint."""
    x, y = position
    dx, dy = offset
    ax.text(x + dx, y + dy, label, fontsize=10, ha="center", va="center")


def _draw_vertical_reference(
    ax: plt.Axes,
    center: Tuple[float, float],
    length: float = 0.4,
) -> None:
    """Draw a short vertical dashed line *below* a joint as global reference."""
    x = center[0]
    y = center[1]
    ax.plot(
        [x, x],
        [y - length, y],
        linestyle="--",
        color="gray",
        linewidth=1.0,
        alpha=0.9,
    )


def _draw_angle_arc(
    ax: plt.Axes,
    center: np.ndarray,
    start_vec: np.ndarray,
    end_vec: np.ndarray,
    radius: float,
    color: str,
    *,
    draw_refs: bool = True,
) -> None:
    """
    Draw a simple circular arc between two direction vectors around a joint.

    The arc spans the smaller angle between start_vec and end_vec.
    """
    a0 = np.arctan2(start_vec[1], start_vec[0])
    a1 = np.arctan2(end_vec[1], end_vec[0])

    def _wrap(angle: float) -> float:
        """Wrap angle into [-pi, pi] for stable interpolation."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    a0 = _wrap(a0)
    a1 = _wrap(a1)

    # Ensure a1 is ahead of a0 in the positive direction while picking the
    # shorter of the two possible arcs.
    if a1 < a0:
        a0, a1 = a1, a0
    if a1 - a0 > np.pi:
        a0, a1 = a1, a0 + 2 * np.pi

    angles = np.linspace(a0, a1, 40)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    ax.plot(x, y, color=color, linewidth=1.5)

    if draw_refs:
        # Draw dashed radius lines to make the reference directions explicit.
        start_dir = start_vec / (np.linalg.norm(start_vec) + 1e-9)
        end_dir = end_vec / (np.linalg.norm(end_vec) + 1e-9)
        for direction in (start_dir, end_dir):
            ax.plot(
                [center[0], center[0] + radius * direction[0]],
                [center[1], center[1] + radius * direction[1]],
                linestyle="--",
                color=color,
                linewidth=1.0,
                alpha=0.7,
            )


def _draw_segment_reference(
    ax: plt.Axes,
    center: np.ndarray,
    direction: np.ndarray,
    length: float = 0.5,
    color: str = "tab:blue",
) -> None:
    """Draw a dashed line along a segment direction passing through a joint."""
    if np.linalg.norm(direction) < 1e-9:
        return
    d = direction / np.linalg.norm(direction)
    ax.plot(
        [center[0], center[0] + length * d[0]],
        [center[1], center[1] + length * d[1]],
        linestyle="--",
        color=color,
        linewidth=1.0,
        alpha=0.6,
    )


def _compute_leg_positions(
    hip_center: np.ndarray,
    hip_angle_deg: float,
    knee_angle_deg: float,
    ankle_angle_deg: float,
    thigh: float,
    shank: float,
    foot_len: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Forward kinematics for a single planar leg."""
    hip_angle = np.deg2rad(hip_angle_deg)
    knee_angle = np.deg2rad(knee_angle_deg)
    ankle_angle = np.deg2rad(ankle_angle_deg) + np.pi / 2.0

    hip = hip_center
    knee = hip + np.array(
        [
            thigh * np.sin(hip_angle),
            -thigh * np.cos(hip_angle),
        ]
    )
    total_knee_angle = hip_angle - knee_angle
    ankle = knee + np.array(
        [
            shank * np.sin(total_knee_angle),
            -shank * np.cos(total_knee_angle),
        ]
    )
    total_ankle_angle = total_knee_angle + ankle_angle
    foot = ankle + np.array(
        [
            foot_len * np.sin(total_ankle_angle),
            -foot_len * np.cos(total_ankle_angle),
        ]
    )
    return hip, knee, ankle, foot


def generate_reference_figure(output_path: str) -> None:
    """
    Generate and save the forward-kinematics reference diagram.

    Args:
        output_path: Path to the PNG file to create.
    """
    # Match the same simple planar chain used in forward_kinematics_plots
    thigh = 1.0
    shank = 1.0
    foot_len = 0.5

    # Nominal pose (degrees) for illustration
    # Ipsilateral leg: more hip flexion than knee flexion so that the shank
    # has a positive global angle (leans forward).
    hip_angle_ipsi_deg = 40.0
    # Contralateral leg: larger hip extension so that the joint angle at the
    # hip is more apparent relative to the torso reference.
    hip_angle_contra_deg = -35.0
    knee_angle_deg = 20.0
    # Dorsiflexion at ipsilateral ankle; stronger plantarflexion at
    # contralateral ankle so the joint angle is more apparent.
    ankle_angle_ipsi_deg = 30.0
    ankle_angle_contra_deg = -25.0

    # Both hips are attached to the same torso base point for clarity.
    # Shifted upward slightly so the feet do not clip the bottom.
    hip_center = np.array([0.8, 0.3])
    hip_ipsi_center = hip_center
    hip_contra_center = hip_center

    hip_ipsi, knee_ipsi, ankle_ipsi, foot_ipsi = _compute_leg_positions(
        hip_center=hip_ipsi_center,
        hip_angle_deg=hip_angle_ipsi_deg,
        knee_angle_deg=knee_angle_deg,
        ankle_angle_deg=ankle_angle_ipsi_deg,
        thigh=thigh,
        shank=shank,
        foot_len=foot_len,
    )
    hip_contra, knee_contra, ankle_contra, foot_contra = _compute_leg_positions(
        hip_center=hip_contra_center,
        hip_angle_deg=hip_angle_contra_deg,
        knee_angle_deg=knee_angle_deg,
        ankle_angle_deg=ankle_angle_contra_deg,
        thigh=thigh,
        shank=shank,
        foot_len=foot_len,
    )

    fig, ax = plt.subplots(figsize=(7, 7))

    # World axes in bottom-left corner, away from the hips.
    _draw_axes(ax, origin=(-1.8, -1.7), length=0.8)

    # Torso segment (green) above ipsilateral hip with slight forward tilt
    torso_length = 1.5
    # Moderate torso tilt so the global torso angle is visible but not extreme
    torso_angle_deg = 15.0
    torso_theta = np.deg2rad(torso_angle_deg)
    torso_vec = np.array(
        [
            torso_length * np.sin(torso_theta),
            torso_length * np.cos(torso_theta),
        ]
    )
    torso_top = hip_ipsi + torso_vec
    ax.plot(
        [hip_ipsi[0], torso_top[0]],
        [hip_ipsi[1], torso_top[1]],
        color="tab:green",
        linewidth=3,
    )

    # Ipsilateral leg (blue) with joint-angle arcs
    _draw_leg(
        ax,
        hip=hip_ipsi,
        knee=knee_ipsi,
        ankle=ankle_ipsi,
        foot=foot_ipsi,
        color="tab:blue",
    )

    # Contralateral leg (orange) with joint-angle arcs
    _draw_leg(
        ax,
        hip=hip_contra,
        knee=knee_contra,
        ankle=ankle_contra,
        foot=foot_contra,
        color="tab:orange",
    )

    # No global vertical reference lines on contralateral joints; joint angles
    # are defined relative to local dashed references instead.

    # Angle arcs for ipsilateral global angles (φ_*) and contralateral joint
    # angles (θ_*).
    vertical_down = np.array([0.0, -1.0])
    vertical_up = np.array([0.0, 1.0])

    # Global reference lines at ipsilateral hip and knee for φ_thigh and φ_shank
    _draw_vertical_reference(ax, hip_ipsi, length=0.6)
    _draw_vertical_reference(ax, knee_ipsi, length=0.6)

    # Torso global angle φ_torso at hip: between vertical up and torso segment.
    torso_vec = torso_top - hip_ipsi
    _draw_angle_arc(
        ax,
        center=hip_ipsi,
        start_vec=vertical_up,
        end_vec=torso_vec,
        radius=0.32,
        color="tab:green",
        draw_refs=False,
    )
    # Overwrite torso angle reference lines with requested colors:
    # - Vertical reference in gray (matching other global references)
    # - Torso reference (downward from the joint) in green.
    torso_angle_radius = 0.32
    vertical_dir = vertical_up / (np.linalg.norm(vertical_up) + 1e-9)
    torso_down_dir = -torso_vec / (np.linalg.norm(torso_vec) + 1e-9)
    ax.plot(
        [hip_ipsi[0], hip_ipsi[0] + torso_angle_radius * vertical_dir[0]],
        [hip_ipsi[1], hip_ipsi[1] + torso_angle_radius * vertical_dir[1]],
        linestyle="--",
        color="gray",
        linewidth=1.0,
        alpha=0.9,
    )
    ax.plot(
        [hip_ipsi[0], hip_ipsi[0] + torso_angle_radius * torso_down_dir[0]],
        [hip_ipsi[1], hip_ipsi[1] + torso_angle_radius * torso_down_dir[1]],
        linestyle="--",
        color="tab:green",
        linewidth=1.0,
        alpha=0.9,
    )
    _angle_annotation(ax, hip_ipsi, r"$-\phi_{\mathrm{torso}}$", (0.38, 0.32))

    # Global segment angles φ_* on ipsilateral leg (blue)
    thigh_vec_ipsi = knee_ipsi - hip_ipsi
    shank_vec_ipsi = ankle_ipsi - knee_ipsi
    foot_vec_ipsi = foot_ipsi - ankle_ipsi

    # φ_thigh at hip: vertical vs ipsi thigh
    _draw_angle_arc(
        ax,
        center=hip_ipsi,
        start_vec=vertical_down,
        end_vec=thigh_vec_ipsi,
        radius=0.22,
        color="tab:blue",
        draw_refs=False,
    )
    _angle_annotation(ax, hip_ipsi, r"$+\phi_{\mathrm{thigh}}$", (0.18, 0.12))

    # φ_shank at knee: vertical vs ipsi shank
    _draw_angle_arc(
        ax,
        center=knee_ipsi,
        start_vec=vertical_down,
        end_vec=shank_vec_ipsi,
        radius=0.20,
        color="tab:blue",
        draw_refs=False,
    )
    _angle_annotation(ax, knee_ipsi, r"$+\phi_{\mathrm{shank}}$", (0.20, -0.02))

    # Horizontal global reference for φ_foot at ipsilateral ankle (global +x)
    foot_ref_len_ipsi = 0.4
    ax.plot(
        [ankle_ipsi[0], ankle_ipsi[0] + foot_ref_len_ipsi],
        [ankle_ipsi[1], ankle_ipsi[1]],
        linestyle="--",
        color="gray",
        linewidth=1.0,
        alpha=0.9,
    )
    _draw_angle_arc(
        ax,
        center=ankle_ipsi,
        start_vec=np.array([1.0, 0.0]),
        end_vec=foot_vec_ipsi,
        radius=0.20,
        color="tab:blue",
        draw_refs=False,
    )
    _angle_annotation(ax, ankle_ipsi, r"$+\phi_{\mathrm{foot}}$", (0.22, -0.20))

    # Center of pressure (CoP) marker on contralateral foot (red cross),
    # positioned slightly proximal toward the ankle.
    cop_alpha = 0.7  # 0 = at ankle, 1 = at foot tip
    cop_pos = ankle_contra + cop_alpha * (foot_contra - ankle_contra)
    cop_size = 0.06
    ax.plot(
        [cop_pos[0] - cop_size, cop_pos[0] + cop_size],
        [cop_pos[1] - cop_size, cop_pos[1] + cop_size],
        color="red",
        linewidth=1.5,
    )
    ax.plot(
        [cop_pos[0] - cop_size, cop_pos[0] + cop_size],
        [cop_pos[1] + cop_size, cop_pos[1] - cop_size],
        color="red",
        linewidth=1.5,
    )

    # Ground reaction force (GRF) vector shown as a purple arrow originating
    # at the CoP and pointing mostly toward the contralateral hip (combined
    # vertical + shear in the global frame).
    grf_dir = hip_contra - cop_pos
    grf_norm = np.linalg.norm(grf_dir) + 1e-9
    grf_dir = grf_dir / grf_norm
    grf_length = 0.8
    ax.arrow(
        cop_pos[0],
        cop_pos[1],
        grf_length * grf_dir[0],
        grf_length * grf_dir[1],
        head_width=0.06,
        head_length=0.10,
        length_includes_head=True,
        color="purple",
        linewidth=2.0,
    )

    # Joint angles θ_* on contralateral leg (orange)
    # Hip joint angle θ_hip: between torso reference direction and
    # contralateral thigh. We reuse the torso_down_dir direction so that the
    # arc visually terminates on the same torso dashed line orientation.
    thigh_vec_contra = knee_contra - hip_contra
    _draw_angle_arc(
        ax,
        center=hip_contra,
        start_vec=torso_down_dir,
        end_vec=thigh_vec_contra,
        radius=0.26,
        color="tab:orange",
    )
    _angle_annotation(ax, hip_contra, r"$-\theta_{\mathrm{hip}}$", (-0.38, 0.12))

    # Knee joint angle θ_knee: between contralateral thigh and shank
    thigh_from_knee_contra = hip_contra - knee_contra
    shank_vec_contra = ankle_contra - knee_contra
    thigh_ref_down_contra = knee_contra - hip_contra
    _draw_segment_reference(
        ax,
        knee_contra,
        thigh_ref_down_contra,
        length=0.45,
        color="tab:orange",
    )
    _draw_angle_arc(
        ax,
        center=knee_contra,
        start_vec=thigh_ref_down_contra,
        end_vec=shank_vec_contra,
        radius=0.22,
        color="tab:orange",
    )
    _angle_annotation(ax, knee_contra, r"$+\theta_{\mathrm{knee}}$", (-0.40, -0.02))

    # Ankle joint angle θ_ankle: between shank-based reference and foot
    shank_from_ankle_contra = knee_contra - ankle_contra
    shank_ref_contra = np.array(
        [
            shank_from_ankle_contra[1],
            -shank_from_ankle_contra[0],
        ]
    )
    foot_vec_contra = foot_contra - ankle_contra
    _draw_segment_reference(
        ax,
        ankle_contra,
        shank_ref_contra,
        length=0.45,
        color="tab:orange",
    )
    _draw_angle_arc(
        ax,
        center=ankle_contra,
        start_vec=shank_ref_contra,
        end_vec=foot_vec_contra,
        radius=0.24,
        color="tab:orange",
    )
    _angle_annotation(ax, ankle_contra, r"$-\theta_{\mathrm{ankle}}$", (-0.40, -0.26))

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (forward)")
    ax.set_ylabel("y (up)")

    # Set view limits so everything is clearly visible
    ax.set_xlim(-2.1, 2.6)
    ax.set_ylim(-2.0, 2.7)

    ax.set_title(
        "Planar Forward Kinematic Chain\n"
        "Global (ipsilateral, blue) and joint (contralateral, orange) angles"
    )

    # Legend block describing the main visual elements
    legend_lines = [
        plt.Line2D([0], [0], color="black", linewidth=2, label="world axes"),
        plt.Line2D([0], [0], color="tab:green", linewidth=3, label="torso segment"),
        plt.Line2D([0], [0], color="tab:blue", linewidth=3, label="ipsilateral leg"),
        plt.Line2D(
            [0],
            [0],
            color="tab:orange",
            linewidth=3,
            label="contralateral leg",
        ),
        plt.Line2D(
            [0],
            [0],
            color="gray",
            linewidth=1.5,
            linestyle="--",
            label="global reference lines",
        ),
        plt.Line2D(
            [0],
            [0],
            color="tab:blue",
            linewidth=1.5,
            label=r"segment / torso angles $\phi_*$ (global, ipsi)",
        ),
        plt.Line2D(
            [0],
            [0],
            color="tab:orange",
            linewidth=1.5,
            label=r"joint angles $\theta_*$ (contra)",
        ),
        plt.Line2D(
            [0],
            [0],
            color="red",
            linewidth=1.5,
            marker="x",
            markersize=6,
            label="center of pressure (CoP, ankle frame)",
        ),
        plt.Line2D(
            [0],
            [0],
            color="purple",
            linewidth=2.0,
            label="ground reaction force (GRF, global frame)",
        ),
    ]
    ax.legend(
        handles=legend_lines,
        loc="upper left",
        fontsize=8,
        framealpha=0.9,
    )

    # Explanatory text below the legend describing how joint angles are
    # related to link (segment) angles in this schematic.
    definitions_text = (
        r"Definitions (schematic):" "\n"
        r"$\phi_*$: global link angles (ipsilateral leg)" "\n"
        r"$\theta_{\mathrm{hip}} = \phi_{\mathrm{thigh}} - \phi_{\mathrm{torso}}$" "\n"
        r"$\theta_{\mathrm{knee}} = \phi_{\mathrm{shank}} - \phi_{\mathrm{thigh}}$" "\n"
        r"$\theta_{\mathrm{ankle}} = \phi_{\mathrm{foot}} - (\phi_{\mathrm{shank}} - 90^\circ)$"
    )
    ax.text(
        0.02,
        0.72,
        definitions_text,
        transform=ax.transAxes,
        fontsize=7,
        va="top",
    )

    # Remove tick labels for a cleaner diagram, keep axes labels
    ax.set_xticks([])
    ax.set_yticks([])

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reference image for the planar forward kinematic chain."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="forward_kinematics_reference.png",
        help="Path to the output PNG file (default: forward_kinematics_reference.png)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    generate_reference_figure(args.output)


if __name__ == "__main__":
    main()
