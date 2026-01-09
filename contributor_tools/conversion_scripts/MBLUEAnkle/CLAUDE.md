# MBLUE Ankle Exoskeleton Conversion

## Data Location

Source data is in the MBLUEAnkleOpenSimProcessing repository:
```
../MBLUEAnkleOpenSimProcessing/Subject_Data/
```

The data consists of `*_NormalizedStrides.mat` files containing phase-normalized (101 points) gait data.

## Data Structure

Each .mat file contains:
- `dataOut['bare']` - No exoskeleton condition
- `dataOut['exo']` - With ankle exoskeleton condition

Under each condition:
- Level walking: `level_0x75`, `level_1x0`, `level_1x25` (speeds 0.75, 1.0, 1.25 m/s)
- Incline walking: `incline_5deg`, `incline_10deg`
- Decline walking: `decline_5deg`, `decline_10deg`
- Sit-to-stand: `STS['sit_stand']`, `STS['stand_sit']`
- Crouch/squat: `crouch`
- Stairs: `stairs['ascent']`, `stairs['descent']` (nested by step: s2, s3, s4)

## Subjects

10 able-bodied subjects (AB01-AB11, excluding AB07 who withdrew):
- Mix of male/female, ages 21-57
- Body mass range: 54.3 - 83.3 kg

## Running the Conversion

```bash
python3 contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py \
    --input ../MBLUEAnkleOpenSimProcessing/Subject_Data
```

Options:
- `--condition bare|exo|all` - Filter by exoskeleton condition (default: all)
- `--subjects AB01 AB02` - Process specific subjects only
- `--test` - Process only first subject for testing
- `--vicon-path PATH` - Path to raw Vicon data for COP extraction (optional)

Output goes to `converted_datasets/mblue_ankle_phase.parquet` by default.

**Tip**: For Dropbox integration, copy the output to `$LOCOHUB_DROPBOX_FOLDER` for automatic syncing and share link generation. See the [Dropbox Integration](../../CLAUDE.md#dropbox-integration) section in the main contributor tools docs.

### COP Extraction

To include Center of Pressure (COP) data, provide the path to raw Vicon data:

```bash
python3 contributor_tools/conversion_scripts/MBLUEAnkle/convert_mblue_ankle_to_parquet.py \
    --input ../MBLUEAnkleOpenSimProcessing/Subject_Data \
    --vicon-path /mnt/s/MBLUE_Ankle_Data/Able-Bodied
```

COP data is extracted from `.mot` files in the Vicon data directory. The expected structure:
```
Able-Bodied/
├── AB01/
│   └── MMDDYYYY/
│       ├── bare_level.mot
│       ├── bare_5deg_incline.mot
│       └── ...
├── AB02/
└── ...
```

## Data Notes

- Source angles are in degrees, converted to radians
- Knee angle is extension-positive in source, negated to flexion-positive standard
- Moments are in Nm, normalized by body mass to Nm/kg
- GRF is vertical only (Newtons), normalized by body weight to BW
- Phase normalized from 101 to 150 points to match standard format
- Contralateral data is 50% phase-shifted from ipsilateral (standard gait convention)
  - Note: Actual phase offset varies 49.6-51.3% but 50% approximation is used because
    time-based synchronization has complications with boundary conditions

### COP Data (when --vicon-path provided)

- `cop_anterior_{ipsi,contra}_m` - COP in walking direction (heel-to-toe) (m)
  - Derived from negated OpenSim pz coordinate
- `cop_lateral_{ipsi,contra}_m` - COP perpendicular to walking direction (medial-lateral) (m)
  - Derived from OpenSim px coordinate
- COP is zeroed to heel strike position (foot-relative coordinates)
- COP is masked (NaN) during swing phase when vertical GRF < 20N threshold
- Force plate assignments vary by task (e.g., decline walking swaps left/right plates)
