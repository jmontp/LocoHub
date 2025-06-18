# Week 1 Concrete Example: Foundation Phase

**Specific, actionable tasks that demonstrate the evolutionary approach.**

## Sub-Agent A: Foundation & Test Infrastructure

### **Concrete Task Assignment**
```markdown
## Sub-Agent A: Create Shared Validation Foundation

Build the test infrastructure and domain knowledge base that enables all other validation work.

### Specific Deliverables

1. **Test Data Setup** (`source/tests/fixtures/`)
   - Load existing validation specs from `docs/standard_spec/validation_expectations_kinematic.md`
   - Create 3 test parquet files:
     - `test_walking_valid.parquet` - walking data that should pass all validations
     - `test_walking_invalid.parquet` - walking data with known validation failures
     - `test_mixed_tasks.parquet` - multiple tasks (walking, running) 
   
2. **Domain Knowledge Documentation** (`docs/validation_domain/`)
   - Document current validation approach from existing `source/validation/` code
   - Map out what validation ranges exist for walking task
   - Document expected validation failure patterns
   - List biomechanical constraints and edge cases
   
3. **Shared Test Utilities** (`source/tests/validation_utils.py`)
   - `load_test_dataset(name: str) -> pd.DataFrame`
   - `get_walking_validation_ranges() -> Dict[str, Dict[str, float]]`
   - `create_validation_failure_data(failure_type: str) -> pd.DataFrame`
   - `assert_validation_report_contains(report_path: str, expected_content: List[str])`

### Success Criteria
- Other sub-agents can load test data with one function call
- Walking validation ranges are documented and accessible
- Test utilities enable validation testing without setup overhead

### Example Usage Other Sub-Agents Will Have
```python
# Other sub-agents can immediately start with:
from tests.validation_utils import load_test_dataset, get_walking_validation_ranges

data = load_test_dataset("walking_valid")
ranges = get_walking_validation_ranges()
# Now focus on validation logic, not test setup
```
```

### **Why This Works**
- **Concrete deliverables**: Specific files and functions, not abstract interfaces
- **Real data focus**: Uses actual validation specs and datasets from your project
- **Enables others**: Removes setup friction for other sub-agents
- **Domain knowledge capture**: Documents what's already known about validation

## Sub-Agent B: Walking Validation Prototype (Example Task)

### **Concrete Task Assignment**  
```markdown
## Sub-Agent B: Build Walking Validation MVP

Create the simplest possible working walking validation tool.

### Specific Implementation
File: `source/validation/walking_validator_prototype.py`

```python
def validate_walking_dataset(file_path: str, output_dir: str = ".") -> str:
    """
    Complete walking validation workflow. 
    Returns: path to generated markdown report
    """
    # 1. Load walking validation ranges (use Sub-Agent A's utilities)
    ranges = get_walking_validation_ranges()
    
    # 2. Load and check dataset basic structure
    data = pd.read_parquet(file_path)
    errors = check_basic_structure(data)
    
    # 3. Filter walking strides using known ranges
    walking_data = data[data['task'] == 'walking']
    valid_strides, invalid_strides = filter_walking_strides(walking_data, ranges)
    
    # 4. Generate simple markdown report
    report_path = generate_report(valid_strides, invalid_strides, errors, output_dir)
    
    return report_path

# CLI entry point
if __name__ == "__main__":
    dataset_path = sys.argv[1]
    result = validate_walking_dataset(dataset_path)
    print(f"Report generated: {result}")
```

### Success Criteria
- `python walking_validator_prototype.py test_walking_valid.parquet` produces report
- Report shows pass/fail status and specific validation failures
- Works with Sub-Agent A's test data
- Takes <30 seconds on typical walking dataset

### Learning Objectives
- What validation logic is actually needed?
- What error cases occur in practice?
- What should the report contain?
- Where are the natural component boundaries?
```

## Sub-Agent C: Multi-Task Research (Example Task)

### **Concrete Task Assignment**
```markdown  
## Sub-Agent C: Multi-Task Validation Research

While Sub-Agent B builds walking prototype, research requirements for other tasks.

### Research Questions
1. **Range Differences**: How do knee flexion ranges differ between walking vs running?
2. **Task Detection**: How reliably can we detect task type from data?
3. **Validation Complexity**: Are there task-specific validation rules beyond just different ranges?
4. **Performance Impact**: How much slower is validation with 5 tasks vs 1 task?

### Specific Deliverables
File: `docs/validation_domain/multi_task_analysis.md`

Content should include:
- Comparison table of validation ranges across tasks
- Analysis of task detection challenges
- Performance benchmarks with different task counts
- Recommended multi-task validation strategy

### Research Method
- Use existing validation specs to compare ranges
- Test task detection on available datasets
- Benchmark current validation code with different configurations
- Interview domain experts about task-specific validation requirements

### Success Criteria
- Clear recommendation for multi-task validation approach
- Performance benchmarks inform architecture decisions
- Task complexity is well understood before implementation
```

## Why This Approach Succeeds

### **Concrete vs Abstract**
- **Old way**: "Implement SpecificationManager interface"
- **New way**: "Create `get_walking_validation_ranges()` function that returns knee flexion min/max"

### **Incremental Learning**
- Sub-Agent A creates foundation others can immediately use
- Sub-Agent B discovers real validation requirements through implementation
- Sub-Agent C researches complexity before committing to architecture

### **Real Value at Each Step**
- Week 1: Working walking validation tool
- Week 2: Multi-task support  
- Week 3: Clean interfaces extracted from working code

### **Parallel Work That Actually Works**
- Sub-Agent A: Infrastructure (enables others)
- Sub-Agent B: Implementation (discovers requirements)
- Sub-Agent C: Research (informs future architecture)

**No coordination overhead because each has distinct, valuable work.**

## Next Steps

After Week 1, you'd have:
1. **Shared test infrastructure** that enables rapid validation development
2. **Working walking validation** that demonstrates end-to-end workflow  
3. **Multi-task research** that informs architecture decisions

Then Week 2 can extract clean interfaces from working code and extend to multiple tasks.

**This is how you make sub-agent implementation actually work in practice.**