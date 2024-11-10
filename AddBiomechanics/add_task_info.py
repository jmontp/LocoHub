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
    pass

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