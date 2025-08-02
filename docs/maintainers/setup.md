# Development Environment Setup

This guide walks you through setting up a complete development environment for maintaining the locomotion data standardization system.

## Prerequisites

### Required Software
- **Python 3.8+** - Core language for validation and analysis
- **Git** - Version control
- **MATLAB R2021b+** (optional) - For MATLAB converters and libraries
- **Docker** (optional) - For containerized development

### Recommended Tools
- **VS Code** or **PyCharm** - IDE with Python support
- **GitHub CLI** - For easier PR management
- **Make** - For automation (on Windows: use WSL or Git Bash)

## Step 1: Clone and Fork

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/locomotion-data-standardization
cd locomotion-data-standardization

# Add upstream remote
git remote add upstream https://github.com/original-org/locomotion-data-standardization
```

## Step 2: Python Environment

### Option A: Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools
```

### Option B: Conda Environment
```bash
# Create conda environment
conda create -n locomotion python=3.9
conda activate locomotion

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Verify Installation

```bash
# Run basic tests
pytest tests/test_locomotion_data_library.py -v

# Check imports work
python -c "from lib.core.locomotion_analysis import LocomotionData; print('✓ Core library works')"
python -c "from lib.validation.dataset_validator_phase import PhaseValidator; print('✓ Validation works')"
```

## Step 4: Set Up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run on all files to verify
pre-commit run --all-files
```

## Step 5: Documentation Setup

```bash
# Install documentation tools
pip install mkdocs mkdocs-material mkdocs-mermaid2

# Test documentation build
mkdocs serve
# Visit http://localhost:8000
```

## Step 6: Download Sample Data

```bash
# Create data directory
mkdir -p converted_datasets

# Download sample datasets (if available)
# wget https://example.com/sample_data/umich_2021_phase.parquet -P converted_datasets/
# Or use the Dropbox link from the documentation
```

## Step 7: MATLAB Setup (Optional)

If you're working with MATLAB converters:

```matlab
% In MATLAB, add paths
addpath('source/lib/matlab')
addpath('contributor_scripts/Gtech_2023')
addpath('contributor_scripts/Umich_2021')

% Test MATLAB functionality
data = LocomotionData('path/to/data.parquet');
disp('MATLAB setup complete!')
```

## IDE Configuration

### VS Code
1. Install Python extension
2. Select interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → Choose venv
3. Configure test discovery in `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black"
}
```

### PyCharm
1. Set project interpreter to venv
2. Mark directories:
   - `lib` as Sources Root
   - `tests` as Test Sources Root
3. Configure pytest as test runner

## Troubleshooting

### Common Issues

**Import errors**
```bash
# Ensure you're in the project root
pwd  # Should show .../locomotion-data-standardization

# Add to PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Missing dependencies**
```bash
# Update pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**MATLAB parquet errors**
```matlab
% Install parquet support
% Follow MATLAB's documentation for parquetread/parquetwrite
```

## Docker Development (Alternative)

For a consistent environment:

```bash
# Build development container
docker build -t locomotion-dev -f containers/python-analysis.Dockerfile .

# Run with mounted code
docker run -it -v $(pwd):/workspace locomotion-dev bash

# Inside container
cd /workspace
pytest tests/
```

## Next Steps

Now that your environment is set up:
1. Review the [architecture](architecture.md)
2. Try some [common tasks](tasks.md)
3. Run the [test suite](testing.md)
4. Make your first contribution!

## Getting Help

- Check existing issues on GitHub
- Review test files for usage examples
- Ask questions in discussions/issues