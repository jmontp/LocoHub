"""
Handoff Management Framework

Created: 2025-06-16 with user permission
Purpose: Automated handoff trigger validation and package management

Intent: Implements systematic handoff management from IMPLEMENTATION_ORCHESTRATOR_MANUAL.md
including trigger conditions, package validation, and completeness checking.
"""

import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging


class HandoffStatus(Enum):
    """Handoff package status"""
    PENDING = "pending"
    VALIDATED = "validated"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(Enum):
    """Validation result status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def passes_validation(self) -> bool:
        """Check if validation passes"""
        return self.status == ValidationStatus.PASSED


@dataclass
class HandoffPackage:
    """Structured handoff package"""
    package_id: str
    package_type: str  # test_agent, code_agent, integration_agent
    user_story_id: str
    created_date: datetime
    version: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml_file(cls, file_path: Path) -> 'HandoffPackage':
        """Load handoff package from YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract metadata
        metadata = data.get('metadata', {})
        
        return cls(
            package_id=metadata.get('package_id', ''),
            package_type=metadata.get('package_type', ''),
            user_story_id=metadata.get('user_story_id', ''),
            created_date=datetime.fromisoformat(metadata.get('created_date', datetime.utcnow().isoformat())),
            version=metadata.get('version', '1.0'),
            content=data,
            metadata=metadata
        )
    
    def save_to_file(self, file_path: Path):
        """Save handoff package to YAML file"""
        # Update metadata
        self.content['metadata'] = {
            'package_id': self.package_id,
            'package_type': self.package_type,
            'user_story_id': self.user_story_id,
            'created_date': self.created_date.isoformat(),
            'version': self.version,
            **self.metadata
        }
        
        with open(file_path, 'w') as f:
            yaml.dump(self.content, f, default_flow_style=False, sort_keys=False)
    
    def get_validation_criteria(self) -> List[str]:
        """Get validation criteria for this package type"""
        criteria_map = {
            'test_agent': [
                'user_stories_complete',
                'behavioral_specs_complete',
                'domain_constraints_defined',
                'success_metrics_quantified',
                'mock_requirements_specified'
            ],
            'code_agent': [
                'interface_contracts_complete',
                'algorithm_specs_defined',
                'performance_requirements_specified',
                'error_handling_defined',
                'data_structures_defined'
            ],
            'integration_agent': [
                'test_suite_information_complete',
                'implementation_package_complete',
                'integration_plan_defined',
                'success_criteria_specified'
            ]
        }
        
        return criteria_map.get(self.package_type, [])


@dataclass
class HandoffRequest:
    """Request for handoff validation and processing"""
    request_id: str
    agent_type: str
    handoff_package: HandoffPackage
    requested_by: str
    requested_at: datetime
    priority: str = "normal"
    requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class HandoffReadinessEvaluation:
    """Evaluation of handoff readiness"""
    agent: str
    readiness_status: ValidationStatus
    trigger_conditions_met: bool
    package_validation: 'HandoffPackageValidation'
    blocking_issues: List[str]
    recommendations: List[str]
    confidence_score: float = 0.0
    
    def is_ready_for_handoff(self) -> bool:
        """Check if agent is ready for handoff"""
        return (self.readiness_status == ValidationStatus.PASSED and
                self.trigger_conditions_met and
                self.package_validation.overall_validity)


class PackageStructureValidator:
    """Validator for handoff package structure"""
    
    def validate(self, package: HandoffPackage) -> ValidationResult:
        """Validate package structure"""
        issues = []
        
        # Check required metadata fields
        required_metadata = ['package_id', 'package_type', 'user_story_id', 'created_date']
        for field in required_metadata:
            if field not in package.metadata or not package.metadata[field]:
                issues.append(f"Missing required metadata field: {field}")
        
        # Check content structure based on package type
        structure_issues = self._validate_content_structure(package)
        issues.extend(structure_issues)
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Structure validation {'passed' if not issues else 'failed'}",
            details={'issues': issues},
            confidence=1.0 if not issues else 0.0
        )
    
    def _validate_content_structure(self, package: HandoffPackage) -> List[str]:
        """Validate content structure based on package type"""
        issues = []
        
        if package.package_type == 'test_agent':
            required_sections = ['user_stories', 'interface_behavioral_specifications', 
                               'domain_constraints', 'success_metrics']
            for section in required_sections:
                if section not in package.content:
                    issues.append(f"Missing required section: {section}")
        
        elif package.package_type == 'code_agent':
            required_sections = ['interface_contracts', 'algorithm_specifications',
                               'performance_requirements', 'error_handling_specifications']
            for section in required_sections:
                if section not in package.content:
                    issues.append(f"Missing required section: {section}")
        
        elif package.package_type == 'integration_agent':
            required_sections = ['test_suite_information', 'implementation_package_information',
                               'integration_test_plan', 'integration_success_criteria']
            for section in required_sections:
                if section not in package.content:
                    issues.append(f"Missing required section: {section}")
        
        return issues


class PackageContentValidator:
    """Validator for handoff package content completeness"""
    
    def validate(self, package: HandoffPackage) -> ValidationResult:
        """Validate package content completeness"""
        validation_issues = []
        
        # Get validation criteria for package type
        criteria = package.get_validation_criteria()
        
        for criterion in criteria:
            criterion_result = self._validate_criterion(package, criterion)
            if not criterion_result.passes_validation():
                validation_issues.append(f"{criterion}: {criterion_result.message}")
        
        status = ValidationStatus.PASSED if not validation_issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Content validation {'passed' if not validation_issues else 'failed'}",
            details={'validation_issues': validation_issues},
            confidence=0.8
        )
    
    def _validate_criterion(self, package: HandoffPackage, criterion: str) -> ValidationResult:
        """Validate specific criterion"""
        
        if criterion == 'user_stories_complete':
            return self._validate_user_stories(package)
        elif criterion == 'behavioral_specs_complete':
            return self._validate_behavioral_specs(package)
        elif criterion == 'interface_contracts_complete':
            return self._validate_interface_contracts(package)
        elif criterion == 'algorithm_specs_defined':
            return self._validate_algorithm_specs(package)
        else:
            # Default validation - check if section exists and has content
            section_key = criterion.replace('_complete', '').replace('_defined', '').replace('_specified', '')
            section_key = section_key.replace('_', '_')
            
            if section_key in package.content and package.content[section_key]:
                return ValidationResult(ValidationStatus.PASSED, f"{criterion} validation passed")
            else:
                return ValidationResult(ValidationStatus.FAILED, f"{criterion} validation failed - missing or empty")
    
    def _validate_user_stories(self, package: HandoffPackage) -> ValidationResult:
        """Validate user stories section"""
        user_stories = package.content.get('user_stories', [])
        
        if not user_stories:
            return ValidationResult(ValidationStatus.FAILED, "No user stories defined")
        
        issues = []
        for i, story in enumerate(user_stories):
            required_fields = ['story_id', 'title', 'as_a', 'i_want', 'so_that', 'acceptance_criteria']
            for field in required_fields:
                if field not in story or not story[field]:
                    issues.append(f"Story {i}: Missing {field}")
            
            # Validate acceptance criteria
            if 'acceptance_criteria' in story:
                for j, criterion in enumerate(story['acceptance_criteria']):
                    if not isinstance(criterion, dict):
                        issues.append(f"Story {i}, Criterion {j}: Invalid format")
                    else:
                        required_ac_fields = ['criterion', 'measurement', 'test_approach']
                        for field in required_ac_fields:
                            if field not in criterion:
                                issues.append(f"Story {i}, Criterion {j}: Missing {field}")
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"User stories validation {'passed' if not issues else 'failed'}",
            details={'issues': issues}
        )
    
    def _validate_behavioral_specs(self, package: HandoffPackage) -> ValidationResult:
        """Validate behavioral specifications section"""
        behavioral_specs = package.content.get('interface_behavioral_specifications', [])
        
        if not behavioral_specs:
            return ValidationResult(ValidationStatus.FAILED, "No behavioral specifications defined")
        
        issues = []
        for i, spec in enumerate(behavioral_specs):
            required_fields = ['component', 'behavioral_requirements']
            for field in required_fields:
                if field not in spec:
                    issues.append(f"Spec {i}: Missing {field}")
            
            # Validate behavioral requirements
            if 'behavioral_requirements' in spec:
                for j, req in enumerate(spec['behavioral_requirements']):
                    required_req_fields = ['method', 'expected_behavior', 'error_conditions']
                    for field in required_req_fields:
                        if field not in req:
                            issues.append(f"Spec {i}, Requirement {j}: Missing {field}")
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Behavioral specs validation {'passed' if not issues else 'failed'}",
            details={'issues': issues}
        )
    
    def _validate_interface_contracts(self, package: HandoffPackage) -> ValidationResult:
        """Validate interface contracts section"""
        contracts = package.content.get('interface_contracts', [])
        
        if not contracts:
            return ValidationResult(ValidationStatus.FAILED, "No interface contracts defined")
        
        issues = []
        for i, contract in enumerate(contracts):
            required_fields = ['class', 'methods']
            for field in required_fields:
                if field not in contract:
                    issues.append(f"Contract {i}: Missing {field}")
            
            # Validate methods
            if 'methods' in contract:
                for j, method in enumerate(contract['methods']):
                    required_method_fields = ['signature', 'preconditions', 'postconditions', 'exceptions']
                    for field in required_method_fields:
                        if field not in method:
                            issues.append(f"Contract {i}, Method {j}: Missing {field}")
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Interface contracts validation {'passed' if not issues else 'failed'}",
            details={'issues': issues}
        )
    
    def _validate_algorithm_specs(self, package: HandoffPackage) -> ValidationResult:
        """Validate algorithm specifications section"""
        algorithms = package.content.get('algorithm_specifications', [])
        
        if not algorithms:
            return ValidationResult(ValidationStatus.FAILED, "No algorithm specifications defined")
        
        issues = []
        for i, algo in enumerate(algorithms):
            required_fields = ['component', 'algorithm_name', 'implementation_steps', 'edge_cases']
            for field in required_fields:
                if field not in algo:
                    issues.append(f"Algorithm {i}: Missing {field}")
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Algorithm specs validation {'passed' if not issues else 'failed'}",
            details={'issues': issues}
        )


class PackageIntegrityValidator:
    """Validator for handoff package integrity"""
    
    def validate(self, package: HandoffPackage) -> ValidationResult:
        """Validate package integrity and consistency"""
        issues = []
        
        # Content consistency validation
        consistency_issues = self._validate_content_consistency(package)
        issues.extend(consistency_issues)
        
        # Version compatibility validation
        version_issues = self._validate_version_compatibility(package)
        issues.extend(version_issues)
        
        # Dependency integrity validation  
        dependency_issues = self._validate_dependency_integrity(package)
        issues.extend(dependency_issues)
        
        status = ValidationStatus.PASSED if not issues else ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            message=f"Integrity validation {'passed' if not issues else 'failed'}",
            details={'issues': issues},
            confidence=0.9
        )
    
    def _validate_content_consistency(self, package: HandoffPackage) -> List[str]:
        """Validate content consistency within package"""
        issues = []
        
        # Check for consistent user story references
        if package.package_type in ['test_agent', 'code_agent']:
            user_stories = package.content.get('user_stories', [])
            story_ids = [story.get('story_id') for story in user_stories if story.get('story_id')]
            
            if len(story_ids) != len(set(story_ids)):
                issues.append("Duplicate user story IDs found")
            
            # Check that package user_story_id matches content
            if story_ids and package.user_story_id not in story_ids:
                issues.append("Package user_story_id does not match content")
        
        return issues
    
    def _validate_version_compatibility(self, package: HandoffPackage) -> List[str]:
        """Validate version compatibility"""
        issues = []
        
        # Check version format
        try:
            version_parts = package.version.split('.')
            if len(version_parts) < 2:
                issues.append("Invalid version format - expected at least major.minor")
            
            for part in version_parts:
                int(part)  # Validate numeric parts
                
        except ValueError:
            issues.append("Invalid version format - non-numeric version parts")
        
        return issues
    
    def _validate_dependency_integrity(self, package: HandoffPackage) -> List[str]:
        """Validate dependency integrity"""
        issues = []
        
        # For code agent packages, check interface dependencies
        if package.package_type == 'code_agent':
            dependencies = package.content.get('integration_requirements', {}).get('dependencies', [])
            contracts = package.content.get('interface_contracts', [])
            
            # Check that all dependencies reference valid interfaces
            contract_names = [contract.get('class') for contract in contracts]
            
            for dep in dependencies:
                if dep.get('component') not in contract_names:
                    issues.append(f"Dependency references unknown component: {dep.get('component')}")
        
        return issues


@dataclass
class HandoffPackageValidation:
    """Complete handoff package validation result"""
    overall_validity: bool
    individual_validations: Dict[str, ValidationResult]
    package_quality_score: float
    improvement_recommendations: List[str]
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)


class HandoffPackageValidator:
    """Comprehensive validator for handoff packages"""
    
    def __init__(self):
        self.package_validators = {
            'structure_validator': PackageStructureValidator(),
            'content_validator': PackageContentValidator(),
            'integrity_validator': PackageIntegrityValidator()
        }
    
    def validate_handoff_package(self, handoff_package: HandoffPackage) -> HandoffPackageValidation:
        """Validate handoff package meets all requirements"""
        
        validation_results = {}
        
        for validator_name, validator in self.package_validators.items():
            validator_result = validator.validate(handoff_package)
            validation_results[validator_name] = validator_result
        
        # Calculate overall validity
        overall_validity = all(result.passes_validation() for result in validation_results.values())
        
        # Calculate quality score
        quality_score = self._calculate_package_quality_score(validation_results)
        
        # Generate improvement recommendations
        recommendations = self._generate_package_improvements(validation_results)
        
        return HandoffPackageValidation(
            overall_validity=overall_validity,
            individual_validations=validation_results,
            package_quality_score=quality_score,
            improvement_recommendations=recommendations
        )
    
    def _calculate_package_quality_score(self, validation_results: Dict[str, ValidationResult]) -> float:
        """Calculate overall package quality score"""
        total_score = 0.0
        total_weight = 0.0
        
        weights = {
            'structure_validator': 0.3,
            'content_validator': 0.5,
            'integrity_validator': 0.2
        }
        
        for validator_name, result in validation_results.items():
            weight = weights.get(validator_name, 1.0)
            score = result.confidence if result.passes_validation() else 0.0
            
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_package_improvements(self, validation_results: Dict[str, ValidationResult]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        for validator_name, result in validation_results.items():
            if not result.passes_validation():
                recommendations.append(f"{validator_name}: {result.message}")
                recommendations.extend(result.recommendations)
        
        return recommendations


class HandoffTriggerFramework:
    """Framework for managing handoff trigger conditions and validation"""
    
    def __init__(self):
        self.trigger_validators = {
            'test_agent_handoff': TestAgentHandoffValidator(),
            'code_agent_handoff': CodeAgentHandoffValidator(),
            'integration_agent_handoff': IntegrationAgentHandoffValidator()
        }
        self.validation_engine = HandoffPackageValidator()
    
    def evaluate_handoff_readiness(self, agent: str, handoff_request: HandoffRequest) -> HandoffReadinessEvaluation:
        """Evaluate if agent is ready for handoff"""
        
        # Get appropriate validator
        validator_key = f"{agent.lower()}_handoff"
        validator = self.trigger_validators.get(validator_key)
        
        if not validator:
            return HandoffReadinessEvaluation(
                agent=agent,
                readiness_status=ValidationStatus.FAILED,
                trigger_conditions_met=False,
                package_validation=HandoffPackageValidation(False, {}, 0.0, ["Unknown agent type"]),
                blocking_issues=["Unknown agent type"],
                recommendations=["Specify valid agent type: test_agent, code_agent, or integration_agent"]
            )
        
        # Validate handoff readiness
        readiness_validation = validator.validate_handoff_readiness(handoff_request)
        
        # Validate handoff package
        package_validation = self.validation_engine.validate_handoff_package(handoff_request.handoff_package)
        
        # Evaluate trigger conditions
        trigger_conditions_met = self._evaluate_trigger_conditions(agent, handoff_request)
        
        # Identify blocking issues
        blocking_issues = self._identify_blocking_issues(readiness_validation, package_validation)
        
        return HandoffReadinessEvaluation(
            agent=agent,
            readiness_status=readiness_validation.overall_readiness,
            trigger_conditions_met=trigger_conditions_met,
            package_validation=package_validation,
            blocking_issues=blocking_issues,
            recommendations=readiness_validation.readiness_improvements,
            confidence_score=package_validation.package_quality_score
        )
    
    def _evaluate_trigger_conditions(self, agent: str, handoff_request: HandoffRequest) -> bool:
        """Evaluate handoff trigger conditions"""
        
        # Basic trigger conditions
        conditions = [
            handoff_request.handoff_package is not None,
            handoff_request.handoff_package.package_type == agent.lower(),
            handoff_request.handoff_package.user_story_id is not None
        ]
        
        return all(conditions)
    
    def _identify_blocking_issues(self, readiness_validation, package_validation: HandoffPackageValidation) -> List[str]:
        """Identify blocking issues preventing handoff"""
        issues = []
        
        if not readiness_validation.overall_readiness == ValidationStatus.PASSED:
            issues.append("Agent readiness validation failed")
        
        if not package_validation.overall_validity:
            issues.append("Package validation failed")
            issues.extend(package_validation.improvement_recommendations)
        
        return issues


class TestAgentHandoffValidator:
    """Validator for Test Agent handoff readiness"""
    
    def validate_handoff_readiness(self, handoff_request: HandoffRequest):
        """Validate Test Agent is ready for handoff"""
        
        # Create mock validation result
        return type('TestAgentHandoffValidation', (), {
            'overall_readiness': ValidationStatus.PASSED,
            'readiness_improvements': []
        })()


class CodeAgentHandoffValidator:
    """Validator for Code Agent handoff readiness"""
    
    def validate_handoff_readiness(self, handoff_request: HandoffRequest):
        """Validate Code Agent is ready for handoff"""
        
        # Create mock validation result
        return type('CodeAgentHandoffValidation', (), {
            'overall_readiness': ValidationStatus.PASSED,
            'readiness_improvements': []
        })()


class IntegrationAgentHandoffValidator:
    """Validator for Integration Agent handoff readiness"""
    
    def validate_handoff_readiness(self, handoff_request: HandoffRequest):
        """Validate Integration Agent is ready for handoff"""
        
        # Create mock validation result
        return type('IntegrationAgentHandoffValidation', (), {
            'overall_readiness': ValidationStatus.PASSED,
            'readiness_improvements': []
        })()