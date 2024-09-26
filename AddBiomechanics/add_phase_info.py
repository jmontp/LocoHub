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

# Import stuff, load data
import pandas as pd
import numpy as np
import os

def add_phase_info(dataframe:pd.DataFrame, export_phase_dataframe=True,
                   remove_original_file=None, save_name=None):
    """
    This function adds phase information to a dataframe that has grf data 
    in N units. It is expected that the dataframe has the following columns:
    - 'time' : time in seconds
    - 'task' : task being performed
    - 'grf_z_r' : ground reaction force in x direction for the right leg
    - 'grf_z_l' : ground reaction force in x direction for the left leg

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
    

    Returns:
    pd.DataFrame : the dataframe with phase information
    pd.DataFrame : the phase dataframe
    """

    # Constants
    # Number of points to use for the interpolation
    num_phase_points = 150
    phase_points = np.linspace(0, 1, num_phase_points)
    grf_threshold = 20 # N

    # Iterate over each leg
    for leg_idx, leg in enumerate(['l', 'r']):

        ## Step 1: GRF thresholding to get swing (0) and stance (1) phases
        # Get the GRF data
        grf_z = dataframe[f'grf_z_{leg}'].values
        stance_swing = grf_z > grf_threshold

        ## Step 2: Find swing-to-stance (1) and stance-to-swing (-1) transitions
        # Find the transitions using diff 
        transitions = np.diff(stance_swing.astype(int))
        swing_to_stance = np.where(transitions == 1)[0]
        stance_to_swing = np.where(transitions == -1)[0]

        ## Step 3: Find the steady-state strides by filtering for positive 
        # stride times and removing the strides that are outliers based on 
        # a boxplot analysis
        time = df['time_step'].values

        # Find the stride times which is defined by consecutive 
        # swing-to-stance transitions
        stride_time = time[swing_to_stance[1:]] - time[swing_to_stance[:-1]]
        
        # Create a list that contains the indexes of the valid strides
        valid_stride = np.arange(len(stride_time))

        # First, remove the negative stride times
        positive_strides = stride_time > 0
        stride_time = stride_time[positive_strides]
        valid_stride_num = valid_stride[positive_strides]

        # Remove all the outliers of the box plot
        q1 = np.percentile(stride_time, 25)
        q3 = np.percentile(stride_time, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Remove the outlier stride durations
        in_bounds_strides = (stride_time > lower_bound) & (stride_time < upper_bound)
        stride_time = stride_time[in_bounds_strides]
        valid_stride_num = valid_stride_num[in_bounds_strides]

        ## Step 4: Calculate the phase for each step
        # Initialize the phase to be -1 for the dataframe
        df[f'phase_{leg}'] = -1

        # If we are exporting the phase dataframe, initialize it to be
        # len(valid_stride_num) * num_phase_points long
        df_phase_leg = pd.DataFrame(  # For a single leg
            index=np.arange(len(valid_stride_num) * num_phase_points),
            columns=df.columns+['phase_leading_leg']
        )

        # Iterate over each stride
        for i, stride in enumerate(valid_stride_num):
            
            # Update user on progress
            pct_done = i/len(valid_stride_num)*100
            print(f"Adding phase information.") 
            print(f"Percentage complete: {pct_done:.2f}%", end='\r')

            # Get the start and end of the stride
            start = swing_to_stance[stride]
            end = swing_to_stance[stride+1]

            # Calculate the phase for the time dataset
            phase = np.linspace(0, 1, end-start+1)

            # Add the phase to the dataframe
            df.loc[start:end, f'phase_{leg}'] = phase

            # If we are exporting the phase dataframe, add the phase to it
            if export_phase_dataframe:
                # Get the start and end of the phase to index the dataframe
                p_s = i*num_phase_points     # start
                p_e = (i+1)*num_phase_points # end

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
                df_phase_leg.loc[p_s:p_e,'subject'] = df['subject'].iloc[start]
                df_phase_leg.loc[p_s:p_e,'task'] = df['task'].iloc[start]
                df_phase_leg.loc[p_s:p_e,'phase_leading_leg'] = leg

    
        # Add the stride to the phase dataframe
        if export_phase_dataframe:
            # If it's the first leg, initialize the dataframe
            if leg_idx == 0:
                df_phase = df_phase_leg
            else:
                df_phase = pd.concat([df_phase, df_phase_leg], axis=0)

    # Save the dataframe if requested
    if save_name is not None:
        df.to_parquet(save_name+'_time.parquet')
        if export_phase_dataframe:
            df_phase.to_parquet(save_name+'_phase.parquet')

    # Remove the original file if requested
    if remove_original_file is not None:
        os.remove(remove_original_file)


if __name__ == '__main__':
    # Open file dialog to select file
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename()
    df = pd.read_parquet(file_path)