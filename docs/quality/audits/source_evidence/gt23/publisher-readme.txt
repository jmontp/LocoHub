/////  OVERVIEW  /////
A Human Lower-Limb Biomechanics and Wearable Sensors Dataset During Cyclic and Non-Cyclic Activities
Corresponding Author: Keaton Scherpereel, keaton@gatech.edu
Collection details and explanation included in the associated publication
Date last modified: 10/16/2023

File Structure:
ProcessedData.zip
	<subject>
		<task name>
			<subject>_<task name>_activity_flag.csv: True if task is actively occurring at each instance in time (boolean).
			<subject>_<task name>_angle.csv: Joint kinematics from opensim (deg) at 200 Hz.
			<subject>_<task name>_emg.csv: EMG measured using Delsys system (V) at 2000 Hz (a different sampling rate than the rest of the data).
			<subject>_<task name>_grf.csv: Measured ground reaction forces in the OpenSim global frame at 200 Hz (y-axis is vertical).
			<subject>_<task name>_imu_real.csv: Measured accel and gyro data from Delsys systems (m/s2 and deg/s) at 200 Hz.
			<subject>_<task name>_imu_sim.csv: Simulated accel and gyro data for general pelvis, thigh, shank, and foot (m/s2 and deg/s) at 200 Hz. See publication for details.
			<subject>_<task name>_insole_sim.csv: Measured ground reaction forces in calcn_l and calcn_r frames at 200 Hz.
			<subject>_<task name>_moment.csv: Joint torques from opensim (Nm) at 200 Hz.
			<subject>_<task name>_moment_filt.csv: Joint torques from opensim (Nm) at 200 Hz. Data are filtered using a zero lag 5th order lowpass filter with a 6 Hz cutoff frequency.
			<subject>_<task name>_power.csv: Joint powers (W) at 200 Hz.
			<subject>_<task name>_velocity.csv: Joint velocities computed using first-order backward finite differencing of _angle data at 200 Hz (deg/s).

Note: <task name> is constructed as <base task name>_<vicon trial number>_<task description>. <vicon trial number> is not consistent across subjects and can largely be ignored since it was only used to increment the trial names when collecting <base task name> data in separate Vicon collections during each experiment. This was implemented to reduce experimental complexity.

RawData.zip
	<subject>
		CSV_Data
			<base task name> Same contents as the subject specific directories in the ProcessedData folder but with all of the transition data from the entire base task
				Activity_Flag.csv: True if task is actively occurring at each instance in time (boolean).
				GroundFrame_GRFs.csv: Measured ground reaction forces in the OpenSim global frame at 200 Hz (y-axis is vertical).
				Joint_Angle.csv: Joint kinematics from opensim (deg) at 200 Hz.
				Joint_Moments.csv: Joint torques from opensim (Nm) at 200 Hz.
				Joint_Powers.csv: Joint powers (W) at 200 Hz.
				Joint_Velocities.csv: Joint velocities computed using first-order backward finite differencing of JointAngle data at 200 Hz (deg/s).
				Raw_EMGs.csv: EMG measured using Delsys system (V) at 2000 Hz (a different sampling rate than the rest of the data).
				Real_IMUs.csv: Measured accel and gyro data from Delsys systems (m/s2 and deg/s) at 200 Hz.
				Virtual_IMUs.csv: Simulated accel and gyro data for general pelvis, thigh, shank, and foot (m/s2 and deg/s) at 200 Hz.
				Virtual_Insoles.csv: Measured ground reaction forces in calcn_l and calcn_r frames at 200 Hz.
		ExtLoads: A folder of <base task name>.mot files containing ground reaction forces (1000 Hz) from each base task split by leg and if necessary (sit_to_stand), pelvis
		MarkerData: A folder of <base task name>.trc files containing marker locations for each frame (200 Hz) from each base task
		Models: A folder of <subject>_Scaled<static_number>.osim files (OpenSim version 3.3) for each subject model (anytime a marker fell off a new model was created with that changed marker position on the skeleton) and a Statics.csv to indicate which <static_number> was used for each base task
		Transforms: A folder of <base task name>.mat files containing a Transforms table that contains the transformation matrices to translate from ground frame to segment frame for each time point and osim body segment
	Subject_masses.csv: A table containing the mass in kg for each subject
	
C3Ds.zip (separate from RawData due to size)
	<subject>
		ViconData: A folder of <base task name>.c3d files for each base task
		
Segmentation.zip (segmentation information listed below)
	<subject>
		<task_name>_parsing.mat: A mat file containing matrices for right and left where each row represents a cycle and the first column is the start time and the second is the end time (if a further breakdown is necessary a types cell array is included with those types and the files are then right_<type> and left_<type>)
		<task_name>_segmentation(optional _<type>).mat: A mat file with angle, moment, power, and velocity structs that contain segmented data and avg data based on the tasks and further delineations as specified by <type>
		
Code.zip
	example_script_IMUs_and_grouping.m: script that gives an example of adding new IMUs and grouping tasks with grouping function
	example_script_plotting.m: script that gives an example of plotting angle, moment, and power for all of the tasks
	GroupTasks.m: function for grouping tasks based on the grouping used in the paper
	Plot_3x3_plots.m: function for plotting subject average curves for this dataset
	TransformIMUs.m: funtion for transforming IMUs to a new desired location
	
Angle_Moment_Power_Plots.zip: A folder containing across subject average plots for angle, moment, and power at each joint

Torque_Velocity_Plots.zip: A folder containing the boundary of torque and velocity requirements for each task

Videos.zip
	Cyclic_tasks.mp4: Video explaining the cyclic tasks (not recorded during actual data collections)
	NonCyclic_Tasks.mp4: Video explaining the non-cyclic tasks (not recorded during actual data collections)

LabSetting.zip
	LabSetting.png: Image picturing the lab collection space and Vicon camera configuration

marker_abbreviations.txt: text file describing the marker placement for interpreting the marker trajectory files
	

/////  SUBJECT MASS  /////
AB01: 78.9 kg
AB02: 82.2 kg
AB03: 113.5 kg
AB05: 71.5 kg
AB06: 79.1 kg
AB07: 62.3 kg
AB08: 87.6 kg
AB09: 84.1 kg
AB10: 67.5 kg
AB11: 65.1 kg
AB12: 64.0 kg
AB13: 67.6 kg
*also included as a .csv in the RawData Folder

/////  GENERAL NOTES  /////
start_stop trials are only included for AB10, AB11, AB12, and AB13.
Invalid forces and moments for treadmill trials are left but are all nans
Treadmill trials are missing one force plate (right leg on treadmill trials except for declines) due to broken equipment 

/////  AB01 SPECIFIC NOTES  /////
No jump_x_90-1 trial

/////  AB02 SPECIFIC NOTES  /////
Deleted step_ups b/c subject placed both feet on the chair with each step up
stairs_1 includes one extra ascent/descent pass over the staircase (stairs_1_11_up, stairs_1_12_down)

/////  AB03 SPECIFIC NOTES  /////
ball toss to the left was collected in two separate segments. 3 tosses are in ball_toss_1_left. 2 tosses are in ball_toss_1_left-2.
No jump_x_90-1 trial

/////  AB05 SPECIFIC NOTES  /////
No weighted_walk trials
No valid running trials
No jump_x_90-1 trial

/////  AB06 SPECIFIC NOTES  /////
No jump_x_90-2 trial

/////  AB07 SPECIFIC NOTES  /////
All treadmill trials measured zero A/P ground reaction force (this is separate from the larger treadmill issue).
The trials effected (and removed from dataset) are:
	dynamic_walk_1_butt-kicks
	dynamic_walk_1_heel-walk
	dynamic_walk_1_high-knees
	dynamic_walk_1_toe-walk
	incline_walk_1_down5
	incline_walk_1_up5
	incline_walk_2_down10
	incline_walk_2_up10
	normal_walk_1_0-6
	normal_walk_1_1-2
	normal_walk_1_1-8
	normal_walk_1_2-0
	normal_walk_1_2-5
	normal_walk_1_shuffle
	normal_walk_1_skip
	obstacle_walk_1
	walk_backward_1_0-6
	walk_backward_1_0-8
	walk_backward_1_1-0
	weighted_walk_1_25lbs

/////  AB10 SPECIFIC NOTES  /////
No valid running trials

/////  AB12 SPECIFIC NOTES  /////
stairs_1 includes one extra ascent/descent pass over the staircase (stairs_1_11_up, stairs_1_12_down)

///// TASK DESCRIPTIONS  /////
Below are the descriptions of each task.
Format:
<base task name>: Overall description.
	<task 1 descriptor>: task description.
	<task 2 descriptor>: task description.
	...

ball_toss: Tossing 15 lbs medicine ball
	_center: tossing/catching medicine ball forwards
	_left: tossing/catching medicine ball to the left
	_right: tossing/catching medicine ball to the right

curb_down: Stepping down from a street curb

curb_up: Stepping up onto a street curb

cutting: Jog/Run into sharp turn
	_left-fast: turn to left during fast running
	_left-slow: turn to left during jogging
	_right-fast: turn to right during fast running
	_right-slow: turn to right during jogging

dynamic_walk: Treadmill calisthenics
	_butt-kicks: butt kick jogging at 0.8 m/s
	_heel-walk: walking on heels at 0.4 m/s
	_high-knees: high knee jogging at 0.8 m/s
	_toe-walk: walking on toes at 0.4 m/s

incline_walk: Treadmill incline/decline walking at 1.2 m/s
	_down5: decline of 5 degrees
	_up5: incline of 5 degrees
	_down10: decline of 10 degrees
	_up10: incline of 10 degrees

jump: Jumping trials
	_fb: forward and backward jumping
	_hop: hopping in place
	_vertical: jumping in place for max height
	_90-1: set 1 of 90 degree jumping (clockwise->counterclockwise->clockwise->counterclockwise->etc.)
	_90-2: set 2 of 90 degree jumping (clockwise->counterclockwise->clockwise->counterclockwise->etc.)
	_180: jump and turn 180 degrees (clockwise->counterclockwise->clockwise->counterclockwise->etc.)
	_lateral: jump side-to-side

lift_weight: lifting weighted/unweighted bag
	0lbs-l-c: lift 0lbs bag in front (center) of subject with left hand
	0lbs-l-l: lift 0lbs bag to left of subject with left hand
	0lbs-r-c: lift 0lbs bag in front (center) of subject with right hand
	0lbs-r-r: lift 0lbs bag to right of subject with right hand
	25lbs-l-c: lift 25lbs bag in front (center) of subject with left hand
	25lbs-l-l: lift 25lbs bag to left of subject with left hand
	25lbs-r-c: lift 25lbs bag in front (center) of subject with right hand
	25lbs-r-r: lift 25lbs bag to right of subject with right hand
	
lunges: lunging forward and backward with left and right legs
	_set1: left/right forward/backward lunging
	_set2: left/right forward/backward lunging
	_set3: left/right forward/backward lunging
	_set4: left/right forward/backward lunging
	_set5: left/right forward/backward lunging
	_left: lunge laterally to left
	_right: lunge laterally to right

meander: freeform, slow walking overground

normal_walk: ambulating at different speeds on a level treadmill
	_0-6: walking at 0.6 m/s
	_1-2: walking at 1.2 m/s
	_1-8: walking at 1.8 m/s
	_2-0: walking at 2.0 m/s
	_2-5: walking at 2.5 m/s
	_shuffle: walking at 0.4 m/s
	_skip: skipping at 1.2 m/s

obstacle_walk: walking while foam block is placed on treadmill to disturb normal walking at 1.0 m/s

poses: standing in static postures (normal standing, feet double shoulder width apart, left foot forward, right foot forward, squat, balance on left foot, balance on right foot, stand on toes, hips to left, hips to right, hips forward, hips backward, point toes in, point toes out, normal stand with 25 lbs weight held to left, normal stand with 25 lbs weight held to right, wide stance standing, wide stance standing w/ left foot forward, wide stance standing w/ right foot forward, normal standing but squeeze legs together)

push: experimenter pushes and pulls subject by torso/shoulders

side_shuffle: lateral shuffling to left and right

sit_to_stand: sit down and stand up from chair
	_short-arm: sit/stand using short chair w/ arm rests
	_short-noarm: sit/stand using short chair w/o arm rests
	_tall-noarm: sit/stand using tall chair w/o arm rests

squats: squatting w/ and w/o added weight
	_0lbs: bodyweight squats
	_25lbs: squats with 25 lbs weight

stairs: walking up and down stairs
	_1_up: stair ascent
	_2_down: stair descent
	_3_up: stair ascent
	_4_down: stair descent
	_5_up: stair ascent
	_6_down: stair descent
	_7_up: stair ascent
	_8_down: stair descent
	_9_up: stair ascent
	_10_down: stair descent

start_stop: starting and stopping walking on overground force plates

step_ups: stepping up onto tall object
	_left: step up using left leg
	_right: step up using right leg

tire_run: jogging on toes overground with high knees (as if running through tires)

tug_of_war: pushing and pulling broomstick between subject and experimenter

turn_and_step: from standing, turn to left or right and start walking
	_left-turn: turn to left
	_right-turn: turn to right

twister: experimenter calls out feet locations for subject to place feet

walk_backward: walking backward on treadmill
	_0-6: at 0.6 m/s
	_0-8: at 0.8 m/s
	_1-0: at 1.0 m/s

weighted_walk: walking on treadmill at 1.0 m/s with weight
	_25lbs: carrying 25 lbs weight

///// SEGMENTATION DETAILS  /////
backward walking, butt kicks, decline, heel walk, high kness, incline, running, shuffling, stairs, toe walking, walking, and weighted walking were segmented by heel strike based on a 20N force threshold on the force plates
skipping was also segmented by heel strikes, but due to the double heel strike per stride, the quick heel strike in the middle of the stride was not used to segment. This gives clean and comparable strides.
hopping was segmented by a similar 20 N threshold for foot contact
lifting tasks were segmented automatically by trunk velocity passing a 0.5 m/s magnitude threshold. This was then debounced and manually verified for consistency.
cutting and tire run were segmented by pass across the force plates, thus from the toe off of the step before coming into contact with the force plates to the heel strike of the first step off the force plates. This was performed by automatically through marker velocity checks and then manually adjusted
the rest of the segmentable trial were segmented by a 0.5 m/s magnitude threshold on pelvis velocity. This was then debounced and manually verified for consistency
some trials were not segmented: meander, poses, push, obstacle_walk, start_stop ,tug_of_war, twister