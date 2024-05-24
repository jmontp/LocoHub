# A human lower-limb biomechanics and wearable sensors dataset during cyclic and non-cyclic activities

[Link to publication](https://springernature.figshare.com/collections/_/5175254)
[Link to detailed description](https://springernature.figshare.com/ndownloader/files/28998039)

This folder contains the code to convert the hirearchical formatted data into the tabular representation. It has two flavors: time indexed and phase indexed. Additionally, an additional script is created to convert the global angles from a rotation matrix representation to euler angles. These scripts are explained below. 


# Time indexed data

The "convert_gtech_nc_raw_to_parquet.py" script converts the data from the raw data of the dataset to a tabular format. To use the script, you first need to download the "RawDataset.zip" from the [dataset repository](https://repository.gatech.edu/entities/publication/20860ffb-71fd-4049-a033-cd0ff308339e) and extract the contents inside this folder. 


## Data Sampling Frequencies

- **Joint Metrics (Angles, Forces, Moments, Powers):** Recorded at 100 Hz
- **Force Plate Data:** Recorded at 1000 Hz


Usage notes:
* Currently this does not include detalied task segmentation such as different walking speeds. 

# Phase indexed data

The "convert_gtech_nc_segmented_to_parquet.m" script converts the data from the segmented portion of the dataset to the tabular format.

Usage Information
* Points per step = 150

Usage configuration
* Phase synchronization: When this flag is set to true, the phases for the right leg and the left leg will both be set to zero. When this flag is false, one leg will have a 50% phase offset so that the the time axis for the left and the right leg are approximately the same.

Usage notes
* Many of the right leg data is missing since there was a hardware error and force plate data could not be collected. Since segmentation of the right foot data could not be

# Task naming

normal_walking -> level_walking
incline_walking (+-) -> inline_walking(+) & decline_walking(-)
stairs (+-) -> stairs_up (+) & stairs_down (-)
