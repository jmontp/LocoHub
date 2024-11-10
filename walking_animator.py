# Importing necessary libraries
# %matplotlib ipympl

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Arc, FancyArrowPatch
import os
import argparse

# Create the argument parser
parser = argparse.ArgumentParser(description='Walking Animator')

# Add the command line arguments
parser.add_argument('-f', '--file', type=str, help='Path to the parquet file')
parser.add_argument('-s', '--subject', type=str, help='Subject name')
parser.add_argument('-t', '--task', type=str, help='Task name')
parser.add_argument('-p', '--pivot', action=argparse.BooleanOptionalAction)
parser.add_argument('-c', '--columns', action=argparse.BooleanOptionalAction)
parser.add_argument('-j', '--jump-points', type=int, default=0,
                    help='Start running at this frame')
parser.add_argument('-g', '--save-gif', action=argparse.BooleanOptionalAction)

# Parse the command line arguments
args = parser.parse_args()

# Get the values from the command line arguments
parquet_file = args.file
subject = args.subject
task = args.task
pivot = args.pivot
columns = args.columns
jump_points = args.jump_points
save_gif = args.save_gif

# Assuming the DataFrame is already loaded and named `df`
df = pd.read_parquet(parquet_file)

# If the pivot argument is given, create a pivot column for the given dataset,
# print it out and then exit
if pivot:
    # Create a pivot column for the given dataset
    pivot_table = df.pivot_table(index='subject', 
        columns='task', aggfunc='size', fill_value=0)
    print(pivot_table//150)
    # Exit the program
    exit()

# If the columns argument is given, print the columns of the DataFrame and exit
if columns:
    print(list(df.columns))
    exit()

# If a subject and task are not given, print the available subjects and tasks
if subject is None or task is None:
    print("Available subjects:")
    print(df['subject'].unique())
    print("Available tasks:")
    print(df['task'].unique())
    exit()


# Filter the DataFrame to only include the desired task and subject
df = df[(df['task'] == task) & (df['subject'] == subject)]
df = df.reset_index(drop=True)
df = df.loc[jump_points:].reset_index(drop=True)

###############################################################################
# Temporary fixes to the dataset that I am analyzing

GLOBAL_FOOT_ANGLE_ROTATION = True
###############################################################################

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
torque_labels = ['hip_torque_s_r', 'knee_torque_s_r', 'ankle_torque_s_r',
                 'hip_torque_s_l', 'knee_torque_s_l', 'ankle_torque_s_l']
right_angles = ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r']
left_angles = ['hip_angle_s_l', 'knee_angle_s_l', 'ankle_angle_s_l']

def calculate_joint_positions(hip_angle, knee_angle, ankle_angle):
    """
    Calculate the positions of the hip, knee, ankle, and foot based on the given angles.
    Adjust angles to match the animation coordinate system.
    """
    hip_angle_rad = np.radians(hip_angle)
    knee_angle_rad = np.radians(knee_angle)
    ankle_angle_rad = np.radians(ankle_angle) + np.pi / 2

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
    fig = plt.figure(figsize=(18, 18))
    grid_spec = fig.add_gridspec(4, 3)

    # Set the y-axis limits for the joint angles and torques plots
    angle_ylim = (-130, 130)
    torque_ylim = (-3, 3)

    # Main stick figure animation subplot
    ax1 = fig.add_subplot(grid_spec[0:2, 0:2])
    ax1.set_xlim(-3, 3)
    ax1.set_ylim(-3, 1)
    ax1.set_aspect('equal')
    ax1.set_title(f"Joint Kinematics for {subject} doing {task}")
    ax1.xaxis.set_visible(False) 
    ax1.yaxis.set_visible(False)

    # Subplots for joint angles and torques of both legs
    ax2 = fig.add_subplot(grid_spec[2, 0])
    ax2.set_title("Joint Angles (Right Leg)")
    ax2.set_xlim(0, 150)
    ax2.set_ylim(*angle_ylim)
    ax2.xaxis.set_visible(False) 
    ax2_data = [ax2.plot([], [], 'r-', label='Hip Angle')[0], 
                ax2.plot([], [], 'g-', label='Knee Angle')[0], 
                ax2.plot([], [], 'b-', label='Ankle Angle')[0]]
    
    # Joint angles plot for the left leg
    ax3 = fig.add_subplot(grid_spec[2, 1])
    ax3.set_title("Joint Angles (Left Leg)")
    ax3.set_xlim(0, 150)
    ax3.set_ylim(*angle_ylim)
    ax3.xaxis.set_visible(False) 
    ax3_data = [ax3.plot([], [], 'r--', label='Hip Angle')[0],
                ax3.plot([], [], 'g--', label='Knee Angle')[0],
                ax3.plot([], [], 'b--', label='Ankle Angle')[0]]

    # Joint torques plot for the right leg
    ax4 = fig.add_subplot(grid_spec[0, 2])
    ax4.set_title("Joint Torques (Right Leg)")
    ax4.set_xlim(0, 150)
    ax4.set_ylim(*torque_ylim)
    ax4.xaxis.set_visible(False) 
    ax4_data = [ax4.plot([], [], 'r-', label='Hip Torque')[0],
                ax4.plot([], [], 'g-', label='Knee Torque')[0],
                ax4.plot([], [], 'b-', label='Ankle Torque')[0]]
    
    # Joint torques plot for the left leg
    ax5 = fig.add_subplot(grid_spec[1, 2])
    ax5.set_title("Joint Torques (Left Leg)")
    ax5.set_xlim(0, 150)
    ax5.set_ylim(*torque_ylim)
    ax5.xaxis.set_visible(False)
    ax5_data = [ax5.plot([], [], 'r--', label='Hip Torque')[0],
                ax5.plot([], [], 'g--', label='Knee Torque')[0],
                ax5.plot([], [], 'b--', label='Ankle Torque')[0]]
    
    # Global foot angle plot for both legs
    ax6 = fig.add_subplot(grid_spec[2, 2])
    ax6.set_title("Global Foot Angle (Right Leg)")
    ax6.set_xlim(0, 150)
    ax6.set_ylim(*angle_ylim)
    ax6.xaxis.set_visible(False)
    ax6_data = [ax6.plot([], [], 'b-', label='Foot Angle Right')[0],
                ax6.plot([], [], 'b--', label='Foot Angle Left')[0]]
    
    # Joint Velocities plot for the right leg
    ax7 = fig.add_subplot(grid_spec[3, 0])
    ax7.set_title("Joint Velocities (Right Leg)")
    ax7.set_xlim(0, 150)
    ax7.set_ylim(-400, 400)
    ax7.xaxis.set_visible(False)
    ax7_data = [ax7.plot([], [], 'r-', label='Hip Velocity')[0],
                ax7.plot([], [], 'g-', label='Knee Velocity')[0],
                ax7.plot([], [], 'b-', label='Ankle Velocity')[0]
               ]
    
    # Joint Velocities plot for the left leg
    ax8 = fig.add_subplot(grid_spec[3, 1])
    ax8.set_title("Joint Velocities (Left Leg)")
    ax8.set_xlim(0, 150)
    ax8.set_ylim(-400, 400)
    ax8.xaxis.set_visible(False)
    ax8_data = [ax8.plot([], [], 'r--', label='Hip Velocity')[0],
                ax8.plot([], [], 'g--', label='Knee Velocity')[0],
                ax8.plot([], [], 'b--', label='Ankle Velocity')[0]
               ]
    
    # Global foot angle plot for both legs
    ax9 = fig.add_subplot(grid_spec[3, 2])
    ax9.set_title("Global Foot Velocity (Right Leg)")
    ax9.set_xlim(0, 150)
    ax9.set_ylim(-400, 400)
    ax9.xaxis.set_visible(False)
    ax9_data = [ax9.plot([], [], 'b-', label='Foot Velocity Right')[0],
                ax9.plot([], [], 'b--', label='Foot Velocity Left')[0]]
    
    # Create a line at zero for all the joint angles and torques plots
    for ax in [ax2, ax3, ax4, ax5, ax6]:
        ax.axhline(0, color='black', lw=1, alpha=0.3)

    # Initialize lines for stick figure animation
    lines = {
        'torso': ax1.plot([], [], 'k-')[0],
        'hip_knee_s_r': ax1.plot([], [], 'ro-', label='hip_r')[0],
        'knee_ankle_s_r': ax1.plot([], [], 'go-', label='knee_r')[0],
        'ankle_foot_s_r': ax1.plot([], [], 'bo-', label='hip_r')[0],
        'hip_knee_s_l': ax1.plot([], [], 'r.--', label='hip_l')[0],  # Dotted lines for left leg
        'knee_ankle_s_l': ax1.plot([], [], 'g.--', label='knee_l')[0],
        'ankle_foot_s_l': ax1.plot([], [], 'b.--', label='ankle_r')[0]
    }
    # Create horizontal lines for the ground
    heel_position = segment_lengths['shank']+segment_lengths['thigh']
    ax1.plot([-3, 3], [-heel_position, -heel_position], 'k-')

    # Initialize torque indicators for both legs if needed
    torque_markers = {
        'hip_torque_s_r': ax1.scatter([], [], s=50, marker='o', color='yellow'),  
        'knee_torque_s_r': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'ankle_torque_s_r': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'hip_torque_s_l': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'knee_torque_s_l': ax1.scatter([], [], s=50, marker='o', color='yellow'),
        'ankle_torque_s_l': ax1.scatter([], [], s=50, marker='o', color='yellow')
      }
    
    # Add legends to the plots
    ax1.legend(loc='upper right')
    ax2.legend(loc='upper right')
    ax3.legend(loc='upper right')
    ax4.legend(loc='upper right')
    ax5.legend(loc='upper right')
    ax6.legend(loc='upper right')
    ax7.legend(loc='upper right')
    ax8.legend(loc='upper right')
    ax9.legend(loc='upper right')


    return fig, ax1, (ax2,ax2_data), (ax3,ax3_data), (ax4,ax4_data), \
           (ax5,ax5_data), (ax6,ax6_data), (ax7,ax7_data), (ax8,ax8_data), \
           (ax9,ax9_data), lines, torque_markers

def animate(i, df, ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9,
             lines, torque_markers): 
    """
    Update the animation for both the right and left legs and the plots for joint angles and torques.
    """
    # Print in the same line the current iteration and update the title
    print(f"\rProcessing frame {i+jump_points+1}/{len(df)}", end='')

    # Get the time or phase for the current frame
    time = df.loc[i, 'time'] if 'time' in df else df.loc[i, 'phase']
    time_str = f'Time {time:.2f}' if 'time' in df else f'Phase {time:.2f}%'
    # Update the title of the stick figure animation
    ax1.set_title(f"Joint Kinematics for {subject} doing {task} (Frame {i+jump_points+1}/{len(df)}) ({time_str})")
    
    #Set the torso position to be vertical 
    lines['torso'].set_data([0, 0], [0, segment_lengths['torso']])

    # Update stick figure for the right leg
    hip_angle_r, knee_angle_r, ankle_angle_r = df.loc[i, right_angles]
    hip_pos_r, knee_pos_r, ankle_pos_r, foot_pos_r = calculate_joint_positions(hip_angle_r, knee_angle_r, ankle_angle_r)
    
    if GLOBAL_FOOT_ANGLE_ROTATION:
        # Calculate the global foot angle as the dot product of the vectors 
        # (foot - ankle) and (1, 0)
        foot_angle_r_fig = np.arccos(np.dot((foot_pos_r - ankle_pos_r), np.array([0,-1])) /
                                (np.linalg.norm(foot_pos_r - ankle_pos_r)))
        foot_angle_r_fig = foot_angle_r_fig - np.pi/2

        # Get the global foot angle from the data in degrees
        foot_angle_r = np.deg2rad(df.loc[i, 'foot_angle_s_r'])

        # Calculate the difference between the two angles
        foot_angle_diff = foot_angle_r - foot_angle_r_fig

        
        # Rotate all the points by the global foot angle to align the foot with the y-axis
        rotation_matrix = np.array([[np.cos(foot_angle_diff), -np.sin(foot_angle_diff)],
                                    [np.sin(foot_angle_diff), np.cos(foot_angle_diff)]])
        hip_pos_r = np.dot(rotation_matrix, hip_pos_r)
        knee_pos_r = np.dot(rotation_matrix, knee_pos_r)
        ankle_pos_r = np.dot(rotation_matrix, ankle_pos_r)
        foot_pos_r = np.dot(rotation_matrix, foot_pos_r)
    
    # Set the stick figure lines to the new positions
    lines['hip_knee_s_r'].set_data([hip_pos_r[0], knee_pos_r[0]], [hip_pos_r[1], knee_pos_r[1]])
    lines['knee_ankle_s_r'].set_data([knee_pos_r[0], ankle_pos_r[0]], [knee_pos_r[1], ankle_pos_r[1]])
    lines['ankle_foot_s_r'].set_data([ankle_pos_r[0], foot_pos_r[0]], [ankle_pos_r[1], foot_pos_r[1]])

    # Update stick figure for the left leg
    hip_angle_l, knee_angle_l, ankle_angle_l = df.loc[i, left_angles]
    hip_pos_l, knee_pos_l, ankle_pos_l, foot_pos_l = calculate_joint_positions(hip_angle_l, knee_angle_l, ankle_angle_l)

    if GLOBAL_FOOT_ANGLE_ROTATION:
        # Calculate the global foot angle as the dot product of the vectors
        # (foot - ankle) and (0, 1)
        foot_angle_l_fig = np.arccos(np.dot((foot_pos_l - ankle_pos_l), np.array([0, -1])) /
                                (np.linalg.norm(foot_pos_l - ankle_pos_l)))
        foot_angle_l_fig = foot_angle_l_fig - np.pi/2

        # Get the global foot angle from the data in degrees
        foot_angle_l = np.deg2rad(df.loc[i, 'foot_angle_s_l'])

        # Calculate the difference between the two angles
        foot_angle_diff = foot_angle_l - foot_angle_l_fig

        # Rotate all the points by the global foot angle to align the foot with the y-axis
        rotation_matrix_l = np.array([[np.cos(foot_angle_diff), -np.sin(foot_angle_diff)],
                                    [np.sin(foot_angle_diff), np.cos(foot_angle_diff)]])

        # Rotate all the points by the global foot angle to align the foot with the y-axis
        hip_pos_l = np.dot(rotation_matrix_l, hip_pos_l)
        knee_pos_l = np.dot(rotation_matrix_l, knee_pos_l)
        ankle_pos_l = np.dot(rotation_matrix_l, ankle_pos_l)
        foot_pos_l = np.dot(rotation_matrix_l, foot_pos_l)

    # Set the stick figure lines to the new positions
    lines['hip_knee_s_l'].set_data([hip_pos_l[0], knee_pos_l[0]], [hip_pos_l[1], knee_pos_l[1]])
    lines['knee_ankle_s_l'].set_data([knee_pos_l[0], ankle_pos_l[0]], [knee_pos_l[1], ankle_pos_l[1]])
    lines['ankle_foot_s_l'].set_data([ankle_pos_l[0], foot_pos_l[0]], [ankle_pos_l[1], foot_pos_l[1]])

    # Set the x-axis limits for the joint angles and torques plots
    start_idx = max(0, i - 150)
    end_idx = i + 1
    # x_axis = np.arange(start_idx, end_idx+1)
    x_axis_start = max(150 - (end_idx - start_idx)+1,0)
    x_axis = np.arange(x_axis_start, 152)

    # Update joint angles plot for the right leg
    ax2, ax2_data = ax2
    ax2_data[0].set_data(x_axis,df.loc[start_idx:end_idx, 'hip_angle_s_r'])
    ax2_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_angle_s_r'])
    ax2_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_angle_s_r'])

    # Update joint angles plot for the left leg
    ax3, ax3_data = ax3
    ax3_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_angle_s_l'])
    ax3_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_angle_s_l'])
    ax3_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_angle_s_l'])

    # Update joint torques plot for the right leg
    ax4, ax4_data = ax4
    ax4_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_torque_s_r'])
    ax4_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_torque_s_r'])
    ax4_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_torque_s_r'])

    # Update joint torques plot for the left leg
    ax5, ax5_data = ax5
    ax5_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_torque_s_l'])
    ax5_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_torque_s_l'])
    ax5_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_torque_s_l'])

    # Update global foot angle plot for the right and left leg
    ax6, ax6_data = ax6
    ax6_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_angle_s_r'])
    ax6_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_angle_s_l'])

    # Update joint velocities plot for the right leg
    ax7, ax7_data = ax7
    ax7_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_vel_s_r'])
    ax7_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_vel_s_r'])
    ax7_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_vel_s_r'])

    # Update joint velocities plot for the left leg
    ax8, ax8_data = ax8
    ax8_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'hip_vel_s_l'])
    ax8_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'knee_vel_s_l'])
    ax8_data[2].set_data(x_axis, df.loc[start_idx:end_idx, 'ankle_vel_s_l'])

    # Update global foot velocity plot for the right and left leg
    ax9, ax9_data = ax9
    ax9_data[0].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_vel_s_r'])
    ax9_data[1].set_data(x_axis, df.loc[start_idx:end_idx, 'foot_vel_s_l'])
    
    # Update torque markers positions
    torque_markers['hip_torque_s_r'].set_offsets([hip_pos_r])
    torque_markers['knee_torque_s_r'].set_offsets([knee_pos_r])
    torque_markers['ankle_torque_s_r'].set_offsets([ankle_pos_r])
    torque_markers['hip_torque_s_l'].set_offsets([hip_pos_l])
    torque_markers['knee_torque_s_l'].set_offsets([knee_pos_l])
    torque_markers['ankle_torque_s_l'].set_offsets([ankle_pos_l])

    # Update the shapes of the torque markers
    # Update hip torque marker based on torque direction
    max_torque = 1.2 # Nm/kg
    markers = [plt.matplotlib.markers.MarkerStyle(marker='x'), 
               plt.matplotlib.markers.MarkerStyle(marker='o', 
                                                  fillstyle='full')]
    markers_styles = {t:markers[1] if df.loc[i,t] >= 0 else markers[0] 
                      for t in torque_labels}
    markers_colors = {t:'purple' if df.loc[i,t] >= 0 else 'orange' 
                      for t in torque_labels}
    marker_opacity = {t:min(np.nan_to_num(abs(df.loc[i,t])/max_torque),1)
                      for t in torque_labels}
    for label in torque_labels:
        torque_markers[label].set_paths([markers_styles[label].get_path()])
        torque_markers[label].set_color(markers_colors[label])
        torque_markers[label].set_alpha(marker_opacity[label])
    

def setup_animation(df):
    """
    Setup and start the animation with the adjusted layout and data.
    """
    # If we are saving, only plot the first 400 frames
    if save_gif:
        # plt.ioff()
        frames = 1000
    else:
        frames = len(df)
    # Initialize the figure and elements
    fig, ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9, lines, torque_markers = \
        init_figure_and_elements()
    anim = FuncAnimation(fig, animate, frames=frames, interval=1,
                         fargs=(df, ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, 
                                ax9, lines, torque_markers))
    
    # Optionally, save the animation and exit
    if save_gif:
        dataset_type = 'time' if 'time' in parquet_file else 'phase'
        # Get the folder that the parquet file is in
        parquet_folder = parquet_file.split('/')[0]
        # Create a validation_gif folder
        if not os.path.exists(f'{parquet_folder}/validation_gif'):
            os.makedirs(f'{parquet_folder}/validation_gif')
        # Get the gif name
        gif_name = (f'{parquet_folder}/validation_gif/' 
                    f'{subject}_{task}_{dataset_type}.gif')
        # Save the animation as a gif
        anim.save(gif_name, fps=30)
        exit()

    # Show the animation
    plt.show()

# Ensure df is correctly loaded with left columns before calling setup_animation
setup_animation(df)