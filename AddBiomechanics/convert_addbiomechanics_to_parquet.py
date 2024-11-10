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
import matplotlib.pyplot as plt
import fastparquet as fp
import os
import numpy as np

from add_phase_info import add_phase_info
from b3d_to_parquet import b3d_to_parquet
from add_task_info import add_task_info
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


#### End of User Configuration Section ########################################


def process_dataset(dataset_name):

    # Convert the b3d files to parquet
    b3d_to_parquet(dataset_name)
    b3d_output_name = os.path.join(output_dir, dataset_name+'.parquet')

    # Invert the columns that need to be inverted
    df = pd.read_parquet(b3d_output_name)
    for column in flip_columns:
        df[column] = -df[column]

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

    # Add task information
    add_task_info(df,dataset_name)

    # Add Phase to the dataframe. This also saves the dataframe 
    # to a time and phase parquet files. 
    add_phase_info(df, export_phase_dataframe=True,
                   save_name=b3d_output_name.replace('.parquet', ''),
                   remove_original_file=b3d_output_name)

    print(f"Finished. Data saved to {b3d_output_name}")

if __name__ == '__main__':
    with Pool() as pool:
        pool.map(process_dataset, datasets_to_process)
