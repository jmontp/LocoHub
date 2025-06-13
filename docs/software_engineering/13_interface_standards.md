# Interface Standards - Consistent Patterns for CLI Tools and APIs

## Overview

This document defines standardized patterns for all CLI tools and APIs in the locomotion data standardization project. Following these standards ensures consistency, predictability, and maintainability across all user-facing components.

---

## CLI Argument Patterns

### **Standard Argument Structure**

All CLI tools follow this consistent pattern:

```bash
python {tool_name}.py [REQUIRED_ARGS] [OPTIONS]

# Examples:
python convert_dataset.py INPUT_PATH OUTPUT_DIR [OPTIONS]
python validate_phase_data.py DATASET_PATH [OPTIONS]
python create_benchmarks.py DATASET_PATHS OUTPUT_DIR [OPTIONS]
```

### **Required Arguments (Positional)**

#### **Input Specification**
- **Single File**: `DATASET_PATH` (path to parquet file)
- **Multiple Files**: `DATASET_PATHS` (space-separated paths)
- **Directory Input**: `INPUT_PATH` (path to directory containing data)

#### **Output Specification**  
- **Output Directory**: `OUTPUT_DIR` (directory for all outputs)
- **Output File**: `OUTPUT_PATH` (specific file path for single outputs)

### **Standard Options (Flags)**

#### **Common Options (All Tools)**
```bash
--verbose, -v          Enable verbose logging output
--quiet, -q            Minimal output for automation scripts
--config FILE          Configuration file override
--output-format TYPE   Report format (json, html, text, all)
--help, -h             Show usage information and exit
--version              Show version information and exit
```

#### **Tool-Specific Options**
```bash
# Conversion Tools
--format TYPE          Force specific input format detection
--mapping FILE         Custom variable mapping configuration
--overwrite           Overwrite existing output files

# Validation Tools  
--mode TYPE           Validation mode (kinematic, kinetic, all)
--specs-file FILE     Custom validation specifications
--plots               Generate validation plots
--fail-fast           Stop on first critical failure

# Benchmark Tools
--split-strategy TYPE  Data splitting method
--train-ratio FLOAT   Training set proportion
--export-formats LIST Output formats for ML frameworks
```

---

## Exit Codes

### **Standard Exit Codes**
```python
EXIT_SUCCESS = 0           # Operation completed successfully
EXIT_GENERAL_ERROR = 1     # General error (catch-all)
EXIT_INVALID_ARGS = 2      # Invalid command line arguments
EXIT_DATA_ERROR = 3        # Data quality or format error
EXIT_VALIDATION_ERROR = 4  # Validation failure
EXIT_CONFIG_ERROR = 5      # Configuration file error
EXIT_PERMISSION_ERROR = 6  # File permission or access error
EXIT_RESOURCE_ERROR = 7    # Insufficient resources (memory, disk)
```

### **Usage in Implementation**
```python
import sys

def main():
    try:
        # Tool implementation
        return EXIT_SUCCESS
    except InvalidArgumentError:
        logger.error("Invalid arguments provided")
        return EXIT_INVALID_ARGS
    except DataQualityError:
        logger.error("Data quality issues detected")
        return EXIT_DATA_ERROR
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return EXIT_GENERAL_ERROR

if __name__ == "__main__":
    sys.exit(main())
```

---

## Error Handling Patterns

### **Exception Hierarchy**
```python
class LocomotionToolError(Exception):
    """Base exception for all locomotion tools"""
    pass

class DataFormatError(LocomotionToolError):
    """Issues with data format or structure"""
    pass

class ValidationError(LocomotionToolError):
    """Data validation failures"""
    pass

class QualityError(LocomotionToolError):
    """Data quality issues"""
    pass

class ConfigurationError(LocomotionToolError):
    """Configuration file or parameter issues"""
    pass
```

### **Error Message Format**
```python
# Error message structure
ERROR: {error_type}: {error_description}
  File: {file_path}
  Context: {additional_context}
  Suggestion: {recommended_action}

# Example
ERROR: ValidationError: Joint angle values exceed biomechanical limits
  File: /data/gtech_2023_phase.parquet
  Context: knee_flexion_angle_ipsi_rad at phase 25% (subject_001, cycle_003)
  Suggestion: Check data collection protocols or adjust validation ranges
```

### **Error Handling Implementation**
```python
def handle_error(error: Exception, context: str = "") -> None:
    """Standardized error handling and logging"""
    error_type = type(error).__name__
    logger.error(f"{error_type}: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    # Provide actionable suggestions based on error type
    if isinstance(error, DataFormatError):
        logger.error("Suggestion: Verify input file format and structure")
    elif isinstance(error, ValidationError):
        logger.error("Suggestion: Review validation report for specific failures")
    elif isinstance(error, ConfigurationError):
        logger.error("Suggestion: Check configuration file syntax and parameters")
```

---

## Progress Reporting Standards

### **Progress Reporter Interface**
```python
class ProgressReporter:
    """Standardized progress reporting for all tools"""
    
    def start_operation(self, operation: str, total_steps: int) -> None:
        """Initialize progress tracking for an operation"""
        
    def update_progress(self, step: int, message: str) -> None:
        """Update progress with current step and status message"""
        
    def complete_operation(self, success: bool, summary: str) -> None:
        """Complete operation with success status and summary"""
        
    def log_warning(self, message: str) -> None:
        """Log warning message"""
        
    def log_error(self, error: Exception) -> None:
        """Log error with standardized format"""
```

### **Progress Display Formats**

#### **Verbose Mode**
```bash
[2024-12-06 10:30:15] Starting dataset conversion...
[2024-12-06 10:30:16] Step 1/5: Detecting input format... DONE (MATLAB)
[2024-12-06 10:30:18] Step 2/5: Loading data... DONE (1,247 gait cycles)
[2024-12-06 10:30:25] Step 3/5: Mapping variables... DONE (23/25 mapped)
[2024-12-06 10:30:35] Step 4/5: Converting to parquet... DONE
[2024-12-06 10:30:37] Step 5/5: Generating report... DONE
[2024-12-06 10:30:37] Conversion completed successfully in 22 seconds
```

#### **Normal Mode**
```bash
Converting dataset: ████████████████████░░ 80% (Step 4/5: Converting to parquet)
Conversion completed successfully in 22 seconds
```

#### **Quiet Mode** 
```bash
# Minimal output - only critical information
Conversion completed: gtech_2023_phase.parquet, gtech_2023_time.parquet
```

---

## Configuration Management

### **Configuration File Format**
```yaml
# config.yaml - Standard configuration structure
tool_name: "convert_dataset"
version: "1.0.0"

# Input/Output Settings
input:
  format: "auto"  # auto, matlab, csv, b3d
  encoding: "utf-8"
  
output:
  directory: "./output"
  formats: ["parquet"]
  overwrite: false
  
# Processing Settings
processing:
  validation_level: "moderate"  # strict, moderate, lenient
  phase_method: "heel_strike"   # heel_strike, statistical
  memory_limit_gb: 8
  
# Reporting Settings
reporting:
  format: "html"  # json, html, text, all
  include_plots: true
  verbose: false
```

### **Configuration Loading Pattern**
```python
class ConfigurationManager:
    """Standardized configuration management"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.config = self.load_default_config()
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load and merge configuration from file"""
        
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting with dot notation"""
        # Example: get_setting("processing.memory_limit_gb", 4)
        
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
```

---

## Logging Standards

### **Log Level Guidelines**
```python
import logging

# Standard logging configuration
def setup_logging(verbose: bool = False, quiet: bool = False):
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Usage guidelines:
logger.debug("Detailed diagnostic information")      # --verbose only
logger.info("General progress information")          # Normal operation
logger.warning("Potential issues or important notes") # Always shown
logger.error("Error conditions requiring attention")  # Always shown
logger.critical("Critical errors causing tool failure") # Always shown
```

### **Log Message Format**
```python
# Structured log messages
logger.info(f"Processing {subject_count} subjects, {cycle_count} gait cycles")
logger.warning(f"Variable '{var_name}' not found in standard mapping")
logger.error(f"Validation failed: {failure_count} errors in {file_path}")

# Include context for debugging
logger.debug(f"Loading data from {file_path} (format: {detected_format})")
logger.debug(f"Applied mapping: {source_var} -> {standard_var}")
```

---

## Output Standards

### **File Naming Conventions**
```bash
# Dataset outputs
{dataset_name}_time.parquet      # Time-indexed data
{dataset_name}_phase.parquet     # Phase-indexed data (150 points/cycle)

# Report outputs
{tool_name}_report.{format}      # Main tool report
{dataset_name}_validation_report.html
{dataset_name}_conversion_report.json

# Plot outputs
{dataset_name}_{task}_{plot_type}.png
{dataset_name}_{task}_animation.gif

# Metadata outputs
{dataset_name}_metadata.json
{tool_name}_configuration.yaml
```

### **Report Structure Standards**
```json
{
  "tool": "validate_phase_data",
  "version": "1.0.0",
  "timestamp": "2024-12-06T10:30:00Z",
  "input": {
    "dataset_path": "/data/gtech_2023_phase.parquet",
    "configuration": {}
  },
  "results": {
    "overall_status": "PASS",
    "summary": {},
    "details": {}
  },
  "performance": {
    "processing_time_seconds": 45.2,
    "memory_usage_mb": 234.5,
    "dataset_size_mb": 123.4
  },
  "metadata": {
    "system_info": {},
    "environment": {}
  }
}
```

---

## API Integration Patterns

### **Core Library Integration**
```python
# Standard pattern for using core libraries
class ToolBase:
    """Base class for all CLI tools"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config = ConfigurationManager(self.__class__.__name__)
        self.progress = ProgressReporter(quiet=args.quiet, verbose=args.verbose)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load_data(self, dataset_path: str) -> LocomotionData:
        """Standardized data loading with error handling"""
        try:
            return LocomotionData.from_parquet(dataset_path)
        except Exception as e:
            raise DataFormatError(f"Failed to load dataset: {e}")
    
    def save_report(self, report: Dict, output_path: str) -> None:
        """Standardized report saving with format detection"""
```

### **Feature Constants Integration**
```python
# Standard pattern for using feature constants
def validate_variable_names(variables: List[str]) -> List[str]:
    """Validate variable names against feature constants"""
    feature_constants = FeatureConstants()
    invalid_variables = []
    
    for var in variables:
        if not feature_constants.is_valid_variable(var):
            invalid_variables.append(var)
            logger.warning(f"Unknown variable: {var}")
    
    return invalid_variables
```

---

## Testing Interface Standards

### **Test Base Classes**
```python
class ToolTestBase(unittest.TestCase):
    """Base class for CLI tool tests"""
    
    def setUp(self):
        self.test_data_dir = Path("test_data")
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
    
    def run_tool(self, args: List[str]) -> Tuple[int, str, str]:
        """Run CLI tool and capture output"""
        # Standard implementation for running tools in tests
        
    def assert_file_exists(self, file_path: Path):
        """Assert file exists with descriptive error"""
        self.assertTrue(file_path.exists(), f"Expected file not found: {file_path}")
    
    def assert_report_valid(self, report_path: Path):
        """Assert report file is valid JSON/HTML"""
```

### **Mock Interface Standards**
```python
# Standard mocking patterns for testing
class MockProgressReporter:
    """Mock progress reporter for testing"""
    
    def __init__(self):
        self.operations = []
        self.progress_updates = []
    
    def start_operation(self, operation: str, total_steps: int):
        self.operations.append((operation, total_steps))
    
    def update_progress(self, step: int, message: str):
        self.progress_updates.append((step, message))
```

These interface standards ensure consistency, predictability, and maintainability across all CLI tools and APIs in the locomotion data standardization project. Following these patterns makes the tools more user-friendly and easier to maintain.