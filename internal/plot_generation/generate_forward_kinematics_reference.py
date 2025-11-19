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
    base_hip_angle_deg = 20.0
    # Ipsilateral leg tilted forward, contralateral tilted backward
    hip_angle_ipsi_deg = base_hip_angle_deg
    hip_angle_contra_deg = -base_hip_angle_deg
    knee_angle_deg = 40.0
    # Use a larger dorsiflexion angle for the ipsilateral foot so that
    # the ankle joint angle θ_ankle is visually apparent.
    ankle_angle_ipsi_deg = 30.0
    ankle_angle_contra_deg = -5.0

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
    # Increase torso tilt so the global torso angle is more apparent
    torso_angle_deg = 25.0
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

    # Contralateral leg (orange) with global-angle arcs
    _draw_leg(
        ax,
        hip=hip_contra,
        knee=knee_contra,
        ankle=ankle_contra,
        foot=foot_contra,
        color="tab:orange",
    )

    # Global reference lines at contralateral joints
    # Hip and knee use vertical (global y) references.
    _draw_vertical_reference(ax, hip_contra, length=0.6)
    _draw_vertical_reference(ax, knee_contra, length=0.6)
    # For the foot global angle, use a horizontal dashed line (global +x)
    # extending to the right of the ankle so that the reference for φ_foot
    # is rotated 90° from vertical and clearly visible.
    foot_ref_len = 0.4
    ax.plot(
        [ankle_contra[0], ankle_contra[0] + foot_ref_len],
        [ankle_contra[1], ankle_contra[1]],
        linestyle="--",
        color="gray",
        linewidth=1.0,
        alpha=0.9,
    )

    # Angle arcs for ipsilateral joint definitions (θ_*) and global angles (φ_*).
    vertical_down = np.array([0.0, -1.0])
    vertical_up = np.array([0.0, 1.0])

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
    _angle_annotation(ax, hip_ipsi, r"$\phi_{\mathrm{torso}}$", (0.38, 0.32))

    # Hip joint angle θ_hip: between torso (previous link) and ipsilateral thigh.
    # Use a torso reference pointing downwards from the hip to keep the dashed
    # line on the same side as the legs.
    torso_ref = -torso_vec
    thigh_vec_ipsi = knee_ipsi - hip_ipsi
    # Torso reference line in green to match the torso segment
    _draw_segment_reference(ax, hip_ipsi, torso_ref, length=0.5, color="tab:green")
    # Use a slightly smaller radius for θ_hip so its arc does not intersect
    # with the larger global thigh/torso arcs on the contralateral side.
    _draw_angle_arc(
        ax,
        center=hip_ipsi,
        start_vec=torso_ref,
        end_vec=thigh_vec_ipsi,
        radius=0.22,
        color="tab:blue",
    )
    # Place θ labels on the left side of the ipsilateral leg to avoid overlap
    # Place ipsilateral joint labels to the right, near their arcs
    _angle_annotation(ax, hip_ipsi, r"$\theta_{\mathrm{hip}}$", (0.35, 0.18))

    # Knee joint angle θ_knee: between thigh (knee→hip, previous link) and shank.
    thigh_from_knee_ipsi = hip_ipsi - knee_ipsi  # knee -> hip (used for angle)
    shank_vec_ipsi = ankle_ipsi - knee_ipsi      # knee -> ankle (solid shank)
    # Dashed reference along the thigh but extended away from the hip (down the leg)
    thigh_ref_down = knee_ipsi - hip_ipsi
    _draw_segment_reference(
        ax,
        knee_ipsi,
        thigh_ref_down,
        length=0.45,
        color="tab:blue",
    )
    _draw_angle_arc(
        ax,
        center=knee_ipsi,
        start_vec=thigh_ref_down,
        end_vec=shank_vec_ipsi,
        radius=0.24,
        color="tab:blue",
    )
    _angle_annotation(ax, knee_ipsi, r"$\theta_{\mathrm{knee}}$", (0.35, -0.05))

    # Ankle joint angle θ_ankle: between shank-based reference (previous link + 90°)
    # and the foot segment.
    shank_from_ankle_ipsi = knee_ipsi - ankle_ipsi  # ankle -> knee
    # Rotate shank vector by -90° so the dashed ankle-reference line is
    # shifted by 90° relative to the shank direction for the foot angle.
    shank_ref = np.array(
        [
            shank_from_ankle_ipsi[1],
            -shank_from_ankle_ipsi[0],
        ]
    )
    foot_vec_ipsi = foot_ipsi - ankle_ipsi
    _draw_segment_reference(
        ax,
        ankle_ipsi,
        shank_ref,
        length=0.45,
        color="tab:blue",
    )
    _draw_angle_arc(
        ax,
        center=ankle_ipsi,
        start_vec=shank_ref,
        end_vec=foot_vec_ipsi,
        radius=0.28,
        color="tab:blue",
    )
    _angle_annotation(ax, ankle_ipsi, r"$\theta_{\mathrm{ankle}}$", (0.40, -0.30))

    # Center of pressure (CoP) marker on ipsilateral foot (red cross),
    # positioned slightly proximal toward the ankle.
    cop_alpha = 0.7  # 0 = at ankle, 1 = at foot tip
    cop_pos = ankle_ipsi + cop_alpha * (foot_ipsi - ankle_ipsi)
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
    # at the CoP and pointing mostly toward the hip (combined vertical + shear).
    grf_dir = hip_ipsi - cop_pos
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

    # Global-angle arcs (φ_*) on contralateral leg versus vertical.
    # Thigh global angle at hip: vertical down vs thigh vector.
    thigh_vec_contra = knee_contra - hip_contra
    # Keep φ_thigh at a larger radius so it is visually separated from θ_hip.
    _draw_angle_arc(
        ax,
        center=hip_contra,
        start_vec=vertical_down,
        end_vec=thigh_vec_contra,
        radius=0.30,
        color="tab:orange",
        draw_refs=False,
    )
    # Place contralateral global thigh/shank/foot labels to the left of that leg
    _angle_annotation(ax, hip_contra, r"$\phi_{\mathrm{thigh}}$", (-0.40, 0.15))

    # Shank global angle at knee: vertical down vs shank.
    shank_vec_contra = ankle_contra - knee_contra
    _draw_angle_arc(
        ax,
        center=knee_contra,
        start_vec=vertical_down,
        end_vec=shank_vec_contra,
        radius=0.24,
        color="tab:orange",
        draw_refs=False,
    )
    _angle_annotation(ax, knee_contra, r"$\phi_{\mathrm{shank}}$", (-0.40, 0.00))

    # Foot global angle at ankle: vertical down vs foot.
    foot_vec_contra = foot_contra - ankle_contra
    _draw_angle_arc(
        ax,
        center=ankle_contra,
        # Start from global +x (aligned with the horizontal dashed reference)
        start_vec=np.array([1.0, 0.0]),
        end_vec=foot_vec_contra,
        radius=0.22,
        color="tab:orange",
        draw_refs=False,
    )
    # Place the foot global-angle label closer to its arc
    _angle_annotation(ax, ankle_contra, r"$\phi_{\mathrm{foot}}$", (-0.30, -0.20))

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (forward)")
    ax.set_ylabel("y (up)")

    # Set view limits so everything is clearly visible
    ax.set_xlim(-2.1, 2.6)
    ax.set_ylim(-2.0, 2.7)

    ax.set_title(
        "Planar Forward Kinematic Chain\n"
        "Joint (ipsilateral, blue) and global (contralateral, orange) angles"
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
            label="vertical reference (global)",
        ),
        plt.Line2D(
            [0],
            [0],
            color="tab:blue",
            linewidth=1.5,
            label=r"joint angles $\theta_*$ (ipsi)",
        ),
        plt.Line2D(
            [0],
            [0],
            color="tab:orange",
            linewidth=1.5,
            label=r"segment / torso angles $\phi_*$ (global)",
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
