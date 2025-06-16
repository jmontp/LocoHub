#!/usr/bin/env python3
"""
Requirements-to-Tests Pipeline

Created: 2025-06-16 with user permission
Purpose: Convert user stories and acceptance criteria to comprehensive test cases

Intent: Implements the core pipeline for transforming requirements documents into
executable test scenarios, ensuring complete coverage of acceptance criteria without
implementation knowledge. This pipeline analyzes user stories, extracts testable
behaviors, and generates comprehensive test cases across all test levels.
"""

import re
import json
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import logging
from pathlib import Path

from test_agent_framework import (
    UserStory, AcceptanceCriteria, TestScenario, TestCase, TestableBehavior,
    ScenarioType, TestLevel, ValidationResult
)

logger = logging.getLogger(__name__)


class RequirementType(Enum):
    """Types of requirements that can be extracted"""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USABILITY = "usability"
    ERROR_HANDLING = "error_handling"


class CoverageLevel(Enum):
    """Test coverage levels for requirements"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass
class RequirementMapping:
    """Maps requirements to test scenarios and coverage"""
    requirement_id: str
    requirement_text: str
    requirement_type: RequirementType
    test_scenarios: List[str] = field(default_factory=list)
    coverage_level: CoverageLevel = CoverageLevel.MISSING
    test_approaches: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class TestCoverageReport:
    """Comprehensive test coverage analysis"""
    story_id: str
    total_requirements: int
    covered_requirements: int
    coverage_percentage: float
    missing_coverage: List[str] = field(default_factory=list)
    partial_coverage: List[str] = field(default_factory=list)
    complete_coverage: List[str] = field(default_factory=list)
    requirement_mappings: List[RequirementMapping] = field(default_factory=list)


@dataclass
class BiomechanicalTestPattern:
    """Domain-specific test patterns for biomechanical validation"""
    pattern_name: str
    description: str
    test_data_requirements: List[str]
    validation_approaches: List[str]
    expected_outcomes: List[str]
    performance_thresholds: Dict[str, Any] = field(default_factory=dict)


class RequirementsAnalyzer:
    """Analyzes requirements for testability and completeness"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RequirementsAnalyzer")
    
    def analyze_user_story_testability(self, story: UserStory) -> Dict[str, Any]:
        """Analyze how testable a user story is"""
        analysis = {
            "story_id": story.story_id,
            "testability_score": 0.0,
            "testable_elements": [],
            "improvement_suggestions": [],
            "requirement_mappings": []
        }
        
        # Analyze acceptance criteria testability
        testable_criteria = 0
        for criteria in story.acceptance_criteria:
            if criteria.is_testable():
                testable_criteria += 1
                analysis["testable_elements"].append(f"Criteria: {criteria.criterion}")
            else:
                analysis["improvement_suggestions"].append(
                    f"Acceptance criteria needs more specific measurement approach: {criteria.criterion}"
                )
        
        # Calculate testability score
        if story.acceptance_criteria:
            criteria_score = testable_criteria / len(story.acceptance_criteria) * 40
        else:
            criteria_score = 0
            analysis["improvement_suggestions"].append("No acceptance criteria defined")
        
        # Check for performance requirements
        perf_score = 20 if story.performance_requirement else 0
        if not story.performance_requirement:
            analysis["improvement_suggestions"].append("No performance requirements specified")
        
        # Check for interface contracts
        interface_score = 20 if story.interface_contract else 0
        if not story.interface_contract:
            analysis["improvement_suggestions"].append("No interface contract specified")
        
        # Check for test scenarios
        scenario_score = 20 if story.test_scenarios else 0
        if not story.test_scenarios:
            analysis["improvement_suggestions"].append("No explicit test scenarios provided")
        
        analysis["testability_score"] = criteria_score + perf_score + interface_score + scenario_score
        
        # Extract requirement mappings
        analysis["requirement_mappings"] = self._extract_requirement_mappings(story)
        
        return analysis
    
    def _extract_requirement_mappings(self, story: UserStory) -> List[RequirementMapping]:
        """Extract and categorize requirements from user story"""
        mappings = []
        
        # Map acceptance criteria to requirements
        for i, criteria in enumerate(story.acceptance_criteria):
            req_type = self._classify_requirement_type(criteria.criterion)
            
            mapping = RequirementMapping(
                requirement_id=f"{story.story_id}_AC_{i+1}",
                requirement_text=criteria.criterion,
                requirement_type=req_type,
                test_approaches=[criteria.test_approach] if criteria.test_approach else [],
                success_criteria=[criteria.success_threshold] if criteria.success_threshold else []
            )
            mappings.append(mapping)
        
        # Map performance requirements
        if story.performance_requirement:
            perf_mapping = RequirementMapping(
                requirement_id=f"{story.story_id}_PERF",
                requirement_text=story.performance_requirement,
                requirement_type=RequirementType.PERFORMANCE,
                test_approaches=["Performance benchmarking"],
                success_criteria=["Meet specified timing requirements"]
            )
            mappings.append(perf_mapping)
        
        return mappings
    
    def _classify_requirement_type(self, requirement_text: str) -> RequirementType:
        """Classify requirement based on text content"""
        text_lower = requirement_text.lower()
        
        if any(word in text_lower for word in ["minutes", "seconds", "speed", "time", "performance"]):
            return RequirementType.PERFORMANCE
        elif any(word in text_lower for word in ["error", "exception", "failure", "invalid"]):
            return RequirementType.ERROR_HANDLING
        elif any(word in text_lower for word in ["quality", "accuracy", "precision", "threshold"]):
            return RequirementType.QUALITY
        elif any(word in text_lower for word in ["user", "interface", "workflow", "experience"]):
            return RequirementType.USABILITY
        else:
            return RequirementType.FUNCTIONAL


class BehaviorExtractor:
    """Extracts testable behaviors from user stories and requirements"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.BehaviorExtractor")
    
    def extract_comprehensive_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract all testable behaviors from user story"""
        behaviors = []
        
        # Extract primary workflow behavior
        primary_behavior = self._extract_primary_behavior(story)
        behaviors.append(primary_behavior)
        
        # Extract behaviors from acceptance criteria
        criteria_behaviors = self._extract_criteria_behaviors(story)
        behaviors.extend(criteria_behaviors)
        
        # Extract error handling behaviors
        error_behaviors = self._extract_error_behaviors(story)
        behaviors.extend(error_behaviors)
        
        # Extract performance behaviors
        if story.performance_requirement:
            perf_behaviors = self._extract_performance_behaviors(story)
            behaviors.extend(perf_behaviors)
        
        # Extract integration behaviors
        if story.interface_contract:
            integration_behaviors = self._extract_integration_behaviors(story)
            behaviors.extend(integration_behaviors)
        
        self.logger.info(f"Extracted {len(behaviors)} testable behaviors from {story.story_id}")
        return behaviors
    
    def _extract_primary_behavior(self, story: UserStory) -> TestableBehavior:
        """Extract primary behavior from 'I want' statement"""
        return TestableBehavior(
            name=f"{story.story_id.lower()}_primary_workflow",
            description=story.i_want,
            input_conditions=self._infer_input_conditions(story.as_a, story.i_want),
            expected_outputs=self._infer_expected_outputs(story.so_that),
            error_conditions=self._infer_error_conditions(story.i_want),
            performance_requirements=[story.performance_requirement] if story.performance_requirement else []
        )
    
    def _extract_criteria_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract behaviors from acceptance criteria"""
        behaviors = []
        
        for i, criteria in enumerate(story.acceptance_criteria):
            behavior = TestableBehavior(
                name=f"{story.story_id.lower()}_criteria_{i+1}",
                description=criteria.criterion,
                input_conditions=self._extract_criteria_inputs(criteria),
                expected_outputs=self._extract_criteria_outputs(criteria),
                error_conditions=self._extract_criteria_errors(criteria),
                performance_requirements=[]
            )
            behaviors.append(behavior)
        
        return behaviors
    
    def _extract_error_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract error handling behaviors"""
        behaviors = []
        
        # Common error scenarios for biomechanical data
        common_errors = [
            "Invalid file format",
            "Missing required columns", 
            "Corrupted data",
            "Network connectivity issues",
            "Insufficient memory",
            "Invalid parameter values"
        ]
        
        for error in common_errors:
            if self._is_relevant_error(error, story):
                behavior = TestableBehavior(
                    name=f"{story.story_id.lower()}_error_{error.lower().replace(' ', '_')}",
                    description=f"Handle {error} gracefully",
                    input_conditions=[f"System encounters {error}"],
                    expected_outputs=["Clear error message", "Graceful failure"],
                    error_conditions=[error],
                    performance_requirements=[]
                )
                behaviors.append(behavior)
        
        return behaviors
    
    def _extract_performance_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract performance-related behaviors"""
        behavior = TestableBehavior(
            name=f"{story.story_id.lower()}_performance_compliance",
            description=f"Meet performance requirement: {story.performance_requirement}",
            input_conditions=["Large dataset", "Standard hardware configuration"],
            expected_outputs=["Processing completed within time limit"],
            error_conditions=["Performance threshold exceeded"],
            performance_requirements=[story.performance_requirement]
        )
        return [behavior]
    
    def _extract_integration_behaviors(self, story: UserStory) -> List[TestableBehavior]:
        """Extract integration and workflow behaviors"""
        behavior = TestableBehavior(
            name=f"{story.story_id.lower()}_integration_workflow",
            description=f"Integrate with {story.interface_contract} successfully",
            input_conditions=["Valid interface configuration", "External dependencies available"],
            expected_outputs=["Successful integration", "Data flow completed"],
            error_conditions=["Interface unavailable", "Integration failure"],
            performance_requirements=[]
        )
        return [behavior]
    
    def _infer_input_conditions(self, as_a: str, i_want: str) -> List[str]:
        """Infer input conditions from user context and wants"""
        conditions = []
        
        # User context conditions
        if "programmer" in as_a.lower():
            conditions.extend(["Development environment available", "Source code access"])
        elif "curator" in as_a.lower():
            conditions.extend(["Dataset access", "Validation tools available"])
        elif "administrator" in as_a.lower():
            conditions.extend(["Admin privileges", "System access"])
        
        # Activity-specific conditions
        if "convert" in i_want.lower():
            conditions.extend(["Source dataset", "Conversion configuration"])
        elif "validate" in i_want.lower():
            conditions.extend(["Dataset to validate", "Validation rules"])
        elif "generate" in i_want.lower():
            conditions.extend(["Input data", "Generation parameters"])
        
        return conditions
    
    def _infer_expected_outputs(self, so_that: str) -> List[str]:
        """Infer expected outputs from 'so that' benefits"""
        outputs = []
        
        if "quality" in so_that.lower():
            outputs.append("Quality assessment report")
        if "confidence" in so_that.lower():
            outputs.append("Confidence score")
        if "standardized" in so_that.lower():
            outputs.append("Standardized format output")
        if "efficient" in so_that.lower():
            outputs.append("Optimized processing")
        
        # Default output
        if not outputs:
            outputs.append("Successful operation completion")
        
        return outputs
    
    def _infer_error_conditions(self, i_want: str) -> List[str]:
        """Infer potential error conditions from desired functionality"""
        errors = []
        
        if "convert" in i_want.lower():
            errors.extend(["Invalid source format", "Conversion failure"])
        if "validate" in i_want.lower():
            errors.extend(["Validation rule missing", "Data integrity failure"])
        if "generate" in i_want.lower():
            errors.extend(["Insufficient input data", "Generation failure"])
        
        # Common errors
        errors.extend(["Invalid input", "System unavailable", "Permission denied"])
        
        return errors
    
    def _extract_criteria_inputs(self, criteria: AcceptanceCriteria) -> List[str]:
        """Extract input conditions from acceptance criteria"""
        return [f"Data meeting {criteria.measurement} requirements"]
    
    def _extract_criteria_outputs(self, criteria: AcceptanceCriteria) -> List[str]:
        """Extract expected outputs from acceptance criteria"""
        return [criteria.success_threshold]
    
    def _extract_criteria_errors(self, criteria: AcceptanceCriteria) -> List[str]:
        """Extract error conditions from acceptance criteria"""
        return [f"Data not meeting {criteria.measurement} requirements"]
    
    def _is_relevant_error(self, error: str, story: UserStory) -> bool:
        """Check if error scenario is relevant to the user story"""
        story_text = (story.title + " " + story.i_want + " " + story.so_that).lower()
        
        # Map errors to story contexts
        error_relevance = {
            "invalid file format": ["convert", "file", "dataset"],
            "missing required columns": ["validate", "dataset", "structure"],
            "corrupted data": ["validate", "quality", "integrity"],
            "network connectivity issues": ["download", "remote", "sync"],
            "insufficient memory": ["large", "dataset", "performance"],
            "invalid parameter values": ["configure", "parameter", "setting"]
        }
        
        if error.lower() in error_relevance:
            keywords = error_relevance[error.lower()]
            return any(keyword in story_text for keyword in keywords)
        
        return True  # Include by default


class TestScenarioBuilder:
    """Builds comprehensive test scenarios from behaviors"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestScenarioBuilder")
        self.biomechanical_patterns = self._load_biomechanical_patterns()
    
    def build_comprehensive_scenarios(self, behaviors: List[TestableBehavior], story: UserStory) -> List[TestScenario]:
        """Build comprehensive test scenarios from extracted behaviors"""
        scenarios = []
        
        for behavior in behaviors:
            # Happy path scenarios
            happy_scenarios = self._build_happy_path_scenarios(behavior, story)
            scenarios.extend(happy_scenarios)
            
            # Edge case scenarios
            edge_scenarios = self._build_edge_case_scenarios(behavior, story)
            scenarios.extend(edge_scenarios)
            
            # Error scenarios
            error_scenarios = self._build_error_scenarios(behavior, story)
            scenarios.extend(error_scenarios)
            
            # Performance scenarios
            if behavior.performance_requirements:
                perf_scenarios = self._build_performance_scenarios(behavior, story)
                scenarios.extend(perf_scenarios)
            
            # Domain-specific scenarios
            domain_scenarios = self._build_domain_specific_scenarios(behavior, story)
            scenarios.extend(domain_scenarios)
        
        self.logger.info(f"Built {len(scenarios)} comprehensive test scenarios")
        return scenarios
    
    def _build_happy_path_scenarios(self, behavior: TestableBehavior, story: UserStory) -> List[TestScenario]:
        """Build happy path test scenarios"""
        scenarios = []
        
        # Basic happy path
        basic_scenario = TestScenario(
            name=f"{behavior.name}_happy_path",
            scenario_type=ScenarioType.HAPPY_PATH,
            behavior=behavior,
            test_data_requirements=self._determine_test_data_requirements(behavior, story),
            mock_requirements=self._determine_mock_requirements(behavior, story),
            expected_behavior=behavior.description,
            expected_side_effects=["Successful completion", "Proper logging"]
        )
        scenarios.append(basic_scenario)
        
        # Variations for different data types if relevant
        if self._is_data_processing_behavior(behavior):
            for data_type in ["small_dataset", "medium_dataset", "typical_dataset"]:
                variation_scenario = TestScenario(
                    name=f"{behavior.name}_happy_path_{data_type}",
                    scenario_type=ScenarioType.HAPPY_PATH,
                    behavior=behavior,
                    test_data_requirements=[data_type, "valid_configuration"],
                    mock_requirements=basic_scenario.mock_requirements,
                    expected_behavior=f"{behavior.description} with {data_type}",
                    expected_side_effects=basic_scenario.expected_side_effects
                )
                scenarios.append(variation_scenario)
        
        return scenarios
    
    def _build_edge_case_scenarios(self, behavior: TestableBehavior, story: UserStory) -> List[TestScenario]:
        """Build edge case test scenarios"""
        scenarios = []
        
        # Boundary value scenarios
        boundary_scenario = TestScenario(
            name=f"{behavior.name}_boundary_values",
            scenario_type=ScenarioType.EDGE_CASE,
            behavior=behavior,
            test_data_requirements=["boundary_value_dataset", "edge_case_configuration"],
            mock_requirements=self._determine_mock_requirements(behavior, story),
            expected_behavior="Handle boundary conditions appropriately",
            expected_side_effects=["Boundary condition logging", "Appropriate warnings"]
        )
        scenarios.append(boundary_scenario)
        
        # Empty/minimal data scenarios
        if self._is_data_processing_behavior(behavior):
            minimal_scenario = TestScenario(
                name=f"{behavior.name}_minimal_data",
                scenario_type=ScenarioType.EDGE_CASE,
                behavior=behavior,
                test_data_requirements=["minimal_valid_dataset"],
                mock_requirements=self._determine_mock_requirements(behavior, story),
                expected_behavior="Handle minimal data appropriately",
                expected_side_effects=["Minimal data handling confirmation"]
            )
            scenarios.append(minimal_scenario)
        
        # Maximum capacity scenarios
        if story.performance_requirement:
            max_scenario = TestScenario(
                name=f"{behavior.name}_maximum_capacity",
                scenario_type=ScenarioType.EDGE_CASE,
                behavior=behavior,
                test_data_requirements=["maximum_size_dataset"],
                mock_requirements=self._determine_mock_requirements(behavior, story),
                expected_behavior="Handle maximum capacity appropriately",
                expected_side_effects=["Resource usage monitoring", "Performance metrics"]
            )
            scenarios.append(max_scenario)
        
        return scenarios
    
    def _build_error_scenarios(self, behavior: TestableBehavior, story: UserStory) -> List[TestScenario]:
        """Build error handling test scenarios"""
        scenarios = []
        
        for error_condition in behavior.error_conditions:
            error_scenario = TestScenario(
                name=f"{behavior.name}_error_{error_condition.replace(' ', '_').lower()}",
                scenario_type=ScenarioType.ERROR,
                behavior=behavior,
                test_data_requirements=self._determine_error_test_data(error_condition),
                mock_requirements=self._determine_error_mocks(error_condition),
                expected_behavior="Handle error gracefully",
                expected_side_effects=["Error logged appropriately", "Clean failure state"],
                expected_errors=[error_condition]
            )
            scenarios.append(error_scenario)
        
        return scenarios
    
    def _build_performance_scenarios(self, behavior: TestableBehavior, story: UserStory) -> List[TestScenario]:
        """Build performance test scenarios"""
        scenarios = []
        
        for perf_req in behavior.performance_requirements:
            perf_scenario = TestScenario(
                name=f"{behavior.name}_performance_validation",
                scenario_type=ScenarioType.PERFORMANCE,
                behavior=behavior,
                test_data_requirements=["performance_test_dataset", "performance_configuration"],
                mock_requirements=["performance_monitoring_mocks"],
                expected_behavior=f"Meet performance requirement: {perf_req}",
                expected_side_effects=["Performance metrics collected", "Resource usage tracked"],
                performance_requirements=[perf_req]
            )
            scenarios.append(perf_scenario)
        
        return scenarios
    
    def _build_domain_specific_scenarios(self, behavior: TestableBehavior, story: UserStory) -> List[TestScenario]:
        """Build domain-specific scenarios for biomechanical data"""
        scenarios = []
        
        # Check if this is biomechanical validation behavior
        if self._is_biomechanical_validation_behavior(behavior):
            for pattern in self.biomechanical_patterns:
                if self._pattern_applies_to_behavior(pattern, behavior):
                    domain_scenario = TestScenario(
                        name=f"{behavior.name}_{pattern.pattern_name}",
                        scenario_type=ScenarioType.HAPPY_PATH,
                        behavior=behavior,
                        test_data_requirements=pattern.test_data_requirements,
                        mock_requirements=["biomechanical_validation_mocks"],
                        expected_behavior=f"Validate {pattern.description}",
                        expected_side_effects=pattern.expected_outcomes
                    )
                    scenarios.append(domain_scenario)
        
        return scenarios
    
    def _load_biomechanical_patterns(self) -> List[BiomechanicalTestPattern]:
        """Load domain-specific biomechanical test patterns"""
        patterns = [
            BiomechanicalTestPattern(
                pattern_name="phase_indexing_validation",
                description="exactly 150 points per gait cycle",
                test_data_requirements=["phase_indexed_dataset", "cycle_boundary_data"],
                validation_approaches=["Point count validation", "Phase progression validation"],
                expected_outcomes=["All cycles have 150 points", "Phase progression is monotonic"]
            ),
            BiomechanicalTestPattern(
                pattern_name="biomechanical_range_validation",
                description="biomechanical values within expected ranges",
                test_data_requirements=["range_validation_dataset", "reference_ranges"],
                validation_approaches=["Statistical range checking", "Outlier detection"],
                expected_outcomes=["Values within typical ranges", "Outliers flagged appropriately"]
            ),
            BiomechanicalTestPattern(
                pattern_name="kinematic_pattern_validation",
                description="kinematic patterns match expected gait characteristics",
                test_data_requirements=["kinematic_dataset", "reference_patterns"],
                validation_approaches=["Pattern correlation analysis", "Phase-specific validation"],
                expected_outcomes=["Patterns correlate with references", "Phase-specific ranges respected"]
            )
        ]
        return patterns
    
    def _determine_test_data_requirements(self, behavior: TestableBehavior, story: UserStory) -> List[str]:
        """Determine test data requirements for behavior"""
        requirements = ["valid_test_dataset"]
        
        # Add story-specific requirements
        if "convert" in story.i_want.lower():
            requirements.extend(["source_format_data", "conversion_configuration"])
        elif "validate" in story.i_want.lower():
            requirements.extend(["validation_test_data", "validation_rules"])
        elif "generate" in story.i_want.lower():
            requirements.extend(["generation_input_data", "generation_parameters"])
        
        # Add behavior-specific requirements
        if "phase" in behavior.description.lower():
            requirements.append("phase_indexed_test_data")
        if "performance" in behavior.description.lower():
            requirements.append("performance_test_dataset")
        
        return list(set(requirements))  # Remove duplicates
    
    def _determine_mock_requirements(self, behavior: TestableBehavior, story: UserStory) -> List[str]:
        """Determine mock requirements for behavior"""
        mocks = ["logging_mock"]
        
        # Add interface-specific mocks
        if story.interface_contract:
            contract_name = story.interface_contract.replace('.py', '').replace('_', '')
            mocks.append(f"{contract_name}_mock")
        
        # Add common dependency mocks
        if "file" in behavior.description.lower():
            mocks.append("file_system_mock")
        if "database" in behavior.description.lower():
            mocks.append("database_mock")
        if "network" in behavior.description.lower():
            mocks.append("network_mock")
        
        return mocks
    
    def _determine_error_test_data(self, error_condition: str) -> List[str]:
        """Determine test data for error scenarios"""
        error_data_map = {
            "invalid file format": ["corrupted_file", "wrong_format_file"],
            "missing required columns": ["incomplete_dataset", "wrong_schema_data"],
            "corrupted data": ["corrupted_dataset", "malformed_data"],
            "invalid input": ["invalid_parameters", "out_of_range_values"],
            "system unavailable": ["offline_system_simulation"],
            "permission denied": ["restricted_access_simulation"]
        }
        
        return error_data_map.get(error_condition.lower(), ["error_simulation_data"])
    
    def _determine_error_mocks(self, error_condition: str) -> List[str]:
        """Determine mocks for error scenarios"""
        error_mock_map = {
            "invalid file format": ["file_system_mock"],
            "missing required columns": ["data_schema_mock"],
            "corrupted data": ["data_integrity_mock"],
            "system unavailable": ["system_availability_mock"],
            "network connectivity issues": ["network_mock"],
            "permission denied": ["authorization_mock"]
        }
        
        return error_mock_map.get(error_condition.lower(), ["error_simulation_mock"])
    
    def _is_data_processing_behavior(self, behavior: TestableBehavior) -> bool:
        """Check if behavior involves data processing"""
        data_keywords = ["convert", "validate", "process", "transform", "analyze"]
        return any(keyword in behavior.description.lower() for keyword in data_keywords)
    
    def _is_biomechanical_validation_behavior(self, behavior: TestableBehavior) -> bool:
        """Check if behavior involves biomechanical validation"""
        bio_keywords = ["phase", "gait", "biomechanical", "kinematic", "kinetic", "cycle"]
        return any(keyword in behavior.description.lower() for keyword in bio_keywords)
    
    def _pattern_applies_to_behavior(self, pattern: BiomechanicalTestPattern, behavior: TestableBehavior) -> bool:
        """Check if biomechanical pattern applies to behavior"""
        if "phase" in pattern.pattern_name and "phase" in behavior.description.lower():
            return True
        if "range" in pattern.pattern_name and "validate" in behavior.description.lower():
            return True
        if "kinematic" in pattern.pattern_name and "kinematic" in behavior.description.lower():
            return True
        return False


class TestCoverageAnalyzer:
    """Analyzes test coverage against requirements"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestCoverageAnalyzer")
    
    def analyze_test_coverage(self, story: UserStory, scenarios: List[TestScenario]) -> TestCoverageReport:
        """Analyze test coverage for user story requirements"""
        
        # Extract requirement mappings
        analyzer = RequirementsAnalyzer()
        requirement_mappings = analyzer._extract_requirement_mappings(story)
        
        # Analyze coverage for each requirement
        for mapping in requirement_mappings:
            mapping.test_scenarios = self._find_scenarios_for_requirement(mapping, scenarios)
            mapping.coverage_level = self._assess_coverage_level(mapping, scenarios)
        
        # Calculate overall coverage metrics
        total_requirements = len(requirement_mappings)
        complete_coverage = [m for m in requirement_mappings if m.coverage_level == CoverageLevel.COMPLETE]
        partial_coverage = [m for m in requirement_mappings if m.coverage_level == CoverageLevel.PARTIAL]
        missing_coverage = [m for m in requirement_mappings if m.coverage_level == CoverageLevel.MISSING]
        
        covered_requirements = len(complete_coverage) + (len(partial_coverage) * 0.5)
        coverage_percentage = (covered_requirements / total_requirements * 100) if total_requirements > 0 else 0
        
        report = TestCoverageReport(
            story_id=story.story_id,
            total_requirements=total_requirements,
            covered_requirements=int(covered_requirements),
            coverage_percentage=coverage_percentage,
            complete_coverage=[m.requirement_text for m in complete_coverage],
            partial_coverage=[m.requirement_text for m in partial_coverage],
            missing_coverage=[m.requirement_text for m in missing_coverage],
            requirement_mappings=requirement_mappings
        )
        
        self.logger.info(f"Coverage analysis for {story.story_id}: {coverage_percentage:.1f}% coverage")
        return report
    
    def _find_scenarios_for_requirement(self, requirement: RequirementMapping, scenarios: List[TestScenario]) -> List[str]:
        """Find test scenarios that cover a specific requirement"""
        covering_scenarios = []
        
        # Extract keywords from requirement
        req_keywords = self._extract_keywords(requirement.requirement_text)
        
        for scenario in scenarios:
            # Check if scenario covers this requirement
            scenario_keywords = self._extract_keywords(scenario.behavior.description)
            
            # Calculate keyword overlap
            overlap = len(set(req_keywords) & set(scenario_keywords))
            if overlap > 0:
                covering_scenarios.append(scenario.name)
        
        return covering_scenarios
    
    def _assess_coverage_level(self, requirement: RequirementMapping, scenarios: List[TestScenario]) -> CoverageLevel:
        """Assess coverage level for a requirement"""
        if not requirement.test_scenarios:
            return CoverageLevel.MISSING
        
        # Count scenario types covering this requirement
        scenario_types = set()
        for scenario_name in requirement.test_scenarios:
            scenario = next((s for s in scenarios if s.name == scenario_name), None)
            if scenario:
                scenario_types.add(scenario.scenario_type)
        
        # Assess completeness based on scenario type diversity
        if len(scenario_types) >= 3:  # Happy path, edge case, and error scenarios
            return CoverageLevel.COMPLETE
        elif len(scenario_types) >= 1:
            return CoverageLevel.PARTIAL
        else:
            return CoverageLevel.MISSING
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords


class RequirementsToTestsPipeline:
    """Main pipeline for converting requirements to comprehensive test suites"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RequirementsToTestsPipeline")
        self.analyzer = RequirementsAnalyzer()
        self.behavior_extractor = BehaviorExtractor()
        self.scenario_builder = TestScenarioBuilder()
        self.coverage_analyzer = TestCoverageAnalyzer()
    
    def process_user_story(self, story: UserStory) -> Dict[str, Any]:
        """Process a single user story through the complete pipeline"""
        self.logger.info(f"Processing user story {story.story_id} through requirements-to-tests pipeline")
        
        # Step 1: Analyze testability
        testability_analysis = self.analyzer.analyze_user_story_testability(story)
        
        # Step 2: Extract testable behaviors
        behaviors = self.behavior_extractor.extract_comprehensive_behaviors(story)
        
        # Step 3: Build comprehensive test scenarios
        scenarios = self.scenario_builder.build_comprehensive_scenarios(behaviors, story)
        
        # Step 4: Analyze test coverage
        coverage_report = self.coverage_analyzer.analyze_test_coverage(story, scenarios)
        
        # Compile results
        results = {
            "story_id": story.story_id,
            "testability_analysis": testability_analysis,
            "extracted_behaviors": behaviors,
            "test_scenarios": scenarios,
            "coverage_report": coverage_report,
            "pipeline_metrics": {
                "behaviors_extracted": len(behaviors),
                "scenarios_generated": len(scenarios),
                "coverage_percentage": coverage_report.coverage_percentage,
                "testability_score": testability_analysis["testability_score"]
            }
        }
        
        self.logger.info(f"Pipeline completed for {story.story_id}: "
                        f"{len(scenarios)} scenarios, {coverage_report.coverage_percentage:.1f}% coverage")
        
        return results
    
    def process_multiple_stories(self, stories: List[UserStory]) -> Dict[str, Any]:
        """Process multiple user stories and generate aggregate analysis"""
        all_results = {}
        aggregate_metrics = {
            "total_stories": len(stories),
            "total_behaviors": 0,
            "total_scenarios": 0,
            "average_coverage": 0.0,
            "average_testability": 0.0,
            "coverage_distribution": {"complete": 0, "partial": 0, "missing": 0}
        }
        
        for story in stories:
            result = self.process_user_story(story)
            all_results[story.story_id] = result
            
            # Update aggregate metrics
            aggregate_metrics["total_behaviors"] += result["pipeline_metrics"]["behaviors_extracted"]
            aggregate_metrics["total_scenarios"] += result["pipeline_metrics"]["scenarios_generated"]
            aggregate_metrics["average_coverage"] += result["pipeline_metrics"]["coverage_percentage"]
            aggregate_metrics["average_testability"] += result["pipeline_metrics"]["testability_score"]
        
        # Calculate averages
        if stories:
            aggregate_metrics["average_coverage"] /= len(stories)
            aggregate_metrics["average_testability"] /= len(stories)
        
        # Analyze coverage distribution
        for result in all_results.values():
            coverage_report = result["coverage_report"]
            aggregate_metrics["coverage_distribution"]["complete"] += len(coverage_report.complete_coverage)
            aggregate_metrics["coverage_distribution"]["partial"] += len(coverage_report.partial_coverage)
            aggregate_metrics["coverage_distribution"]["missing"] += len(coverage_report.missing_coverage)
        
        return {
            "individual_results": all_results,
            "aggregate_metrics": aggregate_metrics,
            "pipeline_summary": self._generate_pipeline_summary(aggregate_metrics)
        }
    
    def _generate_pipeline_summary(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable pipeline summary"""
        summary = {
            "overall_assessment": self._assess_overall_quality(metrics),
            "coverage_assessment": self._assess_coverage_quality(metrics["average_coverage"]),
            "testability_assessment": self._assess_testability_quality(metrics["average_testability"]),
            "recommendations": self._generate_recommendations(metrics)
        }
        return summary
    
    def _assess_overall_quality(self, metrics: Dict[str, Any]) -> str:
        """Assess overall pipeline quality"""
        avg_coverage = metrics["average_coverage"]
        avg_testability = metrics["average_testability"]
        
        if avg_coverage >= 90 and avg_testability >= 80:
            return "Excellent - Requirements are highly testable with comprehensive coverage"
        elif avg_coverage >= 75 and avg_testability >= 60:
            return "Good - Requirements have solid testability with good coverage"
        elif avg_coverage >= 50 and avg_testability >= 40:
            return "Fair - Requirements need improvement for better testability"
        else:
            return "Poor - Requirements need significant improvement for effective testing"
    
    def _assess_coverage_quality(self, coverage: float) -> str:
        """Assess coverage quality"""
        if coverage >= 90:
            return "Excellent coverage - All requirements well-covered by tests"
        elif coverage >= 75:
            return "Good coverage - Most requirements covered with minor gaps"
        elif coverage >= 50:
            return "Fair coverage - Significant requirements covered but improvement needed"
        else:
            return "Poor coverage - Many requirements lack adequate test coverage"
    
    def _assess_testability_quality(self, testability: float) -> str:
        """Assess testability quality"""
        if testability >= 80:
            return "Highly testable - Requirements have clear, measurable criteria"
        elif testability >= 60:
            return "Moderately testable - Requirements mostly clear with some ambiguity"
        elif testability >= 40:
            return "Somewhat testable - Requirements need clarification for better testing"
        else:
            return "Poorly testable - Requirements lack clear, measurable criteria"
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> str:
        """Generate recommendations for improvement"""
        recommendations = []
        
        if metrics["average_coverage"] < 75:
            recommendations.append("Improve test scenario coverage by adding more edge cases and error scenarios")
        
        if metrics["average_testability"] < 60:
            recommendations.append("Enhance acceptance criteria with more specific, measurable requirements")
        
        if metrics["coverage_distribution"]["missing"] > metrics["coverage_distribution"]["complete"]:
            recommendations.append("Focus on creating tests for currently uncovered requirements")
        
        if not recommendations:
            recommendations.append("Requirements are well-structured for comprehensive testing")
        
        return "; ".join(recommendations)


if __name__ == "__main__":
    # Example usage
    pipeline = RequirementsToTestsPipeline()
    
    # Example user story
    example_story = UserStory(
        story_id="US-001",
        title="Efficient Dataset Conversion Workflow",
        as_a="Dataset Curator (Programmer)",
        i_want="to convert raw biomechanical datasets to standardized parquet format efficiently",
        so_that="I can contribute quality datasets without extensive biomechanical expertise",
        acceptance_criteria=[
            AcceptanceCriteria(
                criterion="Complete dataset conversion in ≤60 minutes for typical lab dataset",
                measurement="Processing time measurement",
                test_approach="Automated timing validation",
                success_threshold="≤60 minutes for 500-1000 trials"
            )
        ],
        performance_requirement="≤60 minutes for 500-1000 trials",
        interface_contract="conversion_generate_phase_dataset.py"
    )
    
    # Process story through pipeline
    result = pipeline.process_user_story(example_story)
    
    print(f"Pipeline Results for {example_story.story_id}:")
    print(f"- Behaviors extracted: {len(result['extracted_behaviors'])}")
    print(f"- Scenarios generated: {len(result['test_scenarios'])}")
    print(f"- Coverage: {result['coverage_report'].coverage_percentage:.1f}%")
    print(f"- Testability score: {result['testability_analysis']['testability_score']:.1f}")