# Sub-Agent Implementation Template

**Template for dividing implementation work into independent, parallel sub-agent tasks.**

## Pre-Implementation Planning

### Interface Definition Phase
Before any sub-agent starts implementation, complete interface contracts:

1. **Define all public interfaces** between components
2. **Specify data structures** that cross component boundaries  
3. **Establish error handling** patterns and exception hierarchy
4. **Create mock implementations** for testing component boundaries

---

## Sub-Agent Task Template

### **Sub-Agent Task: [Component Name]**

#### **Scope & Boundaries**
- **What this sub-agent builds**: [Specific component/module to implement]
- **Clear boundaries**: [What it explicitly does NOT handle]
- **Success criteria**: [How to verify successful completion]

#### **Dependencies**
- **Interface dependencies**: [What interfaces from other sub-agents it needs]
- **External dependencies**: [Libraries, existing code, data files it uses]
- **Dependency order**: [Which sub-agents must complete before this one starts]

#### **Interface Contract**
```python
# Public interface this sub-agent must provide
class ComponentName:
    def primary_method(self, input: InputType) -> OutputType:
        """Clear behavioral contract for this method"""
        pass
    
    def secondary_method(self, input: InputType) -> OutputType:
        """Additional interface methods"""
        pass

# Data structures this component returns
@dataclass
class ComponentResult:
    field1: Type
    field2: Type
```

#### **Test-Driven Development Plan**
1. **Unit test framework**: [Test file locations and structure]
2. **Test categories**:
   - Interface contract tests (do public methods work as specified?)
   - Integration boundary tests (does it connect properly to dependencies?)
   - Error handling tests (graceful failure modes)
   - Performance tests (meets speed/memory requirements)
3. **Test data requirements**: [What test datasets/inputs are needed]
4. **Mock strategy**: [How to mock dependencies during testing]

#### **Implementation Strategy**
- **High-level approach**: [Technical approach and key design decisions]
- **File structure**: [What files will be created/modified]
- **Key algorithms**: [Any complex logic or algorithms to implement]
- **Configuration**: [Any settings or configuration this component needs]

#### **Integration Points**
- **Interfaces used**: [What other sub-agent interfaces this depends on]
- **Interfaces provided**: [What this provides to other sub-agents]
- **Integration testing**: [How to verify it works with other components]

#### **Delivery Checklist**
- [ ] All unit tests written and passing
- [ ] Interface contract fully implemented
- [ ] Integration tests with mock dependencies passing
- [ ] Error handling implemented and tested
- [ ] Code documented with clear docstrings
- [ ] Performance meets requirements
- [ ] Component can be imported and used by other sub-agents

---

## Test-Driven Development Workflow

### **Step 1: Write Tests First**
```python
# Example test structure
class TestComponentName:
    def test_primary_method_happy_path(self):
        """Test normal operation of primary method"""
        pass
    
    def test_primary_method_error_cases(self):
        """Test error handling"""
        pass
    
    def test_interface_contract(self):
        """Test that interface behaves as specified"""
        pass
    
    def test_integration_boundaries(self):
        """Test interaction with dependencies (mocked)"""
        pass
```

### **Step 2: Implement to Pass Tests**
- Start with simplest implementation that passes tests
- Refactor for performance and maintainability
- Keep tests passing throughout development

### **Step 3: Integration Testing**
- Test component integration with real dependencies
- Verify end-to-end workflows function correctly
- Update tests if integration reveals interface issues

---

## Coordination Protocol

### **Interface Alignment Meeting**
Before implementation starts:
- Review all interface contracts
- Verify dependencies are correctly specified
- Resolve any interface conflicts or ambiguities
- Confirm test strategy covers integration points

### **Progress Check-ins**
Weekly coordination:
- Report interface completion status
- Identify any interface changes needed
- Coordinate integration testing
- Resolve blocking dependencies

### **Integration Phase**
When components are ready:
- Integration testing with real component interfaces
- End-to-end workflow validation
- Performance testing of complete system
- Documentation and tutorial updates

---

## Template Usage Instructions

### **Creating a Sub-Agent Task**
1. Copy this template for each component
2. Fill in all sections with specific details
3. Review interface contracts with team
4. Begin with test writing, then implementation
5. Use checklist to verify completion

### **Sub-Agent Independence**
- Each sub-agent should work independently
- Dependencies should be clearly mocked during development  
- Integration happens only after individual components complete
- Interface changes require coordination with affected sub-agents

### **Quality Gates**
- **Code quality**: All tests passing, documented, follows coding standards
- **Interface compliance**: Implements exactly the specified interface
- **Error handling**: Graceful failure modes for all error conditions
- **Performance**: Meets speed and memory requirements
- **Integration ready**: Can be imported and used by dependent components

---

## Example Task Assignment

### **Sub-Agent A: SpecificationManager Implementation**

**Scope**: Validation specification parsing and range lookup system
**Boundaries**: Does NOT handle validation logic or CLI interfaces
**Dependencies**: None (core component)

**Interface Contract**:
```python
class SpecificationManager:
    def get_ranges(self, task: str, variable: str, phase: int) -> Dict[str, float]:
        """Return {min, max} validation ranges for task/variable/phase"""
    
    def stage_changes(self, updates: Dict) -> StagingResult:
        """Stage specification changes for review"""
    
    def load_specifications(self, spec_files: List[str]) -> LoadResult:
        """Parse validation specification markdown files"""
```

**Test Plan**: 
- Parse existing validation_expectations_*.md files correctly
- Return accurate ranges for walking/knee_flexion_angle_ipsi_rad at phase 50%
- Handle unknown tasks/variables gracefully
- Staging workflow prevents invalid specifications

**Files**: `source/lib/validation/specification_manager.py`
**Tests**: `source/tests/test_specification_manager.py`

This template ensures each sub-agent has clear scope, well-defined interfaces, and comprehensive test coverage before implementation begins.