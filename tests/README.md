# Tests Directory

Tutorial validation tests for the LocoHub project.

## Structure

```
tests/
├── mock_data/
│   └── mock_dataset_phase.parquet    # Small test dataset (1.1 MB)
├── generate_mock_dataset.py          # Creates the mock dataset
│
├── Python Tests/
├── test_tutorial_01_loading_data.py  # Tutorial 1 tests
├── test_tutorial_02_data_filtering.py # Tutorial 2 tests
├── test_tutorial_03_visualization.py # Tutorial 3 tests
├── test_tutorial_04_cycle_analysis.py # Tutorial 4 tests
├── test_tutorial_05_group_analysis.py # Tutorial 5 tests
├── test_tutorial_06_publication_outputs.py # Tutorial 6 tests
├── test_all_tutorials.py            # Master test runner
├── test_utils.py                     # Common test utilities
│
├── MATLAB Tests/
├── test_matlab_tutorial_01_loading_data.m  # MATLAB Tutorial 1 tests
├── test_matlab_tutorial_02_data_filtering.m # MATLAB Tutorial 2 tests
└── test_all_matlab_tutorials.m      # MATLAB master test runner
```

## Running Tests

### Python Tests

#### Run All Python Tutorial Tests
```bash
python tests/test_all_tutorials.py
```

#### Run Individual Python Tutorial Test
```bash
python tests/test_tutorial_01_loading_data.py
```

### MATLAB Tests

#### Run All MATLAB Tutorial Tests
```matlab
cd tests
test_all_matlab_tutorials
```

#### Run Individual MATLAB Tutorial Test
```matlab
cd tests
test_matlab_tutorial_01_loading_data
```

### Regenerate Mock Dataset
```bash
python tests/generate_mock_dataset.py
```

## Mock Dataset

**Note**: The mock dataset file (`mock_dataset_phase.parquet`) is not committed to git due to `.gitignore` rules.
You must generate it first by running:

```bash
python tests/generate_mock_dataset.py
```

The mock dataset contains:
- 3 subjects (SUB01, SUB02, SUB03)
- 3 tasks (level_walking, incline_walking, decline_walking)
- 5 cycles per subject/task combination
- 150 points per cycle (phase-indexed)
- 18 biomechanical variables

Data is generated using parameterized sine waves with noise added to parameters (not output) for smooth, realistic variation between cycles.

## Test Coverage

Each tutorial test validates:
- All code snippets from the tutorial documentation
- Both library and raw pandas approaches
- Expected outputs and data structures
- Error handling and edge cases

## Adding New Tests

1. Create `test_tutorial_XX_topic.py`
2. Import mock dataset: `MOCK_DATASET = Path(__file__).parent / 'mock_data' / 'mock_dataset_phase.parquet'`
3. Follow existing test patterns
4. Add to test runner if needed

## Requirements

- Python 3.7+
- pandas
- numpy
- matplotlib (optional, for visualization tests)
- scipy (optional, for statistical tests)