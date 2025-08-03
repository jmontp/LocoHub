import pandas as pd
import os
import matplotlib.pyplot as plt

def get_column_data(file_path, column_name):
    # Read the Parquet file
    data = pd.read_parquet(file_path)

    # Get the columns
    columns = data.columns

    # Print the columns
    print(columns)
    return data[column_name] 

def converting_to_phase(data):
    # ToDo: I need to implement the conversion to phase
    #Step 1: have a column of data with 0,1 based on the GRF threshold
    #Step 2: create an histogtam of this data, to remove the outliers (i.e data for standing or other transition activities)
    #Step 3: based on the slopes, do linear interpolation of the time data to phase 0->1
    return data

if __name__ == '__main__':
    # Getting the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Defining the file name
    file_name = 'Camargo2021_Formatted_No_Arm.parquet'

    # Constructing the full file path
    file_path = os.path.join(script_dir, file_name)

    print(file_path)
    c = ['GRF_x_r', 'GRF_y_r','GRF_z_r']
    for column_name in c:

        column_data = get_column_data(file_path, column_name)

        #Plotting
        # Plot the specified column
        plt.plot(column_data, label=column_name)  # You can change 'line' to other plot types like 'bar', 'hist', etc.

    plt.title(f'Plot of GRF Right')
    plt.xlabel('time')
    plt.grid(True)
    plt.legend()
    plt.show()