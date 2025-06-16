# Test Plan: US-08 Create ML Benchmarks

**Created:** 2025-06-16  
**Purpose:** Comprehensive test plan for ML benchmark dataset creation with data leakage prevention  
**User Story:** As an administrator I want to create ML benchmark datasets with proper train/test splits so I can enable machine learning research while preventing data leakage.

## Test Objectives

### Primary Objectives
- **Data Leakage Prevention**: Verify no subject data appears in both training and testing sets
- **Split Quality Assurance**: Validate split ratios, stratification, and statistical properties
- **Metadata Integrity**: Ensure all metadata is preserved and correctly associated with splits
- **Benchmark Usability**: Test that generated benchmarks are scientifically valid and research-ready
- **Scalability Verification**: Confirm performance with datasets of varying sizes and characteristics

### Secondary Objectives
- **Configuration Robustness**: Test various split configurations and edge cases
- **Documentation Completeness**: Verify benchmark documentation meets research standards
- **Reproducibility**: Ensure consistent results across multiple benchmark creation runs
- **Performance Baseline**: Validate establishment of meaningful performance baselines

## Test Scenarios

### 1. Data Leakage Prevention Tests

#### 1.1 Subject-Level Split Verification
- **Test Case**: Verify no subject appears in both train and test sets
- **Methodology**: Cross-reference subject IDs between splits using set intersection
- **Expected Result**: Empty intersection between train and test subject lists
- **Edge Cases**: Test with duplicate subject IDs, missing subject metadata

#### 1.2 Temporal Data Leakage Check
- **Test Case**: Ensure no temporal overlap for longitudinal subjects
- **Methodology**: Check session dates for subjects across splits
- **Expected Result**: No temporal proximity that could indicate data leakage
- **Edge Cases**: Subjects with multiple sessions, irregular sampling intervals

#### 1.3 Derived Feature Leakage
- **Test Case**: Verify no features derived from test data contaminate training
- **Methodology**: Trace feature engineering pipeline for cross-contamination
- **Expected Result**: All normalization/scaling computed only from training data
- **Edge Cases**: Global statistics, population-level features

### 2. Split Quality Assurance Tests

#### 2.1 Split Ratio Accuracy
- **Test Case**: Verify actual split ratios match configured ratios
- **Methodology**: Calculate actual ratios and compare to configuration
- **Expected Result**: Ratios within acceptable tolerance (±2%)
- **Configurations**: 70/30, 80/20, 60/20/20 (train/val/test), custom ratios

#### 2.2 Stratification Validation
- **Test Case**: Test stratification by demographics, tasks, and conditions
- **Methodology**: Compare distribution proportions between splits
- **Expected Result**: Proportional representation maintained across splits
- **Stratification Variables**: Age groups, gender, pathology status, task types

#### 2.3 Statistical Distribution Preservation
- **Test Case**: Verify biomechanical variable distributions preserved
- **Methodology**: Compare means, standard deviations, and distributions
- **Expected Result**: No significant statistical differences between splits
- **Variables**: Joint angles, moments, ground reaction forces, temporal parameters

### 3. Metadata Preservation Tests

#### 3.1 Complete Metadata Transfer
- **Test Case**: Verify all metadata fields preserved in benchmark datasets
- **Methodology**: Compare metadata completeness before and after splitting
- **Expected Result**: 100% metadata preservation with correct associations
- **Metadata Types**: Subject demographics, session info, task parameters, equipment details

#### 3.2 Metadata-Split Consistency
- **Test Case**: Ensure metadata correctly associated with respective splits
- **Methodology**: Verify metadata-data alignment within each split
- **Expected Result**: Perfect alignment between data records and metadata
- **Edge Cases**: Missing metadata, inconsistent subject IDs

#### 3.3 Provenance Tracking
- **Test Case**: Test benchmark creation audit trail
- **Methodology**: Verify all split decisions and configurations are documented
- **Expected Result**: Complete provenance information available
- **Information**: Split configuration, random seeds, creation timestamps, source datasets

### 4. Test Data Requirements

#### 4.1 Dataset Size Variations
- **Small Dataset**: 10-20 subjects for edge case testing
- **Medium Dataset**: 100-200 subjects for standard validation
- **Large Dataset**: 500+ subjects for scalability testing
- **Multi-Site Dataset**: Combined datasets from different sources

#### 4.2 Dataset Characteristics
- **Balanced Demographics**: Even distribution across age, gender, conditions
- **Imbalanced Classes**: Skewed distributions for robustness testing
- **Multi-Task Datasets**: Various locomotion tasks within single dataset
- **Longitudinal Data**: Multiple sessions per subject over time

#### 4.3 Split Configuration Matrix
- **Standard Splits**: 70/30, 80/20 train/test ratios
- **Three-Way Splits**: 60/20/20 train/validation/test
- **Custom Ratios**: Non-standard ratios like 90/10 for large datasets
- **Stratified Splits**: By demographics, pathology status, task difficulty

### 5. Quality Verification Tests

#### 5.1 Benchmark Dataset Completeness
- **Test Case**: Verify all required components present in benchmark package
- **Methodology**: Check for data files, metadata, documentation, baselines
- **Expected Result**: Complete benchmark package ready for research use
- **Components**: Train/test data, metadata files, README, baseline results

#### 5.2 Data Format Consistency
- **Test Case**: Ensure consistent data formats across splits
- **Methodology**: Validate schema compliance and format standards
- **Expected Result**: All splits conform to standardized format specification
- **Formats**: Parquet structure, column naming, data types, phase indexing

#### 5.3 Benchmark Reproducibility
- **Test Case**: Test benchmark creation reproducibility
- **Methodology**: Create identical benchmarks with same configuration
- **Expected Result**: Identical splits when using same random seed
- **Variables**: Random seed control, configuration persistence, environment consistency

### 6. Edge Case Testing

#### 6.1 Insufficient Subject Count
- **Test Case**: Handle datasets with too few subjects for requested splits
- **Methodology**: Attempt splits with various minimum subject thresholds
- **Expected Result**: Graceful failure with informative error messages
- **Scenarios**: 5 subjects with 80/20 split, single subject datasets

#### 6.2 Highly Imbalanced Stratification
- **Test Case**: Test stratification with severe class imbalances
- **Methodology**: Create benchmarks with 95/5 class distributions
- **Expected Result**: Appropriate handling or warning about imbalanced splits
- **Strategies**: Minimum class representation, oversampling notifications

#### 6.3 Missing Stratification Variables
- **Test Case**: Handle incomplete stratification metadata
- **Methodology**: Attempt stratified splits with missing demographic data
- **Expected Result**: Fallback to random splitting with appropriate warnings
- **Missing Data**: Age groups, gender, pathology status

### 7. Performance and Scalability Tests

#### 7.1 Large Dataset Processing
- **Test Case**: Benchmark creation with 1000+ subjects
- **Methodology**: Monitor memory usage, processing time, and success rate
- **Expected Result**: Efficient processing without memory overflow
- **Metrics**: Processing time, peak memory usage, disk I/O efficiency

#### 7.2 Concurrent Benchmark Creation
- **Test Case**: Multiple simultaneous benchmark creation processes
- **Methodology**: Run parallel benchmark creation with different configurations
- **Expected Result**: No resource conflicts or data corruption
- **Scenarios**: Same source dataset, different datasets, mixed configurations

#### 7.3 Storage Efficiency
- **Test Case**: Evaluate benchmark dataset storage requirements
- **Methodology**: Compare compressed vs uncompressed benchmark sizes
- **Expected Result**: Optimal storage without compromising access performance
- **Formats**: Parquet compression, metadata optimization

### 8. Baseline Performance Tests

#### 8.1 Baseline Model Training
- **Test Case**: Train simple baseline models on created benchmarks
- **Methodology**: Train standard ML models and evaluate performance
- **Expected Result**: Reasonable baseline performance metrics established
- **Models**: Linear regression, random forest, simple neural networks

#### 8.2 Performance Metric Calculation
- **Test Case**: Verify baseline performance metrics are scientifically meaningful
- **Methodology**: Compare against expected biomechanical performance ranges
- **Expected Result**: Metrics align with domain knowledge and literature
- **Metrics**: RMSE for continuous variables, accuracy for classification tasks

#### 8.3 Cross-Validation Consistency
- **Test Case**: Ensure baseline results are consistent across validation folds
- **Methodology**: Perform k-fold cross-validation on training splits
- **Expected Result**: Stable performance metrics with reasonable variance
- **Analysis**: Mean performance, confidence intervals, stability assessment

### 9. Documentation and Packaging Tests

#### 9.1 Benchmark Documentation Completeness
- **Test Case**: Verify comprehensive benchmark documentation
- **Methodology**: Review generated documentation against research standards
- **Expected Result**: All necessary information for research use present
- **Content**: Dataset description, split methodology, baseline results, usage examples

#### 9.2 Benchmark Package Integrity
- **Test Case**: Test benchmark package creation and extraction
- **Methodology**: Create, compress, transfer, and extract benchmark packages
- **Expected Result**: Complete package integrity maintained through workflow
- **Formats**: ZIP archives, TAR packages, directory structures

#### 9.3 Usage Example Validation
- **Test Case**: Verify provided usage examples work correctly
- **Methodology**: Execute all provided code examples with created benchmarks
- **Expected Result**: All examples run successfully and produce expected outputs
- **Examples**: Data loading, baseline training, evaluation scripts

### 10. Regression and Integration Tests

#### 10.1 Benchmark Creation Pipeline Integration
- **Test Case**: End-to-end pipeline from raw data to research-ready benchmark
- **Methodology**: Execute complete pipeline with monitoring at each stage
- **Expected Result**: Seamless integration without manual intervention
- **Pipeline**: Data validation → splitting → quality checks → packaging → documentation

#### 10.2 Version Compatibility
- **Test Case**: Ensure benchmark compatibility with different tool versions
- **Methodology**: Test benchmark creation across different software versions
- **Expected Result**: Consistent results across supported versions
- **Versions**: Python versions, dependency versions, data format versions

#### 10.3 Regression Testing Suite
- **Test Case**: Automated testing of benchmark creation functionality
- **Methodology**: Comprehensive test suite covering all major functionality
- **Expected Result**: All tests pass, providing confidence in system reliability
- **Coverage**: Unit tests, integration tests, end-to-end tests

## Test Success Criteria

### Data Integrity
- Zero instances of data leakage across all test scenarios
- 100% metadata preservation and correct association
- Statistical distribution preservation within acceptable tolerances

### Functionality
- Successful benchmark creation across all dataset sizes and configurations
- Proper handling of all edge cases with appropriate error messages
- Reproducible results with identical configurations

### Performance
- Benchmark creation completes within reasonable time bounds for all dataset sizes
- Memory usage remains within system constraints
- Generated benchmarks are storage-efficient while maintaining accessibility

### Documentation
- Complete and accurate documentation for all created benchmarks
- Working usage examples that demonstrate proper benchmark utilization
- Clear provenance information enabling research reproducibility

## Risk Mitigation

### High-Risk Areas
- **Subject-level data leakage**: Implement multiple verification layers
- **Stratification failures**: Provide fallback mechanisms and clear warnings
- **Large dataset processing**: Implement memory-efficient processing strategies
- **Baseline performance validation**: Establish domain-expert review process

### Contingency Plans
- **Processing failures**: Implement checkpoint and resume capabilities
- **Quality issues**: Establish rejection criteria and re-processing workflows
- **Performance problems**: Provide optimization recommendations and alternatives
- **Documentation gaps**: Automated documentation generation with manual review