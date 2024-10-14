"""
This file is meant to add phase information to the add_biomechanics datasets,
but should generally work for any dataframe that has grf data in N units. 

It can be used either by directly calling it and selecting the file, or by 
importing it and using the add_phase_info function.

In general, this is the script version of add_phase_info.ipynb, but with some
additional functionality to make it more generalizable and none of the 
visualization code.

author: José A. Montes Pérez
date: 09/26/2024
email: jmontp@umich.edu
"""

# Reference for phase segmenting non-gait tasks (i.e. squats, jumps, etc.) 
# How gtech 2023 did it, relevant content is at the end.
# https://repository.gatech.edu/server/api/core/bitstreams/b51011a2-061f-419c-9bb3-88e1d6fdf8e8/content

# Import stuff, load data
import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def add_phase_info(df:pd.DataFrame, export_phase_dataframe=True,
                   remove_original_file=None, save_name=None, 
                   plot_distributions=False):
    """
    This function adds phase information to a dataframe that has grf data 
    in N units. It is expected that the dataframe has the following columns:
    - 'time' : time in seconds
    - 'task' : task being performed
    - 'grf_y_r' : ground reaction force in x direction for the right leg
    - 'grf_y_l' : ground reaction force in x direction for the left leg

    This function will add the following columns:
    - 'phase_r' : the phase of the gait cycle for the right leg
    - 'phase_l' : the phase of the gait cycle for the left leg
    
    Optionally, it will also return a dataframe that has equal spacing in phase
    for all the strides. This is useful for analyzing average steps. 

    Parameters:
    dataframe (pd.DataFrame) : the dataframe to add phase information to
    export_phase_dataframe (bool) : whether to return the phase dataframe
    remove_original_file (str) : the path to the original file to remove 
        (optional)
    save_name (str) : the name of the file to save the dataframe to (optional)
        files will have "_time" and "_phase" appended to them.
    plot_distributions (bool) : whether to plot the distributions of the 
        stride times for each subject and task before and after outlier removal

    Returns:
    pd.DataFrame : the dataframe with phase information
    pd.DataFrame : the phase dataframe
    """

    # Constants
    # Number of points to use for the interpolation
    num_phase_points = 150
    phase_points = np.linspace(0, 1, num_phase_points)
    grf_threshold = 50 # N

    # Process per subject
    subjects = df['subject'].unique()
    
    # Initialize the columns
    df['phase_r'] = np.nan
    df['phase_l'] = np.nan
    df['stance_r'] = np.nan
    df['stance_l'] = np.nan
    
    for leg in ['r', 'l']:
        grf_y = df[f'grf_y_{leg}'].values
        stance_swing = grf_y > grf_threshold
        df.loc[stance_swing, f'stance_{leg}'] = 1
        df.loc[~stance_swing, f'stance_{leg}'] = 0

    # Create the phase dataframe if requested
    for subject_idx, subject in tqdm(enumerate(subjects),
                                     total=len(subjects),
                                     desc='Processing subjects'):
        
        # Iterate over each leg
        for leg_idx, leg in enumerate(['l', 'r']):

            ## Step 1: GRF thresholding to get swing (0) and stance (1) phases
            # Get the GRF data
            stance_swing = df.loc[df['subject'] == subject, f'stance_{leg}'].values
            subject_index = df.loc[df['subject'] == subject].index

            ## Step 2: Find swing-to-stance (1) and stance-to-swing (-1) transitions
            # Find the transitions using diff 
            transitions = np.diff(stance_swing.astype(int))
            swing_to_stance = np.where(transitions == 1)[0]
            stance_to_swing = np.where(transitions == -1)[0]

            # Update the index based on the swing-to-stance transitions
            swing_to_stance_df_index = subject_index[swing_to_stance]

            ## Step 3: Find the steady-state strides by filtering for positive 
            # stride times and removing the strides that are outliers based on 
            # a boxplot analysis
            time = df.loc[df['subject'] == subject, 'time']

            # Find the stride times which is defined by consecutive 
            # swing-to-stance transitions
            stride_time = time[swing_to_stance_df_index].diff().values
            # Remove the first stride time because it is always 0
            stride_time = stride_time[1:]
            # Create stride tuples with the start and stop time for each stride
            stride_tuples = [(swing_to_stance_df_index[i], 
                              swing_to_stance_df_index[i+1]) 
                             for i in range(len(stride_time))]

            # First, remove the negative stride times
            positive_strides = stride_time > 0
            stride_time = stride_time[positive_strides]
            stride_tuples = [stride_tuples[i] 
                             for i in range(len(stride_tuples)) 
                             if positive_strides[i]]
            stride_time_pre_filter = stride_time.copy()

            # If there are no valid strides, skip the leg
            if len(stride_time) == 0:
                continue

            # Remove all the outliers of the box plot
            q1 = np.percentile(stride_time, 25)
            q3 = np.percentile(stride_time, 75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr

            # Remove the outlier stride durations that are longer than the upper
            # do not do lower bound
            in_bounds_strides = (stride_time > lower_bound) & (stride_time < upper_bound)
            # in_bounds_strides = stride_time < upper_bound
            stride_time = stride_time[in_bounds_strides]
            stride_tuples = [stride_tuples[i] for i in range(len(stride_tuples)) if in_bounds_strides[i]]

            # Plot the distributions of the stride times for each subject and task
            if plot_distributions:
                plot_distributions_function(stride_time_pre_filter, stride_time,
                                            subject, leg)

            ## Step 4: Calculate the phase for each step
            # If we are exporting the phase dataframe, initialize it to be
            # len(valid_stride_num) * num_phase_points long
            df_phase_leg = pd.DataFrame(  # For a single leg
                index=np.arange(len(stride_tuples) * num_phase_points),
                columns=list(df.columns)+['phase','phase_leading_leg']
            )

            # Iterate over each stride
            for i, (start,end) in tqdm(enumerate(stride_tuples), 
                                  total=len(stride_tuples),
                                  desc=f'Calculating phase {leg}'):
      
                # Calculate the phase for the time dataset
                phase = np.linspace(0, 1, end-start+1)

                # Add the phase to the dataframe
                df.loc[start:end, f'phase_{leg}'] = phase

                # If we are exporting the phase dataframe, add the phase to it
                if export_phase_dataframe:
                    # Get the start and end of the phase to index the dataframe
                    p_s = i*num_phase_points     # start
                    p_e = (i+1)*num_phase_points-1 # end

                    # Create the axis to interpolate the data for the phase for 
                    # the given stride
                    phase_stride_points = np.linspace(0,1,end-start+1)

                    # Interpolate the data
                    for column in df.columns:
                        # Verify that the column is a float column
                        if df[column].dtype != 'float64':
                            continue
                        # Interpolate the data
                        data = df.loc[start:end, column].values
                        interp_data = np.interp(
                            phase_points, phase_stride_points, data
                        )
                        df_phase_leg.loc[p_s:p_e, column] = interp_data
                    # Add the subject and task information to the dataframe
                    df_phase_leg.loc[p_s:p_e,'subject'] = df.loc[start, 'subject']
                    df_phase_leg.loc[p_s:p_e,'task'] = df.loc[start, 'task']
                    df_phase_leg.loc[p_s:p_e,'phase_leading_leg'] = leg
                    df_phase_leg.loc[p_s:p_e,'phase'] = phase_points

        
            # Add the stride to the phase dataframe
            if export_phase_dataframe and save_name is not None:
                # If it's the first leg, initialize the dataframe
                if subject_idx == 0 and leg_idx == 0:
                    # Save the first leg dataframe to parquet
                    df_phase_leg.to_parquet(save_name+'_phase.parquet',
                                            engine='fastparquet')
                else:
                    # Try to remove the phase_{leg} column from the dataframe
                    try:
                        df_phase_leg = df_phase_leg.drop(columns=['phase_l',
                                                                  'phase_r'])
                    except:
                        pass
                    # Append the dataframe to the existing one
                    df_phase_leg.to_parquet(save_name+'_phase.parquet', 
                                            engine='fastparquet',
                                            append=True)
    # Fill the NaN values with the previous value
    # df = df.ffill()
    
    # Remove the original file if requested
    if remove_original_file is not None:
        os.remove(remove_original_file)
    # Save the dataframe if requested
    if save_name is not None:
        # Remove the 'time' in the save name
        save_name = save_name.replace('_time', '')
        df.to_parquet(save_name+'_time.parquet')

    if plot_distributions:
        import matplotlib.pyplot as plt
        plt.show()

def plot_distributions_function(time_distribution, filtered_time_distribution,
                                subject, leg):
    """
    Plots the distributions of the stride times for each subject and task 
    before and after outlier removal.
    """
    import matplotlib.pyplot as plt
    # Plot the distributions
    plt.figure()
    plt.hist(time_distribution, bins=50, alpha=0.5, label='Pre-filter')
    plt.hist(filtered_time_distribution, bins=50, alpha=0.5, label='Post-filter')
    plt.title(f'Stride time distribution for {subject} {leg}')
    plt.xlabel('Stride time (s)')
    plt.ylabel('Frequency')
    plt.legend()

if __name__ == '__main__':
    # Open file dialog to select file
    # import tkinter as tk
    # from tkinter import filedialog
    # root = tk.Tk()
    # root.withdraw()
    # file_path = filedialog.askopenfilename()

    # file_path = '/datasets/AddBiomechanics/processed_data/Carter2023.parquet'
    file_path = '../Umich_2021/umich_2021_time.parquet'
    df = pd.read_parquet(file_path)

    add_phase_info(df, save_name=file_path[:-8],
                   remove_original_file=file_path,
                   export_phase_dataframe=False,
                   plot_distributions=True)
