import numpy as np

"""
This file contains the functions to add task information to the dataframe. 
There is also a column called "task_info_1" and "task_info_2" which contain
additional information about the task. 

The official task labels are: 
     task             | task_info_1    | task_info_2
- 0: standing_still   | ramp angle     | walking speed
- 1: level_walking    | ramp angle     | walking speed
- 3: decline_walking  | ramp angle     | walking speed
- 4: incline_walking  | ramp angle     | walking speed
- 5: stair_ascent     | step height    | step width
- 6: stair_descent    | step height    | step width
- 7: perturbations    | ramp angle     | walking speed
- 8: sit_to_stand     | N/A            | N/A
- 9: stand_to_sit     | N/A            | N/A
"""



def add_task_info_moore2015(df):
    pass

def add_task_info_camargo2021(df):
    pass

def add_task_info_falisse2017(df):
    pass

def add_task_info_fregly2012(df):
    pass

def add_task_info_hamner2013(df):
    pass

def add_task_info_han2023(df):
    pass

def add_task_info_santos2017(df):
    """"
    This dataset is only for standing still, therefore the entire 
    dataframe is set to task 0: standing still. and the task_info_1 and 
    task_info_2 are set to N/A.
    """
    df.loc[:, 'task'] = 'standing_still'
    df.loc[:, 'task_info_1'] = np.nan
    df.loc[:, 'task_info_2'] = np.nan

def add_task_info_tan2021(df):
    pass

def add_task_info_tan2022(df):
    pass

def add_task_info_tiziana2019(df):
    pass

def add_task_info_vanderzee2022(df):
    pass

def add_task_info_wang2023(df):
    pass

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