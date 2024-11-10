"""
This file is meant to convert the add_biomechanics datasets to tabular data 
in the form of parquet files. To do this, it uses the nimblephysics library
to process the b3d files and extract the relevant information.

In general you need to select which datasets you want to proces (using the 
"datasets_to_process" variable), and then point the script to the directory 
where the file structure that is in the format of google drive download is
(using the "base_dir" variable). This can be configured with the 

author: José A. Montes Pérez
date: 09/26/2024
email:jmontp@umich.edu
"""



import pandas as pd
from tqdm import tqdm
import nimblephysics as nimble
import matplotlib.pyplot as plt
import fastparquet as fp
import os
import numpy as np

from add_phase_info import add_phase_info
from multiprocessing import Pool

#thus script requested the use of nimble physics
# pip3 install nimblephysics

#### User Confiuration Section ###############################################


base_dir = '/datasets/AddBiomechanics/raw_data/'
output_dir='/datasets/AddBiomechanics/processed_data/'

datasets_to_process = [
  #'Moore2015',
  #'Camargo2021',
  #'Falisse2017',
  #'Fregly2012',
  #'Hamner2013',
  #'Han2023',
  #'Santos2017',
  'Tan2021',
  #'Tan2022',
  #'Tiziana2019',
  #'vanderZee2022',
  #'Wang2023',
  #'Carter2023',
]

#### End of User Configuration Section ########################################

# Data types to flip 
flip_columns = [
    # 'grf_x_r',
    # 'grf_x_l',

    # # Only flip the left cop x 
    # 'cop_x_l',

    # 'cop_z_r',

    # # Flip knee values
    # 'knee_angle_s_r',
    # 'knee_angle_s_l',
    # 'knee_vel_s_r',
    # 'knee_vel_s_l',
    # 'knee_torque_s_r',
    # 'knee_torque_s_l',
]

#### Function Definitions #####################################################

def osim_rotate_matrix(x, y, z):
    """
    Generate a rotation matrix given Euler angles (x, y, z).

    Parameters:
    x (float): Rotation around the x-axis in radians.
    y (float): Rotation around the y-axis in radians.
    z (float): Rotation around the z-axis in radians.

    Returns:
    np.ndarray: A 3x3 rotation matrix.
    """

    # Rotation matrix around the x-axis
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(x), -np.sin(x)],
                    [0, np.sin(x), np.cos(x)]])

    # Rotation matrix around the y-axis
    R_y = np.array([[np.cos(y), 0, np.sin(y)],
                    [0, 1, 0],
                    [-np.sin(y), 0, np.cos(y)]])

    # Rotation matrix around the z-axis
    R_z = np.array([[np.cos(z), -np.sin(z), 0],
                    [np.sin(z), np.cos(z), 0],
                    [0, 0, 1]])

    # Combined rotation matrix
    R = np.dot(R_z, np.dot(R_x, R_y))

    return R


#### Main Execution ###########################################################

dataset_count = 0 
chunk_size=100000
# Process each dataset separately
def process_dataset(dataset):
    dataset_path = os.path.join(base_dir, f'{dataset}_Formatted_No_Arm')

    data = []
    is_first_chunk = True
    # Check if it's a directory
    if not os.path.isdir(dataset_path):
        print(f"Skipping {dataset_path}, not a directory")
        return
    
    # Loop through each subject in the dataset with a progress bar (tqdm)
    for sub_idx, subject in tqdm(enumerate(os.listdir(dataset_path)),
                                    desc=f'Subjects in {dataset}',
                                    total=len(os.listdir(dataset_path))):

        # For debugging purposes, we can limit the number of subjects
        # if sub_idx > 0:
        #     break

        # Get the path to the subject's folder
        subject_path = os.path.join(dataset_path, subject)

        # If it is not a directory, skip it
        if not os.path.isdir(subject_path):
            print(f"Skipping {subject_path}, not a directory")
            continue

        # Look for the b3d file in the subject's folder
        b3d_file_path = None
        for file in os.listdir(subject_path):
            if file.endswith('.b3d'):
                b3d_file_path = os.path.join(subject_path, file)

        # If no b3d file was found, skip this subject
        if b3d_file_path is None:
            print(f"Skipping {subject_path}, no b3d file found")
            continue

        # Process the dataset. If something fails, skip to the next subject
        try:
            # Create a SubjectOnDisk object
            my_subject = nimble.biomechanics.SubjectOnDisk(b3d_file_path)

            # Process each trial in the subject. Each trial represents
            # one continuous recording of the subject performing a task.
            # There might be multiple trials for a particular task.
            num_trial = my_subject.getNumTrials()

            # Loop through each trial
            for trial_turn in tqdm(range(num_trial),
                                    desc=f'Trials in {subject}'):

                # Label the accumulated time
                accum_time = 0

                # ff is the frames for a single piece of task
                # We need to specify the number of frames to read.
                big_n = 1_000_000  # Needs arbitrary large number to read all frames
                ff = my_subject.readFrames(trial_turn, 0, big_n)

                # Get the task name and time interval
                task = my_subject.getTrialOriginalName(trial_turn)
                timestep = my_subject.getTrialTimestep(trial_turn)

                # iterate through every frame
                for i, a in enumerate(ff):

                    # ss is a single frame of information
                    # There are 2 processing passes. The first one is for
                    # the kinematics and the second one is for the dynamics
                    ss = a.processingPasses[1]

                    # Get the high level variables for each frame
                    grf = (ss.groundContactForceInRootFrame)
                    cop = (ss.groundContactCenterOfPressureInRootFrame)
                    contacted = ss.contact
                    poses = ss.pos
                    vels = ss.vel
                    torque = ss.tau
                    jointposes=    ss.jointCentersInRootFrame
                    jointposes=jointposes.reshape(-1, 3)

               

                    # Extract x, y, z coordinates
                    mtpPos_x_r = jointposes[5, 0]
                    mtpPos_y_r = jointposes[5, 1]
                    mtpPos_z_r = jointposes[5, 2]
                    
                    mtpPos_x_l = jointposes[10, 0]
                    mtpPos_y_l = jointposes[10, 1]
                    mtpPos_z_l = jointposes[10, 2]

                    COM_poses=ss.comPos
                    COM_veles=ss.comVel
                    # Assigning variables to poses array elements
                    comPos_x_c=COM_poses[0]
                    comPos_y_c=COM_poses[1]
                    comPos_z_c=COM_poses[2]
                    comVel_x_c=COM_veles[0]
                    comVel_y_c=COM_veles[1]
                    comVel_z_c=COM_veles[2]
                    
                    pelvis_angle_s = poses[0]
                    pelvis_angle_f = poses[1]
                    pelvis_angle_t = poses[2]
                    hip_angle_s_r = poses[6]
                    hip_angle_f_r = poses[7]
                    hip_angle_t_r = poses[8]
                    knee_angle_s_r = poses[9]
                    ankle_angle_s_r = poses[10]
                    ankle_angle_t_r = poses[11]
                    hip_angle_s_l = poses[13]
                    hip_angle_f_l = poses[14]
                    hip_angle_t_l = poses[15]
                    knee_angle_s_l = poses[16]
                    ankle_angle_s_l = poses[17]
                    ankle_angle_t_l = poses[18]

                    pelvis_vel_s = vels[0]
                    pelvis_vel_f = vels[1]
                    pelvis_vel_t = vels[2]
                    hip_vel_s_r = vels[6]
                    hip_vel_f_r = vels[7]
                    hip_vel_t_r = vels[8]
                    knee_vel_s_r = vels[9]
                    ankle_vel_s_r = vels[10]
                    ankle_vel_t_r = vels[11]
                    hip_vel_s_l = vels[13]
                    hip_vel_f_l = vels[14]
                    hip_vel_t_l = vels[15]
                    knee_vel_s_l = vels[16]
                    ankle_vel_s_l = vels[17]
                    ankle_vel_t_l = vels[18]

                    pelvis_torque_s = torque[0]
                    pelvis_torque_f = torque[1]
                    pelvis_torque_t = torque[2]
                    hip_torque_s_r = torque[6]
                    hip_torque_f_r = torque[7]
                    hip_torque_t_r = torque[8]
                    knee_torque_s_r = torque[9]
                    ankle_torque_s_r = torque[10]
                    ankle_torque_t_r = torque[11]
                    hip_torque_s_l = torque[13]
                    hip_torque_f_l = torque[14]
                    hip_torque_t_l = torque[15]
                    knee_torque_s_l = torque[16]
                    ankle_torque_s_l = torque[17]
                    ankle_torque_t_l = torque[18]

                    # We need to forwards propagate the pelvis angles
                    # to the shank, thigh, and foot angles. Therefore,
                    # we need to calculate the rotation matrices for each
                    # segment.
                    R_pelvis = osim_rotate_matrix(pelvis_angle_f, pelvis_angle_t, pelvis_angle_s)
                    R_hip_r = osim_rotate_matrix(hip_angle_f_r, hip_angle_t_r, hip_angle_s_r)
                    R_hip_l = osim_rotate_matrix(hip_angle_f_l, hip_angle_t_l, hip_angle_s_l)
                    R_knee_r = osim_rotate_matrix(0, 0, -knee_angle_s_r)
                    R_knee_l = osim_rotate_matrix(0, 0, -knee_angle_s_l)
                    R_ankle_r = osim_rotate_matrix(0, ankle_angle_t_r, ankle_angle_s_r)
                    R_ankle_l = osim_rotate_matrix(0, ankle_angle_t_l, ankle_angle_s_l)

                    # Calculate the angles of the shank
                    R_right_shank_all = np.dot(R_pelvis, np.dot(R_hip_r, (R_knee_r)))
                    R_left_shank_all = np.dot(R_pelvis, np.dot(R_hip_l, R_knee_l))
                    shank_angle_r = R_right_shank_all[1, 0]
                    shank_angle_l = R_left_shank_all[1, 0]

                    # Calculate the velocities of the shank with finite
                    # differences. If it is the first frame, we need to
                    # initialize the previous angles.
                    if i == 0:
                        prev_shank_angle_r = shank_angle_r
                        prev_shank_angle_l = shank_angle_l
                    # Finite interval
                    shank_vel_r = (shank_angle_r - prev_shank_angle_r) / timestep
                    shank_vel_l = (shank_angle_l - prev_shank_angle_l) / timestep
                    # Update the previous angles for next finite difference
                    prev_shank_angle_r = shank_angle_r
                    prev_shank_angle_l = shank_angle_l

                    # Calculate the angles of the thigh
                    R_right_thigh_all = np.dot(R_pelvis, R_hip_r)
                    R_left_thigh_all = np.dot(R_pelvis, R_hip_l)
                    thigh_angle_r = R_right_thigh_all[1, 0]
                    thigh_angle_l = R_left_thigh_all[1, 0]
                    # Calculate the velocities of the thigh with finite
                    # differences.
                    if i == 0:
                        prev_thigh_angle_r = thigh_angle_r
                        prev_thigh_angle_l = thigh_angle_l
                    # Finite difference
                    thigh_vel_l = (thigh_angle_l - prev_thigh_angle_l) / timestep
                    thigh_vel_r = (thigh_angle_r - prev_thigh_angle_r) / timestep
                    # Update the previous angles for next finite difference
                    prev_thigh_angle_r = thigh_angle_r
                    prev_thigh_angle_l = thigh_angle_l

                    # Calculate the angles of the ankle
                    R_right_foot_all = np.dot(R_pelvis, np.dot(R_hip_r, np.dot(R_knee_r, R_ankle_r)))
                    R_left_foot_all = np.dot(R_pelvis, np.dot(R_hip_l, np.dot(R_knee_l, R_ankle_l)))
                    dorsi_angle_r = R_right_foot_all[1, 0]
                    dorsi_angle_l = R_left_foot_all[1, 0]
                    # Calculate the velocities of the ankle with finite
                    # differences. If it is the first frame, we need to
                    # initialize the previous angles.
                    if i == 0:
                        prev_dorsi_angle_r = dorsi_angle_r
                        prev_dorsi_angle_l = dorsi_angle_l
                    # Finite difference
                    ankle_vel_r = (dorsi_angle_r - prev_dorsi_angle_r) / timestep
                    ankle_vel_l = (dorsi_angle_l - prev_dorsi_angle_l) / timestep
                    # Update the previous angles for next finite difference
                    prev_dorsi_angle_r = dorsi_angle_r
                    prev_dorsi_angle_l = dorsi_angle_l

                    # Format the subject name
                    # Remove the _split{number}.
                    if '_split' in file:
                        subject = file.split('_split')[0]
                    else:
                        # Remove the file extension
                        subject = file.split('.')[0]

                    
                    # Get the mass of the subject
                    mass = my_subject.getMassKg()

                    record = {
                        
                        'subject': subject,
                        'subject_mass': mass,
                        'task': task,
                        'frame_number': i,
                        'time': accum_time,
                        'comPos_x_c':comPos_x_c,
                        'comPos_y_c':comPos_y_c,
                        'comPos_z_c':comPos_z_c,
                        'comVel_x_c':comVel_x_c,
                        'comVel_y_c':comVel_y_c,
                        'comVel_z_c':comVel_z_c,
                        'contact_r': contacted[0],
                        'contact_l': contacted[1],
                        'mtpPos_x_r': mtpPos_x_r,
                        'mtpPos_y_r': mtpPos_y_r,
                        'mtpPos_z_r': mtpPos_z_r,
                        'mtpPos_x_l': mtpPos_x_l,
                        'mtpPos_y_l': mtpPos_y_l,
                        'mtpPos_z_l': mtpPos_z_l,
                        
                        'grf_x_r': grf[0],
                        'grf_y_r': grf[1],
                        'grf_z_r': grf[2],

                        'grf_x_l': grf[3],
                        'grf_y_l': grf[4],
                        'grf_z_l': grf[5],
                            'contact_r': contacted[0],
                            'contact_l': contacted[1],

                            'grf_x_r': grf[0],
                            'grf_y_r': grf[1],
                            'grf_z_r': grf[2],

                            'grf_x_l': grf[3],
                            'grf_y_l': grf[4],
                            'grf_z_l': grf[5],

                            'cop_x_r': cop[0],
                            'cop_y_r': cop[1],
                            'cop_z_r': cop[2],

                            'cop_x_l': cop[3],
                            'cop_y_l': cop[4],
                            'cop_z_l': cop[5],

                            'pelvis_angle_s': pelvis_angle_s,
                            'pelvis_angle_f': pelvis_angle_f,
                            'pelvis_angle_t': pelvis_angle_t,

                            'hip_angle_s_r': hip_angle_s_r,
                            'hip_angle_f_r': hip_angle_f_r,
                            'hip_angle_t_r': hip_angle_t_r,
                            'knee_angle_s_r': knee_angle_s_r,
                            'ankle_angle_s_r': ankle_angle_s_r,
                            # 'ankle_angle_f_r': ankle_angle_f_r,
                            'ankle_angle_t_r': ankle_angle_t_r,
                            'hip_angle_s_l': hip_angle_s_l,
                            'hip_angle_f_l': hip_angle_f_l,
                            'hip_angle_t_l': hip_angle_t_l,
                            'knee_angle_s_l': knee_angle_s_l,
                            'ankle_angle_s_l': ankle_angle_s_l,
                            # 'ankle_angle_f_l': ankle_angle_f_l,
                            'ankle_angle_t_l': ankle_angle_t_l,
                            
                            'dorsi_angle_r': dorsi_angle_r,
                            'dorsi_angle_l': dorsi_angle_l,
                            'shank_angle_r': shank_angle_r,
                            'shank_angle_l': shank_angle_l,
                            'thigh_angle_r': thigh_angle_r,
                            'thigh_angle_l': thigh_angle_l,

                            'shank_vel_r': shank_vel_r,
                            'shank_vel_l': shank_vel_l,
                            'thigh_vel_r': thigh_vel_r,
                            'thigh_vel_l': thigh_vel_l,
                            'ankle_vel_r': ankle_vel_r,
                            'ankle_vel_l': ankle_vel_l,

                            'pelvis_vel_s': pelvis_vel_s,
                            'pelvis_vel_f': pelvis_vel_f,
                            'pelvis_vel_t': pelvis_vel_t,
                            'hip_vel_s_r': hip_vel_s_r,
                            'hip_vel_f_r': hip_vel_f_r,
                            'hip_vel_t_r': hip_vel_t_l,
                            'knee_vel_s_r': knee_vel_s_r,
                            'ankle_vel_s_r': ankle_vel_s_r,
                            'ankle_vel_t_r': ankle_vel_t_r,
                            'hip_vel_s_l': hip_vel_s_l,
                            'hip_vel_f_l': hip_vel_f_l,
                            'hip_vel_t_l': hip_vel_t_l,
                            'knee_vel_s_l': knee_vel_s_l,
                            'ankle_vel_s_l': ankle_vel_s_l,
                            'ankle_vel_t_l': ankle_vel_t_l,

                            'pelvis_torque_s': pelvis_torque_s,
                            'pelvis_torque_f': pelvis_torque_f,
                            'pelvis_torque_t': pelvis_torque_t,
                            'hip_torque_s_r': hip_torque_s_r,
                            'hip_torque_f_r': hip_torque_f_r,
                            'hip_torque_t_r': hip_torque_t_r,
                            'knee_torque_s_r': knee_torque_s_r,
                            'ankle_torque_s_r': ankle_torque_s_r,
                            'ankle_torque_t_r': ankle_torque_t_r,
                            'hip_torque_s_l': hip_torque_s_l,
                            'hip_torque_f_l': hip_torque_f_l,
                            'hip_torque_t_l': hip_torque_t_l,
                            'knee_torque_s_l': knee_torque_s_l,
                            'ankle_torque_s_l': ankle_torque_s_l,
                        }
                    accum_time+=timestep

                    # Add the record to the data list
                    data.append(record)

                    # If we have enough data, then save it to a file
                    if len(data)>=chunk_size:

                        df = pd.DataFrame(data)

                        # Save the DataFrame to a Parquet file. If it is the
                        # first chunk, then we need to create the file. If it
                        # is not the first chunk, then we need to append to the
                        # existing file.
                        output_path = os.path.join(output_dir, dataset+'_partial_'+'.parquet')
                        df.to_parquet(output_path, engine='fastparquet',
                                    index=False,append=not is_first_chunk)

                        # Set the first chunk flag to false and reset data 
                        # since it's already saved. 
                        is_first_chunk=False
                        data=[]
            
        # If something fails, skip to the next subject
        except Exception as e:
            print(f"Skipping {subject_path}, error: {e}")
            continue
        
        # If there is any data left, save it to a file
        if len(data)>0:
            df = pd.DataFrame(data)
            print(len(data))
            # Save the DataFrame to a Parquet file
            output_path = os.path.join(output_dir,  dataset+'_partial_'+'.parquet')
            df.to_parquet(output_path, engine='fastparquet',index=False,append=not is_first_chunk)

    # Rename the dataset file
    output_path = os.path.join(output_dir, dataset+'_partial_'+'.parquet')
    final_output_name = os.path.join(output_dir, dataset+'.parquet')
    os.rename(output_path, final_output_name)

    ### Final post processing ################################################
    # Invert the columns that need to be inverted
    df = pd.read_parquet(final_output_name)
    for column in flip_columns:
        df[column] = -df[column]

    # Add task information
    # TODO: Add task information

    # Mass normalize the torques
    mass_column = 'subject_mass'
    torque_columns = [col for col in df.columns if 'torque' in col]
    for col in torque_columns:
        # Divide by the mass but check if the mass is zero
        df[col] = df[col] / df[mass_column].replace(0, 1)
        # If there are zero masses, report the subject
        zero_subjects = df[df[mass_column] == 0]['subject'].unique()
        if len(zero_subjects) > 0:
            print(f"Warning: Zero mass for subjects {zero_subjects}")

    # Change from radians to degrees
    angle_columns = [col for col in df.columns if 'angle' in col]
    vel_columns = [col for col in df.columns if 'vel' in col]
    df[angle_columns] = np.rad2deg(df[angle_columns])
    df[vel_columns] = np.rad2deg(df[vel_columns])

    # Add Phase to the dataframe
    add_phase_info(df, export_phase_dataframe=True,
                   save_name=final_output_name.replace('.parquet', ''),
                   remove_original_file=final_output_name)

    print(f"Finished. Data saved to {final_output_name}")

if __name__ == '__main__':
    with Pool() as pool:
        pool.map(process_dataset, datasets_to_process)
