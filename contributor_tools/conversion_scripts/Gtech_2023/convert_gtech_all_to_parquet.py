'''
This file is meant to convert the dataset to a pandas dataframe
'''

import pandas as pd
import numpy as np
import os
import sys
import gc
from tqdm import tqdm
from task_mapping import parse_gtech_activity_name, get_subject_metadata
###############################################################################
# User configuration section

# This is the base path to the dataset. If you extracted the dataset to the 
# same folder as this file, you don't need to change this
base_path = './RawData'

# This is the list of data types that we want to save. The options are:
# 'Activity_Flag', 'GroundFrame_GRFs', 'Joint_Angle', 'Joint_Moments',
# 'Joint_Powers', 'Joint_Velocities', 'Raw_EMGs', 'Real_IMUs', 'Virtual_IMUs',
# 'Virtual_Insoles', 'Link_Angle',
# Currently the only standardized names are
# 'Joint_Angle', 'Joint_Velocities', 'Joint_Moments', 'Link_Angle'
data_to_save = ['Joint_Moments', 'Joint_Angle', 
                'Joint_Velocities', 'Link_Angle', 'Link_Velocities',"GroundFrame_GRFs"]

###############################################################################
# Don't modify anything below this line

# These are used to convert the activity names to a shorter version
short_activity_names = ['ball_toss', 'curb_down', 'curb_up', 'cutting',
                        'dynamic_walk', 'incline_walk', 'jump', 'lift_weight',
                        'lunges', 'meander', 'normal_walk', 'obstacle_walk',
                        'poses', 'push', 'side_shuffle', 'sit_to_stand', 
                        'squats', 'stairs', 'step_ups', 'tire_run', 
                        'tug_of_war', 'turn_and_step', 'twister', 
                        'walk_backward', 'weighted_walk']

standard_column_names = {

    # Joint Angle
    'hip_flexion_r':'hip_flexion_angle_r_rad',
    'hip_adduction_r':'hip_adduction_angle_r_rad',
    'hip_rotation_r':'hip_rotation_angle_r_rad',
    'knee_angle_r':'knee_flexion_angle_r_rad',
    'ankle_angle_r':'ankle_dorsiflexion_angle_r_rad',
    'subtalar_angle_r':'ankle_eversion_angle_r_rad',
    
    'hip_flexion_l':'hip_flexion_angle_l_rad',
    'hip_adduction_l':'hip_adduction_angle_l_rad',
    'hip_rotation_l':'hip_rotation_angle_l_rad',
    'knee_angle_l':'knee_flexion_angle_l_rad',
    'ankle_angle_l':'ankle_dorsiflexion_angle_l_rad',
    'subtalar_angle_l':'ankle_eversion_angle_l_rad',

    # Joint Velocities
    'hip_flexion_velocity_r': 'hip_flexion_velocity_r_rad_s',
    'hip_adduction_velocity_r': 'hip_adduction_velocity_r_rad_s',
    'hip_rotation_velocity_r': 'hip_rotation_velocity_r_rad_s',
    'knee_velocity_r': 'knee_flexion_velocity_r_rad_s',
    'ankle_velocity_r': 'ankle_dorsiflexion_velocity_r_rad_s',
    'subtalar_velocity_r': 'ankle_eversion_velocity_r_rad_s',	
    
    'hip_flexion_velocity_l': 'hip_flexion_velocity_l_rad_s',
    'hip_adduction_velocity_l': 'hip_adduction_velocity_l_rad_s',
    'hip_rotation_velocity_l': 'hip_rotation_velocity_l_rad_s',
    'knee_velocity_l': 'knee_flexion_velocity_l_rad_s',
    'ankle_velocity_l': 'ankle_dorsiflexion_velocity_l_rad_s',
    'subtalar_velocity_l': 'ankle_eversion_velocity_l_rad_s',

    # Joint Moments
    'hip_flexion_r_moment': 'hip_flexion_moment_r_Nm',
    'hip_adduction_r_moment': 'hip_adduction_moment_r_Nm',
    'hip_rotation_r_moment': 'hip_rotation_moment_r_Nm',
    'knee_angle_r_moment': 'knee_flexion_moment_r_Nm',
    'ankle_angle_r_moment': 'ankle_dorsiflexion_moment_r_Nm',
    'subtalar_angle_r_moment': 'ankle_eversion_moment_r_Nm',

    'hip_flexion_l_moment': 'hip_flexion_moment_l_Nm',
    'hip_adduction_l_moment': 'hip_adduction_moment_l_Nm',
    'hip_rotation_l_moment': 'hip_rotation_moment_l_Nm',
    'knee_angle_l_moment': 'knee_flexion_moment_l_Nm',
    'ankle_angle_l_moment': 'ankle_dorsiflexion_moment_l_Nm',
    'subtalar_angle_l_moment': 'ankle_eversion_moment_l_Nm',

    # Link Angle
    'pelvis_Y':'pelvis_angle_f',
    'pelvis_Z':'pelvis_angle_s',
    'pelvis_X':'pelvis_angle_t',
    'torso_Y':'torso_angle_f',	
    'torso_Z':'torso_angle_s',	
    'torso_X':'torso_angle_t',

    'femur_r_Y':'thigh_angle_f_r',
    'femur_r_Z':'thigh_angle_s_r',
    'femur_r_X':'thigh_angle_t_r',
    'tibia_r_Y':'shank_angle_f_r',	
    'tibia_r_Z':'shank_angle_s_r',	
    'tibia_r_X':'shank_angle_t_r',	
    'talus_r_Y':'talus_angle_f_r',	
    'talus_r_Z':'talus_angle_s_r',	
    'talus_r_X':'talus_angle_t_r',	
    'calcn_r_Y':'foot_angle_f_r',	
    'calcn_r_Z':'foot_angle_s_r',	
    'calcn_r_X':'foot_angle_t_r',	
    'toes_r_Y':'toes_angle_f_r',	
    'toes_r_Z':'toes_angle_s_r',	
    'toes_r_X':'toes_angle_t_r',	
    
    'femur_l_Y':'thigh_angle_f_l',	
    'femur_l_Z':'thigh_angle_s_l',	
    'femur_l_X':'thigh_angle_t_l',	
    'tibia_l_Y':'shank_angle_f_l',	
    'tibia_l_Z':'shank_angle_s_l',	
    'tibia_l_X':'shank_angle_t_l',	
    'talus_l_Y':'talus_angle_f_l',
    'talus_l_Z':'talus_angle_s_l',	
    'talus_l_X':'talus_angle_t_l',	
    'calcn_l_Y':'foot_angle_f_l',	
    'calcn_l_Z':'foot_angle_s_l',	
    'calcn_l_X':'foot_angle_t_l',	
    'toes_l_Y':'toes_angle_f_l',	
    'toes_l_Z':'toes_angle_s_l',	
    'toes_l_X':'toes_angle_t_l',	

    # Link Velocities
    'pelvis_vel_Y':'pelvis_vel_f',
    'pelvis_vel_Z':'pelvis_vel_s',
    'pelvis_vel_X':'pelvis_vel_t',
    'torso_vel_Y':'torso_vel_f',
    'torso_vel_Z':'torso_vel_s',
    'torso_vel_X':'torso_vel_t',
    'femur_r_vel_Y':'thigh_vel_f_r',
    'femur_r_vel_Z':'thigh_vel_s_r',
    'femur_r_vel_X':'thigh_vel_t_r',
    'tibia_r_vel_Y':'shank_vel_f_r',
    'tibia_r_vel_Z':'shank_vel_s_r',
    'tibia_r_vel_X':'shank_vel_t_r',
    'talus_r_vel_Y':'talus_vel_f_r',
    'talus_r_vel_Z':'talus_vel_s_r',
    'talus_r_vel_X':'talus_vel_t_r',
    'calcn_r_vel_Y':'foot_vel_f_r',
    'calcn_r_vel_Z':'foot_vel_s_r',
    'calcn_r_vel_X':'foot_vel_t_r',
    'toes_r_vel_Y':'toes_vel_f_r',
    'toes_r_vel_Z':'toes_vel_s_r',
    'toes_r_vel_X':'toes_vel_t_r',

    'femur_l_vel_Y':'thigh_vel_f_l',
    'femur_l_vel_Z':'thigh_vel_s_l',
    'femur_l_vel_X':'thigh_vel_t_l',
    'tibia_l_vel_Y':'shank_vel_f_l',
    'tibia_l_vel_Z':'shank_vel_s_l',
    'tibia_l_vel_X':'shank_vel_t_l',
    'talus_l_vel_Y':'talus_vel_f_l',
    'talus_l_vel_Z':'talus_vel_s_l',
    'talus_l_vel_X':'talus_vel_t_l',
    'calcn_l_vel_Y':'foot_vel_f_l',
    'calcn_l_vel_Z':'foot_vel_s_l',
    'calcn_l_vel_X':'foot_vel_t_l',
    'toes_l_vel_Y':'toes_vel_f_l',
    'toes_l_vel_Z':'toes_vel_s_l',
    'toes_l_vel_X':'toes_vel_t_l',

    # GRF - Ground Reaction Forces (keeping left/right for time-indexed data)
    # From z*x=y coordinate to x*y=z coordinate system
    # Using standardized naming: grf_<axis>_<side>_<unit>
    "RForceX": "grf_anterior_r_N",
    "RForceY_Vertical": "grf_vertical_r_N",
    "RForceZ": "grf_lateral_r_N",
    "RCOPX": "cop_anterior_r_m",
    "RCOPY_Vertical": "cop_vertical_r_m",
    "RCOPZ": "cop_lateral_r_m",
    "LForceX": "grf_anterior_l_N",
    "LForceY_Vertical": "grf_vertical_l_N",
    "LForceZ": "grf_lateral_l_N",
    "LCOPX": "cop_anterior_l_m",
    "LCOPY_Vertical": "cop_vertical_l_m",
    "LCOPZ": "cop_lateral_l_m",
}


# Create a function that will fix joint angle conventions. In the dataset the 
cols_to_flip_signs = [ 
     # Flip knee torques if needed
    # 'knee_flexion_moment_r_Nm','knee_flexion_moment_l_Nm',
    # From z*x=y coordinate to x*y=z - update for standardized naming
    "cop_anterior_r_m", 
    "cop_anterior_l_m",
    "cop_lateral_r_m",
    "cop_lateral_l_m",
    "grf_anterior_r_N",
    "grf_anterior_l_N",
    "grf_lateral_r_N",
    "grf_lateral_l_N"
]
import re
def convert_dataset_to_pandas():
    '''
    This function is meant to convert the dataset to a pandas dataframe
    '''
    # First, get a list of all the files that are available in the dataset
    # Then we will filter down to the files that we are interested in saving,
    # and then append them to a dataframe
    file_list = []
    # Check if a specific subject was provided as argument
    if len(sys.argv) > 1:
        subject_to_process = sys.argv[1]
        # Verify the subject exists
        if os.path.exists(os.path.join(base_path, subject_to_process)):
            subject_dirs = [subject_to_process]
            print(f"Processing single subject: {subject_to_process}")
        else:
            print(f"Subject {subject_to_process} not found in {base_path}")
            sys.exit(1)
    else:
        # Get all subject folders
        subject_dirs = os.listdir(base_path)
        pattern = re.compile(r'^[^a-zA-Z]')
        
        # Use list comprehension to filter out strings that start with non-letter characters
        subject_dirs = [string for string in subject_dirs if not pattern.match(string)]
        print(f"Processing all subjects: {subject_dirs}")


    # Remove the Subject_masses.csv file
    try:
        subject_dirs.remove('Subject_masses.csv')
        
    except ValueError:
        pass

    # Remove pycache
    try:
        
        subject_dirs.remove('__pycache__')
    except ValueError:
        pass

    # (1) Create a list of all the files that we want to potentially save
    for subject in tqdm(subject_dirs):
        # Loop through the activity folders
        for activity in os.listdir(os.path.join(base_path, subject, "CSV_Data")):
            # Loop through the files
            for file in os.listdir(os.path.join(base_path, subject, 
                                                "CSV_Data", activity)):
                # Append the file to the list
                file_list.append((subject, activity, file))    
    
    # Create an dictionary to store the dataframes for a subject and activity
    # The keys will be a tuple of (subject, activity). This will be used to 
    # concatenate the dataframes later
    dataframes = {}

    # (2) Loop through the files and decide if we want to keep it. If we do
    # keep it, append it to the dictionary
    print("Start picking\n")
    for file_wrap in tqdm(file_list):
        subject, activity, file_name=file_wrap
        # Get the data unit (moment_filt, angle, velocity, etc)
        data_unit = file_name.split('.')[0]
    
        # If the data type is not in the list of data to save, skip it
        if data_unit not in data_to_save:
            continue
        
        # Show the progress on the same line
        #print(f'Processing {subject} {activity} {data_unit}'+' '*20, end='\r')

        # Get the file path
        file_path = os.path.join(base_path, subject, "CSV_Data", activity, file_name)
        
        # Read the file into a dataframe
        df = pd.read_csv(file_path, header=0)
        
        # Add the subject and activity to the dictionary
        if (subject, activity) not in dataframes.keys():
            dataframes[(subject, activity)] = []

        # Add the dataframe to the dictionary
        dataframes[(subject, activity)].append((data_unit,df))

    # (3) For all the (subject, activity) tuples, horizontally concatenate the 
    # dataframes. Additionally add the global angles if they are in the 
    # data_to_save list (assuming they have been calculated with 
    # convert_gtech_nc_rotm_to_eul_csv.m) 
    print("Start processing \n")
    #Create an empty dataframe
    df_total = pd.DataFrame()



    # Log for missing data
    missing_log= open("_datamissing.txt", "w")
    print("hhh")

    # Loop through the keys
    for key_num, key in tqdm(enumerate(dataframes.keys())):

        # Show percentage of completion in the same line
        #print(f'Processing {key_num+1}/{len(dataframes.keys())}'+' '*30,      end='\r')

        # Verify that we have all the data types that we want
        # assert len(dataframes[key]) == len(data_to_save), \
        #     print(f'Missing data for {key}')
        
        #Report data missing in the log, instead of breaking
        if len(dataframes[key]) != len(data_to_save):
             missing_log.write(f'Missing data for {key}\n')
             

        # Get the subject and activity
        subject = key[0]
        activity = key[1]

        # Create an empty dataframe to concatenate the data units
        _,df =  dataframes[key][0]

        # Merge all the dataframes
        for data_type,sub_df in dataframes[key][1:]:
            df = pd.merge(df, sub_df, on='time')

        # Rename time column to follow standard
        df.rename(columns={'time': 'time_s'}, inplace=True)

        # Following naming convention: DATASET_POPULATION+NUMBER
        # GT23 = Georgia Tech 2023, AB = Able-bodied
        # Extract subject number (e.g., '01' from 'AB01')
        subject_num = subject[2:] if subject.startswith('AB') else subject
        subject_id = 'GT23_AB' + subject_num.zfill(2)
        df['subject'] = subject_id

        # Parse activity name using task mapping utility
        task, task_id, task_info = parse_gtech_activity_name(activity)
        df['task'] = task
        df['task_id'] = task_id
        df['task_info'] = task_info

        # Add subject metadata (empty for now, could be populated from metadata files)
        df['subject_metadata'] = get_subject_metadata(subject_id)

        # Add step column (initialize to 0 for time-indexed data)
        df['step'] = 0

        # Concatenate the different subject/activities with the rest of the 
        # dataset
        df_total = pd.concat([df_total, df], 
                             ignore_index=True, 
                             axis=0)

    print("Processing done")
    # (4) Update the column names to the standardized names and flip the signs
    # of the joint angles and torques
    print(df_total.columns)
    df_total.rename(columns=standard_column_names, inplace=True)
    print(df_total.columns)
    #testing for float/string bugs
    #df_total[cols_to_flip_signs] = df_total[cols_to_flip_signs] * -1

    # (4b) Convert joint angles and velocities from degrees to radians
    # Joint angle columns that need conversion (not segment/link angles)
    joint_angle_cols = [
        'hip_flexion_angle_r_rad', 'hip_adduction_angle_r_rad', 'hip_rotation_angle_r_rad',
        'knee_flexion_angle_r_rad', 'ankle_dorsiflexion_angle_r_rad', 'ankle_eversion_angle_r_rad',
        'hip_flexion_angle_l_rad', 'hip_adduction_angle_l_rad', 'hip_rotation_angle_l_rad',
        'knee_flexion_angle_l_rad', 'ankle_dorsiflexion_angle_l_rad', 'ankle_eversion_angle_l_rad'
    ]
    
    # Joint velocity columns that need conversion (not segment/link velocities)
    joint_velocity_cols = [
        'hip_flexion_velocity_r_rad_s', 'hip_adduction_velocity_r_rad_s', 'hip_rotation_velocity_r_rad_s',
        'knee_flexion_velocity_r_rad_s', 'ankle_dorsiflexion_velocity_r_rad_s', 'ankle_eversion_velocity_r_rad_s',
        'hip_flexion_velocity_l_rad_s', 'hip_adduction_velocity_l_rad_s', 'hip_rotation_velocity_l_rad_s',
        'knee_flexion_velocity_l_rad_s', 'ankle_dorsiflexion_velocity_l_rad_s', 'ankle_eversion_velocity_l_rad_s'
    ]
    
    # Convert degrees to radians for joint angles
    for col in joint_angle_cols:
        if col in df_total.columns:
            df_total[col] = df_total[col] * np.pi / 180.0
            print(f"Converted {col} from degrees to radians")
    
    # Convert deg/s to rad/s for joint velocities
    for col in joint_velocity_cols:
        if col in df_total.columns:
            df_total[col] = df_total[col] * np.pi / 180.0
            print(f"Converted {col} from deg/s to rad/s")
    
    # (5) Save the dataframe
    print(df_total.columns)
    
    # Determine output filename
    if len(sys.argv) > 1:
        output_filename = f'gtech_2023_time_{sys.argv[1]}.parquet'
    else:
        output_filename = 'gtech_2023_time.parquet'
    
    # Save to converted_datasets folder in project root
    output_path = os.path.join('..', '..', '..', 'converted_datasets', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df_total.to_parquet(output_path)
    print(f'Done - saved to {output_path}')
    print(f'Memory usage: {df_total.memory_usage(deep=True).sum() / 1024**2:.1f} MB')
        
if __name__ == '__main__':
    convert_dataset_to_pandas()
