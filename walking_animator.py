# Importing necessary libraries
# %matplotlib ipympl

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Arc, FancyArrowPatch

# Assuming the DataFrame is already loaded and named `df`
# df = pd.read_csv("path_to_your_dataset.csv")
# df = pd.read_parquet("all_datasets_c.parquet")

# The features that are used in the Georgia Tech non cyclic data
dataset_features = [
    

    'hip_flexion_l','hip_flexion_l_moment',
    'knee_angle_l', 'ankle_angle_l', 'foot_angle_l', 
    'knee_velocity_l', 'ankle_velocity_l', 'foot_velocity_l', 
    'knee_angle_l_moment', 'ankle_angle_l_moment', 

    'hip_flexion_r','hip_flexion_r_moment',
    'knee_angle_r', 'ankle_angle_r', 'foot_angle_r',
    'knee_velocity_r', 'ankle_velocity_r', 'foot_velocity_r',
    'knee_angle_r_moment', 'ankle_angle_r_moment',
    
    'activity', 'subject', 'time'
]

# Load the data
print("Loading Georgia Tech non cyclic data")
df = pd.read_parquet('../energy_shaping_ML/datasets/gtech_non_cyclic_raw.parquet',
                                          columns=dataset_features)

# Convert to the standardized naming
df.columns = [
    'hip_angle', 'hip_torque',
    'knee_angle', 'ankle_angle', 'foot_angle',
    'knee_velocity', 'ankle_velocity', 'foot_velocity', 
    'knee_torque', 'ankle_torque', 

    'hip_angle_c','hip_torque_c',
    'knee_angle_c', 'ankle_angle_c', 'foot_angle_c',
    'knee_velocity_c', 'ankle_velocity_c', 'foot_velocity_c',
    'knee_torque_c', 'ankle_torque_c',
    
    'task', 'subject_name', 'time'
]

# Flip everything but task, subject_name, and time
for feature in df.columns:
    if feature not in ['task', 'subject_name', 'time']:
        df[feature] = -df[feature]


# Filter for the subjects and level-ground tasks
# Print tasks and subjects
pivot_table = df.pivot_table(index='subject_name', 
                                                columns='task', 
                                                aggfunc='size', 
                                                fill_value=0)
print(df.columns)
print(pivot_table//150)
task = "normal_walk"
subject = "Gtech_NC_AB01"
df = df[(df['task'] == task) & (df['subject_name'] == subject)]
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

# Define segment lengths (same for both legs)
segment_lengths = {'thigh': 1, 'shank': 1, 'foot': 0.5, 'torso': 2}
torque_labels = ['hip_torque', 'knee_torque', 'ankle_torque',
                 'hip_torque_c', 'knee_torque_c', 'ankle_torque_c']

def calculate_joint_positions(hip_angle, knee_angle, ankle_angle):
    """
    Calculate the positions of the hip, knee, ankle, and foot based on the given angles.
    Adjust angles to match the animation coordinate system.
    """
    hip_angle_rad = -np.radians(hip_angle)
    knee_angle_rad = np.radians(knee_angle)
    ankle_angle_rad = -np.radians(ankle_angle) - np.pi / 2

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
    Initialize the figure with a layout for five subplots.
    """
    fig = plt.figure(figsize=(18, 10))
    grid_spec = fig.add_gridspec(3, 3)

    # Main stick figure animation subplot
    ax1 = fig.add_subplot(grid_spec[0:2, 0:2])
    ax1.set_xlim(-3, 3)
    ax1.set_ylim(-3, 1)
    ax1.set_aspect('equal')
    ax1.set_title(f"Joint Kinematics for {subject} doing {task}")

    # Subplots for joint angles and torques of both legs
    ax2 = fig.add_subplot(grid_spec[2, 0])
    ax2.set_title("Joint Angles (Normal Leg)")
    ax2_data = [ax2.plot([], [], 'r-', label='Hip Angle')[0], 
                ax2.plot([], [], 'g-', label='Knee Angle')[0], 
                ax2.plot([], [], 'b-', label='Ankle Angle')[0]]
    
    ax3 = fig.add_subplot(grid_spec[2, 1])
    ax3.set_title("Joint Angles (Contralateral Leg)")
    ax3_data = [ax3.plot([], [], 'r--', label='Hip Angle (C)')[0],
                ax3.plot([], [], 'g--', label='Knee Angle (C)')[0],
                ax3.plot([], [], 'b--', label='Ankle Angle (C)')[0]]


    ax4 = fig.add_subplot(grid_spec[0, 2])
    ax4.set_title("Joint Torques (Normal Leg)")
    ax4_data = [ax4.plot([], [], 'r-', label='Hip Torque')[0],
                ax4.plot([], [], 'g-', label='Knee Torque')[0],
                ax4.plot([], [], 'b-', label='Ankle Torque')[0]]
    
    ax5 = fig.add_subplot(grid_spec[1, 2])
    ax5.set_title("Joint Torques (Contralateral Leg)")
    ax5_data = [ax5.plot([], [], 'r--', label='Hip Torque (C)')[0],
                ax5.plot([], [], 'g--', label='Knee Torque (C)')[0],
                ax5.plot([], [], 'b--', label='Ankle Torque (C)')[0]]

    ax6 = fig.add_subplot(grid_spec[2, 2])
    ax6.set_title("Global Foot Angle (Normal Leg)")
    ax6_data = [ax6.plot([], [], 'b-', label='Foot Angle')[0],
                ax6.plot([], [], 'b--', label='Foot Angle (C)')[0]]

    # Initialize lines for stick figure animation
    lines = {
        'torso': ax1.plot([], [], 'k-')[0],
        'hip_knee': ax1.plot([], [], 'ro-')[0],
        'knee_ankle': ax1.plot([], [], 'go-')[0],
        'ankle_foot': ax1.plot([], [], 'bo-')[0],
        'hip_knee_c': ax1.plot([], [], 'r.--')[0],  # Dotted lines for contralateral leg
        'knee_ankle_c': ax1.plot([], [], 'g.--')[0],
        'ankle_foot_c': ax1.plot([], [], 'b.--')[0]
    }

    # Initialize torque indicators for both legs if needed
    torque_markers = {
        'hip_torque': ax1.scatter([], [], s=50, marker='o', color='yellow'),  
        'knee_torque': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'ankle_torque': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'hip_torque_c': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'knee_torque_c': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'ankle_torque_c': ax1.scatter([], [], s=50, marker='o', color='yellow')
      }

    return fig, ax1, (ax2,ax2_data), (ax3,ax3_data), (ax4,ax4_data), \
           (ax5,ax5_data), (ax6,ax6_data), lines, torque_markers

def animate(i, df, ax1, ax2, ax3, ax4, ax5, ax6, lines, torque_markers):
    """
    Update the animation for both the normal and contralateral legs and the plots for joint angles and torques.
    """
    # Print in the same line the current iteration
    print(f"\rProcessing frame {i+1}/{len(df)}", end='')

    #Set the torso position to be vertical 
    lines['torso'].set_data([0, 0], [0, segment_lengths['torso']])

    # Update stick figure for the normal leg
    hip_angle, knee_angle, ankle_angle = df.loc[i, ['hip_angle', 'knee_angle', 'ankle_angle']]
    hip_pos, knee_pos, ankle_pos, foot_pos = calculate_joint_positions(hip_angle, knee_angle, ankle_angle)

    # Calculate the global foot angle as the dot product of the vectors 
    # (foot - ankle) and (-1, 0)
    foot_angle = np.arccos(np.dot((foot_pos - ankle_pos), np.array([-1, 0])) /
                            (np.linalg.norm(foot_pos - ankle_pos)))
    # Rotate all the points by the global foot angle to align the foot with the y-axis
    rotation_matrix = np.array([[np.cos(foot_angle), -np.sin(foot_angle)],
                                [np.sin(foot_angle), np.cos(foot_angle)]])
    hip_pos = np.dot(rotation_matrix, hip_pos)
    knee_pos = np.dot(rotation_matrix, knee_pos)
    ankle_pos = np.dot(rotation_matrix, ankle_pos)
    foot_pos = np.dot(rotation_matrix, foot_pos)
    
    # Set the stick figure lines to the new positions
    lines['hip_knee'].set_data([hip_pos[0], knee_pos[0]], [hip_pos[1], knee_pos[1]])
    lines['knee_ankle'].set_data([knee_pos[0], ankle_pos[0]], [knee_pos[1], ankle_pos[1]])
    lines['ankle_foot'].set_data([ankle_pos[0], foot_pos[0]], [ankle_pos[1], foot_pos[1]])

    # Update stick figure for the contralateral leg
    hip_angle_c, knee_angle_c, ankle_angle_c = df.loc[i, ['hip_angle_c', 'knee_angle_c', 'ankle_angle_c']]
    hip_pos_c, knee_pos_c, ankle_pos_c, foot_pos_c = calculate_joint_positions(hip_angle_c, knee_angle_c, ankle_angle_c)

    # Calculate the global foot angle as the dot product of the vectors
    # (foot - ankle) and (-1, 0)
    foot_angle_c = np.arccos(np.dot((foot_pos_c - ankle_pos_c), np.array([-1, 0])) /
                            (np.linalg.norm(foot_pos_c - ankle_pos_c)))
    # Rotate all the points by the global foot angle to align the foot with the y-axis
    rotation_matrix_c = np.array([[np.cos(foot_angle_c), -np.sin(foot_angle_c)],
                                [np.sin(foot_angle_c), np.cos(foot_angle_c)]])

    # Rotate all the points by the global foot angle to align the foot with the y-axis
    hip_pos_c = np.dot(rotation_matrix_c, hip_pos_c)
    knee_pos_c = np.dot(rotation_matrix_c, knee_pos_c)
    ankle_pos_c = np.dot(rotation_matrix_c, ankle_pos_c)
    foot_pos_c = np.dot(rotation_matrix_c, foot_pos_c)
    
    lines['hip_knee_c'].set_data([hip_pos_c[0], knee_pos_c[0]], [hip_pos_c[1], knee_pos_c[1]])
    lines['knee_ankle_c'].set_data([knee_pos_c[0], ankle_pos_c[0]], [knee_pos_c[1], ankle_pos_c[1]])
    lines['ankle_foot_c'].set_data([ankle_pos_c[0], foot_pos_c[0]], [ankle_pos_c[1], foot_pos_c[1]])

    # Set the x-axis limits for the joint angles and torques plots
    start_idx = max(0, i - 150)
    end_idx = i + 1
    x_axis = np.arange(start_idx, end_idx+1)

    # Update joint angles plot for the normal leg
    ax2, ax2_data = ax2
    ax2_data[0].set_data(x_axis,df.loc[start_idx:end_idx, 'hip_angle'])
    ax2_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_angle'])
    ax2_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_angle'])
    ax2.set_ylim(-180, 180)
    ax2.set_xlim(start_idx, end_idx)

    # Update joint angles plot for the contralateral leg
    ax3, ax3_data = ax3
    ax3_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_angle_c'])
    ax3_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_angle_c'])
    ax3_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_angle_c'])
    ax3.set_ylim(-180, 180)
    ax3.set_xlim(start_idx, end_idx)

    # Update joint torques plot for the normal leg
    ax4, ax4_data = ax4
    ax4_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_torque'])
    ax4_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_torque'])
    ax4_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_torque'])
    ax4.set_ylim(-180, 180)
    ax4.set_xlim(start_idx, end_idx)

    # Update joint torques plot for the contralateral leg
    ax5, ax5_data = ax5
    ax5_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_torque_c'])
    ax5_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_torque_c'])
    ax5_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_torque_c'])
    ax5.set_ylim(-180, 180)
    ax5.set_xlim(start_idx, end_idx)

    # Update global foot angle plot for the normal and contralateral leg
    ax6, ax6_data = ax6
    ax6_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_angle'])
    ax6_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_angle_c'])
    ax6.set_ylim(-180, 180)
    ax6.set_xlim(start_idx, end_idx)

    # Update torque markers positions
    torque_markers['hip_torque'].set_offsets([hip_pos])
    torque_markers['knee_torque'].set_offsets([knee_pos])
    torque_markers['ankle_torque'].set_offsets([ankle_pos])
    torque_markers['hip_torque_c'].set_offsets([hip_pos_c])
    torque_markers['knee_torque_c'].set_offsets([knee_pos_c])
    torque_markers['ankle_torque_c'].set_offsets([ankle_pos_c])

    # Update the shapes of the torque markers
    # Update hip torque marker based on torque direction
    max_torque = 2.0 # Nm/kg
    markers = [plt.matplotlib.markers.MarkerStyle(marker='x'), 
               plt.matplotlib.markers.MarkerStyle(marker='o', 
                                                  fillstyle='full')]
    markers_styles = {t:markers[1] if df.loc[i,t] >= 0 else markers[0] 
                      for t in torque_labels}
    markers_colors = {t:'purple' if df.loc[i,t] >= 0 else 'orange' 
                      for t in torque_labels}
    marker_opacity = {t:np.nan_to_num(abs(df.loc[i,t])/max_torque)  
                      for t in torque_labels}
    for label in torque_labels:
        torque_markers[label].set_paths([markers_styles[label].get_path()])
        torque_markers[label].set_color(markers_colors[label])
        torque_markers[label].set_alpha(marker_opacity[label])
    

def setup_animation(df):
    """
    Setup and start the animation with the adjusted layout and data.
    """
    fig, ax1, ax2, ax3, ax4, ax5, ax6, lines, torque_markers = init_figure_and_elements()
    anim = FuncAnimation(fig, animate, frames=len(df), interval=1,
                         fargs=(df, ax1, ax2, ax3, ax4, ax5, ax6, lines, torque_markers))
    plt.show()
    # Optionally, save the animation
    # anim.save('animation.gif', writer='imagemagick', fps=10)

# Ensure df is correctly loaded with contralateral columns before calling setup_animation
setup_animation(df)