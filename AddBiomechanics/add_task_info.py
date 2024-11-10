import numpy as np

"""
This file contains the functions to add task information to the dataframe. 
There is also a column called "task_info_1" and "task_info_2" which contain
additional information about the task. 

The official task labels are: 
     task               | task_info_1    | task_info_2   
     -------------------|----------------|----------------	
- 0: standing_still     | ramp angle     | walking speed
- 1: level_walking      | ramp angle     | walking speed
- 3: decline_walking    | ramp angle     | walking speed
- 4: incline_walking    | ramp angle     | walking speed
- 5: stair_ascent       | step height    | step width
- 6: stair_descent      | step height    | step width
- 7: perturbations      | ramp angle     | walking speed
- 8: sit_to_stand       | N/A            | N/A
- 9: stand_to_sit       | N/A            | N/A
- 10: running           | ramp angle     | walking speed
- 11: modified_walking  | ramp angle     | walking speed
- 12: non_cyclic        | N/A            | N/A
"""



def add_task_info_moore2015(df):
    # Add a column called task_info with additional information 
    # about the task
    df['task_info'] = df['task']

    # There's only level-ground walking in this dataset
    df['task'] = 'level_walking'

    # Add a list of the walking speeds
    # https://peerj.com/articles/918/ 
    # Table 1
    walking_speed_task_speed_list = [
        # [Task number, Speed (m/s)]
        # 0.8 m/s
        [[9,12,15,16,19,25,32,40,46,49,55,61,67,73,76],0.8],
        # 1.2 m/s
        [[10,13,17,20,26,31,41,47,50,56,62,68,74,77],1.2],
        # 1.6 m/s
        [[11,14,18,21,27,33,42,48,51,57,63,69,75,78],1.6],
    ]
    # Add a column called walking_speed
    df['task_info_2'] = None
    # Set the walking speed for each task
    for task_list,speed in walking_speed_task_speed_list:
        for task in task_list:
            # First, convert the task number to a string
            task_str = str(task)
            # Then, set the walking speed for the task
            df.loc[df['task_info'].str.contains(task_str), 
                   'task_info_2'] = speed

    # Verify that all the walking speeds have been set
    assert df['task_info_2'].isnull().sum() == 0, \
        'Not all walking speeds have been set for the Moore2015 dataset'
    
    # Set the ramp angle to be zero 
    df['task_info_1'] = 0


def add_task_info_camargo2021(df):
    pass

def add_task_info_falisse2017(df):
    pass

def add_task_info_fregly2012(df):
    # TODO:Varun
    # Keep the original task column as task_info 
    df['task_info'] = df['task']
    # Set the subject name as the first two characters of the task
    df['subject'] = df['task'].str[:2]
    # Remove the first three characters of the task name
    df['task_info'] = df['task_info'].apply(lambda x: x[3:])

    # Create a list of the original tasks and the new task name
    # to be used for the conversion
    task_conversion_list = [
        # [Original task, New task]
        ['ngait', 'level_walking'],              # Normal Gait
        
        ['mtpgait', 'modified_walking'],    # Medial Trus
        ['medthrust', 'modified_walking'],  # Medial Thrust
        ['mtgait', 'modified_walking'],     # Medial Thrust Gait

        ['wpgait', 'modified_walking'],     # Walking Pole
        ['tsgait', 'modified_walking'],     # Trunk Sway Gait
        
        ['mildcrouch', 'modified_walking'], # Mild Crouch Gait
        ['crouch_og', 'modified_walking'],  # Crouch Gait
        
        ['bouncy', 'modified_walking'],     # Bouncy Gait
        ['smooth', 'modified_walking'],     # Smooth Gait?
        ['rightturn', 'modified_walking'],  # Right Turn
    ]
    # Convert the tasks to the same format as in the other datasets
    for old_task,new_task in task_conversion_list:
        df.loc[df['task'].str.contains(old_task), 'task'] = new_task

    # Set the ramp angle to be zero 
    df['task_info_1'] = 0

    # Set the walking speed to be None
    df['task_info_2'] = np.nan

def add_task_info_hamner2013(df):
    """
    This dataset contains running tasks with different speeds at level ground
    """
    # Preserve the original task information
    df['task_info'] = df['task']
    
    # Set the new task information
    df['task'] = 'running'
    
    # Running speed is dependent on the integer value of the task
    # Tasks are 'run200', 'run300', 'run400', and 'run500'	
    df['task_info_2'] = None
    for i in range(2,6):
        df.loc[df['task_info'].str.contains(str(i)), 'task_info_2'] = float(i)
    # Verify that all the walking speeds have been set
    assert df['task_info_2'].isnull().sum() == 0, \
        'Not all walking speeds have been set for the Hamner2013 dataset'
    
    # Set the ramp angle to be zero 
    df['task_info_1'] = 0

def add_task_info_han2023(df):
    pass

def add_task_info_santos2017(df):
    """"
    This dataset is only for standing still, therefore the entire 
    dataframe is set to task 0: standing still. and the task_info_1 and 
    task_info_2 are set to N/A.
    """
    # Preserve the original task information
    df['task_info'] = df['task']
    
    # Set the new task information
    df['task'] = 'standing_still'
    df['task_info_1'] = np.nan
    df['task_info_2'] = np.nan

def add_task_info_tan2021(df):
    pass

def add_task_info_tan2022(df):
    """
    This dataset only has running
    """
    # Preserve the original task information
    df['task_info'] = df['task']
    
    # This dataset only has running
    df['task'] = 'running'

    # Set the ramp angle to be zero 
    df['task_info_1'] = 0

    # Set the walking speed to be None
    df['task_info_2'] = np.nan

def add_task_info_tiziana2019(df):
    pass

def add_task_info_vanderzee2022(df):
    # https://www.nature.com/articles/s41597-022-01817-1/tables/3
    # Has all the information for the speed, step length, step frequency, 
    # step width, and walking condition

    # Add a column called task_info with additional information 
    # about the task
    df['task_info'] = df['task']
    # Split the information from trial{number} to {number} (i.e. remove 
    # the word trial)
    df['task_info'] = df['task_info'].str.replace('trial', '')

    # Create a list of the original tasks and the new task name
    # to be used for the conversion
    task_conversion_list = [
        # [Original task, New task]
        ['trial', 'level_walking'],
    ]
    # Convert the tasks to the same format as in the other datasets
    for old_task,new_task in task_conversion_list:
        df.loc[df['task'].str.contains(old_task), 'task'] = new_task

    # Set the ramp angle to be zero 
    df['task_info_1'] = 0

    # Set the walking speed to be None
    df['task_info_2'] = np.nan


def add_task_info_wang2023(df):
     # Add a column called task_info with additional information 
    # about the task
    df['task_info'] = df['task']
    
    # Create a list of the original tasks and the new task name 
    # to be used for the conversion
    task_conversion_list = [
        # [Original task, New task]
        ['walk',         'level_walking'],
        ['run',          'running'],
        ['static_pose',  'non_cyclic'],
        ['jump',         'non_cyclic'],
        ['lunge',        'non_cyclic'],
        ['squat',        'non_cyclic'],
        ['land',         'non_cyclic'],
    ]
    # Convert the tasks to the same format as in the other datasets
    for old_task,new_task in task_conversion_list:
        df.loc[df['task'].str.contains(old_task), 'task'] = new_task

    # Add ground inclination
    df['task_info_1'] = 0

def add_task_info_carter2023(df):
    pass

dataset_name_to_function = {
    'Moore2015': add_task_info_moore2015,
    'Camargo2021': add_task_info_camargo2021,
    'Falisse2017': add_task_info_falisse2017,
    'Fregly2012': add_task_info_fregly2012,
    'Hamner2013': add_task_info_hamner2013,
    'Han2023': add_task_info_han2023,
    'Santos2017': add_task_info_santos2017,
    'Tan2021': add_task_info_tan2021,
    'Tan2022': add_task_info_tan2022,
    'Tiziana2019': add_task_info_tiziana2019,
    'vanderZee2022': add_task_info_vanderzee2022,
    'Wang2023': add_task_info_wang2023,
    'Carter2023': add_task_info_carter2023,
}


def add_task_info(df, dataset_name):
    dataset_name_to_function[dataset_name](df)