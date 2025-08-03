# UMich 2021 Dataset Structure

This document describes the structure of the MATLAB `.mat` files used in the UMich 2021 dataset, focusing on the organization of data and participant details.

## File Overview

The dataset consists of two primary .mat files:
- `Streaming.mat`: Contains time-series data
- `Normalized.mat`: Contains phase-normalized data

Both files have identical top-level structure with subject data.

## Data Structure

### Top-level Structure

Both `.mat` files contain a single top-level struct with subject IDs as field names:

```
Streaming (or Normalized)
├── AB01
├── AB02
├── AB03
├── ...
└── AB10
```

Each subject entry contains the following fields:

```
Subject (e.g., AB01)
├── ParticipantDetails
├── Tread (treadmill trials)
├── Run
├── Wtr (walk-to-run transition)
├── Sts (sit-to-stand)
└── Stair
```

### ParticipantDetails Structure

The `ParticipantDetails` field is a cell array with dimensions [11 × 3] where:
- Column 1: Feature name
- Column 2: Value
- Column 3: Units

Example structure:

```
ParticipantDetails = {
    'ParticipantName'    'AB01'     ''
    'Sex'                 2         ''        % 1=female, 2=male
    'Age'                 24        'years'
    'Bodymass'            87        'kg'
    'Height'              1900      'mm'
    'LeftLegLength'       951       'mm'
    'LeftKneeWidth'       130       'mm'
    'LeftAnkleWidth'      82        'mm'
    'RightLegLength'      958       'mm'
    'RightKneeWidth'      130       'mm'
    'RightAnkleWidth'     86        'mm'
};
```

### Treadmill Data Structure

The `Tread` field contains trials at different inclines:

```
Tread
├── d10  (decline 10°)
├── d5   (decline 5°)
├── i0   (level)
├── i5   (incline 5°)
└── i10  (incline 10°)
```

### Run Data Structure

The `Run` field contains trials at different speeds:

```
Run
├── s1x8  (1.8 m/s)
├── s2x0  (2.0 m/s)
├── s2x2  (2.2 m/s)
└── s2x4  (2.4 m/s)
```

### Trial Data Structure

Each trial (e.g., `Tread.i0`) contains the following fields in the `Streaming.mat` file:

```
Trial
├── jointAngles
│   ├── RHipAngles (R = Right)
│   ├── LHipAngles (L = Left)
│   ├── RKneeAngles
│   ├── LKneeAngles
│   ├── RAnkleAngles
│   ├── LAnkleAngles
│   ├── RPelvisAngles
│   ├── LPelvisAngles
│   ├── RFootProgressAngles
│   └── LFootProgressAngles
├── jointMoments
│   ├── RHipMoment
│   ├── LHipMoment
│   ├── RKneeMoment
│   ├── LKneeMoment
│   ├── RAnkleMoment
│   └── LAnkleMoment
└── forceplates
    ├── RForce
    ├── LForce
    ├── RCoP
    └── LCoP
```

In the `Normalized.mat` file, the trial data is organized with an additional dimension for strides. 
However, the structure is more nested than previously described:

1. A top-level task condition (e.g., `Run.s1x8` or `Walk.s0x8`) is a struct.
2. This struct then contains further sub-field structs. These sub-fields represent specific secondary conditions, such as incline (e.g., `in0`, `in5`, `d5`) or acceleration/deceleration states (e.g., `a0x2`, `d0x2`).
3. It is these deepest sub-field structs (SecondaryCondition) that actually contain the `jointAngles` and `forceplates` fields.

Example Path: `Normalized.AB01.Walk.s0x8.in5.jointAngles.HipAngles`

```
Subject.Task.PrimaryCondition (e.g., Walk.s0x8)
└── SecondaryCondition (e.g., in5, a0x2, etc.)
    ├── jointAngles  % NOTE: This field and its subfields (e.g., HipAngles) may be missing.
    │   ├── HipAngles[points, planes, strides]
    │   ├── KneeAngles[points, planes, strides]
    │   ├── AnkleAngles[points, planes, strides]
    │   ├── PelvisAngles[points, planes, strides]
    │   └── FootProgressAngles[points, planes, strides]
    ├── jointMoments % NOTE: This field and its subfields may be missing.
    │   ├── HipMoment[points, planes, strides]
    │   ├── KneeMoment[points, planes, strides]
    │   └── AnkleMoment[points, planes, strides]
    └── forceplates  % NOTE: This field and its subfields may be missing.
        ├── Force[points, dimensions, strides]
        └── CoP[points, dimensions, strides]
```

Additionally, the `Tread` field (described under 'Data Structure' -> 'Subject') may be missing for some subjects in `Normalized.mat`.

## Data Conventions

This section describes the conventions for data as present in the raw `.mat` files. The conversion scripts (`convert_umich_time_to_parquet.m` and `convert_umich_phase_to_parquet.m`) transform this data to align with OpenSim conventions (XYZ: Anterior+, Up+, Right+) as specified in the main project `units_and_conventions.md` document.

### Coordinate System for Joint Angles & Moments (Indices in MAT files)
- Index 1 (e.g., `HipAngles(:,1)`): Sagittal plane motion (Flexion/Extension)
- Index 2 (e.g., `HipAngles(:,2)`): Frontal plane motion (Adduction/Abduction, Varus/Valgus, Inversion/Eversion)
- Index 3 (e.g., `HipAngles(:,3)`): Transverse plane motion (Internal/External Rotation)

Assumed Positive Directions in Raw MAT files (consistent with OpenSim for direct use or after script's negation):
- Sagittal plane angles/moments: Positive for Flexion (e.g., hip flexion, ankle dorsiflexion). Knee flexion angle raw data is an exception, assumed positive for extension, and is negated by conversion scripts.
- Frontal plane angles/moments: Positive for Adduction (hip), Valgus (knee), Inversion (ankle).
- Transverse plane angles/moments: Positive for External Rotation.

### GRF & CoP Dimensions (Indices in MAT files `forceplates.Force` and `forceplates.CoP`)
- Index 1: Anterior-Posterior (AP) direction. Assumed positive for Anterior.
- Index 2: Vertical direction. Assumed positive for Downward. Conversion scripts negate this for Upward positive (OpenSim Y+).
- Index 3: Medial-Lateral (ML) direction. Assumed positive for Leftward. Conversion scripts negate this for Rightward positive (OpenSim Z+).

The conversion scripts map these raw components to the standard's column names (`ap_grf_r_N`, `vertical_grf_r_N`, `ml_grf_r_N`) and apply necessary sign flips to ensure the final Parquet files adhere to an Anterior+, Up+, Right+ (OpenSim XYZ) convention.

## Participant Statistics

Statistics for the 10 subjects in the dataset:

| Feature | Range | Mean | Units |
|---------|-------|------|-------|
| Gender | 1-2 | 1.5 | (1=female, 2=male) |
| Age | 20-60 | 30.4 | years |
| Body Mass | 53.7-87.0 | 74.63 | kg |
| Height | 1617-1900 | 1727.8 | mm |
| Left Leg Length | 766-991 | 911.1 | mm |
| Left Knee Width | 95-130 | 110.8 | mm |
| Left Ankle Width | 61-82 | 69.6 | mm |
| Right Leg Length | 782-990 | 910.3 | mm |
| Right Knee Width | 96-130 | 110.9 | mm |
| Right Ankle Width | 61-86 | 70.5 | mm | 