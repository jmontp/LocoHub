'''
This file is meant to convert the dataset to a pandas dataframe
'''

import pandas as pd
import numpy as np
import os


short_activity_names = ['ball_toss', 'curb_down', 'curb_up', 'cutting',
                        'dynamic_walk', 'incline_walk', 'jump', 'lift_weight',
                        'lunges', 'meander', 'normal_walk', 'obstacle_walk',
                        'poses', 'push', 'side_shuffle', 'sit_to_stand', 
                        'squats', 'stairs', 'step_ups', 'tire_run', 
                        'tug_of_war', 'turn_and_step', 'twister', 
                        'walk_backward', 'weighted_walk',]

data_to_save = ['Moments', 'Angle', 'Velocities']

def convert_dataset_to_pandas():
    '''
    This function is meant to convert the dataset to a pandas dataframe
    '''
    # First, get a list of all the files that are available in the dataset
    # Then we will filter down to the files that we are interested in saving,
    # and then append them to a dataframe
    file_list = []
    # Loop through the subject folders
    base_path = 'RawData'
    # Get the subject folders
    subject_dirs = os.listdir(base_path)
    # Remove the Subject_masses.csv file
    try:
        subject_dirs.remove('Subject_masses.csv')
    except ValueError:
        pass

    # Loop through the subject folders
    for subject in subject_dirs:
    # for subject in ["AB01", "AB02"]:
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

    # Loop through the files and decide if we want to keep it
    for subject, activity, file_name in file_list:
        
        # Get the data unit (moment_filt, angle, velocity, etc)
        data_unit = file_name.split('_')[-1].split('.')[0]
    
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

    # For all the (subject, activity) tuples, concatenate the dataframes since
    # they have different data in them. Additionally add the marker data
    # Create an empty dataframe
    df_total = pd.DataFrame()

    # Loop through the keys
    for key in dataframes.keys():
        
        # Verify that we have all the data types
        assert len(dataframes[key]) == len(data_to_save), \
            print(f'Missing data type for {key}')

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