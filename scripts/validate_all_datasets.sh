#!/bin/bash
# Validation script for Phase 0
# This script runs validation on all available datasets

WORKSPACE_ROOT="/mnt/c/Users/jmontp/Documents/workspace/locomotion-data-standardization"
cd "$WORKSPACE_ROOT"

echo "=== Phase 0 Validation Script ==="
echo "Starting at: $(date)"
echo

# Create output directory for reports
REPORT_DIR="$WORKSPACE_ROOT/validation_reports/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo "Report directory: $REPORT_DIR"
echo

# Function to check if Python packages are available
check_python_deps() {
    python3 -c "
import sys
try:
    import pandas
    import numpy
    import plotly
    print('✓ All required packages available')
    sys.exit(0)
except ImportError as e:
    print(f'✗ Missing package: {e}')
    print('Please install: pandas, numpy, plotly, pyarrow, kaleido')
    sys.exit(1)
"
    return $?
}

# Function to validate a dataset
validate_dataset() {
    local dataset_name=$1
    local parquet_file=$2
    local metadata_subject=$3
    local metadata_task=$4
    
    echo "----------------------------------------"
    echo "Validating: $dataset_name"
    echo "File: $parquet_file"
    
    if [ ! -f "$parquet_file" ]; then
        echo "✗ File not found: $parquet_file"
        return 1
    fi
    
    # Run validation script
    echo "Running validation_blueprint_enhanced.py..."
    python3 "$WORKSPACE_ROOT/source/tests/validation_blueprint_enhanced.py" \
        --input "$parquet_file" \
        --mode comprehensive \
        --output "$REPORT_DIR/${dataset_name}_validation.csv" \
        2>&1 | tee "$REPORT_DIR/${dataset_name}_validation.log"
    
    # Run mosaic plotter with diagnostic mode
    echo "Running mosaic plotter diagnostic..."
    python3 "$WORKSPACE_ROOT/source/visualization/mozaic_plot.py" \
        --input_parquet "$parquet_file" \
        --diagnostic \
        --export-png \
        ${metadata_subject:+--metadata_subject "$metadata_subject"} \
        ${metadata_task:+--metadata_task "$metadata_task"} \
        2>&1 | tee "$REPORT_DIR/${dataset_name}_mosaic.log"
    
    # Generate validation GIFs (sample subjects/tasks)
    echo "Generating validation GIFs..."
    python3 "$WORKSPACE_ROOT/source/visualization/walking_animator.py" \
        -f "$parquet_file" \
        --save-gif \
        2>&1 | head -100 >> "$REPORT_DIR/${dataset_name}_animator.log"
    
    echo "✓ Completed $dataset_name validation"
    echo
}

# Check dependencies
echo "Checking Python dependencies..."
if ! check_python_deps; then
    echo "
=== Manual Installation Required ===
Since we cannot install packages automatically, please run these commands manually:

1. Install pip (if not available):
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python3 get-pip.py --user --break-system-packages

2. Install required packages:
   python3 -m pip install --user pandas numpy plotly pyarrow kaleido matplotlib --break-system-packages

3. Re-run this script after installation
"
    exit 1
fi

# Find and validate datasets
echo "=== Starting Dataset Validation ==="

# Gtech 2023 datasets
if [ -f "$WORKSPACE_ROOT/source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet" ]; then
    validate_dataset "Gtech_2023_phase" \
        "$WORKSPACE_ROOT/source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet"
fi

if [ -f "$WORKSPACE_ROOT/source/conversion_scripts/Gtech_2023/gtech_2023_time.parquet" ]; then
    validate_dataset "Gtech_2023_time" \
        "$WORKSPACE_ROOT/source/conversion_scripts/Gtech_2023/gtech_2023_time.parquet"
fi

# UMich 2021 datasets
if [ -f "$WORKSPACE_ROOT/source/conversion_scripts/Umich_2021/umich_2021_phase.parquet" ]; then
    validate_dataset "UMich_2021_phase" \
        "$WORKSPACE_ROOT/source/conversion_scripts/Umich_2021/umich_2021_phase.parquet" \
        "$WORKSPACE_ROOT/source/conversion_scripts/Umich_2021/metadata_subject.parquet" \
        "$WORKSPACE_ROOT/source/conversion_scripts/Umich_2021/metadata_task_phase.parquet"
fi

# Generate summary report
echo "=== Generating Summary Report ==="
cat > "$REPORT_DIR/VALIDATION_SUMMARY.md" << EOF
# Phase 0 Validation Summary
Generated: $(date)

## Datasets Validated
$(ls -la "$REPORT_DIR"/*.log 2>/dev/null | wc -l) datasets processed

## Key Findings
### Data Compliance
- Check individual validation logs for 150-point compliance
- Review mosaic diagnostic output for specific issues

### Validation Results
- See CSV files for detailed error codes
- Check PNG files in plots/png/ for visual validation

## Next Steps
1. Fix any data conversion issues identified
2. Re-run validation on problematic datasets
3. Proceed to Phase 1 when all datasets pass

## Files Generated
$(ls -la "$REPORT_DIR"/*)
EOF

echo
echo "=== Validation Complete ==="
echo "Summary report: $REPORT_DIR/VALIDATION_SUMMARY.md"
echo "Completed at: $(date)"