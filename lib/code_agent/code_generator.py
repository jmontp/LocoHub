"""
Code Generator

Created: 2025-01-16 with user permission
Purpose: Generate implementation code from interface contracts and architecture designs

Intent: Creates clean, efficient, and compliant implementation code based on interface
contracts and behavioral specifications. Generates classes, methods, data structures,
and supporting code without test bias.
"""

import os
import re
import ast
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .contract_parser import InterfaceContract, MethodSpec, ParameterSpec, ParameterType


class GenerationStrategy(Enum):
    """Code generation strategies"""
    TEMPLATE_BASED = "template_based"
    AST_BASED = "ast_based"
    HYBRID = "hybrid"


class ArchitecturePattern(Enum):
    """Supported architecture patterns"""
    SIMPLE = "simple"
    LAYERED = "layered"
    DEPENDENCY_INJECTION = "dependency_injection"
    FACTORY = "factory"
    REPOSITORY = "repository"
    STRATEGY = "strategy"


@dataclass
class CodeTemplate:
    """Template for code generation"""
    name: str
    template: str
    variables: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class GeneratedMethod:
    """Generated method implementation"""
    name: str
    signature: str
    implementation: str
    docstring: str
    imports: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class GeneratedClass:
    """Generated class implementation"""
    name: str
    base_classes: List[str]
    methods: List[GeneratedMethod]
    class_variables: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    docstring: str = ""


@dataclass
class Implementation:
    """Complete implementation package"""
    classes: List[GeneratedClass]
    standalone_functions: List[GeneratedMethod]
    imports: List[str]
    generated_files: List[str] = field(default_factory=list)
    
    # Architecture information
    architecture_pattern: ArchitecturePattern = ArchitecturePattern.SIMPLE
    component_relationships: Dict[str, List[str]] = field(default_factory=dict)
    
    # Quality metrics
    lines_of_code: int = 0
    complexity_score: float = 0.0
    test_coverage_potential: float = 0.0
    
    # Metadata
    generation_timestamp: datetime = field(default_factory=datetime.now)
    generator_version: str = "1.0.0"


class CodeGenerator:
    """
    Generates implementation code from interface contracts and architecture designs.
    
    Supports multiple generation strategies and architecture patterns to create
    high-quality, maintainable code that satisfies interface contracts without
    test bias.
    """
    
    def __init__(self, strategy: GenerationStrategy = GenerationStrategy.HYBRID):
        """
        Initialize code generator.
        
        Args:
            strategy: Code generation strategy to use
        """
        self.strategy = strategy
        self.logger = self._setup_logging()
        
        # Load code templates
        self.templates = self._load_code_templates()
        
        # Generation state
        self.current_implementation: Optional[Implementation] = None
        self.generated_imports: set = set()
        
        self.logger.info(f"Code generator initialized with strategy: {strategy.value}")
    
    def _setup_logging(self):
        """Set up logging for code generator"""
        import logging
        logger = logging.getLogger("CodeGenerator")
        logger.setLevel(logging.INFO)
        return logger
    
    def _load_code_templates(self) -> Dict[str, CodeTemplate]:
        """Load code generation templates"""
        templates = {
            'class_template': CodeTemplate(
                name='class_template',
                template=self._get_class_template(),
                variables={'class_name': '', 'base_classes': [], 'methods': [], 'docstring': ''}
            ),
            'method_template': CodeTemplate(
                name='method_template',
                template=self._get_method_template(),
                variables={'method_name': '', 'parameters': [], 'return_type': '', 'implementation': ''}
            ),
            'init_method_template': CodeTemplate(
                name='init_method_template',
                template=self._get_init_method_template(),
                variables={'parameters': [], 'assignments': []}
            ),
            'validation_method_template': CodeTemplate(
                name='validation_method_template',
                template=self._get_validation_method_template(),
                variables={'validation_rules': []}
            ),
            'error_handling_template': CodeTemplate(
                name='error_handling_template',
                template=self._get_error_handling_template(),
                variables={'exception_type': '', 'error_message': '', 'recovery_action': ''}
            ),
            'performance_optimization_template': CodeTemplate(
                name='performance_optimization_template',
                template=self._get_performance_optimization_template(),
                variables={'optimization_type': '', 'implementation': ''}
            )
        }
        
        return templates
    
    def _get_class_template(self) -> str:
        """Get class template"""
        return '''class {class_name}{inheritance}:
    """
    {docstring}
    """
    
{class_variables}
    
    def __init__(self{init_parameters}):
        """
        Initialize {class_name}.
        
{init_parameter_docs}
        """
{init_implementation}
    
{methods}'''
    
    def _get_method_template(self) -> str:
        """Get method template"""
        return '''    def {method_name}(self{parameters}){return_annotation}:
        """
        {docstring}
        
{parameter_docs}
        
        Returns:
            {return_description}
            
{raises_docs}
        """
{implementation}'''
    
    def _get_init_method_template(self) -> str:
        """Get __init__ method template"""
        return '''        # Initialize dependencies
{dependency_assignments}
        
        # Initialize state
{state_initialization}
        
        # Validate configuration
{validation_calls}'''
    
    def _get_validation_method_template(self) -> str:
        """Get validation method template"""
        return '''        # Validate input parameters
{parameter_validation}
        
        # Validate business rules
{business_rule_validation}
        
        # Validate data integrity
{data_integrity_validation}'''
    
    def _get_error_handling_template(self) -> str:
        """Get error handling template"""
        return '''        try:
{primary_implementation}
        except {exception_type} as e:
            self.logger.error(f"{error_context}: {{str(e)}}")
{error_recovery}
            raise {custom_exception}(
                message="{error_message}",
                context="{error_context}",
                suggestion="{recovery_suggestion}"
            )'''
    
    def _get_performance_optimization_template(self) -> str:
        """Get performance optimization template"""
        return '''        # Performance optimization: {optimization_type}
        if {optimization_condition}:
{optimized_implementation}
        else:
{standard_implementation}'''
    
    async def generate_implementation(
        self,
        architecture_design: Dict[str, Any],
        interface_contracts: List[InterfaceContract],
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> Implementation:
        """
        Generate complete implementation from architecture design and contracts.
        
        Args:
            architecture_design: Architecture design specification
            interface_contracts: List of interface contracts to implement
            behavioral_specifications: Behavioral requirements and constraints
            performance_requirements: Performance requirements and optimizations
            
        Returns:
            Complete implementation package
        """
        self.logger.info("Starting implementation generation")
        
        # Initialize implementation
        implementation = Implementation(
            classes=[],
            standalone_functions=[],
            imports=[],
            architecture_pattern=self._determine_architecture_pattern(architecture_design)
        )
        
        self.current_implementation = implementation
        self.generated_imports.clear()
        
        # Generate components for each interface contract
        for contract in interface_contracts:
            self.logger.info(f"Generating implementation for contract: {contract.name}")
            
            # Generate class implementation
            generated_class = await self._generate_class_from_contract(
                contract, architecture_design, behavioral_specifications, performance_requirements
            )
            
            if generated_class:
                implementation.classes.append(generated_class)
        
        # Generate supporting components
        await self._generate_supporting_components(
            implementation, architecture_design, behavioral_specifications
        )
        
        # Apply architecture patterns
        await self._apply_architecture_patterns(
            implementation, architecture_design
        )
        
        # Optimize implementation
        await self._optimize_implementation(
            implementation, performance_requirements
        )
        
        # Finalize imports and metadata
        implementation.imports = list(self.generated_imports)
        implementation.lines_of_code = self._calculate_lines_of_code(implementation)
        implementation.complexity_score = self._calculate_complexity_score(implementation)
        
        self.logger.info(f"Implementation generation completed: {len(implementation.classes)} classes")
        
        return implementation
    
    def _determine_architecture_pattern(self, architecture_design: Dict[str, Any]) -> ArchitecturePattern:
        """Determine architecture pattern from design"""
        patterns = architecture_design.get('patterns', [])
        
        if 'layered' in patterns:
            return ArchitecturePattern.LAYERED
        elif 'dependency_injection' in patterns:
            return ArchitecturePattern.DEPENDENCY_INJECTION
        elif 'factory' in patterns:
            return ArchitecturePattern.FACTORY
        elif 'repository' in patterns:
            return ArchitecturePattern.REPOSITORY
        elif 'strategy' in patterns:
            return ArchitecturePattern.STRATEGY
        else:
            return ArchitecturePattern.SIMPLE
    
    async def _generate_class_from_contract(
        self,
        contract: InterfaceContract,
        architecture_design: Dict[str, Any],
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> Optional[GeneratedClass]:
        """Generate class implementation from interface contract"""
        
        try:
            # Determine class structure from architecture
            class_structure = self._determine_class_structure(contract, architecture_design)
            
            # Generate methods
            methods = []
            
            # Generate __init__ method
            init_method = await self._generate_init_method(
                contract, architecture_design, behavioral_specifications
            )
            if init_method:
                methods.append(init_method)
            
            # Generate interface methods
            for method_spec in contract.methods:
                generated_method = await self._generate_method_from_spec(
                    method_spec, contract, behavioral_specifications, performance_requirements
                )
                if generated_method:
                    methods.append(generated_method)
            
            # Generate supporting methods
            supporting_methods = await self._generate_supporting_methods(
                contract, behavioral_specifications, performance_requirements
            )
            methods.extend(supporting_methods)
            
            # Create class
            generated_class = GeneratedClass(
                name=contract.name,
                base_classes=self._determine_base_classes(contract, architecture_design),
                methods=methods,
                class_variables=self._generate_class_variables(contract),
                imports=self._determine_class_imports(contract),
                docstring=self._generate_class_docstring(contract)
            )
            
            return generated_class
            
        except Exception as e:
            self.logger.error(f"Error generating class for contract {contract.name}: {str(e)}")
            return None
    
    def _determine_class_structure(
        self, 
        contract: InterfaceContract, 
        architecture_design: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine class structure from contract and architecture"""
        
        # Find component design for this contract
        components = architecture_design.get('components', [])
        component_design = None
        
        for component in components:
            if component.get('name') == contract.name:
                component_design = component
                break
        
        if component_design:
            return component_design
        
        # Default simple structure
        return {
            'name': contract.name,
            'architecture_type': 'simple',
            'main_class': contract.name
        }
    
    async def _generate_init_method(
        self,
        contract: InterfaceContract,
        architecture_design: Dict[str, Any],
        behavioral_specifications: Dict[str, Any]
    ) -> GeneratedMethod:
        """Generate __init__ method for class"""
        
        # Determine dependencies from architecture design
        dependencies = self._determine_class_dependencies(contract, architecture_design)
        
        # Generate parameters
        parameters = self._generate_init_parameters(dependencies)
        
        # Generate parameter documentation
        parameter_docs = self._generate_parameter_docs(parameters)
        
        # Generate implementation
        implementation = self._generate_init_implementation(
            dependencies, behavioral_specifications
        )
        
        # Generate signature
        param_strs = [f"{param['name']}: {param['type']}" for param in parameters]
        if param_strs:
            signature = f"def __init__(self, {', '.join(param_strs)}):"
        else:
            signature = "def __init__(self):"
        
        # Generate docstring
        docstring = f"Initialize {contract.name} with required dependencies."
        if parameters:
            docstring += "\n\nArgs:\n"
            for param in parameters:
                docstring += f"    {param['name']}: {param['description']}\n"
        
        return GeneratedMethod(
            name="__init__",
            signature=signature,
            implementation=implementation,
            docstring=docstring
        )
    
    def _determine_class_dependencies(
        self, 
        contract: InterfaceContract, 
        architecture_design: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Determine class dependencies from architecture design"""
        dependencies = []
        
        # Standard dependencies based on contract analysis
        if contract.name == "PhaseValidator":
            dependencies.extend([
                {
                    'name': 'spec_manager',
                    'type': 'ValidationSpecManager',
                    'description': 'Specification manager for validation ranges'
                },
                {
                    'name': 'error_handler',
                    'type': 'ErrorHandler',
                    'description': 'Error handler for standardized error reporting'
                },
                {
                    'name': 'progress_reporter',
                    'type': 'Optional[ProgressReporter]',
                    'description': 'Progress reporter for operation tracking',
                    'default': 'None'
                }
            ])
        elif contract.name == "ValidationSpecManager":
            dependencies.extend([
                {
                    'name': 'config_manager',
                    'type': 'ConfigurationManager',
                    'description': 'Configuration manager for settings'
                },
                {
                    'name': 'error_handler',
                    'type': 'ErrorHandler',
                    'description': 'Error handler for standardized error reporting'
                },
                {
                    'name': 'progress_reporter',
                    'type': 'Optional[ProgressReporter]',
                    'description': 'Progress reporter for operation tracking',
                    'default': 'None'
                }
            ])
        
        # Add architecture-specific dependencies
        arch_patterns = architecture_design.get('patterns', [])
        if 'dependency_injection' in arch_patterns:
            # Add dependency injection container
            dependencies.append({
                'name': 'container',
                'type': 'DIContainer',
                'description': 'Dependency injection container'
            })
        
        return dependencies
    
    def _generate_init_parameters(self, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate __init__ method parameters from dependencies"""
        parameters = []
        
        for dep in dependencies:
            param = {
                'name': dep['name'],
                'type': dep['type'],
                'description': dep['description']
            }
            
            if 'default' in dep:
                param['default'] = dep['default']
            
            parameters.append(param)
        
        return parameters
    
    def _generate_parameter_docs(self, parameters: List[Dict[str, Any]]) -> str:
        """Generate parameter documentation"""
        if not parameters:
            return ""
        
        docs = []
        for param in parameters:
            doc_line = f"        {param['name']}: {param['description']}"
            docs.append(doc_line)
        
        return "\n".join(docs)
    
    def _generate_init_implementation(
        self,
        dependencies: List[Dict[str, Any]],
        behavioral_specifications: Dict[str, Any]
    ) -> str:
        """Generate __init__ method implementation"""
        
        lines = []
        
        # Add dependency assignments
        lines.append("        # Initialize dependencies")
        for dep in dependencies:
            lines.append(f"        self.{dep['name']} = {dep['name']}")
        
        lines.append("")
        
        # Add state initialization
        lines.append("        # Initialize state")
        lines.append("        self._cache = {}")
        lines.append("        self._is_initialized = False")
        
        lines.append("")
        
        # Add validation
        lines.append("        # Validate dependencies")
        lines.append("        self._validate_dependencies()")
        
        lines.append("")
        
        # Add initialization completion
        lines.append("        # Mark as initialized")
        lines.append("        self._is_initialized = True")
        
        return "\n".join(lines)
    
    async def _generate_method_from_spec(
        self,
        method_spec: MethodSpec,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> Optional[GeneratedMethod]:
        """Generate method implementation from method specification"""
        
        try:
            # Generate method signature
            signature = self._generate_method_signature(method_spec)
            
            # Generate method implementation
            implementation = await self._generate_method_implementation(
                method_spec, contract, behavioral_specifications, performance_requirements
            )
            
            # Generate docstring
            docstring = self._generate_method_docstring(method_spec)
            
            # Determine imports needed
            imports = self._determine_method_imports(method_spec)
            
            return GeneratedMethod(
                name=method_spec.name,
                signature=signature,
                implementation=implementation,
                docstring=docstring,
                imports=imports
            )
            
        except Exception as e:
            self.logger.error(f"Error generating method {method_spec.name}: {str(e)}")
            return None
    
    def _generate_method_signature(self, method_spec: MethodSpec) -> str:
        """Generate method signature from specification"""
        
        # Generate parameter strings
        param_strs = []
        for param in method_spec.parameters:
            param_str = f"{param.name}: {param.type_annotation}"
            if param.default_value is not None:
                param_str += f" = {param.default_value}"
            param_strs.append(param_str)
        
        # Construct signature
        if param_strs:
            signature = f"def {method_spec.name}(self, {', '.join(param_strs)})"
        else:
            signature = f"def {method_spec.name}(self)"
        
        # Add return type annotation
        if method_spec.return_type and method_spec.return_type != 'None':
            signature += f" -> {method_spec.return_type}"
        
        signature += ":"
        
        return signature
    
    async def _generate_method_implementation(
        self,
        method_spec: MethodSpec,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> str:
        """Generate method implementation from specification"""
        
        lines = []
        
        # Add parameter validation
        if method_spec.parameters:
            validation_lines = self._generate_parameter_validation(method_spec)
            lines.extend(validation_lines)
            lines.append("")
        
        # Add behavioral requirements implementation
        if method_spec.preconditions:
            precondition_lines = self._generate_precondition_checks(method_spec)
            lines.extend(precondition_lines)
            lines.append("")
        
        # Generate core implementation based on method purpose
        core_implementation = await self._generate_core_method_implementation(
            method_spec, contract, behavioral_specifications, performance_requirements
        )
        lines.extend(core_implementation)
        
        # Add postcondition checks
        if method_spec.postconditions:
            lines.append("")
            postcondition_lines = self._generate_postcondition_checks(method_spec)
            lines.extend(postcondition_lines)
        
        # Add error handling
        if method_spec.exceptions:
            wrapped_implementation = self._wrap_with_error_handling(lines, method_spec)
            return "\n".join(wrapped_implementation)
        
        return "\n".join(lines)
    
    def _generate_parameter_validation(self, method_spec: MethodSpec) -> List[str]:
        """Generate parameter validation code"""
        lines = []
        lines.append("        # Validate input parameters")
        
        for param in method_spec.parameters:
            if not param.is_optional:
                lines.append(f"        if {param.name} is None:")
                lines.append(f"            raise ValueError(f\"{param.name} cannot be None\")")
            
            # Add type-specific validation
            if param.type == ParameterType.STRING and param.constraints:
                for constraint in param.constraints:
                    if 'min_length' in constraint:
                        min_len = re.search(r'min_length[:\s]*(\d+)', constraint)
                        if min_len:
                            lines.append(f"        if len({param.name}) < {min_len.group(1)}:")
                            lines.append(f"            raise ValueError(f\"{param.name} too short\")")
            
            elif param.type == ParameterType.DATAFRAME:
                lines.append(f"        if not isinstance({param.name}, pd.DataFrame):")
                lines.append(f"            raise TypeError(f\"{param.name} must be a pandas DataFrame\")")
                lines.append(f"        if {param.name}.empty:")
                lines.append(f"            raise ValueError(f\"{param.name} cannot be empty\")")
        
        return lines
    
    def _generate_precondition_checks(self, method_spec: MethodSpec) -> List[str]:
        """Generate precondition check code"""
        lines = []
        lines.append("        # Validate preconditions")
        
        for precondition in method_spec.preconditions:
            # Generate specific checks based on precondition content
            if 'phase-indexed' in precondition.lower():
                lines.append("        if '_phase' not in str(file_path):")
                lines.append("            raise ValueError(\"Expected phase-indexed dataset\")")
            
            elif 'required columns' in precondition.lower():
                lines.append("        required_cols = ['subject', 'task', 'step']")
                lines.append("        missing_cols = [col for col in required_cols if col not in data.columns]")
                lines.append("        if missing_cols:")
                lines.append("            raise ValueError(f\"Missing required columns: {missing_cols}\")")
        
        return lines
    
    async def _generate_core_method_implementation(
        self,
        method_spec: MethodSpec,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> List[str]:
        """Generate core method implementation"""
        
        # Generate implementation based on method name and contract
        if method_spec.name == "validate_dataset":
            return await self._generate_validate_dataset_implementation(
                method_spec, contract, behavioral_specifications, performance_requirements
            )
        elif method_spec.name == "filter_valid_strides":
            return await self._generate_filter_valid_strides_implementation(
                method_spec, contract, behavioral_specifications
            )
        elif method_spec.name == "get_available_tasks":
            return await self._generate_get_available_tasks_implementation(method_spec)
        elif method_spec.name == "analyze_standard_spec_coverage":
            return await self._generate_analyze_coverage_implementation(method_spec)
        elif method_spec.name == "generate_validation_report":
            return await self._generate_report_generation_implementation(method_spec)
        else:
            return await self._generate_generic_method_implementation(
                method_spec, behavioral_specifications
            )
    
    async def _generate_validate_dataset_implementation(
        self,
        method_spec: MethodSpec,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> List[str]:
        """Generate implementation for validate_dataset method"""
        
        lines = []
        
        # Load dataset
        lines.append("        # Load and validate dataset structure")
        lines.append("        try:")
        lines.append("            if not os.path.exists(file_path):")
        lines.append("                raise FileNotFoundError(f\"Dataset file not found: {file_path}\")")
        lines.append("            ")
        lines.append("            # Load dataset using LocomotionData library")
        lines.append("            locomotion_data = LocomotionData(file_path)")
        lines.append("            data = locomotion_data.df")
        lines.append("        except Exception as e:")
        lines.append("            raise DataFormatError(f\"Failed to load dataset: {str(e)}\")")
        lines.append("")
        
        # Initialize result structure
        lines.append("        # Initialize validation result")
        lines.append("        validation_result = PhaseValidationResult(")
        lines.append("            file_path=file_path,")
        lines.append("            validation_passed=False,")
        lines.append("            stride_statistics=StrideStatistics(0, 0, 0, 0.0, {}, {}, {}),")
        lines.append("            coverage_analysis=CoverageAnalysis(0.0, {}, {}, {}, [], [], []),")
        lines.append("            validation_report_path='',")
        lines.append("            plot_paths=[],")
        lines.append("            gif_paths=[],")
        lines.append("            errors=[],")
        lines.append("            warnings=[],")
        lines.append("            processing_time=0.0,")
        lines.append("            validation_timestamp=datetime.now(),")
        lines.append("            metadata={},")
        lines.append("            input_parameters={'generate_plots': generate_plots, 'generate_gifs': generate_gifs},")
        lines.append("            validation_spec_version='1.0.0',")
        lines.append("            step_classifier_version='1.0.0',")
        lines.append("            stride_filter_result=None")
        lines.append("        )")
        lines.append("")
        
        # Perform stride-level filtering
        lines.append("        # Perform stride-level filtering")
        lines.append("        stride_filter_result = self.filter_valid_strides(data)")
        lines.append("        validation_result.stride_filter_result = stride_filter_result")
        lines.append("")
        
        # Update validation statistics
        lines.append("        # Update validation statistics")
        lines.append("        validation_result.stride_statistics = StrideStatistics(")
        lines.append("            total_count=stride_filter_result.total_strides,")
        lines.append("            valid_count=stride_filter_result.valid_strides,")
        lines.append("            invalid_count=stride_filter_result.invalid_strides,")
        lines.append("            pass_rate=stride_filter_result.pass_rate,")
        lines.append("            by_task=stride_filter_result.task_specific_pass_rates,")
        lines.append("            by_subject={},")
        lines.append("            quality_distribution={}")
        lines.append("        )")
        lines.append("")
        
        # Generate plots if requested
        lines.append("        # Generate validation plots if requested")
        lines.append("        if generate_plots:")
        lines.append("            try:")
        lines.append("                plot_paths = self._generate_validation_plots(")
        lines.append("                    locomotion_data, stride_filter_result, output_dir")
        lines.append("                )")
        lines.append("                validation_result.plot_paths = plot_paths")
        lines.append("            except Exception as e:")
        lines.append("                validation_result.warnings.append(")
        lines.append("                    ValidationError(f\"Plot generation failed: {str(e)}\", file_path)")
        lines.append("                )")
        lines.append("")
        
        # Generate GIFs if requested
        lines.append("        # Generate animated GIFs if requested")
        lines.append("        if generate_gifs:")
        lines.append("            try:")
        lines.append("                gif_paths = self._generate_validation_gifs(")
        lines.append("                    locomotion_data, stride_filter_result, output_dir")
        lines.append("                )")
        lines.append("                validation_result.gif_paths = gif_paths")
        lines.append("            except Exception as e:")
        lines.append("                validation_result.warnings.append(")
        lines.append("                    ValidationError(f\"GIF generation failed: {str(e)}\", file_path)")
        lines.append("                )")
        lines.append("")
        
        # Determine final validation status
        lines.append("        # Determine final validation status")
        lines.append("        # Dataset passes if it has valid structure AND at least some valid strides")
        lines.append("        has_valid_structure = len(validation_result.errors) == 0")
        lines.append("        has_valid_strides = stride_filter_result.valid_strides > 0")
        lines.append("        validation_result.validation_passed = has_valid_structure and has_valid_strides")
        lines.append("")
        
        # Return result
        lines.append("        return validation_result")
        
        # Add required imports
        self.generated_imports.update([
            'import os',
            'from datetime import datetime',
            'from lib.core.locomotion_analysis import LocomotionData',
            'from .data_structures import PhaseValidationResult, StrideStatistics, CoverageAnalysis',
            'from .exceptions import DataFormatError, ValidationError'
        ])
        
        return lines
    
    async def _generate_filter_valid_strides_implementation(
        self,
        method_spec: MethodSpec,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any]
    ) -> List[str]:
        """Generate implementation for filter_valid_strides method"""
        
        lines = []
        
        # Get available variables
        lines.append("        # Determine available variables for validation")
        lines.append("        if available_variables is None:")
        lines.append("            # Auto-detect available kinematic and kinetic variables")
        lines.append("            kinematic_vars = [var for var in self.KINEMATIC_VARIABLES if var in data.columns]")
        lines.append("            kinetic_vars = [var for var in self.KINETIC_VARIABLES if var in data.columns]")
        lines.append("            available_variables = kinematic_vars + kinetic_vars")
        lines.append("")
        
        # Initialize filtering result
        lines.append("        # Initialize filtering result")
        lines.append("        total_strides = len(data.groupby(['subject', 'task', 'step']))")
        lines.append("        valid_strides = 0")
        lines.append("        rejection_reasons = []")
        lines.append("        valid_stride_data = []")
        lines.append("")
        
        # Process each stride
        lines.append("        # Process each stride for validation")
        lines.append("        for (subject, task, step), stride_data in data.groupby(['subject', 'task', 'step']):")
        lines.append("            stride_valid = True")
        lines.append("            stride_rejections = []")
        lines.append("")
        
        # Validate stride structure
        lines.append("            # Validate stride structure (150 points)")
        lines.append("            if len(stride_data) != 150:")
        lines.append("                stride_rejections.append(StrideRejection(")
        lines.append("                    stride_id=f\"{subject}_{task}_{step}\",")
        lines.append("                    subject_id=subject,")
        lines.append("                    task=task,")
        lines.append("                    variable='structure',")
        lines.append("                    phase=0,")
        lines.append("                    value=len(stride_data),")
        lines.append("                    expected_min=150,")
        lines.append("                    expected_max=150,")
        lines.append("                    reason=f\"Invalid stride length: {len(stride_data)} (expected 150)\",")
        lines.append("                    violation_severity='critical',")
        lines.append("                    validation_rule_applied='phase_structure_validation',")
        lines.append("                    specification_source='standard_spec',")
        lines.append("                    detection_timestamp=datetime.now(),")
        lines.append("                    phase_percentage=0.0,")
        lines.append("                    variable_units='points',")
        lines.append("                    biomechanical_context='Phase-indexed data requires exactly 150 points per gait cycle',")
        lines.append("                    remediation_suggestion='Re-interpolate data to 150 points per cycle'")
        lines.append("                ))")
        lines.append("                stride_valid = False")
        lines.append("")
        
        # Validate at representative phases
        lines.append("            # Validate at representative phases (0%, 25%, 50%, 75%)")
        lines.append("            if stride_valid:")
        lines.append("                representative_phases = [0, 37, 75, 112]  # 0%, 25%, 50%, 75% of 150")
        lines.append("                ")
        lines.append("                for phase_idx in representative_phases:")
        lines.append("                    phase_percent = (phase_idx / 149) * 100")
        lines.append("                    ")
        lines.append("                    for variable in available_variables:")
        lines.append("                        if variable in stride_data.columns:")
        lines.append("                            value = stride_data[variable].iloc[phase_idx]")
        lines.append("                            ")
        lines.append("                            # Get validation range for this task/variable/phase")
        lines.append("                            validation_range = self._get_validation_range(task, variable, phase_percent)")
        lines.append("                            ")
        lines.append("                            if validation_range and not validation_range.contains(value):")
        lines.append("                                stride_rejections.append(StrideRejection(")
        lines.append("                                    stride_id=f\"{subject}_{task}_{step}\",")
        lines.append("                                    subject_id=subject,")
        lines.append("                                    task=task,")
        lines.append("                                    variable=variable,")
        lines.append("                                    phase=phase_idx,")
        lines.append("                                    value=value,")
        lines.append("                                    expected_min=validation_range.min_value,")
        lines.append("                                    expected_max=validation_range.max_value,")
        lines.append("                                    reason=f\"Value {value:.3f} outside expected range\",")
        lines.append("                                    violation_severity=validation_range.violation_severity(value),")
        lines.append("                                    validation_rule_applied=f\"{task}_{variable}_phase_{phase_percent}\",")
        lines.append("                                    specification_source='validation_expectations',")
        lines.append("                                    detection_timestamp=datetime.now(),")
        lines.append("                                    phase_percentage=phase_percent,")
        lines.append("                                    variable_units=self._get_variable_units(variable),")
        lines.append("                                    biomechanical_context=self._get_biomechanical_context(variable, task),")
        lines.append("                                    remediation_suggestion=self._get_remediation_suggestion(variable, value, validation_range)")
        lines.append("                                ))")
        lines.append("                                stride_valid = False")
        lines.append("")
        
        # Update results
        lines.append("            # Update results")
        lines.append("            if stride_valid:")
        lines.append("                valid_strides += 1")
        lines.append("                valid_stride_data.append(stride_data)")
        lines.append("            else:")
        lines.append("                rejection_reasons.extend(stride_rejections)")
        lines.append("")
        
        # Create filtered dataset
        lines.append("        # Create filtered dataset from valid strides")
        lines.append("        if valid_stride_data:")
        lines.append("            filtered_data = pd.concat(valid_stride_data, ignore_index=True)")
        lines.append("        else:")
        lines.append("            filtered_data = pd.DataFrame()  # Empty dataset if no valid strides")
        lines.append("")
        
        # Calculate statistics
        lines.append("        # Calculate filtering statistics")
        lines.append("        invalid_strides = total_strides - valid_strides")
        lines.append("        pass_rate = valid_strides / total_strides if total_strides > 0 else 0.0")
        lines.append("")
        
        # Create result object
        lines.append("        # Create filtering result")
        lines.append("        filtering_result = StrideFilterResult(")
        lines.append("            filtered_data=filtered_data,")
        lines.append("            total_strides=total_strides,")
        lines.append("            valid_strides=valid_strides,")
        lines.append("            invalid_strides=invalid_strides,")
        lines.append("            pass_rate=pass_rate,")
        lines.append("            rejection_reasons=rejection_reasons,")
        lines.append("            rejection_categories=self._categorize_rejections(rejection_reasons),")
        lines.append("            most_common_rejections=self._get_most_common_rejections(rejection_reasons),")
        lines.append("            coverage_info=self._calculate_coverage_info(filtered_data),")
        lines.append("            task_specific_pass_rates=self._calculate_task_pass_rates(data, filtered_data),")
        lines.append("            variable_specific_pass_rates=self._calculate_variable_pass_rates(rejection_reasons, available_variables),")
        lines.append("            phase_specific_pass_rates=self._calculate_phase_pass_rates(rejection_reasons),")
        lines.append("            filtering_timestamp=datetime.now(),")
        lines.append("            filtering_parameters={'available_variables': available_variables},")
        lines.append("            validation_spec_applied='standard_validation_expectations',")
        lines.append("            step_classifier_config=StepClassifierConfig([0, 25, 50, 75], 0.1, True, [], [], []),")
        lines.append("            data_quality_score=self._calculate_data_quality_score(pass_rate, rejection_reasons),")
        lines.append("            confidence_intervals={},")
        lines.append("            biomechanical_plausibility=self._calculate_biomechanical_plausibility(filtered_data),")
        lines.append("            audit_trail=[],")
        lines.append("            processing_stats=ProcessingStats(datetime.now(), 0.0, 0.0, 0)")
        lines.append("        )")
        lines.append("")
        
        lines.append("        return filtering_result")
        
        # Add required imports
        self.generated_imports.update([
            'import pandas as pd',
            'from datetime import datetime',
            'from .data_structures import StrideFilterResult, StrideRejection, StepClassifierConfig, ProcessingStats'
        ])
        
        return lines
    
    async def _generate_get_available_tasks_implementation(self, method_spec: MethodSpec) -> List[str]:
        """Generate implementation for get_available_tasks method"""
        
        lines = []
        
        lines.append("        # Get unique tasks from dataset")
        lines.append("        if 'task' not in data.columns:")
        lines.append("            raise ValueError(\"Dataset missing 'task' column\")")
        lines.append("")
        lines.append("        dataset_tasks = set(data['task'].unique())")
        lines.append("")
        lines.append("        # Filter to known standard tasks")
        lines.append("        from lib.core.feature_constants import TASK_DEFINITIONS")
        lines.append("        standard_tasks = set(TASK_DEFINITIONS.keys())")
        lines.append("")
        lines.append("        # Get intersection of dataset tasks and standard tasks")
        lines.append("        valid_tasks = dataset_tasks.intersection(standard_tasks)")
        lines.append("")
        lines.append("        # Log warnings for unknown tasks")
        lines.append("        unknown_tasks = dataset_tasks - standard_tasks")
        lines.append("        if unknown_tasks:")
        lines.append("            self.logger.warning(f\"Unknown tasks found: {sorted(list(unknown_tasks))}\")")
        lines.append("")
        lines.append("        return sorted(list(valid_tasks))")
        
        return lines
    
    async def _generate_analyze_coverage_implementation(self, method_spec: MethodSpec) -> List[str]:
        """Generate implementation for analyze_standard_spec_coverage method"""
        
        lines = []
        
        lines.append("        # Import standard variable definitions")
        lines.append("        from lib.core.feature_constants import get_feature_list")
        lines.append("")
        lines.append("        coverage_analysis = {}")
        lines.append("")
        lines.append("        # Analyze kinematic variable coverage")
        lines.append("        kinematic_variables = get_feature_list('kinematic')")
        lines.append("        kinematic_coverage = {}")
        lines.append("        for variable in kinematic_variables:")
        lines.append("            kinematic_coverage[variable] = variable in data.columns")
        lines.append("        coverage_analysis['kinematic'] = kinematic_coverage")
        lines.append("")
        lines.append("        # Analyze kinetic variable coverage")
        lines.append("        kinetic_variables = get_feature_list('kinetic')")
        lines.append("        kinetic_coverage = {}")
        lines.append("        for variable in kinetic_variables:")
        lines.append("            kinetic_coverage[variable] = variable in data.columns")
        lines.append("        coverage_analysis['kinetic'] = kinetic_coverage")
        lines.append("")
        lines.append("        return coverage_analysis")
        
        return lines
    
    async def _generate_report_generation_implementation(self, method_spec: MethodSpec) -> List[str]:
        """Generate implementation for generate_validation_report method"""
        
        lines = []
        
        lines.append("        # Create output directory if it doesn't exist")
        lines.append("        output_path = Path(output_path)")
        lines.append("        output_path.parent.mkdir(parents=True, exist_ok=True)")
        lines.append("")
        lines.append("        # Generate comprehensive validation report")
        lines.append("        with open(output_path, 'w') as f:")
        lines.append("            f.write(\"# Dataset Validation Report\\n\\n\")")
        lines.append("            f.write(f\"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\")")
        lines.append("            f.write(f\"**Dataset**: `{result.file_path}`\\n\\n\")")
        lines.append("")
        lines.append("            # Validation summary")
        lines.append("            f.write(\"## Validation Summary\\n\\n\")")
        lines.append("            f.write(f\"- **Validation Status**: {'✅ PASSED' if result.validation_passed else '❌ FAILED'}\\n\")")
        lines.append("            f.write(f\"- **Total Strides**: {result.stride_statistics.total_count}\\n\")")
        lines.append("            f.write(f\"- **Valid Strides**: {result.stride_statistics.valid_count}\\n\")")
        lines.append("            f.write(f\"- **Pass Rate**: {result.stride_statistics.pass_rate:.1%}\\n\")")
        lines.append("            f.write(f\"- **Processing Time**: {result.processing_time:.2f} seconds\\n\\n\")")
        lines.append("")
        lines.append("            # Stride filtering results")
        lines.append("            if result.stride_filter_result:")
        lines.append("                f.write(\"## Stride Filtering Results\\n\\n\")")
        lines.append("                f.write(f\"- **Rejection Rate**: {(1 - result.stride_filter_result.pass_rate):.1%}\\n\")")
        lines.append("                f.write(f\"- **Most Common Rejections**:\\n\")")
        lines.append("                for reason, count in result.stride_filter_result.most_common_rejections[:5]:")
        lines.append("                    f.write(f\"  - {reason}: {count} occurrences\\n\")")
        lines.append("                f.write(\"\\n\")")
        lines.append("")
        lines.append("            # Coverage analysis")
        lines.append("            f.write(\"## Coverage Analysis\\n\\n\")")
        lines.append("            f.write(f\"- **Overall Coverage**: {result.coverage_analysis.overall_coverage:.1%}\\n\")")
        lines.append("            f.write(f\"- **Variable Coverage**:\\n\")")
        lines.append("            for variable, coverage in result.coverage_analysis.variable_coverage.items():")
        lines.append("                f.write(f\"  - {variable}: {coverage:.1%}\\n\")")
        lines.append("            f.write(\"\\n\")")
        lines.append("")
        lines.append("            # Generated artifacts")
        lines.append("            if result.plot_paths:")
        lines.append("                f.write(\"## Generated Plots\\n\\n\")")
        lines.append("                for plot_path in result.plot_paths:")
        lines.append("                    plot_name = Path(plot_path).name")
        lines.append("                    f.write(f\"- ![{plot_name}]({plot_name})\\n\")")
        lines.append("                f.write(\"\\n\")")
        lines.append("")
        lines.append("            # Recommendations")
        lines.append("            f.write(\"## Recommendations\\n\\n\")")
        lines.append("            if result.validation_passed:")
        lines.append("                f.write(\"✅ Dataset appears to be high quality and ready for analysis.\\n\")")
        lines.append("            else:")
        lines.append("                f.write(\"⚠️ Dataset has validation issues that should be addressed:\\n\")")
        lines.append("                f.write(\"1. Review data collection protocols for high rejection rates\\n\")")
        lines.append("                f.write(\"2. Check sensor calibration and data quality\\n\")")
        lines.append("                f.write(\"3. Consider updating validation ranges if appropriate\\n\")")
        lines.append("")
        lines.append("        return ReportGenerationResult(")
        lines.append("            success=True,")
        lines.append("            report_path=str(output_path),")
        lines.append("            generation_time=datetime.now(),")
        lines.append("            file_size_mb=output_path.stat().st_size / (1024 * 1024)")
        lines.append("        )")
        
        # Add required imports
        self.generated_imports.update([
            'from pathlib import Path',
            'from datetime import datetime',
            'from .data_structures import ReportGenerationResult'
        ])
        
        return lines
    
    async def _generate_generic_method_implementation(
        self,
        method_spec: MethodSpec,
        behavioral_specifications: Dict[str, Any]
    ) -> List[str]:
        """Generate generic method implementation"""
        
        lines = []
        
        # Add basic implementation based on method name patterns
        if 'validate' in method_spec.name.lower():
            lines.append("        # Perform validation logic")
            lines.append("        validation_result = True")
            lines.append("        errors = []")
            lines.append("")
            lines.append("        # TODO: Implement specific validation logic")
            lines.append("        # Based on behavioral specifications and requirements")
            lines.append("")
            lines.append("        return validation_result, errors")
        
        elif 'generate' in method_spec.name.lower():
            lines.append("        # Generate requested output")
            lines.append("        result = {}")
            lines.append("")
            lines.append("        # TODO: Implement generation logic")
            lines.append("        # Based on method specifications and requirements")
            lines.append("")
            lines.append("        return result")
        
        elif 'calculate' in method_spec.name.lower() or 'compute' in method_spec.name.lower():
            lines.append("        # Perform calculations")
            lines.append("        result = 0.0")
            lines.append("")
            lines.append("        # TODO: Implement calculation logic")
            lines.append("        # Based on algorithm specifications")
            lines.append("")
            lines.append("        return result")
        
        else:
            lines.append("        # TODO: Implement method logic")
            lines.append("        # Based on interface contract and behavioral specifications")
            lines.append("        pass")
        
        return lines
    
    def _generate_postcondition_checks(self, method_spec: MethodSpec) -> List[str]:
        """Generate postcondition check code"""
        lines = []
        lines.append("        # Validate postconditions")
        
        for postcondition in method_spec.postconditions:
            # Generate specific checks based on postcondition content
            if 'return' in postcondition.lower() and 'not none' in postcondition.lower():
                lines.append("        if result is None:")
                lines.append("            raise RuntimeError(\"Method must return a valid result\")")
        
        return lines
    
    def _wrap_with_error_handling(self, implementation_lines: List[str], method_spec: MethodSpec) -> List[str]:
        """Wrap implementation with error handling"""
        lines = []
        
        # Add try block
        lines.append("        try:")
        
        # Indent implementation
        for line in implementation_lines:
            if line.strip():
                lines.append("    " + line)
            else:
                lines.append("")
        
        # Add exception handling
        for exception in method_spec.exceptions:
            exception_type = exception.get('type', 'Exception')
            exception_desc = exception.get('description', 'An error occurred')
            
            lines.append(f"        except {exception_type} as e:")
            lines.append(f"            self.error_handler.handle_error(e)")
            lines.append(f"            raise")
        
        return lines
    
    def _generate_method_docstring(self, method_spec: MethodSpec) -> str:
        """Generate method docstring from specification"""
        
        lines = []
        
        # Add description
        if method_spec.description:
            lines.append(method_spec.description)
            lines.append("")
        
        # Add parameters section
        if method_spec.parameters:
            lines.append("Args:")
            for param in method_spec.parameters:
                param_doc = f"    {param.name}: {param.description or 'Parameter description'}"
                if param.is_optional:
                    param_doc += f" (default: {param.default_value})"
                lines.append(param_doc)
            lines.append("")
        
        # Add returns section
        if method_spec.return_description:
            lines.append("Returns:")
            lines.append(f"    {method_spec.return_description}")
            lines.append("")
        
        # Add raises section
        if method_spec.exceptions:
            lines.append("Raises:")
            for exception in method_spec.exceptions:
                exc_type = exception.get('type', 'Exception')
                exc_desc = exception.get('description', 'Error description')
                lines.append(f"    {exc_type}: {exc_desc}")
            lines.append("")
        
        # Add behavioral requirements
        if method_spec.preconditions or method_spec.postconditions:
            lines.append("Requirements:")
            
            if method_spec.preconditions:
                lines.append("    Preconditions:")
                for condition in method_spec.preconditions:
                    lines.append(f"    - MUST {condition}")
            
            if method_spec.postconditions:
                lines.append("    Postconditions:")
                for condition in method_spec.postconditions:
                    lines.append(f"    - MUST {condition}")
        
        return "\n".join(lines)
    
    def _determine_method_imports(self, method_spec: MethodSpec) -> List[str]:
        """Determine imports needed for method"""
        imports = []
        
        # Check parameter types
        for param in method_spec.parameters:
            if param.type == ParameterType.DATAFRAME:
                imports.append('import pandas as pd')
            elif param.type == ParameterType.NUMPY_ARRAY:
                imports.append('import numpy as np')
        
        # Check return type
        if 'pd.DataFrame' in method_spec.return_type:
            imports.append('import pandas as pd')
        elif 'np.ndarray' in method_spec.return_type:
            imports.append('import numpy as np')
        
        return list(set(imports))
    
    async def _generate_supporting_methods(
        self,
        contract: InterfaceContract,
        behavioral_specifications: Dict[str, Any],
        performance_requirements: Dict[str, Any]
    ) -> List[GeneratedMethod]:
        """Generate supporting methods for class"""
        
        supporting_methods = []
        
        # Generate validation helper methods
        validation_method = self._generate_validation_helper_method(contract)
        if validation_method:
            supporting_methods.append(validation_method)
        
        # Generate dependency validation method
        dependency_validation_method = self._generate_dependency_validation_method(contract)
        if dependency_validation_method:
            supporting_methods.append(dependency_validation_method)
        
        # Generate caching methods if needed
        if any('cache' in str(spec).lower() for spec in [behavioral_specifications, performance_requirements]):
            cache_methods = self._generate_cache_methods(contract)
            supporting_methods.extend(cache_methods)
        
        # Generate logging methods
        logging_method = self._generate_logging_method(contract)
        if logging_method:
            supporting_methods.append(logging_method)
        
        return supporting_methods
    
    def _generate_validation_helper_method(self, contract: InterfaceContract) -> Optional[GeneratedMethod]:
        """Generate validation helper method"""
        
        lines = []
        lines.append("        \"\"\"Validate dependencies are properly initialized.\"\"\"")
        lines.append("        if not hasattr(self, 'spec_manager') or self.spec_manager is None:")
        lines.append("            raise ValueError(\"SpecificationManager dependency not initialized\")")
        lines.append("        ")
        lines.append("        if not hasattr(self, 'error_handler') or self.error_handler is None:")
        lines.append("            raise ValueError(\"ErrorHandler dependency not initialized\")")
        
        return GeneratedMethod(
            name="_validate_dependencies",
            signature="def _validate_dependencies(self):",
            implementation="\n".join(lines),
            docstring="Validate that all required dependencies are properly initialized."
        )
    
    def _generate_dependency_validation_method(self, contract: InterfaceContract) -> Optional[GeneratedMethod]:
        """Generate dependency validation method"""
        
        lines = []
        lines.append("        \"\"\"Get validation range for specific task, variable, and phase.\"\"\"")
        lines.append("        # Load validation specifications for task")
        lines.append("        if task in self._validation_ranges_cache:")
        lines.append("            task_ranges = self._validation_ranges_cache[task]")
        lines.append("        else:")
        lines.append("            task_ranges = self.spec_manager.load_validation_specs(task)")
        lines.append("            self._validation_ranges_cache[task] = task_ranges")
        lines.append("        ")
        lines.append("        # Get specific range for variable and phase")
        lines.append("        return task_ranges.get_range(task, variable, phase)")
        
        return GeneratedMethod(
            name="_get_validation_range",
            signature="def _get_validation_range(self, task: str, variable: str, phase: float) -> Optional[ValidationRange]:",
            implementation="\n".join(lines),
            docstring="Get validation range for specific task, variable, and phase."
        )
    
    def _generate_cache_methods(self, contract: InterfaceContract) -> List[GeneratedMethod]:
        """Generate caching methods"""
        methods = []
        
        # Cache initialization
        cache_init_lines = []
        cache_init_lines.append("        \"\"\"Initialize caching system.\"\"\"")
        cache_init_lines.append("        self._validation_ranges_cache = {}")
        cache_init_lines.append("        self._data_quality_cache = {}")
        cache_init_lines.append("        self._cache_max_size = 100")
        
        methods.append(GeneratedMethod(
            name="_initialize_cache",
            signature="def _initialize_cache(self):",
            implementation="\n".join(cache_init_lines),
            docstring="Initialize caching system for performance optimization."
        ))
        
        # Cache cleanup
        cache_cleanup_lines = []
        cache_cleanup_lines.append("        \"\"\"Clear all cached data.\"\"\"")
        cache_cleanup_lines.append("        self._validation_ranges_cache.clear()")
        cache_cleanup_lines.append("        self._data_quality_cache.clear()")
        
        methods.append(GeneratedMethod(
            name="_clear_cache",
            signature="def _clear_cache(self):",
            implementation="\n".join(cache_cleanup_lines),
            docstring="Clear all cached data to free memory."
        ))
        
        return methods
    
    def _generate_logging_method(self, contract: InterfaceContract) -> Optional[GeneratedMethod]:
        """Generate logging helper method"""
        
        lines = []
        lines.append("        \"\"\"Set up logging for this component.\"\"\"")
        lines.append("        import logging")
        lines.append("        logger = logging.getLogger(f\"{self.__class__.__name__}\")")
        lines.append("        logger.setLevel(logging.INFO)")
        lines.append("        ")
        lines.append("        if not logger.handlers:")
        lines.append("            handler = logging.StreamHandler()")
        lines.append("            formatter = logging.Formatter(")
        lines.append("                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'")
        lines.append("            )")
        lines.append("            handler.setFormatter(formatter)")
        lines.append("            logger.addHandler(handler)")
        lines.append("        ")
        lines.append("        return logger")
        
        return GeneratedMethod(
            name="_setup_logging",
            signature="def _setup_logging(self):",
            implementation="\n".join(lines),
            docstring="Set up logging for this component."
        )
    
    def _determine_base_classes(self, contract: InterfaceContract, architecture_design: Dict[str, Any]) -> List[str]:
        """Determine base classes for generated class"""
        base_classes = []
        
        # Add inheritance from contract
        if contract.inheritance:
            base_classes.append(contract.inheritance)
        
        # Add interface implementations
        base_classes.extend(contract.implements)
        
        # Add architecture-specific base classes
        arch_patterns = architecture_design.get('patterns', [])
        if 'dependency_injection' in arch_patterns:
            base_classes.append('DIComponent')
        
        return base_classes
    
    def _generate_class_variables(self, contract: InterfaceContract) -> List[str]:
        """Generate class variables"""
        class_vars = []
        
        # Add standard class variables based on contract
        if contract.name == "PhaseValidator":
            class_vars.extend([
                "    # Standard feature groups",
                "    KINEMATIC_VARIABLES = ['hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',",
                "                          'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',",
                "                          'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad']",
                "    ",
                "    KINETIC_VARIABLES = ['hip_moment_ipsi_Nm', 'hip_moment_contra_Nm',",
                "                        'knee_moment_ipsi_Nm', 'knee_moment_contra_Nm',", 
                "                        'ankle_moment_ipsi_Nm', 'ankle_moment_contra_Nm']",
                "    ",
                "    # Validation constants",
                "    POINTS_PER_CYCLE = 150",
                "    REPRESENTATIVE_PHASES = [0, 25, 50, 75]"
            ])
        
        return class_vars
    
    def _determine_class_imports(self, contract: InterfaceContract) -> List[str]:
        """Determine imports needed for class"""
        imports = []
        
        # Standard imports based on contract type
        if contract.contract_type.value == "class_interface":
            imports.extend([
                'from typing import Dict, List, Optional, Any',
                'from datetime import datetime',
                'import logging'
            ])
        
        # Contract-specific imports
        if contract.name == "PhaseValidator":
            imports.extend([
                'import pandas as pd',
                'import numpy as np',
                'from pathlib import Path',
                'from lib.core.locomotion_analysis import LocomotionData'
            ])
        
        return imports
    
    def _generate_class_docstring(self, contract: InterfaceContract) -> str:
        """Generate class docstring"""
        
        lines = []
        
        # Add class description
        if contract.description:
            lines.append(contract.description)
            lines.append("")
        
        # Add contract information
        lines.append(f"Contract Type: {contract.contract_type.value}")
        
        if contract.user_personas:
            lines.append(f"User Personas: {', '.join(contract.user_personas)}")
        
        if contract.workflow_integration:
            lines.append(f"Workflow Integration: {', '.join(contract.workflow_integration)}")
        
        # Add implementation notes
        lines.append("")
        lines.append("This implementation satisfies the interface contract requirements")
        lines.append("and behavioral specifications without test bias.")
        
        return "\n".join(lines)
    
    async def _generate_supporting_components(
        self,
        implementation: Implementation,
        architecture_design: Dict[str, Any],
        behavioral_specifications: Dict[str, Any]
    ):
        """Generate supporting components like data structures and utilities"""
        
        # Generate data structure classes
        data_structures = await self._generate_data_structures(behavioral_specifications)
        implementation.classes.extend(data_structures)
        
        # Generate utility functions
        utility_functions = await self._generate_utility_functions(architecture_design)
        implementation.standalone_functions.extend(utility_functions)
        
        # Generate exception classes
        exception_classes = await self._generate_exception_classes(behavioral_specifications)
        implementation.classes.extend(exception_classes)
    
    async def _generate_data_structures(self, behavioral_specifications: Dict[str, Any]) -> List[GeneratedClass]:
        """Generate data structure classes"""
        data_classes = []
        
        # Generate result classes
        validation_result_class = self._generate_validation_result_class()
        if validation_result_class:
            data_classes.append(validation_result_class)
        
        stride_filter_result_class = self._generate_stride_filter_result_class()
        if stride_filter_result_class:
            data_classes.append(stride_filter_result_class)
        
        return data_classes
    
    def _generate_validation_result_class(self) -> GeneratedClass:
        """Generate PhaseValidationResult data class"""
        
        # This would generate the data class structure
        # For brevity, returning a simplified version
        return GeneratedClass(
            name="PhaseValidationResult",
            base_classes=[],
            methods=[],
            docstring="Result of phase-indexed dataset validation"
        )
    
    def _generate_stride_filter_result_class(self) -> GeneratedClass:
        """Generate StrideFilterResult data class"""
        
        return GeneratedClass(
            name="StrideFilterResult", 
            base_classes=[],
            methods=[],
            docstring="Result of stride-level filtering validation"
        )
    
    async def _generate_utility_functions(self, architecture_design: Dict[str, Any]) -> List[GeneratedMethod]:
        """Generate utility functions"""
        return []  # Placeholder
    
    async def _generate_exception_classes(self, behavioral_specifications: Dict[str, Any]) -> List[GeneratedClass]:
        """Generate exception classes"""
        return []  # Placeholder
    
    async def _apply_architecture_patterns(
        self,
        implementation: Implementation,
        architecture_design: Dict[str, Any]
    ):
        """Apply architecture patterns to implementation"""
        
        patterns = architecture_design.get('patterns', [])
        
        for pattern in patterns:
            if pattern == 'dependency_injection':
                await self._apply_dependency_injection_pattern(implementation, architecture_design)
            elif pattern == 'factory':
                await self._apply_factory_pattern(implementation, architecture_design)
            elif pattern == 'repository':
                await self._apply_repository_pattern(implementation, architecture_design)
    
    async def _apply_dependency_injection_pattern(
        self,
        implementation: Implementation,
        architecture_design: Dict[str, Any]
    ):
        """Apply dependency injection pattern"""
        # Add DI container and modify constructors
        pass
    
    async def _apply_factory_pattern(
        self,
        implementation: Implementation,
        architecture_design: Dict[str, Any]
    ):
        """Apply factory pattern"""
        # Generate factory classes
        pass
    
    async def _apply_repository_pattern(
        self,
        implementation: Implementation,
        architecture_design: Dict[str, Any]
    ):
        """Apply repository pattern"""
        # Generate repository interfaces and implementations
        pass
    
    async def _optimize_implementation(
        self,
        implementation: Implementation,
        performance_requirements: Dict[str, Any]
    ):
        """Optimize implementation for performance"""
        
        # Apply performance optimizations
        await self._optimize_memory_usage(implementation)
        await self._optimize_execution_speed(implementation)
        await self._optimize_scalability(implementation)
    
    async def _optimize_memory_usage(self, implementation: Implementation):
        """Optimize memory usage in implementation"""
        # Add memory optimization techniques
        pass
    
    async def _optimize_execution_speed(self, implementation: Implementation):
        """Optimize execution speed in implementation"""
        # Add speed optimization techniques
        pass
    
    async def _optimize_scalability(self, implementation: Implementation):
        """Optimize scalability in implementation"""
        # Add scalability optimization techniques
        pass
    
    def _calculate_lines_of_code(self, implementation: Implementation) -> int:
        """Calculate total lines of code in implementation"""
        total_lines = 0
        
        for class_impl in implementation.classes:
            for method in class_impl.methods:
                total_lines += len(method.implementation.split('\n'))
        
        for function in implementation.standalone_functions:
            total_lines += len(function.implementation.split('\n'))
        
        return total_lines
    
    def _calculate_complexity_score(self, implementation: Implementation) -> float:
        """Calculate complexity score of implementation"""
        # This would implement cyclomatic complexity calculation
        # For now, return a placeholder based on number of methods
        total_methods = sum(len(class_impl.methods) for class_impl in implementation.classes)
        return float(total_methods) * 2.5  # Simplified calculation
    
    async def apply_fixes(self, implementation: Implementation, fixes: List[Dict[str, Any]]) -> Implementation:
        """Apply fixes to implementation for compliance improvement"""
        
        self.logger.info(f"Applying {len(fixes)} fixes to implementation")
        
        for fix in fixes:
            fix_type = fix.get('type')
            
            if fix_type == 'add_method':
                await self._apply_add_method_fix(implementation, fix)
            elif fix_type == 'fix_signature':
                await self._apply_signature_fix(implementation, fix)
            elif fix_type == 'add_exception_handling':
                await self._apply_exception_handling_fix(implementation, fix)
        
        return implementation
    
    async def _apply_add_method_fix(self, implementation: Implementation, fix: Dict[str, Any]):
        """Apply fix to add missing method"""
        # Implementation for adding missing method
        pass
    
    async def _apply_signature_fix(self, implementation: Implementation, fix: Dict[str, Any]):
        """Apply fix to correct method signature"""
        # Implementation for fixing method signature
        pass
    
    async def _apply_exception_handling_fix(self, implementation: Implementation, fix: Dict[str, Any]):
        """Apply fix to add exception handling"""
        # Implementation for adding exception handling
        pass