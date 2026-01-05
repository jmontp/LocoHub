# GaTech 2024 TaskAgnostic Conversion

## Data Location

Source data is stored on the S: drive:
```
S:\locomotion_data\GaTech_2024_TaskAgnostic\Parsed
```

In WSL, this translates to:
```
/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Parsed
```

## Running the Conversion

```bash
python3 contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py \
    --input /mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Parsed
```

Output goes to `converted_datasets/gtech_2024_phase.parquet` by default.
