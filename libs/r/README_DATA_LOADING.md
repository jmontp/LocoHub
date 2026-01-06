# Enhanced Data Loading for R LocomotionData Package

Created: 2024-06-19 with user permission  
Purpose: Documentation for enhanced Parquet file reading and data validation  

Intent: Provide comprehensive guide for the new robust data loading capabilities including memory-efficient processing, validation, and format conversion.

## Overview

The enhanced data loading system provides robust, memory-efficient Parquet file reading with comprehensive validation and format detection capabilities. This implementation addresses the challenges of working with large biomechanical datasets while ensuring data quality and compatibility.

## Key Features

### 1. Memory-Efficient Parquet Loading
- **Chunked reading** for files larger than memory limits
- **Progress indicators** for long-running operations  
- **Memory usage monitoring** and optimization
- **Streaming support** using Apache Arrow

### 2. Comprehensive Data Validation
- **Structure validation** with detailed reporting
- **Phase indexing verification** (150 points per cycle)
- **Column presence and type checking**
- **Missing value detection and reporting**

### 3. Format Detection and Conversion
- **Automatic format detection** (phase vs time-indexed)
- **Time-to-phase conversion** with gait cycle detection
- **Column naming convention validation**
- **Data integrity preservation**

### 4. Robust Error Handling
- **Clear error messages** for common issues
- **Graceful degradation** for optional features
- **Comprehensive logging** and progress reporting
- **Memory constraint handling**

## Core Functions

### loadParquetData()

Memory-efficient parquet file loading with streaming support.

```r
# Basic loading
data <- loadParquetData("dataset.parquet")

# Large file with chunking
data <- loadParquetData("large_dataset.parquet", 
                       chunk_size = 50000,
                       memory_limit = 1.5)

# With validation
data <- loadParquetData("dataset.parquet", 
                       validate_structure = TRUE,
                       show_progress = TRUE)
```

**Parameters:**
- `file_path`: Path to parquet file
- `chunk_size`: Rows per chunk for large files (default: 100000)
- `memory_limit`: Maximum memory usage in GB (default: 2.0)
- `show_progress`: Show loading progress (default: TRUE)
- `validate_structure`: Validate file structure (default: TRUE)

**Features:**
- Automatic chunked loading for large files
- Memory usage monitoring
- Progress reporting
- Structure validation

### validateParquetStructure()

Comprehensive parquet file structure validation.

```r
# Basic validation
result <- validateParquetStructure("dataset.parquet")

# With specific requirements
result <- validateParquetStructure("dataset.parquet",
                                  required_columns = c("knee_angle", "hip_moment"))

# Check validation results
if (result$valid) {
  cat("File structure is valid")
} else {
  cat("Issues found:", paste(result$issues, collapse = "; "))
}
```

**Returns:**
- `valid`: Boolean indicating overall validity
- `issues`: Character vector of critical issues
- `warnings`: Character vector of warnings
- `file_info`: File size and metadata
- `column_info`: Column names and types
- `data_format_info`: Phase indexing validation

### detectDataFormat()

Automatic detection of data format (phase vs time-indexed).

```r
# Detect format
format_info <- detectDataFormat("dataset.parquet")

cat("Format:", format_info$format)
cat("Confidence:", format_info$confidence)

# Act on detection
if (format_info$format == "time_indexed") {
  # Convert to phase-indexed
  phase_data <- convertTimeToPhase("dataset.parquet")
}
```

**Returns:**
- `format`: "phase_indexed", "time_indexed", or "unknown"
- `confidence`: Confidence score (0-1)
- `details`: Detailed analysis information
- `recommendations`: Suggested next steps

### convertTimeToPhase()

Convert time-indexed data to phase-indexed format.

```r
# Basic conversion
phase_data <- convertTimeToPhase("time_data.parquet", 
                                "phase_data.parquet")

# With custom parameters
phase_data <- convertTimeToPhase("time_data.csv",
                                time_col = "time_s",
                                points_per_cycle = 101,
                                show_progress = TRUE)
```

**Features:**
- Automatic gait event detection
- Interpolation to standard phase grid
- Multiple subject-task handling
- Progress reporting

## Integration with LocomotionData Class

The enhanced loading functions integrate seamlessly with the existing LocomotionData S4 class:

```r
# Enhanced loading is automatic
loco <- new("LocomotionData", 
            data_path = "dataset.parquet",
            file_type = "auto")

# Memory-efficient loading for large files
loco <- new("LocomotionData",
            data_path = "large_dataset.parquet") 

# The class automatically uses enhanced loading with:
# - Memory management
# - Structure validation  
# - Progress reporting
# - Error handling
```

## Memory Management

### Chunked Loading Strategy

For files larger than the memory limit, the system automatically:

1. **Opens** the parquet file using Arrow scanner
2. **Reads** data in specified chunk sizes
3. **Processes** each chunk individually
4. **Combines** chunks using efficient rbindlist
5. **Cleans up** memory between chunks

### Memory Monitoring

```r
# Check current memory usage
memory_info <- getMemoryUsage()
cat("Memory used:", memory_info$total_memory_gb, "GB")

# Monitor largest objects
print(memory_info$largest_objects)
```

## Validation System

### Structure Validation

The validation system checks:

- **Required columns**: subject, task, phase
- **Data types**: Numeric phase values, character IDs
- **Phase indexing**: ~150 points per cycle
- **Missing values**: Detection and reporting
- **File integrity**: Readable structure and metadata

### Phase Indexing Validation

```r
# Phase validation details
validation <- validateParquetStructure("dataset.parquet")
phase_info <- validation$data_format_info$phase_validation

if (phase_info$is_phase_indexed) {
  cat("Phase-indexed with", phase_info$points_per_cycle, "points per cycle")
} else {
  cat("Time-indexed data detected")
}
```

## Error Handling

### Common Error Scenarios

1. **File not found**
   ```r
   # Clear error message with path
   Error: Parquet file not found: /path/to/missing.parquet
   ```

2. **Missing required columns**
   ```r
   # Helpful column listing
   Error: Missing required columns: subject, task
   Available columns: id, value, timestamp
   ```

3. **Memory constraints**
   ```r
   # Automatic chunked loading
   Large file detected (5.2 GB > 2.0 GB limit). Using chunked loading...
   ```

4. **Invalid data format**
   ```r
   # Format detection and suggestions
   Warning: Data appears time-indexed. Consider converting to phase-indexed format.
   ```

## Performance Characteristics

### Benchmarks

Typical performance on standard hardware:

- **Small files** (<100MB): Direct loading, <1 second
- **Medium files** (100MB-2GB): Direct loading, 2-10 seconds  
- **Large files** (>2GB): Chunked loading, 30-60 seconds per GB
- **Memory usage**: ~2x file size for direct loading, ~chunk_size for chunked

### Optimization Tips

1. **Adjust chunk size** based on available memory
2. **Use parquet format** instead of CSV for better performance
3. **Enable progress reporting** for long operations
4. **Validate structure** only when necessary

## Error Recovery

### Automatic Fallbacks

1. **File format detection**: Try parquet → CSV → error
2. **Memory constraints**: Direct → chunked loading
3. **Missing packages**: Core functions → enhanced features
4. **Data conversion**: Preserve data → warn about issues

### Manual Recovery

```r
# Handle specific errors
tryCatch({
  data <- loadParquetData("problematic.parquet")
}, error = function(e) {
  # Fallback to basic loading
  data <- arrow::read_parquet("problematic.parquet")
})
```

## Dependencies

### Required Packages
- `arrow`: Parquet file operations
- `data.table`: Efficient data manipulation
- `methods`: S4 class system
- `stats`: Statistical functions
- `utils`: Utility functions

### Optional Packages
- `pryr`: Enhanced memory monitoring
- `magrittr`: Pipe operators for cleaner syntax

## Best Practices

### Loading Large Datasets

```r
# Monitor memory before loading
memory_before <- getMemoryUsage()$total_memory_gb

# Load with appropriate settings
data <- loadParquetData("large_dataset.parquet",
                       chunk_size = 50000,
                       memory_limit = 1.0,
                       show_progress = TRUE)

# Check memory usage after
memory_after <- getMemoryUsage()$total_memory_gb
cat("Memory increase:", memory_after - memory_before, "GB")
```

### Validating Data Pipeline

```r
# 1. Detect format
format_info <- detectDataFormat("input.parquet")

# 2. Convert if needed
if (format_info$format == "time_indexed") {
  phase_data <- convertTimeToPhase("input.parquet", "output.parquet")
  input_file <- "output.parquet"
} else {
  input_file <- "input.parquet"
}

# 3. Validate structure
validation <- validateParquetStructure(input_file)
if (!validation$valid) {
  stop("Data validation failed:", paste(validation$issues, collapse = "; "))
}

# 4. Load into LocomotionData
loco <- new("LocomotionData", data_path = input_file)
```

### Error Handling Strategy

```r
# Comprehensive error handling
safe_load_locomotion_data <- function(file_path) {
  tryCatch({
    # Try enhanced loading
    loco <- new("LocomotionData", data_path = file_path)
    return(loco)
    
  }, error = function(e) {
    cat("Enhanced loading failed:", e$message, "\n")
    
    # Try basic loading
    tryCatch({
      if (tools::file_ext(file_path) == "parquet") {
        data <- arrow::read_parquet(file_path)
      } else {
        data <- read.csv(file_path)
      }
      # Manual validation and processing
      return(data)
      
    }, error = function(e2) {
      stop("All loading methods failed:", e2$message)
    })
  })
}
```

## Future Enhancements

### Planned Features
1. **Parallel processing** for multi-core systems
2. **Cloud storage support** (S3, GCS, Azure)
3. **Compressed format support** (gzip, brotli)
4. **Advanced caching** with disk persistence
5. **Real-time validation** during data collection

### Integration Opportunities
1. **Database connectivity** for large-scale storage
2. **Distributed computing** frameworks (Spark, Dask)
3. **Machine learning pipelines** with automatic preprocessing
4. **Quality control dashboards** with real-time monitoring

## Troubleshooting

### Common Issues

1. **"Package 'arrow' not found"**
   ```r
   install.packages("arrow")
   ```

2. **"Memory limit exceeded"**
   ```r
   # Reduce chunk size or memory limit
   loadParquetData(file, chunk_size = 10000, memory_limit = 0.5)
   ```

3. **"Phase indexing validation failed"**
   ```r
   # Check if data needs conversion
   format_info <- detectDataFormat(file)
   if (format_info$format == "time_indexed") {
     convertTimeToPhase(file, "converted.parquet")
   }
   ```

4. **"Missing required columns"**
   ```r
   # Check available columns
   validation <- validateParquetStructure(file)
   print(validation$column_info$column_names)
   ```

### Performance Issues

1. **Slow loading**: Increase chunk_size or use SSD storage
2. **High memory usage**: Decrease memory_limit or chunk_size  
3. **Validation timeouts**: Disable structure validation for trusted files
4. **Conversion failures**: Check gait event detection parameters

---

This enhanced data loading system provides a powerful, flexible foundation for working with large-scale biomechanical datasets while maintaining data quality and system performance.