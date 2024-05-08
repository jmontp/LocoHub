"""
This script is meant to re-run the validation gifs for all the different 
datasets that we have created. To do this you have to input manually a 
file, subject, and task. This will then run the gif for the different
datasets in parallel.
"""

import os
import numpy as np
import pandas as pd
import multiprocessing
import subprocess
import multiprocessing



# Write down the file, subject, and task that you want to run the validation 
# gifs for

umich_2021_time = {
    'file':'Umich_2021/umich_2021_time_indexed.parquet',
    'subject_task_pairs': [('Umich_2021_AB01', 'level_walking', 2000),
                           ('Umich_2021_AB02', 'incline_walking', 2000),
                           ('Umich_2021_AB04', 'decline_walking', 2000),
                           ('Umich_2021_AB06', 'running', 2000),
                           ('Umich_2021_AB08','transitions', 2000)]
}

umich_2021_phase = {
    'file':'Umich_2021/umich_2021_phase_indexed.parquet',
    'subject_task_pairs': [('Umich_2021_AB01', 'level_walking', 0),
                           ('Umich_2021_AB02', 'incline_walking', 0),
                           ('Umich_2021_AB04', 'decline_walking', 0),
                           ('Umich_2021_AB06', 'running', 0)]
}

gtech_2023_time = {
    'file':'Gtech_2023/gtech_2023_time_indexed.parquet',
    'subject_task_pairs': [('Gtech_2023_AB01', 'dynamic_walk', 2000),
                           ('Gtech_2023_AB02', 'jump', 2000),
                           ('Gtech_2023_AB03', 'normal_walk', 2000),
                           ('Gtech_2023_AB12', 'stairs', 2000),
                           ('Gtech_2023_AB11', 'squats', 2000),
                           ('Gtech_2023_AB06', 'sit_to_stand', 2000)]
}

gtech_2023_phase = {
    'file':'Gtech_2023/gtech_2023_phase_indexed.parquet',
    'subject_task_pairs': [('Gtech_2023_AB01', 'dynamic_walk', 0),
                           ('Gtech_2023_AB02', 'jump', 0),
                           ('Gtech_2023_AB03', 'normal_walk', 0),
                           ('Gtech_2023_AB11', 'stairs', 0),
                           ('Gtech_2023_AB12', 'squats', 0),
                           ('Gtech_2023_AB06', 'sit_to_stand', 0)]
}


# Create a list of the different datasets
datasets = [
            umich_2021_time, 
            # umich_2021_phase, 
            # gtech_2023_time, 
            # gtech_2023_phase
            ]


def run_walking_animator(file, subject, task, jump):
    print(f"Starting {subject} {task}")
    subprocess.run(['python3', 'walking_animator.py', '-f', file, '-s', subject, '-t', task, '-j', f'{jump}', '-g'])
    print(f"Finished {subject} {task}")

# Create a pool of worker processes
pool = multiprocessing.Pool()

# Call the walking_animator.py script for each dataset in parallel
for dataset in datasets:
    file = dataset['file']
    subject_task_pairs = dataset['subject_task_pairs']
    for subject, task, jump in subject_task_pairs:
        pool.apply_async(run_walking_animator, args=(file, subject, task, jump))

# Close the pool and wait for all processes to finish
pool.close()
pool.join()
