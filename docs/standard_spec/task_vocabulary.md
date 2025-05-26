# Task Vocabulary

This document defines the standardized task names and their descriptions for the locomotion data standardization project.

## Standard Task Names

### Walking and Running Tasks
- **level_walking**: Level ground walking at varying velocities
- **incline_walking**: Walking at an upward sloped angle
- **decline_walking**: Walking at a downward sloped angle
- **walk_backward**: Walking backward on treadmill
- **weighted_walk**: Walking on treadmill at 1.0 m/s with weight
  - **weighted_walk_25lbs**: Carrying 25 lbs weight
- **run**: Running at level ground
- **meander**: Freeform, slow walking overground
- **obstacle_walk**: Walking while foam block is placed on treadmill to disturb normal walking at 1.0 m/s

### Stair and Step Tasks
- **up_stairs**: Going up stairs
- **down_stairs**: Going down stairs
- **stairs**: Generic stair walking (up and down)
- **step_ups**: Stepping up onto tall object
- **curb_up**: Stepping up onto a street curb
- **curb_down**: Stepping down from a street curb

### Dynamic Movement Tasks
- **jump**: Jumping trials
- **cutting**: Jog/run into sharp turn
- **side_shuffle**: Lateral shuffling to left and right
- **tire_run**: Jogging on toes overground with high knees (as if running through tires)
- **turn_and_step**: From standing, turn to left or right and start walking

### Sit-Stand Transitions
- **sit_to_stand**: Rising from seated to standing position
- **stand_to_sit**: Lowering from standing to seated position

### Exercise and Strength Tasks
- **squats**: Squatting with and without added weight
- **lunges**: Lunging forward and backward with left and right legs
- **lift_weight**: Lifting weighted/unweighted bag

### Interactive Tasks
- **ball_toss_l**: Tossing the ball at left
- **ball_toss_m**: Tossing the ball at middle
- **ball_toss_r**: Tossing the ball at right
- **push**: Experimenter pushes and pulls subject by torso/shoulders
- **tug_of_war**: Pushing and pulling broomstick between subject and experimenter
- **twister**: Experimenter calls out feet locations for subject to place feet

### Static and Control Tasks
- **poses**: Standing in static postures
- **start_stop**: Starting and stopping walking on overground force plates
- **transitions**: Transitions between different tasks

## Usage Notes

1. Task names should be used exactly as specified (case-sensitive)
2. When a task has variations (e.g., weighted_walk_25lbs), use the most specific name available
3. For tasks performed at different speeds or conditions, include relevant parameters in the metadata_task.parquet file
4. New task names should be added to this vocabulary before use in datasets