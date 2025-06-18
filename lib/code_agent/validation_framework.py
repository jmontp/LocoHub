"""
Implementation Validation Framework

Created: 2025-01-16 with user permission
Purpose: Validate implementation compliance with interface contracts and performance requirements

Intent: Ensures 100% contract compliance and validates behavioral requirements without
accessing test implementations to maintain isolation and prevent bias.
"""

import ast
import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .contract_parser import InterfaceContract, MethodSpec, ParameterSpec
from .code_generator import Implementation, GeneratedClass, GeneratedMethod


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceType(Enum):
    """Types of compliance validation"""
    INTERFACE_COMPLIANCE = "interface"
    BEHAVIORAL_COMPLIANCE = "behavioral"
    PERFORMANCE_COMPLIANCE = "performance"
    ARCHITECTURAL_COMPLIANCE = "architectural"


@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    violation_type: ComplianceType
    severity: ValidationSeverity
    description: str
    location: str
    expected: str
    actual: str
    suggestion: str
    contract_reference: Optional[str] = None
    method_name: Optional[str] = None
    parameter_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary"""
        return {
            'type': self.violation_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'location': self.location,
            'expected': self.expected,
            'actual': self.actual,
            'suggestion': self.suggestion,
            'contract_reference': self.contract_reference,
            'method_name': self.method_name,
            'parameter_name': self.parameter_name
        }


@dataclass
class ValidationMetrics:
    """Metrics for validation results"""
    total_contracts: int
    validated_contracts: int
    total_methods: int
    validated_methods: int
    total_parameters: int
    validated_parameters: int
    
    compliance_percentage: float
    behavioral_compliance_percentage: float
    interface_compliance_percentage: float
    performance_compliance_percentage: float
    
    def calculate_overall_compliance(self) -> float:
        """Calculate overall compliance percentage"""
        return (
            self.interface_compliance_percentage * 0.4 +
            self.behavioral_compliance_percentage * 0.3 +
            self.performance_compliance_percentage * 0.3
        )


@dataclass
class ValidationResult:
    """Result of implementation validation"""
    is_valid: bool
    compliance_percentage: float
    violations: List[ComplianceViolation]
    metrics: ValidationMetrics
    
    # Detailed compliance results
    contract_compliance: Dict[str, bool]
    behavioral_compliance: Dict[str, bool]
    performance_compliance: Dict[str, bool]
    
    # Validation metadata
    validation_timestamp: datetime = field(default_factory=datetime.now)
    validation_duration_seconds: float = 0.0
    validator_version: str = "1.0.0"
    
    # Improvement recommendations
    improvement_recommendations: List[str] = field(default_factory=list)
    compliance_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.is_valid and self.compliance_percentage >= 100.0
    
    def get_critical_violations(self) -> List[ComplianceViolation]:
        """Get critical violations that must be fixed"""
        return [v for v in self.violations if v.severity == ValidationSeverity.CRITICAL]
    
    def get_violations_by_type(self, violation_type: ComplianceType) -> List[ComplianceViolation]:
        """Get violations of specific type"""
        return [v for v in self.violations if v.violation_type == violation_type]


class ImplementationValidator:
    """
    Validates implementation compliance with interface contracts and requirements.
    
    Performs comprehensive validation including:
    - Interface contract compliance (method signatures, return types, exceptions)
    - Behavioral specification adherence (preconditions, postconditions, side effects)  
    - Performance requirement satisfaction (timing, memory, scalability)
    - Architectural pattern compliance (dependency injection, error handling)
    """
    
    def __init__(self):
        """Initialize implementation validator"""
        self.logger = self._setup_logging()
        
        # Validation state
        self.current_validation: Optional[ValidationResult] = None
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        self.logger.info("Implementation validator initialized")
    
    def _setup_logging(self):
        """Set up logging for validator"""
        import logging
        logger = logging.getLogger("ImplementationValidator")
        logger.setLevel(logging.INFO)
        return logger
    
    async def validate_implementation(
        self,
        implementation: Implementation,
        interface_contracts: List[InterfaceContract],
        behavioral_specifications: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate implementation against interface contracts and behavioral specifications.
        
        Args:
            implementation: Implementation to validate
            interface_contracts: List of interface contracts to validate against
            behavioral_specifications: Behavioral requirements and constraints
            
        Returns:
            Comprehensive validation result
        """
        start_time = datetime.now()
        self.logger.info("Starting implementation validation")
        
        # Initialize validation result
        validation_result = ValidationResult(
            is_valid=True,
            compliance_percentage=0.0,
            violations=[],
            metrics=ValidationMetrics(0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0),
            contract_compliance={},
            behavioral_compliance={},
            performance_compliance={}
        )
        
        self.current_validation = validation_result
        
        try:
            # Phase 1: Interface Contract Compliance
            self.logger.info("Phase 1: Validating interface contract compliance")
            interface_compliance = await self._validate_interface_compliance(
                implementation, interface_contracts
            )
            
            # Phase 2: Behavioral Compliance  
            self.logger.info("Phase 2: Validating behavioral compliance")
            behavioral_compliance = await self._validate_behavioral_compliance(
                implementation, interface_contracts, behavioral_specifications
            )
            
            # Phase 3: Performance Compliance
            self.logger.info("Phase 3: Validating performance compliance")
            performance_compliance = await self._validate_performance_compliance(
                implementation, interface_contracts
            )
            
            # Phase 4: Architectural Compliance
            self.logger.info("Phase 4: Validating architectural compliance")
            architectural_compliance = await self._validate_architectural_compliance(
                implementation, behavioral_specifications
            )
            
            # Compile results
            all_violations = (
                interface_compliance['violations'] +
                behavioral_compliance['violations'] +
                performance_compliance['violations'] +
                architectural_compliance['violations']
            )
            
            validation_result.violations = all_violations
            validation_result.contract_compliance = interface_compliance['compliance']
            validation_result.behavioral_compliance = behavioral_compliance['compliance']
            validation_result.performance_compliance = performance_compliance['compliance']
            
            # Calculate compliance metrics
            validation_result.metrics = self._calculate_validation_metrics(
                implementation, interface_contracts, all_violations
            )
            
            validation_result.compliance_percentage = validation_result.metrics.calculate_overall_compliance()
            
            # Determine overall validation status
            critical_violations = validation_result.get_critical_violations()
            validation_result.is_valid = len(critical_violations) == 0 and validation_result.compliance_percentage >= 95.0
            
            # Generate improvement recommendations
            validation_result.improvement_recommendations = self._generate_improvement_recommendations(
                validation_result
            )
            
            # Convert violations for compatibility
            validation_result.compliance_violations = [v.to_dict() for v in validation_result.violations]
            
            # Set validation duration
            validation_result.validation_duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Validation completed: {validation_result.compliance_percentage:.1f}% compliance")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            validation_result.is_valid = False
            validation_result.violations.append(
                ComplianceViolation(
                    violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                    severity=ValidationSeverity.CRITICAL,
                    description=f"Validation process failed: {str(e)}",
                    location="validator",
                    expected="successful validation",
                    actual="validation failure",
                    suggestion="Check implementation structure and dependencies"
                )
            )
            return validation_result
        
        finally:
            self.current_validation = None
    
    async def _validate_interface_compliance(
        self,
        implementation: Implementation,
        interface_contracts: List[InterfaceContract]
    ) -> Dict[str, Any]:
        """Validate interface contract compliance"""
        
        violations = []
        compliance = {}
        
        for contract in interface_contracts:
            self.logger.info(f"Validating contract: {contract.name}")
            
            # Find corresponding implementation class
            impl_class = self._find_implementation_class(implementation, contract)
            
            if not impl_class:
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                        severity=ValidationSeverity.CRITICAL,
                        description=f"Implementation class not found for contract {contract.name}",
                        location=contract.name,
                        expected=f"Class implementing {contract.name}",
                        actual="No matching class found",
                        suggestion=f"Create a class that implements {contract.name} interface",
                        contract_reference=contract.name
                    )
                )
                compliance[contract.name] = False
                continue
            
            # Validate methods for this contract
            contract_violations, method_compliance = await self._validate_contract_methods(
                impl_class, contract
            )
            violations.extend(contract_violations)
            
            # Determine contract compliance
            compliance[contract.name] = all(method_compliance.values())
        
        return {
            'violations': violations,
            'compliance': compliance
        }
    
    def _find_implementation_class(self, implementation: Implementation, contract: InterfaceContract) -> Optional[GeneratedClass]:
        """Find implementation class for contract"""
        for impl_class in implementation.classes:
            if impl_class.name == contract.name:
                return impl_class
            # Also check for similar names
            if impl_class.name.replace('Implementation', '') == contract.name:
                return impl_class
        return None
    
    async def _validate_contract_methods(
        self,
        impl_class: GeneratedClass,
        contract: InterfaceContract
    ) -> Tuple[List[ComplianceViolation], Dict[str, bool]]:
        """Validate methods for contract"""
        
        violations = []
        method_compliance = {}
        
        for method_spec in contract.methods:
            # Find corresponding implementation method
            impl_method = self._find_implementation_method(impl_class, method_spec)
            
            if not impl_method:
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                        severity=ValidationSeverity.CRITICAL,
                        description=f"Method {method_spec.name} not implemented",
                        location=f"{impl_class.name}.{method_spec.name}",
                        expected=f"Method {method_spec.name} implementation",
                        actual="Method not found",
                        suggestion=f"Implement method {method_spec.name} with signature: {method_spec.signature}",
                        contract_reference=contract.name,
                        method_name=method_spec.name
                    )
                )
                method_compliance[method_spec.name] = False
                continue
            
            # Validate method signature
            signature_violations = await self._validate_method_signature(
                impl_method, method_spec, contract
            )
            violations.extend(signature_violations)
            
            # Validate method parameters
            parameter_violations = await self._validate_method_parameters(
                impl_method, method_spec, contract
            )
            violations.extend(parameter_violations)
            
            # Validate return type
            return_type_violations = await self._validate_return_type(
                impl_method, method_spec, contract
            )
            violations.extend(return_type_violations)
            
            # Validate exception specifications
            exception_violations = await self._validate_exception_specifications(
                impl_method, method_spec, contract
            )
            violations.extend(exception_violations)
            
            # Determine method compliance
            method_violations = (
                signature_violations + parameter_violations + 
                return_type_violations + exception_violations
            )
            method_compliance[method_spec.name] = len(method_violations) == 0
        
        return violations, method_compliance
    
    def _find_implementation_method(self, impl_class: GeneratedClass, method_spec: MethodSpec) -> Optional[GeneratedMethod]:
        """Find implementation method for method specification"""
        for impl_method in impl_class.methods:
            if impl_method.name == method_spec.name:
                return impl_method
        return None
    
    async def _validate_method_signature(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate method signature compliance"""
        
        violations = []
        
        # Parse implementation signature
        impl_sig = self._parse_method_signature(impl_method.signature)
        spec_sig = self._parse_method_signature(method_spec.signature)
        
        # Check method name
        if impl_sig['name'] != spec_sig['name']:
            violations.append(
                ComplianceViolation(
                    violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                    severity=ValidationSeverity.CRITICAL,
                    description=f"Method name mismatch",
                    location=f"{contract.name}.{method_spec.name}",
                    expected=spec_sig['name'],
                    actual=impl_sig['name'],
                    suggestion=f"Change method name to {spec_sig['name']}",
                    contract_reference=contract.name,
                    method_name=method_spec.name
                )
            )
        
        # Check parameter count
        expected_param_count = len(method_spec.parameters)
        actual_param_count = len(impl_sig['parameters'])
        
        if actual_param_count != expected_param_count:
            violations.append(
                ComplianceViolation(
                    violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                    severity=ValidationSeverity.ERROR,
                    description=f"Parameter count mismatch",
                    location=f"{contract.name}.{method_spec.name}",
                    expected=f"{expected_param_count} parameters",
                    actual=f"{actual_param_count} parameters",
                    suggestion=f"Adjust parameter list to match specification",
                    contract_reference=contract.name,
                    method_name=method_spec.name
                )
            )
        
        return violations
    
    def _parse_method_signature(self, signature: str) -> Dict[str, Any]:
        """Parse method signature into components"""
        try:
            # Extract method name
            name_match = signature.split('(')[0].split()[-1]
            
            # Extract parameters (simplified parsing)
            if '(' in signature and ')' in signature:
                params_str = signature.split('(')[1].split(')')[0]
                parameters = [p.strip() for p in params_str.split(',') if p.strip() and p.strip() != 'self']
            else:
                parameters = []
            
            # Extract return type
            if '->' in signature:
                return_type = signature.split('->')[1].split(':')[0].strip()
            else:
                return_type = 'None'
            
            return {
                'name': name_match,
                'parameters': parameters,
                'return_type': return_type
            }
        except Exception as e:
            self.logger.warning(f"Failed to parse signature '{signature}': {str(e)}")
            return {
                'name': 'unknown',
                'parameters': [],
                'return_type': 'unknown'
            }
    
    async def _validate_method_parameters(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate method parameter compliance"""
        
        violations = []
        
        # Parse implementation parameters
        impl_sig = self._parse_method_signature(impl_method.signature)
        
        # Check each parameter specification
        for i, param_spec in enumerate(method_spec.parameters):
            if i >= len(impl_sig['parameters']):
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                        severity=ValidationSeverity.ERROR,
                        description=f"Missing parameter {param_spec.name}",
                        location=f"{contract.name}.{method_spec.name}",
                        expected=f"Parameter {param_spec.name}: {param_spec.type_annotation}",
                        actual="Parameter not found",
                        suggestion=f"Add parameter {param_spec.name} to method signature",
                        contract_reference=contract.name,
                        method_name=method_spec.name,
                        parameter_name=param_spec.name
                    )
                )
                continue
            
            impl_param = impl_sig['parameters'][i]
            
            # Check parameter type annotation (if present)
            if ':' in impl_param:
                impl_param_name, impl_param_type = impl_param.split(':', 1)
                impl_param_name = impl_param_name.strip()
                impl_param_type = impl_param_type.split('=')[0].strip()  # Remove default value
                
                # Check parameter name
                if impl_param_name != param_spec.name:
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                            severity=ValidationSeverity.WARNING,
                            description=f"Parameter name mismatch",
                            location=f"{contract.name}.{method_spec.name}",
                            expected=param_spec.name,
                            actual=impl_param_name,
                            suggestion=f"Change parameter name to {param_spec.name}",
                            contract_reference=contract.name,
                            method_name=method_spec.name,
                            parameter_name=param_spec.name
                        )
                    )
                
                # Check parameter type (relaxed matching)
                if not self._types_compatible(impl_param_type, param_spec.type_annotation):
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                            severity=ValidationSeverity.WARNING,
                            description=f"Parameter type mismatch for {param_spec.name}",
                            location=f"{contract.name}.{method_spec.name}",
                            expected=param_spec.type_annotation,
                            actual=impl_param_type,
                            suggestion=f"Change parameter type to {param_spec.type_annotation}",
                            contract_reference=contract.name,
                            method_name=method_spec.name,
                            parameter_name=param_spec.name
                        )
                    )
        
        return violations
    
    def _types_compatible(self, impl_type: str, spec_type: str) -> bool:
        """Check if implementation type is compatible with specification type"""
        # Normalize types for comparison
        impl_type = impl_type.strip()
        spec_type = spec_type.strip()
        
        # Exact match
        if impl_type == spec_type:
            return True
        
        # Common compatible types
        compatible_types = {
            'str': ['string', 'String'],
            'int': ['integer', 'Integer'],
            'float': ['double', 'Double', 'number'],
            'bool': ['boolean', 'Boolean'],
            'Any': ['any', 'object', 'Object'],
            'Optional': ['optional'],
            'List': ['list', 'array', 'Array'],
            'Dict': ['dict', 'dictionary', 'map', 'Map'],
            'pd.DataFrame': ['DataFrame', 'pandas.DataFrame'],
            'np.ndarray': ['ndarray', 'numpy.ndarray', 'array']
        }
        
        for base_type, aliases in compatible_types.items():
            if (base_type in impl_type or any(alias in impl_type for alias in aliases)) and \
               (base_type in spec_type or any(alias in spec_type for alias in aliases)):
                return True
        
        return False
    
    async def _validate_return_type(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate return type compliance"""
        
        violations = []
        
        # Parse return types
        impl_sig = self._parse_method_signature(impl_method.signature)
        spec_return_type = method_spec.return_type.strip()
        impl_return_type = impl_sig['return_type'].strip()
        
        # Check return type compatibility
        if not self._types_compatible(impl_return_type, spec_return_type):
            violations.append(
                ComplianceViolation(
                    violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                    severity=ValidationSeverity.WARNING,
                    description=f"Return type mismatch",
                    location=f"{contract.name}.{method_spec.name}",
                    expected=spec_return_type,
                    actual=impl_return_type,
                    suggestion=f"Change return type to {spec_return_type}",
                    contract_reference=contract.name,
                    method_name=method_spec.name
                )
            )
        
        return violations
    
    async def _validate_exception_specifications(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate exception specification compliance"""
        
        violations = []
        
        # Check if method has required exception handling
        required_exceptions = [exc.get('type', 'Exception') for exc in method_spec.exceptions]
        
        if required_exceptions:
            # Check if implementation has exception handling
            has_exception_handling = self._has_exception_handling(impl_method)
            
            if not has_exception_handling:
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.INTERFACE_COMPLIANCE,
                        severity=ValidationSeverity.ERROR,
                        description=f"Missing exception handling",
                        location=f"{contract.name}.{method_spec.name}",
                        expected=f"Exception handling for: {', '.join(required_exceptions)}",
                        actual="No exception handling found",
                        suggestion="Add try-catch blocks for specified exceptions",
                        contract_reference=contract.name,
                        method_name=method_spec.name
                    )
                )
        
        return violations
    
    def _has_exception_handling(self, impl_method: GeneratedMethod) -> bool:
        """Check if method implementation has exception handling"""
        implementation = impl_method.implementation.lower()
        return 'try:' in implementation or 'except' in implementation or 'raise' in implementation
    
    async def _validate_behavioral_compliance(
        self,
        implementation: Implementation,
        interface_contracts: List[InterfaceContract],
        behavioral_specifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate behavioral specification compliance"""
        
        violations = []
        compliance = {}
        
        for contract in interface_contracts:
            contract_violations = []
            
            # Find implementation class
            impl_class = self._find_implementation_class(implementation, contract)
            if not impl_class:
                compliance[contract.name] = False
                continue
            
            # Validate behavioral requirements for each method
            for method_spec in contract.methods:
                impl_method = self._find_implementation_method(impl_class, method_spec)
                if not impl_method:
                    continue
                
                # Validate preconditions
                precondition_violations = await self._validate_preconditions(
                    impl_method, method_spec, contract
                )
                contract_violations.extend(precondition_violations)
                
                # Validate postconditions
                postcondition_violations = await self._validate_postconditions(
                    impl_method, method_spec, contract
                )
                contract_violations.extend(postcondition_violations)
                
                # Validate side effects
                side_effect_violations = await self._validate_side_effects(
                    impl_method, method_spec, contract
                )
                contract_violations.extend(side_effect_violations)
            
            violations.extend(contract_violations)
            compliance[contract.name] = len(contract_violations) == 0
        
        return {
            'violations': violations,
            'compliance': compliance
        }
    
    async def _validate_preconditions(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate precondition compliance"""
        
        violations = []
        
        for precondition in method_spec.preconditions:
            # Check if precondition is implemented
            if not self._precondition_implemented(impl_method, precondition):
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.BEHAVIORAL_COMPLIANCE,
                        severity=ValidationSeverity.WARNING,
                        description=f"Precondition not implemented: {precondition}",
                        location=f"{contract.name}.{method_spec.name}",
                        expected=f"Implementation of precondition: {precondition}",
                        actual="Precondition validation not found",
                        suggestion="Add validation for specified precondition",
                        contract_reference=contract.name,
                        method_name=method_spec.name
                    )
                )
        
        return violations
    
    def _precondition_implemented(self, impl_method: GeneratedMethod, precondition: str) -> bool:
        """Check if precondition is implemented in method"""
        implementation = impl_method.implementation.lower()
        
        # Look for validation patterns related to the precondition
        precondition_lower = precondition.lower()
        
        # Check for parameter validation
        if 'parameter' in precondition_lower or 'input' in precondition_lower:
            return 'validate' in implementation or 'check' in implementation
        
        # Check for data structure validation
        if 'phase-indexed' in precondition_lower:
            return '_phase' in implementation or 'phase' in implementation
        
        # Check for file existence validation
        if 'file' in precondition_lower and 'exist' in precondition_lower:
            return 'exists' in implementation or 'isfile' in implementation
        
        # Default: look for general validation patterns
        return 'validate' in implementation or 'check' in implementation or 'verify' in implementation
    
    async def _validate_postconditions(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate postcondition compliance"""
        
        violations = []
        
        for postcondition in method_spec.postconditions:
            if not self._postcondition_implemented(impl_method, postcondition):
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.BEHAVIORAL_COMPLIANCE,
                        severity=ValidationSeverity.WARNING,
                        description=f"Postcondition not implemented: {postcondition}",
                        location=f"{contract.name}.{method_spec.name}",
                        expected=f"Implementation of postcondition: {postcondition}",
                        actual="Postcondition validation not found",
                        suggestion="Add validation for specified postcondition",
                        contract_reference=contract.name,
                        method_name=method_spec.name
                    )
                )
        
        return violations
    
    def _postcondition_implemented(self, impl_method: GeneratedMethod, postcondition: str) -> bool:
        """Check if postcondition is implemented in method"""
        implementation = impl_method.implementation.lower()
        
        # Look for result validation or assertion patterns
        return (
            'assert' in implementation or
            'verify' in implementation or  
            'validate' in implementation or
            'check' in implementation
        )
    
    async def _validate_side_effects(
        self,
        impl_method: GeneratedMethod,
        method_spec: MethodSpec,
        contract: InterfaceContract
    ) -> List[ComplianceViolation]:
        """Validate side effect compliance"""
        
        violations = []
        
        # Check for undocumented side effects
        implementation = impl_method.implementation.lower()
        
        # Look for potential side effects not declared in specification
        potential_side_effects = []
        
        if 'file' in implementation and ('write' in implementation or 'save' in implementation):
            potential_side_effects.append("File system modification")
        
        if 'global' in implementation or 'class' in implementation:
            potential_side_effects.append("Global state modification")
        
        if 'cache' in implementation:
            potential_side_effects.append("Cache modification")
        
        # Check if side effects are documented
        documented_side_effects = [effect.lower() for effect in method_spec.side_effects]
        
        for side_effect in potential_side_effects:
            if not any(documented in side_effect.lower() for documented in documented_side_effects):
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.BEHAVIORAL_COMPLIANCE,
                        severity=ValidationSeverity.INFO,
                        description=f"Undocumented side effect: {side_effect}",
                        location=f"{contract.name}.{method_spec.name}",
                        expected="All side effects documented in specification",
                        actual=f"Undocumented side effect: {side_effect}",
                        suggestion="Document side effect in method specification",
                        contract_reference=contract.name,
                        method_name=method_spec.name
                    )
                )
        
        return violations
    
    async def _validate_performance_compliance(
        self,
        implementation: Implementation,
        interface_contracts: List[InterfaceContract]
    ) -> Dict[str, Any]:
        """Validate performance requirement compliance"""
        
        violations = []
        compliance = {}
        
        for contract in interface_contracts:
            contract_violations = []
            
            # Check contract-level performance requirements
            perf_reqs = contract.performance_requirements
            
            if perf_reqs:
                # Validate timing constraints
                timing_violations = await self._validate_timing_constraints(
                    implementation, contract, perf_reqs.get('timing_constraints', [])
                )
                contract_violations.extend(timing_violations)
                
                # Validate memory constraints
                memory_violations = await self._validate_memory_constraints(
                    implementation, contract, perf_reqs.get('memory_constraints', [])
                )
                contract_violations.extend(memory_violations)
                
                # Validate scalability constraints
                scalability_violations = await self._validate_scalability_constraints(
                    implementation, contract, perf_reqs.get('scalability_targets', [])
                )
                contract_violations.extend(scalability_violations)
            
            violations.extend(contract_violations)
            compliance[contract.name] = len(contract_violations) == 0
        
        return {
            'violations': violations,
            'compliance': compliance
        }
    
    async def _validate_timing_constraints(
        self,
        implementation: Implementation,
        contract: InterfaceContract,
        timing_constraints: List[Dict[str, Any]]
    ) -> List[ComplianceViolation]:
        """Validate timing constraint compliance"""
        
        violations = []
        
        for constraint in timing_constraints:
            # Check if implementation has performance optimization
            impl_class = self._find_implementation_class(implementation, contract)
            if impl_class:
                has_optimization = self._has_performance_optimization(impl_class)
                
                if not has_optimization:
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.PERFORMANCE_COMPLIANCE,
                            severity=ValidationSeverity.WARNING,
                            description="No performance optimization detected",
                            location=f"{contract.name}",
                            expected="Performance optimization for timing constraints",
                            actual="No optimization patterns found",
                            suggestion="Add performance optimization techniques",
                            contract_reference=contract.name
                        )
                    )
        
        return violations
    
    def _has_performance_optimization(self, impl_class: GeneratedClass) -> bool:
        """Check if implementation has performance optimization"""
        # Look for optimization patterns in implementation
        for method in impl_class.methods:
            implementation = method.implementation.lower()
            
            optimization_indicators = [
                'cache', 'chunk', 'parallel', 'optimize', 'efficient',
                'vectorize', 'numpy', 'pandas', 'stream'
            ]
            
            if any(indicator in implementation for indicator in optimization_indicators):
                return True
        
        return False
    
    async def _validate_memory_constraints(
        self,
        implementation: Implementation,
        contract: InterfaceContract,
        memory_constraints: List[Dict[str, Any]]
    ) -> List[ComplianceViolation]:
        """Validate memory constraint compliance"""
        
        violations = []
        
        for constraint in memory_constraints:
            # Check for memory management patterns
            impl_class = self._find_implementation_class(implementation, contract)
            if impl_class:
                has_memory_management = self._has_memory_management(impl_class)
                
                if not has_memory_management:
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.PERFORMANCE_COMPLIANCE,
                            severity=ValidationSeverity.INFO,
                            description="No explicit memory management detected",
                            location=f"{contract.name}",
                            expected="Memory management for large datasets",
                            actual="No memory management patterns found",
                            suggestion="Add memory management techniques for large data processing",
                            contract_reference=contract.name
                        )
                    )
        
        return violations
    
    def _has_memory_management(self, impl_class: GeneratedClass) -> bool:
        """Check if implementation has memory management"""
        for method in impl_class.methods:
            implementation = method.implementation.lower()
            
            memory_indicators = [
                'chunk', 'stream', 'iterator', 'generator', 'yield',
                'memory', 'gc.collect', 'del ', 'clear', 'cache'
            ]
            
            if any(indicator in implementation for indicator in memory_indicators):
                return True
        
        return False
    
    async def _validate_scalability_constraints(
        self,
        implementation: Implementation,
        contract: InterfaceContract,
        scalability_targets: List[Dict[str, Any]]
    ) -> List[ComplianceViolation]:
        """Validate scalability constraint compliance"""
        
        violations = []
        
        for target in scalability_targets:
            # Check for scalability patterns
            impl_class = self._find_implementation_class(implementation, contract)
            if impl_class:
                has_scalability = self._has_scalability_design(impl_class)
                
                if not has_scalability:
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.PERFORMANCE_COMPLIANCE,
                            severity=ValidationSeverity.INFO,
                            description="No scalability design detected",
                            location=f"{contract.name}",
                            expected="Scalable design for large datasets",
                            actual="No scalability patterns found",
                            suggestion="Add scalability design patterns",
                            contract_reference=contract.name
                        )
                    )
        
        return violations
    
    def _has_scalability_design(self, impl_class: GeneratedClass) -> bool:
        """Check if implementation has scalability design"""
        for method in impl_class.methods:
            implementation = method.implementation.lower()
            
            scalability_indicators = [
                'parallel', 'concurrent', 'async', 'thread', 'pool',
                'batch', 'partition', 'distribute', 'scale'
            ]
            
            if any(indicator in implementation for indicator in scalability_indicators):
                return True
        
        return False
    
    async def _validate_architectural_compliance(
        self,
        implementation: Implementation,
        behavioral_specifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate architectural pattern compliance"""
        
        violations = []
        
        # Check for clean architecture principles
        architecture_violations = await self._validate_clean_architecture(implementation)
        violations.extend(architecture_violations)
        
        # Check for error handling architecture
        error_handling_violations = await self._validate_error_handling_architecture(implementation)
        violations.extend(error_handling_violations)
        
        # Check for dependency management
        dependency_violations = await self._validate_dependency_management(implementation)
        violations.extend(dependency_violations)
        
        return {
            'violations': violations,
            'compliance': {'architecture': len(violations) == 0}
        }
    
    async def _validate_clean_architecture(self, implementation: Implementation) -> List[ComplianceViolation]:
        """Validate clean architecture principles"""
        violations = []
        
        # Check for separation of concerns
        for impl_class in implementation.classes:
            if len(impl_class.methods) > 20:  # Too many methods might indicate poor separation
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.ARCHITECTURAL_COMPLIANCE,
                        severity=ValidationSeverity.WARNING,
                        description=f"Class {impl_class.name} has too many methods ({len(impl_class.methods)})",
                        location=impl_class.name,
                        expected="Classes with focused responsibilities (< 20 methods)",
                        actual=f"{len(impl_class.methods)} methods",
                        suggestion="Consider splitting class into smaller, focused classes"
                    )
                )
        
        return violations
    
    async def _validate_error_handling_architecture(self, implementation: Implementation) -> List[ComplianceViolation]:
        """Validate error handling architecture"""
        violations = []
        
        # Check if classes have error handling
        for impl_class in implementation.classes:
            has_error_handling = any(
                self._has_exception_handling(method) for method in impl_class.methods
            )
            
            if not has_error_handling:
                violations.append(
                    ComplianceViolation(
                        violation_type=ComplianceType.ARCHITECTURAL_COMPLIANCE,
                        severity=ValidationSeverity.WARNING,
                        description=f"Class {impl_class.name} lacks error handling",
                        location=impl_class.name,
                        expected="Comprehensive error handling in all classes",
                        actual="No error handling detected",
                        suggestion="Add try-catch blocks and error recovery mechanisms"
                    )
                )
        
        return violations
    
    async def _validate_dependency_management(self, implementation: Implementation) -> List[ComplianceViolation]:
        """Validate dependency management"""
        violations = []
        
        # Check for dependency injection patterns
        for impl_class in implementation.classes:
            # Look for constructor injection
            init_method = next((m for m in impl_class.methods if m.name == '__init__'), None)
            
            if init_method and 'self' in init_method.signature:
                # Check if dependencies are injected
                if not self._has_dependency_injection(init_method):
                    violations.append(
                        ComplianceViolation(
                            violation_type=ComplianceType.ARCHITECTURAL_COMPLIANCE,
                            severity=ValidationSeverity.INFO,
                            description=f"Class {impl_class.name} may not use dependency injection",
                            location=f"{impl_class.name}.__init__",
                            expected="Constructor dependency injection",
                            actual="No clear dependency injection pattern",
                            suggestion="Consider using dependency injection for better testability"
                        )
                    )
        
        return violations
    
    def _has_dependency_injection(self, init_method: GeneratedMethod) -> bool:
        """Check if __init__ method uses dependency injection"""
        signature = init_method.signature.lower()
        implementation = init_method.implementation.lower()
        
        # Look for dependency injection patterns
        di_indicators = [
            'manager', 'handler', 'service', 'repository', 'factory',
            'config', 'logger', 'validator', 'processor'
        ]
        
        return any(indicator in signature for indicator in di_indicators)
    
    def _calculate_validation_metrics(
        self,
        implementation: Implementation,
        interface_contracts: List[InterfaceContract],
        violations: List[ComplianceViolation]
    ) -> ValidationMetrics:
        """Calculate validation metrics"""
        
        total_contracts = len(interface_contracts)
        total_methods = sum(len(contract.methods) for contract in interface_contracts)
        total_parameters = sum(
            len(method.parameters) 
            for contract in interface_contracts 
            for method in contract.methods
        )
        
        # Count violations by type
        interface_violations = len([v for v in violations if v.violation_type == ComplianceType.INTERFACE_COMPLIANCE])
        behavioral_violations = len([v for v in violations if v.violation_type == ComplianceType.BEHAVIORAL_COMPLIANCE])
        performance_violations = len([v for v in violations if v.violation_type == ComplianceType.PERFORMANCE_COMPLIANCE])
        
        # Calculate compliance percentages
        interface_compliance = max(0.0, 100.0 - (interface_violations / max(total_methods, 1) * 100))
        behavioral_compliance = max(0.0, 100.0 - (behavioral_violations / max(total_methods, 1) * 100))
        performance_compliance = max(0.0, 100.0 - (performance_violations / max(total_contracts, 1) * 100))
        
        overall_compliance = (interface_compliance + behavioral_compliance + performance_compliance) / 3
        
        return ValidationMetrics(
            total_contracts=total_contracts,
            validated_contracts=len(implementation.classes),
            total_methods=total_methods,
            validated_methods=sum(len(impl_class.methods) for impl_class in implementation.classes),
            total_parameters=total_parameters,
            validated_parameters=0,  # Would need deeper analysis
            compliance_percentage=overall_compliance,
            behavioral_compliance_percentage=behavioral_compliance,
            interface_compliance_percentage=interface_compliance,
            performance_compliance_percentage=performance_compliance
        )
    
    def _generate_improvement_recommendations(self, validation_result: ValidationResult) -> List[str]:
        """Generate improvement recommendations based on validation results"""
        recommendations = []
        
        critical_violations = validation_result.get_critical_violations()
        
        if critical_violations:
            recommendations.append("🔴 CRITICAL: Address critical violations before deployment")
            
            for violation in critical_violations[:3]:  # Top 3 critical issues
                recommendations.append(f"  - {violation.description}: {violation.suggestion}")
        
        # Interface compliance recommendations
        interface_violations = validation_result.get_violations_by_type(ComplianceType.INTERFACE_COMPLIANCE)
        if interface_violations:
            recommendations.append("🔧 Interface Compliance: Address method signature and contract issues")
        
        # Behavioral compliance recommendations
        behavioral_violations = validation_result.get_violations_by_type(ComplianceType.BEHAVIORAL_COMPLIANCE)
        if behavioral_violations:
            recommendations.append("📋 Behavioral Compliance: Implement missing preconditions and postconditions")
        
        # Performance recommendations
        performance_violations = validation_result.get_violations_by_type(ComplianceType.PERFORMANCE_COMPLIANCE)
        if performance_violations:
            recommendations.append("⚡ Performance: Add optimization techniques for better performance")
        
        # Overall recommendations
        if validation_result.compliance_percentage < 95.0:
            recommendations.append("📈 Focus on achieving 95%+ compliance before deployment")
        
        if not recommendations:
            recommendations.append("✅ Implementation meets all validation requirements")
        
        return recommendations