# CLAUDE.md - AddBiomechanics Conversion

Transform OpenSim/AddBiomechanics B3D format to standardized Parquet.

## Key Scripts

**Main Conversion**:
- `convert_addbiomechanics_to_parquet.py` - B3D → time-indexed Parquet
- `add_phase_info.py` - Time → phase-indexed (150 points/cycle)
- `add_task_info.py` - Add standardized task metadata

**Core Processing**:
- `b3d_to_parquet.py` - Low-level B3D format parser
- `extract_biomechanics_dataset.sh` - Data extraction utility

## Processing Pipeline

```
B3D Files → convert_addbiomechanics_to_parquet.py → Time-indexed Parquet
                                                         ↓
Phase-indexed Parquet ← add_phase_info.py ← add_task_info.py
```

## Dependencies

**Heavy Requirements** (>2GB total):
- `nimblephysics` - Physics simulation for B3D parsing
- `torch` - Deep learning framework dependency

**Installation**:
```bash
cd source/conversion_scripts/AddBiomechanics
pip install -r requirements.txt
python -c "import nimblephysics; print('Success')"
```

## Key Features

**Data Processing**:
- Full 3D biomechanics with joint angles, moments, GRFs
- Coordinate transformations to OpenSim standard
- Standardized variable naming implementation
- Phase normalization with gait event detection

**Quality Assurance**:
- B3D format validation
- Memory-efficient processing for large files
- Error handling for malformed data
- Output validation against standard specification

## Performance Considerations

**Memory**: Conversion process is memory-intensive (>1GB files)
**Processing Time**: Significant for large datasets
**Storage**: Intermediate files require substantial disk space

## Known Limitations

- Right-leg data may be incomplete for some subjects
- Complex task name mapping from original to standard
- Multiple coordinate frame conversions required
- Large output file sizes (>1GB possible)

## Testing

```bash
# Test core components
python b3d_to_parquet.py --input sample.b3d --output test.parquet
python convert_addbiomechanics_to_parquet.py --input_dir ./b3d_files/ --output_dir ./converted/
python ../../tests/validation_blueprint_enhanced.py --input converted/dataset_phase.parquet
```

---

*Most complex conversion requiring careful dependency and memory management.*