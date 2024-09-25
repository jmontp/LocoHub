import pandas as pd
from tqdm import tqdm
import nimblephysics as nimble
import matplotlib.pyplot as plt
import fastparquet as fp
import os
import numpy as np

#thus script requested the use of nimble physics
# pip3 install nimblephysics

#### User Confiuration Section ###############################################


base_dir = './raw_data/'
output_dir='/processed_data/'

datasets_to_process = [
  'Tiziana2019',
  
  
]

#### End of User Configuration Section ########################################


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
for dataset in datasets_to_process:
    

    dataset_path = os.path.join(base_dir, dataset)

    # Load the raw data
    df = pd.read_parquet(os.path.join(base_dir, f'{dataset}_Formatted_No_Arm.parquet'))

    data=[]
    is_first_chunk = True
    # Check if it's a directory
    if os.path.isdir(dataset_path):

        # Loop through each subject in the dataset
        for subject in tqdm(os.listdir(dataset_path)):
            
            # Get the path to the subject's folder
            subject_path = os.path.join(dataset_path, subject)

            # If it is not a directory, skip it
            if not os.path.isdir(subject_path):
                print(f"Skipping {subject_path}, not a directory")
                continue
            
            # Look for the b3d file in the subject's folder
            b3d_file_path = None
            for file in os.listdir(subject_path):
                if file.endswith('.b3d'):#&file.startswith("P023")|file.startswith("P051"):
                    b3d_file_path = os.path.join(subject_path, file)
            # If no b3d file was found, skip this subject
            if b3d_file_path is None:
                print(f"Skipping {subject_path}, no b3d file found")
                continue

                #print(f"Processing {b3d_file_path}")
                # specific processing code here
            
            # Process the dataset. If something fails, skip to the next subject
            try:

                # Create a SubjectOnDisk object
                my_subject = nimble.biomechanics.SubjectOnDisk(b3d_file_path)

                # Process each trial in the subject. Each trial represents 
                # one continuous recordin of the subject performing a task.
                # There might be multiple trials for a particular task. 
                num_trial=my_subject.getNumTrials()
                
                # Loop through each trial
                for trial_turn in range(num_trial):

                    # Lalbel the acumulated time
                    accum_time=0

                    #ff is the frames for a single piece of task
                    # We need to specify the number of frames to read.
                    big_n=1e+10 # Needs arbitrary large number to read all frames
                    ff=my_subject.readFrames(trial_turn,0,big_n)
                    
                    # Get the task name and time interval
                    task=my_subject.getTrialOriginalName(trial_turn)
                    timestep=my_subject.getTrialTimestep(trial_turn)

                    # iterate through every frame
                    for i,a in enumerate(ff):

                        # ss is a single frame of information  
                        # There are 2 processing passes. The first one is for 
                        # the kinematics and the second one is for the dynamics     
                        ss=a.processingPasses[1] 

                        # Get the high level variables for each frame
                        #acc=ss.acc
                        grf=(ss.groundContactForce)
                        cop=(ss.groundContactCenterOfPressureInRootFrame)
                        cop_org=ss.groundContactCenterOfPressureInRootFrame
                        contacted=ss.contact
                        poses=ss.pos
                        vels=ss.vel
                        tau=ss.tau

                        # Assigning variables to poses array elements
                        # The positions are not documented, so we had to 
                        # reverse engineer them from the positions that are 
                        # found in opensim GUI (lol)
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

                        pelvis_tau_s = ss.tau[0]
                        pelvis_tau_f = ss.tau[1]
                        pelvis_tau_t = ss.tau[2]
                        hip_tau_s_r = ss.tau[6]
                        hip_tau_f_r = ss.tau[7]
                        hip_tau_t_r = ss.tau[8]
                        knee_tau_s_r = ss.tau[9]
                        ankle_tau_s_r = ss.tau[10]
                        ankle_tau_t_r = ss.tau[11]
                        hip_tau_s_l = ss.tau[13]
                        hip_tau_f_l = ss.tau[14]
                        hip_tau_t_l = ss.tau[15]
                        knee_tau_s_l = ss.tau[16]
                        ankle_tau_s_l = ss.tau[17]
                        ankle_tau_t_l = ss.tau[18]

                        # We need to forwards propagate the pelvis angles 
                        # to the shank, thigh, and foot angles. Therefore, 
                        # we need to calculate the rotation matrices for each
                        # segment.
                        R_pelvis=osim_rotate_matrix(pelvis_angle_f,pelvis_angle_t,pelvis_angle_s)
                        R_hip_r=osim_rotate_matrix(hip_angle_f_r,hip_angle_t_r,hip_angle_s_r)
                        R_hip_l=osim_rotate_matrix(hip_angle_f_l,hip_angle_t_l,hip_angle_s_l)
                        R_knee_r=osim_rotate_matrix(0,0,-knee_angle_s_r)
                        R_knee_l=osim_rotate_matrix(0,0,-knee_angle_s_l)
                        R_ankle_r=osim_rotate_matrix(0,ankle_angle_t_r,ankle_angle_s_r)
                        R_ankle_l=osim_rotate_matrix(0,ankle_angle_t_l,ankle_angle_s_l)

                        # Calculate the angles of the shank
                        R_right_shank_all=np.dot(R_pelvis,np.dot(R_hip_r,(R_knee_r)))
                        R_left_shank_all=np.dot(R_pelvis,np.dot(R_hip_l,R_knee_l))
                        shank_angle_r=R_right_shank_all[1,0]
                        shank_angle_l=R_left_shank_all[1,0]
                        
                        # Calculate the velocities of the shank with finite
                        # differences. If it is the first frame, we need to
                        # initialize the previous angles.
                        if i==0:
                            prev_shank_angle_r=shank_angle_r
                            prev_shank_angle_l=shank_angle_l
                        # Fininte ineterval
                        shank_vel_r=(shank_angle_r-prev_shank_angle_r)/timestep
                        shank_vel_l=(shank_angle_l-prev_shank_angle_l)/timestep
                        # Update the previous angles for next finite difference
                        prev_shank_angle_r=shank_angle_r
                        prev_shank_angle_l=shank_angle_l

                        # Calculate the angles of the thigh
                        R_right_thigh_all=np.dot(R_pelvis,R_hip_r)
                        R_left_thigh_all=np.dot(R_pelvis,R_hip_l)
                        thigh_angle_r=R_right_thigh_all[1,0]
                        thigh_angle_l=R_left_thigh_all[1,0]
                        # Calculate the velocities of the thigh with finite
                        # differences.
                        if i==0:
                            prev_thigh_angle_r=thigh_angle_r
                            prev_thigh_angle_l=thigh_angle_l
                        # Finite difference
                        thigh_vel_l=(thigh_angle_l-prev_thigh_angle_l)/timestep
                        thigh_vel_r=(thigh_angle_r-prev_thigh_angle_r)/timestep
                        # Update the previous angles for next finite difference
                        prev_thigh_angle_r=thigh_angle_r
                        prev_thigh_angle_l=thigh_angle_l


                        # Calculate the angles of the ankle
                        R_right_foot_all=np.dot(R_pelvis,np.dot(R_hip_r,np.dot(R_knee_r,R_ankle_r)))
                        R_left_foot_all=np.dot(R_pelvis,np.dot(R_hip_l,np.dot(R_knee_l,R_ankle_l)))
                        dorsi_angle_r=R_right_foot_all[1,0]
                        dorsi_angle_l=R_left_foot_all[1,0]
                        # Calculate the velocities of the ankle with finite
                        # differences. If it is the first frame, we need to
                        # initialize the previous angles.
                        if i==0:
                            prev_dorsi_angle_r=dorsi_angle_r
                            prev_dorsi_angle_l=dorsi_angle_l
                        # Finite difference
                        ankle_vel_r=(dorsi_angle_r-prev_dorsi_angle_r)/timestep
                        ankle_vel_l=(dorsi_angle_l-prev_dorsi_angle_l)/timestep
                        # Update the previous angles for next finite difference
                        prev_dorsi_angle_r=dorsi_angle_r
                        prev_dorsi_angle_l=dorsi_angle_l

                    record = {
                            'subject': file.split('.')[0] ,
                            'task': task,
                            'frame_number': i,
                            'accum_time': accum_time,

                            'contact_r': contacted[0],
                            'contact_l': contacted[1],

                            'GRF_x_r': grf[0],
                            'GRF_y_r': grf[1],
                            'GRF_z_r': grf[2],
                            'GRF_x_l': grf[3],
                            'GRF_y_l': grf[4],
                            'GRF_z_l': grf[5],
                            'COP_x_r': cop[0],
                            'COP_y_r': cop[1],
                            'COP_z_r': cop[2],
                            'COP_x_l': cop[3],
                            'COP_y_l': cop[4],
                            'COP_z_l': cop[5],

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

                            'pelvis_tau_s': pelvis_tau_s,
                            'pelvis_tau_f': pelvis_tau_f,
                            'pelvis_tau_t': pelvis_tau_t,
                            'hip_tau_s_r': hip_tau_s_r,
                            'hip_tau_f_r': hip_tau_f_r,
                            'hip_tau_t_r': hip_tau_t_r,
                            'knee_tau_s_r': knee_tau_s_r,
                            'ankle_tau_s_r': ankle_tau_s_r,
                            'ankle_tau_t_r': ankle_tau_t_r,
                            'hip_tau_s_l': hip_tau_s_l,
                            'hip_tau_f_l': hip_tau_f_l,
                            'hip_tau_t_l': hip_tau_t_l,
                            'knee_tau_s_l': knee_tau_s_l,
                            'ankle_tau_s_l': ankle_tau_s_l,
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
                        output_path = os.path.join(output_dir, dataset+'.parquet')
                        df.to_parquet(output_path, engine='fastparquet',
                                      index=False,append=not is_first_chunk)

                        # Set the first chunk flag to false and reset data 
                        # since it's already saved. 
                        is_first_chunk=False
                        data=[]
            
            # If something fails, skip to the next subject
            except Exception as e:
                continue
            
            # If there is any data left, save it to a file
            if len(data)>0:
                df = pd.DataFrame(data)
                print(len(data))
                # Save the DataFrame to a Parquet file
                output_path = os.path.join(output_dir, dataset+'.parquet')
                df.to_parquet(output_path, engine='fastparquet',index=False,append=not is_first_chunk)

                print(f"Finished. Data saved to {output_path}")
