# Importing necessary libraries
# %matplotlib ipympl

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Arc, FancyArrowPatch

# Assuming the DataFrame is already loaded and named `df`
# df = pd.read_csv("path_to_your_dataset.csv")
df = pd.read_parquet("all_datasets.parquet")

# Filter for the subjects and level-ground tasks
# Print tasks and subjects
pivot_table = df.pivot_table(index='subject_name', 
                                                columns='task', 
                                                aggfunc='size', 
                                                fill_value=0)
print(pivot_table//150)
df = df[(df['task'] == 'Up Stair') & (df['subject_name'] == 'gtech-AB06')]
print('Length of the filtered dataset:', len(df))
df = df.reset_index(drop=True)

# Sample DataFrame initialization (replace with your actual data)
# df = pd.DataFrame({
#     'time': np.linspace(0, 10, 300),
#     'hip_angle': np.sin(np.linspace(0, 10, 300)) * 45,
#     'knee_angle': np.sin(np.linspace(0, 10, 300)) * 45,
#     'ankle_angle': np.sin(np.linspace(0, 10, 300)) * 45,
#     'hip_torque': np.cos(np.linspace(0, 10, 300)) * 20,
#     'knee_torque': np.cos(np.linspace(0, 10, 300)) * 20,
#     'ankle_torque': np.cos(np.linspace(0, 10, 300)) * 20,
# })

# Define segment lengths
segment_lengths = {'thigh': 1, 'shank': 1, 'foot': 0.5}

def calculate_joint_positions(hip_angle, knee_angle, ankle_angle):
    """
    Calculate the positions of the hip, knee, ankle, and foot based on the given angles.
    """
    hip_angle_rad = -np.radians(hip_angle) # Negative to match the animation coordinate system
    knee_angle_rad = np.radians(knee_angle)
    ankle_angle_rad = -np.radians(ankle_angle) - np.pi / 2 # Adjust for the foot segment

    hip_position = np.array([0, 0])
    knee_position = hip_position + np.array([segment_lengths['thigh'] * np.sin(hip_angle_rad),
                                             -segment_lengths['thigh'] * np.cos(hip_angle_rad)])
    total_knee_angle_rad = hip_angle_rad + knee_angle_rad
    ankle_position = knee_position + np.array([segment_lengths['shank'] * np.sin(total_knee_angle_rad),
                                               -segment_lengths['shank'] * np.cos(total_knee_angle_rad)])
    total_ankle_angle_rad = total_knee_angle_rad + ankle_angle_rad
    foot_position = ankle_position + np.array([segment_lengths['foot'] * np.sin(total_ankle_angle_rad),
                                               -segment_lengths['foot'] * np.cos(total_ankle_angle_rad)])

    return hip_position, knee_position, ankle_position, foot_position

def init_figure_and_elements():
    """
    Initialize the figure with one large subplot for the stick figure animation
    and two smaller subplots for joint angles and torques on the side.
    """
    fig = plt.figure(figsize=(14, 8))

    # Main animation subplot: 2 row, 1 columns, first position
    ax1 = fig.add_subplot(2, 2, (1, 3))
    ax1.set_xlim(-2, 2)
    ax1.set_ylim(-3, 1)

    # Joint angles subplot: 2 rows, 2 columns, second position
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_xlim(0, 150)
    ax2.set_ylim(-90, 90)
    ax2.set_title("Joint Angles Over Last 150 Frames")

    # Joint torques subplot: 2 rows, 2 columns, fourth position
    ax3 = fig.add_subplot(2, 2, 4)
    ax3.set_xlim(0, 150)
    # Adjust these limits based on your torque data range
    ax3.set_ylim(-3, 3)
    ax3.set_title("Joint Torques Over Last 150 Frames")
    
    # Initialize lines for stick figure
    lines = {'hip_knee': ax1.plot([], [], 'ro-')[0],
             'knee_ankle': ax1.plot([], [], 'go-')[0],
             'ankle_foot': ax1.plot([], [], 'bo-')[0]}
    
    # Initialize torque indicators (arcs and arrows)
    torque_indicators = {'hip': Arc((0, 0), 0.5, 0.5, theta1=0, theta2=270, color='red', visible=False),
                         'knee': Arc((0, 0), 0.5, 0.5, theta1=0, theta2=270, color='red', visible=False),
                         'ankle': Arc((0, 0), 0.5, 0.5, theta1=0, theta2=270, color='red', visible=False),
                         'hip_arrow': FancyArrowPatch((0, 0), (0, 0), color='red', visible=False, mutation_scale=10),
                         'knee_arrow': FancyArrowPatch((0, 0), (0, 0), color='red', visible=False, mutation_scale=10),
                         'ankle_arrow': FancyArrowPatch((0, 0), (0, 0), color='red', visible=False, mutation_scale=10)}
    
    for key in torque_indicators:
        ax1.add_patch(torque_indicators[key])

    return fig, ax1, ax2, ax3, lines, torque_indicators


def update_torque_indicator(joint_pos, torque, torque_indicator):
    """
    Update the properties of the torque indicator for a joint based on torque magnitude and direction.

    Parameters:
    - joint_pos: The (x, y) position of the joint around which to display the torque indicator.
    - torque_magnitude: The magnitude of the torque at the joint.
    - torque_direction: The direction of the torque (positive or negative).
    - torque_indicator: A dictionary containing the 'arc' and 'arrow' matplotlib objects for the joint.
    """
    # Set the visibility of the torque indicators
    torque_indicator['arc'].set_visible(True)
    torque_indicator['arrow'].set_visible(True)

    # Set the position and size of the arc
    torque_indicator['arc'].center = joint_pos
    torque_indicator['arc'].width = 0.4  # Adjust as necessary
    torque_indicator['arc'].height = 0.4  # Adjust as necessary

    # Set the color based on the direction of the torque
    color = 'green' if np.sign(torque) >= 0 else 'red'
    torque_indicator['arc'].set_edgecolor(color)

    # Set the opacity based on the magnitude of the torque (normalize based on expected range)
    max_torque = 2.0  # Example maximum expected torque, adjust based on your data
    alpha = abs(torque) / max_torque
    alpha = min(max(alpha, 0.1), 1.0)  # Ensure alpha is between 0.1 and 1.0
    if np.isnan(alpha):
        alpha = 0.1
    torque_indicator['arc'].set_alpha(alpha)

    # Update the arrow position and orientation
    arrow_start = joint_pos
    if np.sign(torque) >= 0:
        arrow_end = (joint_pos[0] + 0.2 * np.sin(np.radians(45)), joint_pos[1] + 0.2 * np.cos(np.radians(45)))
    else:
        arrow_end = (joint_pos[0] - 0.2 * np.sin(np.radians(45)), joint_pos[1] - 0.2 * np.cos(np.radians(45)))
    torque_indicator['arrow'].set_positions(arrow_start, arrow_end)
    torque_indicator['arrow'].set_color(color)
    torque_indicator['arrow'].set_alpha(alpha)


def animate(i, df, ax1, ax2, ax3, lines, torque_indicators):
    """ 
    Animation update function.
    """
    hip_angle, knee_angle, ankle_angle = df.loc[i, ['hip_angle', 'knee_angle', 'ankle_angle']]
    hip_pos, knee_pos, ankle_pos, foot_pos = calculate_joint_positions(hip_angle, knee_angle, ankle_angle)

    # Update stick figure lines
    lines['hip_knee'].set_data([hip_pos[0], knee_pos[0]], [hip_pos[1], knee_pos[1]])
    lines['knee_ankle'].set_data([knee_pos[0], ankle_pos[0]], [knee_pos[1], ankle_pos[1]])
    lines['ankle_foot'].set_data([ankle_pos[0], foot_pos[0]], [ankle_pos[1], foot_pos[1]])

    # Update torque indicators 
    update_torque_indicator(hip_pos, df.loc[i, 'hip_torque'], 
                            {'arc': torque_indicators['hip'], 
                             'arrow': torque_indicators['hip_arrow']}
    )
    update_torque_indicator(knee_pos, df.loc[i, 'knee_torque'], 
                            {'arc': torque_indicators['knee'], 
                             'arrow': torque_indicators['knee_arrow']}
    )
    update_torque_indicator(ankle_pos, df.loc[i, 'ankle_torque'], 
                            {'arc': torque_indicators['ankle'], 
                             'arrow': torque_indicators['ankle_arrow']}
    )

    # Update traces for last 150 data points
    start_idx = max(0, i - 150)
    end_idx = i + 1

    ax2.clear()
    ax2.set_xlim(0, 150)
    ax2.set_ylim(-90, 90)
    ax2.set_title("Joint Angles Over Last 150 Frames")
    ax2.plot(df.loc[start_idx:end_idx, 'hip_angle'].values, label='Hip Angle', color='red')
    ax2.plot(df.loc[start_idx:end_idx, 'knee_angle'].values, label='Knee Angle', color='green')
    ax2.plot(df.loc[start_idx:end_idx, 'ankle_angle'].values, label='Ankle Angle', color='blue')
    ax2.legend()

    ax3.clear()
    ax3.set_xlim(0, 150)
    ax3.set_ylim(-3, 3)
    ax3.set_title("Joint Torques Over Last 150 Frames")
    ax3.plot(df.loc[start_idx:end_idx, 'hip_torque'].values, label='Hip Torque', color='red')
    ax3.plot(df.loc[start_idx:end_idx, 'knee_torque'].values, label='Knee Torque', color='green')
    ax3.plot(df.loc[start_idx:end_idx, 'ankle_torque'].values, label='Ankle Torque', color='blue')
    ax3.legend()

def setup_animation(df):
    """
    Setup and start the animation.
    """
    fig, ax1, ax2, ax3, lines, torque_indicators = init_figure_and_elements()
    anim = FuncAnimation(fig, animate, frames=len(df), interval=100, fargs=(df, ax1, ax2, ax3, lines, torque_indicators))
    plt.show()
    # Optionally, save the animation
    # anim.save('animation.gif', writer=PillowWriter(fps=10))

# Make sure to replace `df` with your actual DataFrame
setup_animation(df)