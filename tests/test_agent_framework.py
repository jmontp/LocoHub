#!/usr/bin/env python3
"""
Test Agent Framework

Created: 2025-06-16 with user permission
Purpose: Independent test creation framework based solely on requirements and specifications

Intent: Implements the Test Agent from the three-agent development orchestration system,
creating comprehensive test suites that validate system behavior without implementation knowledge.
This agent operates independently from Code Agent implementations to ensure unbiased behavioral validation.
"""

import os
import re
import json
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Test scenario types"""
    HAPPY_PATH = "happy_path"
    EDGE_CASE = "edge_case"
    ERROR = "error"
    PERFORMANCE = "performance"


class TestLevel(Enum):
    """Test levels"""
    UNIT = "unit"
    INTEGRATION = "integration"  
    PERFORMANCE = "performance"
    USER_ACCEPTANCE = "user_acceptance"


@dataclass
class ValidationResult:
    """Generic validation result structure"""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def combine(cls, results: List['ValidationResult']) -> 'ValidationResult':
        """Combine multiple validation results"""
        overall_success = all(result.success for result in results)
        all_errors = []
        all_warnings = []
        
        for result in results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            
        return cls(success=overall_success, errors=all_errors, warnings=all_warnings)


@dataclass
class AcceptanceCriteria:
    """Acceptance criteria structure from user stories"""
    criterion: str
    measurement: str
    test_approach: str
    success_threshold: str
    
    def is_testable(self) -> bool:
        """Check if criteria has sufficient detail for test creation"""
        required_fields = [self.measurement, self.test_approach, self.success_threshold]
        return all(field.strip() for field in required_fields)


@dataclass
class UserStory:
    """User story structure"""
    story_id: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: List[AcceptanceCriteria]
    test_scenarios: List[str] = field(default_factory=list)
    interface_contract: str = ""
    performance_requirement: str = ""


@dataclass
class InterfaceMethod:
    """Interface method specification"""
    name: str
    signature: str
    return_type: str
    expected_behavior: str
    preconditions: List[str]
    postconditions: List[str]
    error_conditions: List[str]
    performance_requirement: str = ""


@dataclass
class InterfaceSpecification:
    """Interface behavioral specification"""
    component: str
    description: str
    methods: List[InterfaceMethod]


@dataclass
class TestableBehavior:
    """Represents a testable behavior extracted from requirements"""
    name: str
    description: str
    input_conditions: List[str]
    expected_outputs: List[str]
    error_conditions: List[str]
    performance_requirements: List[str]


@dataclass
class TestScenario:
    """Test scenario derived from requirements"""
    name: str
    scenario_type: ScenarioType
    behavior: TestableBehavior
    test_data_requirements: List[str]
    mock_requirements: List[str]
    expected_behavior: str
    expected_side_effects: List[str]
    expected_errors: List[str] = field(default_factory=list)
    performance_requirements: List[str] = field(default_factory=list)
    related_behaviors: List[TestableBehavior] = field(default_factory=list)
    
    def has_performance_requirements(self) -> bool:
        """Check if scenario has performance requirements"""
        return len(self.performance_requirements) > 0


@dataclass
class TestCase:
    """Individual test case"""
    name: str
    description: str
    test_level: TestLevel
    scenario: TestScenario
    setup_code: str
    execution_code: str
    assertions: List[str]
    teardown_code: str = ""
    mock_dependencies: List[str] = field(default_factory=list)
    
    def validates_interface_contract(self) -> bool:
        """Check if test validates interface contract"""
        return "interface" in self.description.lower()
    
    def is_behavioral_focused(self) -> bool:
        """Check if test focuses on behavior rather than implementation"""
        implementation_keywords = ["private", "internal", "_", "impl"]
        return not any(keyword in self.description.lower() for keyword in implementation_keywords)


@dataclass
class TestSuite:
    """Complete test suite for a component or user story"""
    name: str
    description: str
    user_story: UserStory
    unit_tests: List[TestCase] = field(default_factory=list)
    integration_tests: List[TestCase] = field(default_factory=list)
    performance_tests: List[TestCase] = field(default_factory=list)
    user_acceptance_tests: List[TestCase] = field(default_factory=list)
    mock_specifications: List[str] = field(default_factory=list)
    
    def all_tests(self) -> List[TestCase]:
        """Get all test cases in the suite"""
        return (self.unit_tests + self.integration_tests + 
                self.performance_tests + self.user_acceptance_tests)
    
    def count_by_level(self) -> Dict[TestLevel, int]:
        """Count tests by level"""
        counts = {level: 0 for level in TestLevel}
        for test in self.all_tests():
            counts[test.test_level] += 1
        return counts


class RequirementsParser:
    """Parses requirements documents and user stories"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RequirementsParser")
    
    def parse_user_stories_from_markdown(self, file_path: str) -> List[UserStory]:
        """Parse user stories from markdown file"""
        self.logger.info(f"Parsing user stories from {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"User stories file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stories = []
        story_sections = self._extract_story_sections(content)
        
        for section in story_sections:
            story = self._parse_single_story(section)
            if story:
                stories.append(story)
        
        self.logger.info(f"Parsed {len(stories)} user stories")
        return stories
    
    def _extract_story_sections(self, content: str) -> List[str]:
        """Extract individual story sections from markdown"""
        # Look for story patterns like "#### US-001: Title"
        story_pattern = r'#### (US-\d+):(.*?)(?=#### US-\d+:|---|\Z)'
        matches = re.findall(story_pattern, content, re.DOTALL | re.MULTILINE)
        
        sections = []
        for match in matches:
            story_id = match[0]
            story_content = match[1].strip()
            sections.append(f"#### {story_id}: {story_content}")
        
        return sections
    
    def _parse_single_story(self, section: str) -> Optional[UserStory]:
        """Parse a single user story section"""
        try:
            # Extract story ID and title
            id_title_match = re.search(r'#### (US-\d+):\s*(.+)', section)
            if not id_title_match:
                return None
            
            story_id = id_title_match.group(1)
            title = id_title_match.group(2).strip()
            
            # Extract As a/I want/So that
            as_a_match = re.search(r'\*\*As a\*\*\s+(.+)', section)
            i_want_match = re.search(r'\*\*I want\*\*\s+(.+)', section)  
            so_that_match = re.search(r'\*\*So that\*\*\s+(.+)', section)
            
            if not all([as_a_match, i_want_match, so_that_match]):
                self.logger.warning(f"Incomplete user story format for {story_id}")
                return None
            
            as_a = as_a_match.group(1).strip()
            i_want = i_want_match.group(1).strip()
            so_that = so_that_match.group(1).strip()
            
            # Extract acceptance criteria
            acceptance_criteria = self._parse_acceptance_criteria(section)
            
            # Extract test scenarios
            test_scenarios = self._parse_test_scenarios(section)
            
            # Extract interface contract
            interface_contract = self._parse_interface_contract(section)
            
            # Extract performance requirement
            performance_requirement = self._parse_performance_requirement(section)
            
            return UserStory(
                story_id=story_id,
                title=title,
                as_a=as_a,
                i_want=i_want,
                so_that=so_that,
                acceptance_criteria=acceptance_criteria,
                test_scenarios=test_scenarios,
                interface_contract=interface_contract,
                performance_requirement=performance_requirement
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing story section: {e}")
            return None
    
    def _parse_acceptance_criteria(self, section: str) -> List[AcceptanceCriteria]:
        """Parse acceptance criteria from story section"""
        criteria = []
        
        # Look for criteria list items
        criteria_pattern = r'- \*\*([^*]+)\*\*:\s*(.+?)(?=- \*\*|$)'
        matches = re.findall(criteria_pattern, section, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            criterion_name = match[0].strip()
            criterion_desc = match[1].strip()
            
            # For now, create basic criteria structure
            # In a real implementation, we'd parse more detailed criteria
            criteria.append(AcceptanceCriteria(
                criterion=criterion_desc,
                measurement="Automated validation",
                test_approach="Behavioral testing",
                success_threshold="100% compliance"
            ))
        
        return criteria
    
    def _parse_test_scenarios(self, section: str) -> List[str]:
        """Parse test scenarios from story section"""
        scenarios = []
        
        # Look for test scenarios section
        scenarios_match = re.search(r'\*\*Test Scenarios:\*\*(.*?)(?=\*\*|$)', section, re.DOTALL)
        if scenarios_match:
            scenarios_text = scenarios_match.group(1)
            scenario_lines = re.findall(r'\d+\.\s*\*\*([^*]+)\*\*:', scenarios_text)
            scenarios.extend(scenario_lines)
        
        return scenarios
    
    def _parse_interface_contract(self, section: str) -> str:
        """Parse interface contract from story section"""
        contract_match = re.search(r'\*\*Interface Contract:\*\*\s*`([^`]+)`', section)
        return contract_match.group(1) if contract_match else ""
    
    def _parse_performance_requirement(self, section: str) -> str:
        """Parse performance requirement from story section"""
        perf_match = re.search(r'\*\*Performance\*\*:\s*([^*\n]+)', section)
        return perf_match.group(1).strip() if perf_match else ""


class InterfaceSpecParser:
    """Parses interface specifications for behavioral contracts"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.InterfaceSpecParser")
    
    def parse_interface_specifications(self, file_path: str) -> List[InterfaceSpecification]:
        """Parse interface specifications from markdown file"""
        self.logger.info(f"Parsing interface specifications from {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Interface specifications file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        specifications = []
        
        # Extract class/interface definitions
        class_sections = self._extract_class_sections(content)
        
        for section in class_sections:
            spec = self._parse_single_interface(section)
            if spec:
                specifications.append(spec)
        
        self.logger.info(f"Parsed {len(specifications)} interface specifications")
        return specifications
    
    def _extract_class_sections(self, content: str) -> List[str]:
        """Extract class/interface sections from markdown"""
        # Look for class definitions in code blocks
        class_pattern = r'```python\nclass\s+(\w+).*?\n```'
        matches = re.findall(class_pattern, content, re.DOTALL)
        
        sections = []
        for match in matches:
            # Extract the full class section
            class_start = content.find(f'class {match}')
            if class_start != -1:
                # Find the end of this class section
                section_start = content.rfind('###', 0, class_start)
                section_end = content.find('###', class_start)
                if section_end == -1:
                    section_end = len(content)
                
                section = content[section_start:section_end]
                sections.append(section)
        
        return sections
    
    def _parse_single_interface(self, section: str) -> Optional[InterfaceSpecification]:
        """Parse a single interface specification"""
        try:
            # Extract class name and description
            class_match = re.search(r'class\s+(\w+)', section)
            if not class_match:
                return None
            
            component_name = class_match.group(1)
            
            # Extract description from section header or docstring
            desc_match = re.search(r'###\s*([^\n]+)', section)
            description = desc_match.group(1).strip() if desc_match else f"{component_name} interface"
            
            # Extract methods
            methods = self._parse_interface_methods(section)
            
            return InterfaceSpecification(
                component=component_name,
                description=description,
                methods=methods
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing interface section: {e}")
            return None
    
    def _parse_interface_methods(self, section: str) -> List[InterfaceMethod]:
        """Parse interface methods from section"""
        methods = []
        
        # Extract method definitions
        method_pattern = r'def\s+(\w+)\(([^)]*)\)\s*->\s*([^:]+):'
        method_matches = re.findall(method_pattern, section)
        
        for match in method_matches:
            method_name = match[0]
            parameters = match[1]
            return_type = match[2].strip()
            
            # Create method signature
            signature = f"{method_name}({parameters}) -> {return_type}"
            
            # For now, create basic method structure
            # In a real implementation, we'd parse docstrings for detailed behavior
            methods.append(InterfaceMethod(
                name=method_name,
                signature=signature,
                return_type=return_type,
                expected_behavior=f"Execute {method_name} operation according to interface contract",
                preconditions=["Valid input parameters"],
                postconditions=["Return value matches expected type"],
                error_conditions=["Invalid input raises appropriate exception"],
                performance_requirement=""
            ))
        
        return methods


class TestAgent:
    """
    Main Test Agent class implementing comprehensive test creation from requirements.
    
    This agent operates independently from implementation code to ensure unbiased
    behavioral validation based solely on requirements and interface specifications.
    """
    
    def __init__(self, isolation_enforcer=None):
        self.logger = logging.getLogger(f"{__name__}.TestAgent")
        self.requirements_parser = RequirementsParser()
        self.interface_parser = InterfaceSpecParser()
        self.isolation_enforcer = isolation_enforcer
        
        # Initialize test generation components
        self.scenario_generator = TestScenarioGenerator()
        self.test_case_generator = TestCaseGenerator()
        self.test_validator = TestValidator()
        
        self.logger.info("Test Agent initialized")
    
    def create_test_suite_from_requirements(self, 
                                          user_stories_path: str,
                                          interface_specs_path: str,
                                          output_dir: str) -> Dict[str, TestSuite]:
        """
        Create comprehensive test suites from requirements and interface specifications.
        
        This is the main entry point for the Test Agent, creating complete test suites
        that validate system behavior without any implementation knowledge.
        """
        self.logger.info("Starting test suite creation from requirements")
        
        # Validate input files exist and are accessible
        self._validate_input_files([user_stories_path, interface_specs_path])
        
        # Parse user stories
        user_stories = self.requirements_parser.parse_user_stories_from_markdown(user_stories_path)
        
        # Parse interface specifications  
        interface_specs = self.interface_parser.parse_interface_specifications(interface_specs_path)
        
        # Create test suites for each user story
        test_suites = {}
        
        for story in user_stories:
            self.logger.info(f"Creating test suite for {story.story_id}")
            
            # Generate test scenarios from story
            scenarios = self.scenario_generator.generate_scenarios_from_story(story)
            
            # Generate test cases from scenarios
            test_cases = self.test_case_generator.generate_test_cases_from_scenarios(scenarios)
            
            # Find relevant interface specs for this story
            relevant_specs = self._find_relevant_interface_specs(story, interface_specs)
            
            # Generate interface contract tests
            interface_tests = self.test_case_generator.generate_interface_tests(relevant_specs)
            
            # Create test suite
            test_suite = self._organize_tests_into_suite(story, test_cases, interface_tests)
            
            # Validate test suite quality
            validation_result = self.test_validator.validate_test_suite(test_suite, story)
            
            if not validation_result.success:
                self.logger.warning(f"Test suite validation issues for {story.story_id}: {validation_result.errors}")
            
            test_suites[story.story_id] = test_suite
        
        # Generate output files
        self._generate_test_suite_outputs(test_suites, output_dir)
        
        self.logger.info(f"Created {len(test_suites)} test suites")
        return test_suites
    
    def _validate_input_files(self, file_paths: List[str]) -> None:
        """Validate input files are accessible and enforce isolation"""
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Required input file not found: {file_path}")
            
            # Enforce isolation if enforcer is available
            if self.isolation_enforcer:
                self.isolation_enforcer.validate_file_access(file_path, "read")
    
    def _find_relevant_interface_specs(self, story: UserStory, 
                                     interface_specs: List[InterfaceSpecification]) -> List[InterfaceSpecification]:
        """Find interface specifications relevant to a user story"""
        relevant_specs = []
        
        # Match by interface contract name
        if story.interface_contract:
            for spec in interface_specs:
                if story.interface_contract.lower() in spec.component.lower():
                    relevant_specs.append(spec)
        
        # Match by story content keywords
        story_keywords = (story.title + " " + story.i_want + " " + story.so_that).lower()
        for spec in interface_specs:
            if spec.component.lower() in story_keywords:
                relevant_specs.append(spec)
        
        return relevant_specs
    
    def _organize_tests_into_suite(self, story: UserStory, 
                                 test_cases: List[TestCase],
                                 interface_tests: List[TestCase]) -> TestSuite:
        """Organize test cases into a structured test suite"""
        suite = TestSuite(
            name=f"TestSuite_{story.story_id}",
            description=f"Test suite for {story.title}",
            user_story=story
        )
        
        # Organize tests by level
        all_tests = test_cases + interface_tests
        
        for test in all_tests:
            if test.test_level == TestLevel.UNIT:
                suite.unit_tests.append(test)
            elif test.test_level == TestLevel.INTEGRATION:
                suite.integration_tests.append(test)
            elif test.test_level == TestLevel.PERFORMANCE:
                suite.performance_tests.append(test)
            elif test.test_level == TestLevel.USER_ACCEPTANCE:
                suite.user_acceptance_tests.append(test)
        
        return suite
    
    def _generate_test_suite_outputs(self, test_suites: Dict[str, TestSuite], output_dir: str) -> None:
        """Generate test suite files and documentation"""
        os.makedirs(output_dir, exist_ok=True)
        
        for story_id, suite in test_suites.items():
            # Generate Python test files
            self._generate_python_test_file(suite, output_dir)
            
            # Generate test documentation
            self._generate_test_documentation(suite, output_dir)
        
        # Generate overall test report
        self._generate_test_report(test_suites, output_dir)


class TestScenarioGenerator:
    """Generates test scenarios from user stories and requirements"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestScenarioGenerator")
    
    def generate_scenarios_from_story(self, story: UserStory) -> List[TestScenario]:
        """Generate comprehensive test scenarios from a user story"""
        scenarios = []
        
        # Extract testable behaviors from story
        behaviors = self._extract_testable_behaviors(story)
        
        for behavior in behaviors:
            # Generate happy path scenarios
            happy_scenarios = self._create_happy_path_scenarios(behavior)
            scenarios.extend(happy_scenarios)
            
            # Generate edge case scenarios
            edge_scenarios = self._create_edge_case_scenarios(behavior)
            scenarios.extend(edge_scenarios)
            
            # Generate error scenarios
            error_scenarios = self._create_error_scenarios(behavior)
            scenarios.extend(error_scenarios)
            
            # Generate performance scenarios if requirements exist
            if story.performance_requirement:
                perf_scenarios = self._create_performance_scenarios(behavior, story.performance_requirement)
                scenarios.extend(perf_scenarios)
        
        self.logger.info(f"Generated {len(scenarios)} test scenarios for {story.story_id}")
        return scenarios
    
    def _extract_testable_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract testable behaviors from user story"""
        behaviors = []
        
        # Extract primary behavior from "I want" statement
        primary_behavior = TestableBehavior(
            name=f"primary_{story.story_id.lower()}",
            description=story.i_want,
            input_conditions=["Valid user context", "System available"],
            expected_outputs=["Successful operation completion"],
            error_conditions=["Invalid input", "System unavailable"],
            performance_requirements=[story.performance_requirement] if story.performance_requirement else []
        )
        behaviors.append(primary_behavior)
        
        # Extract behaviors from acceptance criteria
        for criteria in story.acceptance_criteria:
            criteria_behavior = TestableBehavior(
                name=f"criteria_{story.story_id.lower()}_{len(behaviors)}",
                description=criteria.criterion,
                input_conditions=["Test data meeting criteria conditions"],
                expected_outputs=[criteria.success_threshold],
                error_conditions=["Data not meeting criteria"],
                performance_requirements=[]
            )
            behaviors.append(criteria_behavior)
        
        return behaviors
    
    def _create_happy_path_scenarios(self, behavior: TestableBehavior) -> List[TestScenario]:
        """Create happy path test scenarios"""
        scenario = TestScenario(
            name=f"{behavior.name}_happy_path",
            scenario_type=ScenarioType.HAPPY_PATH,
            behavior=behavior,
            test_data_requirements=["Valid test dataset", "Proper configuration"],
            mock_requirements=["External dependencies"],
            expected_behavior=behavior.description,
            expected_side_effects=["Successful completion log"]
        )
        return [scenario]
    
    def _create_edge_case_scenarios(self, behavior: TestableBehavior) -> List[TestScenario]:
        """Create edge case test scenarios"""
        scenarios = []
        
        # Boundary value scenarios
        boundary_scenario = TestScenario(
            name=f"{behavior.name}_boundary_values",
            scenario_type=ScenarioType.EDGE_CASE,
            behavior=behavior,
            test_data_requirements=["Boundary value test data", "Edge case configurations"],
            mock_requirements=["Boundary condition mocks"],
            expected_behavior="Handle boundary conditions gracefully",
            expected_side_effects=["Appropriate boundary handling"]
        )
        scenarios.append(boundary_scenario)
        
        return scenarios
    
    def _create_error_scenarios(self, behavior: TestableBehavior) -> List[TestScenario]:
        """Create error handling test scenarios"""
        scenarios = []
        
        for error_condition in behavior.error_conditions:
            error_scenario = TestScenario(
                name=f"{behavior.name}_error_{error_condition.replace(' ', '_').lower()}",
                scenario_type=ScenarioType.ERROR,
                behavior=behavior,
                test_data_requirements=["Invalid test data", "Error condition setup"],
                mock_requirements=["Error simulation mocks"],
                expected_behavior="Handle error gracefully",
                expected_side_effects=["Error logged", "Graceful failure"],
                expected_errors=[error_condition]
            )
            scenarios.append(error_scenario)
        
        return scenarios
    
    def _create_performance_scenarios(self, behavior: TestableBehavior, requirement: str) -> List[TestScenario]:
        """Create performance test scenarios"""
        scenario = TestScenario(
            name=f"{behavior.name}_performance",
            scenario_type=ScenarioType.PERFORMANCE,
            behavior=behavior,
            test_data_requirements=["Performance test dataset", "Load test configuration"],
            mock_requirements=["Performance monitoring mocks"],
            expected_behavior=f"Meet performance requirement: {requirement}",
            expected_side_effects=["Performance metrics collected"],
            performance_requirements=[requirement]
        )
        return [scenario]


class TestCaseGenerator:
    """Generates executable test cases from test scenarios"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestCaseGenerator")
    
    def generate_test_cases_from_scenarios(self, scenarios: List[TestScenario]) -> List[TestCase]:
        """Generate executable test cases from test scenarios"""
        test_cases = []
        
        for scenario in scenarios:
            # Determine test level based on scenario type and behavior
            test_level = self._determine_test_level(scenario)
            
            # Generate test case
            test_case = TestCase(
                name=f"test_{scenario.name}",
                description=f"Test {scenario.behavior.description} - {scenario.scenario_type.value}",
                test_level=test_level,
                scenario=scenario,
                setup_code=self._generate_setup_code(scenario),
                execution_code=self._generate_execution_code(scenario),
                assertions=self._generate_assertions(scenario),
                teardown_code=self._generate_teardown_code(scenario),
                mock_dependencies=scenario.mock_requirements
            )
            
            test_cases.append(test_case)
        
        self.logger.info(f"Generated {len(test_cases)} test cases from scenarios")
        return test_cases
    
    def generate_interface_tests(self, interface_specs: List[InterfaceSpecification]) -> List[TestCase]:
        """Generate test cases for interface contracts"""
        test_cases = []
        
        for spec in interface_specs:
            for method in spec.methods:
                # Generate contract compliance test
                contract_test = TestCase(
                    name=f"test_{spec.component.lower()}_{method.name}_contract",
                    description=f"Test {spec.component}.{method.name} interface contract compliance",
                    test_level=TestLevel.UNIT,
                    scenario=self._create_interface_scenario(spec, method),
                    setup_code=self._generate_interface_setup(spec, method),
                    execution_code=self._generate_interface_execution(spec, method),
                    assertions=self._generate_interface_assertions(spec, method),
                    mock_dependencies=[f"{spec.component}_mock"]
                )
                test_cases.append(contract_test)
        
        return test_cases
    
    def _determine_test_level(self, scenario: TestScenario) -> TestLevel:
        """Determine appropriate test level for scenario"""
        if scenario.scenario_type == ScenarioType.PERFORMANCE:
            return TestLevel.PERFORMANCE
        elif "workflow" in scenario.behavior.description.lower() or "end-to-end" in scenario.behavior.description.lower():
            return TestLevel.USER_ACCEPTANCE
        elif "integration" in scenario.behavior.description.lower():
            return TestLevel.INTEGRATION
        else:
            return TestLevel.UNIT
    
    def _generate_setup_code(self, scenario: TestScenario) -> str:
        """Generate test setup code"""
        setup_lines = [
            "# Test setup",
            "def setUp(self):",
            "    # Initialize test environment"
        ]
        
        # Add mock setup
        for mock_req in scenario.mock_requirements:
            setup_lines.append(f"    self.{mock_req.lower().replace(' ', '_')}_mock = Mock()")
        
        # Add test data setup
        for data_req in scenario.test_data_requirements:
            setup_lines.append(f"    self.{data_req.lower().replace(' ', '_')} = self._create_{data_req.lower().replace(' ', '_')}()")
        
        return "\n".join(setup_lines)
    
    def _generate_execution_code(self, scenario: TestScenario) -> str:
        """Generate test execution code"""
        execution_lines = [
            "# Test execution",
            f"def test_{scenario.name}(self):",
            f"    # Execute {scenario.behavior.description}",
            "    result = self._execute_test_scenario()"
        ]
        
        return "\n".join(execution_lines)
    
    def _generate_assertions(self, scenario: TestScenario) -> List[str]:
        """Generate test assertions"""
        assertions = []
        
        # Basic success assertion
        assertions.append("self.assertIsNotNone(result)")
        
        # Scenario-specific assertions
        if scenario.scenario_type == ScenarioType.HAPPY_PATH:
            assertions.append("self.assertTrue(result.success)")
        elif scenario.scenario_type == ScenarioType.ERROR:
            assertions.append("self.assertFalse(result.success)")
            for error in scenario.expected_errors:
                assertions.append(f"self.assertIn('{error}', str(result.errors))")
        elif scenario.scenario_type == ScenarioType.PERFORMANCE:
            for perf_req in scenario.performance_requirements:
                assertions.append(f"# Performance requirement: {perf_req}")
                assertions.append("self.assertLess(result.execution_time, self.performance_threshold)")
        
        # Expected behavior assertions
        assertions.append(f"# Verify: {scenario.expected_behavior}")
        
        return assertions
    
    def _generate_teardown_code(self, scenario: TestScenario) -> str:
        """Generate test teardown code"""
        return """# Test teardown
def tearDown(self):
    # Clean up test environment
    pass"""
    
    def _create_interface_scenario(self, spec: InterfaceSpecification, method: InterfaceMethod) -> TestScenario:
        """Create test scenario for interface method"""
        behavior = TestableBehavior(
            name=f"{spec.component}_{method.name}_interface",
            description=method.expected_behavior,
            input_conditions=method.preconditions,
            expected_outputs=method.postconditions,
            error_conditions=method.error_conditions,
            performance_requirements=[method.performance_requirement] if method.performance_requirement else []
        )
        
        return TestScenario(
            name=f"{spec.component}_{method.name}_contract",
            scenario_type=ScenarioType.HAPPY_PATH,
            behavior=behavior,
            test_data_requirements=["Valid method parameters"],
            mock_requirements=[f"{spec.component}_dependencies"],
            expected_behavior=method.expected_behavior,
            expected_side_effects=method.postconditions
        )
    
    def _generate_interface_setup(self, spec: InterfaceSpecification, method: InterfaceMethod) -> str:
        """Generate setup code for interface test"""
        return f"""# Interface test setup for {spec.component}.{method.name}
def setUp(self):
    self.{spec.component.lower()}_mock = Mock(spec={spec.component})
    self.test_parameters = self._create_valid_parameters()"""
    
    def _generate_interface_execution(self, spec: InterfaceSpecification, method: InterfaceMethod) -> str:
        """Generate execution code for interface test"""
        return f"""# Interface test execution for {spec.component}.{method.name}
def test_{spec.component.lower()}_{method.name}_interface(self):
    # Test interface contract: {method.signature}
    result = self.{spec.component.lower()}_mock.{method.name}(**self.test_parameters)"""
    
    def _generate_interface_assertions(self, spec: InterfaceSpecification, method: InterfaceMethod) -> List[str]:
        """Generate assertions for interface test"""
        assertions = [
            "# Interface contract assertions",
            f"# Method: {method.signature}",
            "self.assertIsNotNone(result)"
        ]
        
        # Add postcondition assertions
        for postcondition in method.postconditions:
            assertions.append(f"# Postcondition: {postcondition}")
        
        # Add error condition tests
        for error_condition in method.error_conditions:
            assertions.append(f"# Error condition: {error_condition}")
        
        return assertions


class TestValidator:
    """Validates test suite quality and completeness"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestValidator")
    
    def validate_test_suite(self, test_suite: TestSuite, user_story: UserStory) -> ValidationResult:
        """Validate test suite completeness and quality"""
        validation_errors = []
        validation_warnings = []
        
        # Validate requirements coverage
        coverage_result = self._validate_requirements_coverage(test_suite, user_story)
        validation_errors.extend(coverage_result.errors)
        validation_warnings.extend(coverage_result.warnings)
        
        # Validate test independence
        independence_result = self._validate_test_independence(test_suite)
        validation_errors.extend(independence_result.errors)
        validation_warnings.extend(independence_result.warnings)
        
        # Validate behavioral focus
        behavioral_result = self._validate_behavioral_focus(test_suite)
        validation_errors.extend(behavioral_result.errors)
        validation_warnings.extend(behavioral_result.warnings)
        
        # Validate test quality
        quality_result = self._validate_test_quality(test_suite)
        validation_errors.extend(quality_result.errors)
        validation_warnings.extend(quality_result.warnings)
        
        return ValidationResult(
            success=len(validation_errors) == 0,
            errors=validation_errors,
            warnings=validation_warnings
        )
    
    def _validate_requirements_coverage(self, test_suite: TestSuite, user_story: UserStory) -> ValidationResult:
        """Validate that all requirements are covered by tests"""
        errors = []
        warnings = []
        
        # Check acceptance criteria coverage
        for criteria in user_story.acceptance_criteria:
            if not self._has_test_for_criteria(test_suite, criteria):
                errors.append(f"No test found for acceptance criteria: {criteria.criterion}")
        
        # Check test scenario coverage
        for scenario in user_story.test_scenarios:
            if not self._has_test_for_scenario(test_suite, scenario):
                warnings.append(f"No test found for test scenario: {scenario}")
        
        # Check test level distribution
        counts = test_suite.count_by_level()
        if counts[TestLevel.UNIT] == 0:
            warnings.append("No unit tests found")
        if counts[TestLevel.INTEGRATION] == 0:
            warnings.append("No integration tests found")
        
        return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_test_independence(self, test_suite: TestSuite) -> ValidationResult:
        """Validate that tests can run independently"""
        errors = []
        warnings = []
        
        for test in test_suite.all_tests():
            # Check for proper mocking
            if not test.mock_dependencies and test.test_level != TestLevel.USER_ACCEPTANCE:
                warnings.append(f"Test {test.name} may have external dependencies without mocks")
            
            # Check for implementation dependencies (basic check)
            if "impl" in test.description.lower() or "_private" in test.name:
                errors.append(f"Test {test.name} may depend on implementation details")
        
        return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_behavioral_focus(self, test_suite: TestSuite) -> ValidationResult:
        """Validate that tests focus on behavior rather than implementation"""
        errors = []
        warnings = []
        
        for test in test_suite.all_tests():
            if not test.is_behavioral_focused():
                errors.append(f"Test {test.name} may focus on implementation rather than behavior")
            
            if not test.validates_interface_contract() and test.test_level == TestLevel.UNIT:
                warnings.append(f"Unit test {test.name} should validate interface contract")
        
        return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_test_quality(self, test_suite: TestSuite) -> ValidationResult:
        """Validate overall test quality"""
        errors = []
        warnings = []
        
        for test in test_suite.all_tests():
            # Check test completeness
            if not test.assertions:
                errors.append(f"Test {test.name} has no assertions")
            
            if not test.setup_code.strip():
                warnings.append(f"Test {test.name} has no setup code")
            
            if not test.execution_code.strip():
                errors.append(f"Test {test.name} has no execution code")
        
        return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _has_test_for_criteria(self, test_suite: TestSuite, criteria: AcceptanceCriteria) -> bool:
        """Check if test suite has test for acceptance criteria"""
        criteria_keywords = criteria.criterion.lower().split()
        
        for test in test_suite.all_tests():
            test_description = test.description.lower()
            if any(keyword in test_description for keyword in criteria_keywords):
                return True
        
        return False
    
    def _has_test_for_scenario(self, test_suite: TestSuite, scenario: str) -> bool:
        """Check if test suite has test for scenario"""
        scenario_keywords = scenario.lower().split()
        
        for test in test_suite.all_tests():
            test_name = test.name.lower()
            if any(keyword in test_name for keyword in scenario_keywords):
                return True
        
        return False


if __name__ == "__main__":
    # Example usage
    test_agent = TestAgent()
    
    # Example paths (would be provided by orchestration system)
    user_stories_path = "/path/to/user_stories.md"
    interface_specs_path = "/path/to/interface_specs.md"
    output_dir = "/path/to/test_output"
    
    try:
        test_suites = test_agent.create_test_suite_from_requirements(
            user_stories_path,
            interface_specs_path,
            output_dir
        )
        
        print(f"Successfully created {len(test_suites)} test suites")
        
    except Exception as e:
        print(f"Test Agent error: {e}")