'''
This file is meant to convert the dataset to a pandas dataframe
'''

import pandas as pd
import numpy as np
import os

###############################################################################
# User configuration section

# This is the base path to the dataset. If you extracted the dataset to the 
# same folder as this file, you don't need to change this
base_path = 'RawData'

# This is the list of data types that we want to save. The options are:
# 'Activity_Flag', 'GroundFrame_GRFs', 'Joint_Angle', 'Joint_Moments',
# 'Joint_Powers', 'Joint_Velocities', 'Raw_EMGs', 'Real_IMUs', 'Virtual_IMUs',
# 'Virtual_Insoles', 'Link_Angle',
# Currently the only standardized names are
# 'Joint_Angle', 'Joint_Velocities', 'Joint_Moments', 'Link_Angle'
data_to_save = ['Joint_Moments', 'Angle', 'Velocities']

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

def convert_dataset_to_pandas():
    '''
    This function is meant to convert the dataset to a pandas dataframe
    '''
    # First, get a list of all the files that are available in the dataset
    # Then we will filter down to the files that we are interested in saving,
    # and then append them to a dataframe
    file_list = []
    # Get the subject folders
    subject_dirs = os.listdir(base_path)
    # Remove the Subject_masses.csv file
    try:
        subject_dirs.remove('Subject_masses.csv')
    except ValueError:
        pass

    # (1) Create a list of all the files that we want to potentially save
    for subject in subject_dirs:
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
    for subject, activity, file_name in file_list:
        
        # Get the data unit (moment_filt, angle, velocity, etc)
        data_unit = file_name.split('.')[0]
    
        # If the data type is not in the list of data to save, skip it
        if data_unit not in data_to_save:
            continue
        
        print(f'Processing {subject} {activity} {data_unit}')

        # Get the file path
        file_path = os.path.join(base_path, subject, "CSV_Data", activity, file_name)
        
        # Read the file into a dataframe
        df = pd.read_csv(file_path, header=0)
        
        # Add the subject and activity to the dictionary
        if (subject, activity) not in dataframes.keys():
            dataframes[(subject, activity)] = []

        # Add the dataframe to the dictionary
        dataframes[(subject, activity)].append(df)

    # (3) For all the (subject, activity) tuples, horizontally concatenate the 
    # dataframes. Additionally add the global angles if they are in the 
    # data_to_save list (assuming they have been calculated with 
    # convert_gtech_nc_rotm_to_eul_csv.m) 
    
    #Create an empty dataframe
    df_total = pd.DataFrame()

    # Loop through the keys
    for key in dataframes.keys():
        
        # Verify that we have all the data types that we want
        assert len(dataframes[key]) == len(data_to_save), \
            print(f'Missing data for {key}')

        # Get the subject and activity
        subject = key[0]
        activity = key[1]

        # Create an empty dataframe to concatenate the data units
        df = pd.DataFrame()

        # Merge all the dataframes
        df = pd.merge(dataframes[key][0], dataframes[key][1], on='time')
        df = pd.merge(df, dataframes[key][2], on='time')

        # Load the global angle data. This is in the Transforms_Euler folder
        # You need to run a matlab script to generate this data
        try:
            # Load the global angles
            global_angles_file = os.path.join(base_path, subject, 
                                              "Transforms_Euler", 
                                              f"{activity}.csv")
            cols = ['calcn_r_Z', 'calcn_l_Z']
            global_angles_df = \
                pd.read_csv(global_angles_file, usecols=cols, header=0)
            
            # Extract the global foot angle from the dataset. We are taking 
            # this as the calcaneus angle
            df['foot_angle_r'] = global_angles_df['calcn_r_Z']
            df['foot_angle_l'] = global_angles_df['calcn_l_Z']

            # Calculate the derivative of the global foot angle
            df['foot_velocity_r'] = np.gradient(df['foot_angle_r'], df['time'])
            df['foot_velocity_l'] = np.gradient(df['foot_angle_l'], df['time'])

            print(f"Adding the marker data for {subject} {activity}")
        
        except(KeyError):
            print(f"Missing global angle data for {subject} {activity}")

        # Add the activity and subject columns
        df['activity_long'] = activity
        df['subject'] = 'Gtech_NC_' + subject

        # Add the activity short name
        for short_activity_name in short_activity_names:
            if short_activity_name in activity:
                df['activity'] = short_activity_name
                break

        # Concatenate the different subject/activities with the rest of the 
        # dataset
        df_total = pd.concat([df_total, df], 
                             ignore_index=True, 
                             axis=0)
            
    # Save the dataframe
    df_total.to_parquet('gtech_non_cyclic_raw.parquet')
    print('Done')
        
if __name__ == '__main__':
    convert_dataset_to_pandas()