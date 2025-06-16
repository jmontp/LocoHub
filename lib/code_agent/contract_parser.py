"""
Interface Contract Parser

Created: 2025-01-16 with user permission
Purpose: Parse interface contracts from documentation and specifications

Intent: Extracts behavioral specifications, method signatures, and requirements
from interface contract documentation to enable contract-driven code generation
without test bias.
"""

import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import markdown
from datetime import datetime


class ContractType(Enum):
    """Types of interface contracts"""
    CLASS_INTERFACE = "class_interface"
    API_INTERFACE = "api_interface"
    DATA_CONTRACT = "data_contract"
    BEHAVIORAL_SPEC = "behavioral_spec"


class ParameterType(Enum):
    """Parameter types for method signatures"""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "List"
    DICT = "Dict"
    OPTIONAL = "Optional"
    DATAFRAME = "pd.DataFrame"
    NUMPY_ARRAY = "np.ndarray"
    CUSTOM_TYPE = "custom"


@dataclass
class ParameterSpec:
    """Specification for method parameter"""
    name: str
    type: ParameterType
    type_annotation: str
    description: str
    constraints: List[str] = field(default_factory=list)
    default_value: Optional[Any] = None
    is_optional: bool = False
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class MethodSpec:
    """Specification for interface method"""
    name: str
    signature: str
    parameters: List[ParameterSpec]
    return_type: str
    return_description: str
    description: str
    
    # Behavioral requirements
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    
    # Exception specifications
    exceptions: List[Dict[str, str]] = field(default_factory=list)
    
    # Performance requirements
    timing_requirements: List[Dict[str, Any]] = field(default_factory=list)
    memory_requirements: List[Dict[str, Any]] = field(default_factory=list)
    
    # Implementation hints
    algorithm_hints: List[str] = field(default_factory=list)
    optimization_priorities: List[str] = field(default_factory=list)
    
    # Requirements traceability
    user_stories: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass
class InterfaceContract:
    """Complete interface contract specification"""
    name: str
    contract_type: ContractType
    description: str
    
    # Method specifications
    methods: List[MethodSpec] = field(default_factory=list)
    
    # Class-level specifications
    class_properties: List[Dict[str, Any]] = field(default_factory=list)
    class_constraints: List[str] = field(default_factory=list)
    
    # Dependencies and relationships
    dependencies: List[str] = field(default_factory=list)
    inheritance: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    
    # Performance specifications
    performance_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Domain-specific requirements
    domain_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Requirements traceability
    source_documents: List[str] = field(default_factory=list)
    user_personas: List[str] = field(default_factory=list)
    workflow_integration: List[str] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0.0"
    creation_date: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)


class InterfaceContractParser:
    """
    Parser for extracting interface contracts from documentation and specifications.
    
    Supports multiple input formats:
    - Markdown documentation with structured contracts
    - Python source files with annotated interfaces
    - JSON/YAML specification files
    - Requirements documents with behavioral specifications
    """
    
    def __init__(self):
        """Initialize the contract parser"""
        self.logger = self._setup_logging()
        
        # Parsing patterns for different contract elements
        self.method_pattern = re.compile(
            r'def\s+(\w+)\s*\((.*?)\)\s*->\s*([^:]+):\s*"""(.*?)"""',
            re.DOTALL | re.MULTILINE
        )
        
        self.behavioral_pattern = re.compile(
            r'MUST\s+(.*?)(?=\n|$)', 
            re.IGNORECASE
        )
        
        self.requirement_pattern = re.compile(
            r'Requirements?\s*(?:Traceability)?[:\s]*([^:]+):(.+?)(?=\n\n|\Z)',
            re.DOTALL | re.IGNORECASE
        )
        
        # Cache for parsed contracts
        self.contract_cache: Dict[str, InterfaceContract] = {}
    
    def _setup_logging(self):
        """Set up logging for contract parser"""
        import logging
        logger = logging.getLogger("ContractParser")
        logger.setLevel(logging.INFO)
        return logger
    
    def parse_contract_from_markdown(self, markdown_path: Union[str, Path]) -> List[InterfaceContract]:
        """
        Parse interface contracts from markdown documentation.
        
        Args:
            markdown_path: Path to markdown file with interface contracts
            
        Returns:
            List of parsed interface contracts
            
        Raises:
            FileNotFoundError: If markdown file doesn't exist
            ValueError: If contract format is invalid
        """
        markdown_path = Path(markdown_path)
        
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
        
        self.logger.info(f"Parsing contracts from: {markdown_path}")
        
        # Read markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse contracts from markdown
        contracts = self._parse_markdown_contracts(content, str(markdown_path))
        
        self.logger.info(f"Parsed {len(contracts)} contracts from {markdown_path}")
        
        # Cache parsed contracts
        for contract in contracts:
            self.contract_cache[contract.name] = contract
        
        return contracts
    
    def _parse_markdown_contracts(self, content: str, source_file: str) -> List[InterfaceContract]:
        """Parse interface contracts from markdown content"""
        contracts = []
        
        # Split content into sections
        sections = self._split_markdown_sections(content)
        
        for section in sections:
            # Check if section contains an interface contract
            if self._is_interface_contract_section(section):
                contract = self._parse_contract_section(section, source_file)
                if contract:
                    contracts.append(contract)
        
        return contracts
    
    def _split_markdown_sections(self, content: str) -> List[str]:
        """Split markdown content into logical sections"""
        # Split by major headings (##)
        sections = re.split(r'\n## ', content)
        
        # Restore heading markers
        for i in range(1, len(sections)):
            sections[i] = '## ' + sections[i]
        
        return sections
    
    def _is_interface_contract_section(self, section: str) -> bool:
        """Check if a section contains an interface contract"""
        # Look for contract indicators
        contract_indicators = [
            'class ',
            'def ',
            'interface',
            'contract',
            'PhaseValidator',
            'TimeValidator',
            'QualityAssessor',
            'DatasetComparator',
            'ValidationSpecManager',
            'AutomatedFineTuner',
            'BenchmarkCreator'
        ]
        
        return any(indicator in section for indicator in contract_indicators)
    
    def _parse_contract_section(self, section: str, source_file: str) -> Optional[InterfaceContract]:
        """Parse an individual contract section"""
        try:
            # Extract contract name from heading
            contract_name = self._extract_contract_name(section)
            if not contract_name:
                return None
            
            # Determine contract type
            contract_type = self._determine_contract_type(section)
            
            # Extract description
            description = self._extract_contract_description(section)
            
            # Parse Python code blocks for method specifications
            methods = self._parse_methods_from_section(section)
            
            # Extract requirements traceability
            requirements_info = self._extract_requirements_traceability(section)
            
            # Extract behavioral specifications
            behavioral_specs = self._extract_behavioral_specifications(section)
            
            # Extract performance requirements
            performance_reqs = self._extract_performance_requirements(section)
            
            # Create contract object
            contract = InterfaceContract(
                name=contract_name,
                contract_type=contract_type,
                description=description,
                methods=methods,
                source_documents=[source_file],
                user_personas=requirements_info.get('user_personas', []),
                workflow_integration=requirements_info.get('workflow_integration', []),
                performance_requirements=performance_reqs,
                domain_constraints=behavioral_specs
            )
            
            return contract
            
        except Exception as e:
            self.logger.error(f"Error parsing contract section: {str(e)}")
            return None
    
    def _extract_contract_name(self, section: str) -> Optional[str]:
        """Extract contract name from section heading"""
        # Look for heading patterns
        heading_match = re.search(r'##\s+(.+?)(?:\s+-|$)', section)
        if heading_match:
            return heading_match.group(1).strip()
        
        # Look for class names in code blocks
        class_match = re.search(r'class\s+(\w+)', section)
        if class_match:
            return class_match.group(1)
        
        return None
    
    def _determine_contract_type(self, section: str) -> ContractType:
        """Determine the type of contract from section content"""
        if 'class ' in section:
            return ContractType.CLASS_INTERFACE
        elif 'def ' in section:
            return ContractType.API_INTERFACE
        elif 'dataclass' in section or '@dataclass' in section:
            return ContractType.DATA_CONTRACT
        else:
            return ContractType.BEHAVIORAL_SPEC
    
    def _extract_contract_description(self, section: str) -> str:
        """Extract contract description from section"""
        # Look for description in docstrings or prose
        lines = section.split('\n')
        description_lines = []
        
        in_description = False
        for line in lines:
            line = line.strip()
            
            # Skip heading
            if line.startswith('##'):
                continue
            
            # Start collecting description after requirements block
            if 'Requirements Traceability:' in line:
                in_description = True
                continue
            
            # Stop at code blocks
            if line.startswith('```'):
                break
            
            if in_description and line:
                description_lines.append(line)
        
        return '\n'.join(description_lines).strip()
    
    def _parse_methods_from_section(self, section: str) -> List[MethodSpec]:
        """Parse method specifications from section"""
        methods = []
        
        # Extract Python code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', section, re.DOTALL)
        
        for code_block in code_blocks:
            # Parse method definitions from code block
            method_specs = self._parse_methods_from_code(code_block)
            methods.extend(method_specs)
        
        return methods
    
    def _parse_methods_from_code(self, code: str) -> List[MethodSpec]:
        """Parse method specifications from Python code"""
        methods = []
        
        try:
            # Parse the code with AST
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_spec = self._parse_method_node(node, code)
                    if method_spec:
                        methods.append(method_spec)
                        
        except SyntaxError as e:
            self.logger.warning(f"Syntax error parsing code: {str(e)}")
            # Fall back to regex parsing
            methods = self._parse_methods_with_regex(code)
        
        return methods
    
    def _parse_method_node(self, node: ast.FunctionDef, full_code: str) -> Optional[MethodSpec]:
        """Parse method specification from AST node"""
        try:
            # Extract method name
            method_name = node.name
            
            # Extract parameters
            parameters = self._extract_parameters_from_node(node)
            
            # Extract return type
            return_type = self._extract_return_type_from_node(node)
            
            # Extract docstring
            docstring = ast.get_docstring(node) or ""
            
            # Parse docstring for additional specifications
            doc_specs = self._parse_method_docstring(docstring)
            
            # Create method specification
            method_spec = MethodSpec(
                name=method_name,
                signature=self._reconstruct_signature(node),
                parameters=parameters,
                return_type=return_type,
                return_description=doc_specs.get('return_description', ''),
                description=doc_specs.get('description', ''),
                preconditions=doc_specs.get('preconditions', []),
                postconditions=doc_specs.get('postconditions', []),
                exceptions=doc_specs.get('exceptions', []),
                timing_requirements=doc_specs.get('timing_requirements', []),
                memory_requirements=doc_specs.get('memory_requirements', []),
                user_stories=doc_specs.get('user_stories', []),
                acceptance_criteria=doc_specs.get('acceptance_criteria', [])
            )
            
            return method_spec
            
        except Exception as e:
            self.logger.error(f"Error parsing method node: {str(e)}")
            return None
    
    def _extract_parameters_from_node(self, node: ast.FunctionDef) -> List[ParameterSpec]:
        """Extract parameter specifications from AST node"""
        parameters = []
        
        for arg in node.args.args:
            # Skip 'self' parameter
            if arg.arg == 'self':
                continue
            
            # Extract parameter information
            param_name = arg.arg
            param_annotation = self._extract_annotation(arg.annotation) if arg.annotation else 'Any'
            param_type = self._infer_parameter_type(param_annotation)
            
            # Check for default values
            defaults = node.args.defaults
            default_value = None
            is_optional = False
            
            # Calculate if this parameter has a default
            num_args = len(node.args.args)
            num_defaults = len(defaults)
            arg_index = node.args.args.index(arg)
            
            if arg_index >= num_args - num_defaults:
                default_index = arg_index - (num_args - num_defaults)
                default_value = self._extract_default_value(defaults[default_index])
                is_optional = True
            
            param_spec = ParameterSpec(
                name=param_name,
                type=param_type,
                type_annotation=param_annotation,
                description=f"Parameter {param_name}",  # TODO: Extract from docstring
                default_value=default_value,
                is_optional=is_optional
            )
            
            parameters.append(param_spec)
        
        return parameters
    
    def _extract_annotation(self, annotation) -> str:
        """Extract type annotation as string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Attribute):
            return f"{self._extract_annotation(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            base = self._extract_annotation(annotation.value)
            slice_val = self._extract_annotation(annotation.slice)
            return f"{base}[{slice_val}]"
        else:
            return 'Any'
    
    def _infer_parameter_type(self, annotation: str) -> ParameterType:
        """Infer parameter type from annotation string"""
        annotation_lower = annotation.lower()
        
        if 'str' in annotation_lower:
            return ParameterType.STRING
        elif 'int' in annotation_lower:
            return ParameterType.INTEGER
        elif 'float' in annotation_lower:
            return ParameterType.FLOAT
        elif 'bool' in annotation_lower:
            return ParameterType.BOOLEAN
        elif 'list' in annotation_lower:
            return ParameterType.LIST
        elif 'dict' in annotation_lower:
            return ParameterType.DICT
        elif 'optional' in annotation_lower:
            return ParameterType.OPTIONAL
        elif 'dataframe' in annotation_lower:
            return ParameterType.DATAFRAME
        elif 'ndarray' in annotation_lower or 'array' in annotation_lower:
            return ParameterType.NUMPY_ARRAY
        else:
            return ParameterType.CUSTOM_TYPE
    
    def _extract_return_type_from_node(self, node: ast.FunctionDef) -> str:
        """Extract return type from AST node"""
        if node.returns:
            return self._extract_annotation(node.returns)
        return 'Any'
    
    def _extract_default_value(self, default_node) -> Any:
        """Extract default value from AST node"""
        if isinstance(default_node, ast.Constant):
            return default_node.value
        elif isinstance(default_node, ast.Name):
            return default_node.id
        else:
            return None
    
    def _reconstruct_signature(self, node: ast.FunctionDef) -> str:
        """Reconstruct method signature from AST node"""
        params = []
        
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {self._extract_annotation(arg.annotation)}"
            params.append(param_str)
        
        # Add defaults
        defaults = node.args.defaults
        num_defaults = len(defaults)
        for i, default in enumerate(defaults):
            param_index = len(params) - num_defaults + i
            if param_index >= 0:
                default_val = self._extract_default_value(default)
                params[param_index] += f" = {default_val}"
        
        signature = f"def {node.name}({', '.join(params)})"
        
        if node.returns:
            signature += f" -> {self._extract_annotation(node.returns)}"
        
        return signature
    
    def _parse_methods_with_regex(self, code: str) -> List[MethodSpec]:
        """Fall back to regex-based method parsing"""
        methods = []
        
        # Find method definitions with regex
        method_matches = self.method_pattern.findall(code)
        
        for match in method_matches:
            method_name, params_str, return_type, docstring = match
            
            # Parse parameters
            parameters = self._parse_parameters_from_string(params_str)
            
            # Parse docstring
            doc_specs = self._parse_method_docstring(docstring)
            
            method_spec = MethodSpec(
                name=method_name,
                signature=f"def {method_name}({params_str}) -> {return_type}",
                parameters=parameters,
                return_type=return_type.strip(),
                return_description=doc_specs.get('return_description', ''),
                description=doc_specs.get('description', ''),
                preconditions=doc_specs.get('preconditions', []),
                postconditions=doc_specs.get('postconditions', []),
                exceptions=doc_specs.get('exceptions', [])
            )
            
            methods.append(method_spec)
        
        return methods
    
    def _parse_parameters_from_string(self, params_str: str) -> List[ParameterSpec]:
        """Parse parameters from parameter string"""
        parameters = []
        
        # Split parameters and parse each one
        param_parts = params_str.split(',')
        
        for part in param_parts:
            part = part.strip()
            if not part or part == 'self':
                continue
            
            # Extract parameter name and type
            if ':' in part:
                name_part, type_part = part.split(':', 1)
                param_name = name_part.strip()
                
                # Handle default values
                if '=' in type_part:
                    type_annotation, default_str = type_part.split('=', 1)
                    type_annotation = type_annotation.strip()
                    default_value = default_str.strip()
                    is_optional = True
                else:
                    type_annotation = type_part.strip()
                    default_value = None
                    is_optional = False
            else:
                param_name = part
                type_annotation = 'Any'
                default_value = None
                is_optional = False
            
            param_type = self._infer_parameter_type(type_annotation)
            
            param_spec = ParameterSpec(
                name=param_name,
                type=param_type,
                type_annotation=type_annotation,
                description=f"Parameter {param_name}",
                default_value=default_value,
                is_optional=is_optional
            )
            
            parameters.append(param_spec)
        
        return parameters
    
    def _parse_method_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse method docstring for specifications"""
        specs = {
            'description': '',
            'return_description': '',
            'preconditions': [],
            'postconditions': [],
            'exceptions': [],
            'timing_requirements': [],
            'memory_requirements': [],
            'user_stories': [],
            'acceptance_criteria': []
        }
        
        # Extract description (first paragraph)
        lines = docstring.strip().split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                break
            description_lines.append(line)
        
        specs['description'] = ' '.join(description_lines)
        
        # Extract behavioral requirements (MUST statements)
        must_statements = self.behavioral_pattern.findall(docstring)
        specs['preconditions'] = must_statements
        
        # Extract requirements traceability
        requirements_matches = self.requirement_pattern.findall(docstring)
        for req_type, req_content in requirements_matches:
            req_type = req_type.strip().lower()
            req_items = [item.strip() for item in req_content.split('-') if item.strip()]
            
            if 'user stor' in req_type:
                specs['user_stories'] = req_items
            elif 'acceptance' in req_type:
                specs['acceptance_criteria'] = req_items
        
        # Extract exceptions from docstring
        if 'Raises:' in docstring:
            raises_section = docstring.split('Raises:')[1].split('\n\n')[0]
            exception_lines = raises_section.strip().split('\n')
            
            for line in exception_lines:
                line = line.strip()
                if line and ':' in line:
                    exc_type, exc_desc = line.split(':', 1)
                    specs['exceptions'].append({
                        'type': exc_type.strip(),
                        'description': exc_desc.strip()
                    })
        
        return specs
    
    def _extract_requirements_traceability(self, section: str) -> Dict[str, List[str]]:
        """Extract requirements traceability information"""
        traceability = {
            'user_personas': [],
            'user_stories': [],
            'workflow_integration': [],
            'cli_entry_points': []
        }
        
        # Look for requirements traceability sections
        if 'Requirements Traceability:' in section:
            traceability_section = section.split('Requirements Traceability:')[1]
            
            # Extract user personas
            if 'User Personas:' in traceability_section:
                personas_text = traceability_section.split('User Personas:')[1].split('\n')[0]
                traceability['user_personas'] = [p.strip() for p in personas_text.split(',')]
            
            # Extract user stories
            user_story_matches = re.findall(r'User Stor(?:y|ies)[:\s]+([^\n]+)', traceability_section)
            for match in user_story_matches:
                traceability['user_stories'].extend([s.strip() for s in match.split(',')])
            
            # Extract workflow integration
            if 'Workflow Integration:' in traceability_section:
                workflow_text = traceability_section.split('Workflow Integration:')[1].split('\n')[0]
                traceability['workflow_integration'] = [w.strip() for w in workflow_text.split(',')]
            
            # Extract CLI entry points
            if 'CLI Entry Point:' in traceability_section:
                cli_text = traceability_section.split('CLI Entry Point:')[1].split('\n')[0]
                traceability['cli_entry_points'] = [c.strip() for c in cli_text.split(',')]
        
        return traceability
    
    def _extract_behavioral_specifications(self, section: str) -> Dict[str, Any]:
        """Extract behavioral specifications and MUST requirements"""
        behavioral_specs = {
            'must_requirements': [],
            'should_requirements': [],
            'may_requirements': [],
            'domain_constraints': [],
            'quality_requirements': []
        }
        
        # Extract MUST requirements
        must_matches = re.findall(r'MUST\s+([^.\n]+)', section, re.IGNORECASE)
        behavioral_specs['must_requirements'] = [req.strip() for req in must_matches]
        
        # Extract SHOULD requirements
        should_matches = re.findall(r'SHOULD\s+([^.\n]+)', section, re.IGNORECASE)
        behavioral_specs['should_requirements'] = [req.strip() for req in should_matches]
        
        # Extract MAY requirements
        may_matches = re.findall(r'MAY\s+([^.\n]+)', section, re.IGNORECASE)
        behavioral_specs['may_requirements'] = [req.strip() for req in may_matches]
        
        return behavioral_specs
    
    def _extract_performance_requirements(self, section: str) -> Dict[str, Any]:
        """Extract performance requirements from section"""
        performance_reqs = {
            'timing_constraints': [],
            'memory_constraints': [],
            'throughput_requirements': [],
            'scalability_targets': []
        }
        
        # Look for performance-related keywords and extract requirements
        performance_patterns = [
            (r'(?:within|under|<)\s+(\d+)\s*(second|minute|ms|millisecond)', 'timing'),
            (r'(?:memory|RAM|limit).*?(\d+)\s*(GB|MB|KB)', 'memory'),
            (r'(?:process|handle).*?(\d+).*?(?:dataset|file|record)', 'throughput'),
            (r'(?:scale|support).*?(\d+).*?(?:concurrent|parallel|user)', 'scalability')
        ]
        
        for pattern, category in performance_patterns:
            matches = re.findall(pattern, section, re.IGNORECASE)
            for match in matches:
                value, unit = match
                performance_reqs[f'{category}_constraints'].append({
                    'value': int(value),
                    'unit': unit,
                    'context': 'extracted_from_documentation'
                })
        
        return performance_reqs
    
    def parse_contract_from_python_file(self, python_path: Union[str, Path]) -> List[InterfaceContract]:
        """
        Parse interface contracts from Python source file.
        
        Args:
            python_path: Path to Python file with interface definitions
            
        Returns:
            List of parsed interface contracts
        """
        python_path = Path(python_path)
        
        if not python_path.exists():
            raise FileNotFoundError(f"Python file not found: {python_path}")
        
        self.logger.info(f"Parsing contracts from Python file: {python_path}")
        
        # Read Python source
        with open(python_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Parse with AST
        try:
            tree = ast.parse(source_code)
            contracts = self._parse_contracts_from_ast(tree, str(python_path))
            
            self.logger.info(f"Parsed {len(contracts)} contracts from {python_path}")
            
            # Cache parsed contracts
            for contract in contracts:
                self.contract_cache[contract.name] = contract
            
            return contracts
            
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in {python_path}: {str(e)}")
    
    def _parse_contracts_from_ast(self, tree: ast.AST, source_file: str) -> List[InterfaceContract]:
        """Parse interface contracts from AST"""
        contracts = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                contract = self._parse_class_contract(node, source_file)
                if contract:
                    contracts.append(contract)
        
        return contracts
    
    def _parse_class_contract(self, node: ast.ClassDef, source_file: str) -> Optional[InterfaceContract]:
        """Parse interface contract from class AST node"""
        try:
            class_name = node.name
            class_docstring = ast.get_docstring(node) or ""
            
            # Parse methods from class
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_spec = self._parse_method_node(item, "")
                    if method_spec:
                        methods.append(method_spec)
            
            # Create contract
            contract = InterfaceContract(
                name=class_name,
                contract_type=ContractType.CLASS_INTERFACE,
                description=class_docstring,
                methods=methods,
                source_documents=[source_file]
            )
            
            return contract
            
        except Exception as e:
            self.logger.error(f"Error parsing class contract: {str(e)}")
            return None
    
    def analyze_contract(self, contract: InterfaceContract) -> Dict[str, Any]:
        """
        Analyze interface contract for implementation requirements.
        
        Args:
            contract: Interface contract to analyze
            
        Returns:
            Analysis results with implementation guidance
        """
        analysis = {
            'complexity_assessment': self._assess_contract_complexity(contract),
            'dependency_analysis': self._analyze_contract_dependencies(contract),
            'performance_analysis': self._analyze_performance_requirements(contract),
            'behavioral_analysis': self._analyze_behavioral_requirements(contract),
            'implementation_recommendations': self._generate_implementation_recommendations(contract)
        }
        
        return analysis
    
    def _assess_contract_complexity(self, contract: InterfaceContract) -> Dict[str, Any]:
        """Assess complexity of interface contract"""
        method_count = len(contract.methods)
        param_complexity = sum(len(method.parameters) for method in contract.methods)
        behavioral_complexity = sum(
            len(method.preconditions) + len(method.postconditions) 
            for method in contract.methods
        )
        
        complexity_score = method_count + (param_complexity * 0.5) + (behavioral_complexity * 0.3)
        
        if complexity_score < 5:
            complexity_level = 'low'
        elif complexity_score < 15:
            complexity_level = 'medium'
        else:
            complexity_level = 'high'
        
        return {
            'level': complexity_level,
            'score': complexity_score,
            'method_count': method_count,
            'parameter_complexity': param_complexity,
            'behavioral_complexity': behavioral_complexity
        }
    
    def _analyze_contract_dependencies(self, contract: InterfaceContract) -> Dict[str, Any]:
        """Analyze dependencies in interface contract"""
        return {
            'explicit_dependencies': contract.dependencies,
            'inferred_dependencies': self._infer_dependencies_from_types(contract),
            'inheritance_chain': contract.inheritance,
            'interface_implementations': contract.implements
        }
    
    def _infer_dependencies_from_types(self, contract: InterfaceContract) -> List[str]:
        """Infer dependencies from type annotations"""
        dependencies = set()
        
        for method in contract.methods:
            # Check parameter types
            for param in method.parameters:
                if param.type == ParameterType.CUSTOM_TYPE:
                    dependencies.add(param.type_annotation)
            
            # Check return type
            if 'pd.DataFrame' in method.return_type:
                dependencies.add('pandas')
            elif 'np.ndarray' in method.return_type:
                dependencies.add('numpy')
        
        return list(dependencies)
    
    def _analyze_performance_requirements(self, contract: InterfaceContract) -> Dict[str, Any]:
        """Analyze performance requirements"""
        timing_reqs = []
        memory_reqs = []
        
        for method in contract.methods:
            timing_reqs.extend(method.timing_requirements)
            memory_reqs.extend(method.memory_requirements)
        
        # Add contract-level requirements
        timing_reqs.extend(contract.performance_requirements.get('timing_constraints', []))
        memory_reqs.extend(contract.performance_requirements.get('memory_constraints', []))
        
        return {
            'timing_requirements': timing_reqs,
            'memory_requirements': memory_reqs,
            'has_performance_constraints': len(timing_reqs) > 0 or len(memory_reqs) > 0
        }
    
    def _analyze_behavioral_requirements(self, contract: InterfaceContract) -> Dict[str, Any]:
        """Analyze behavioral requirements"""
        all_preconditions = []
        all_postconditions = []
        all_exceptions = []
        
        for method in contract.methods:
            all_preconditions.extend(method.preconditions)
            all_postconditions.extend(method.postconditions)
            all_exceptions.extend(method.exceptions)
        
        return {
            'preconditions': all_preconditions,
            'postconditions': all_postconditions,
            'exceptions': all_exceptions,
            'behavioral_complexity': len(all_preconditions) + len(all_postconditions),
            'error_handling_requirements': len(all_exceptions)
        }
    
    def _generate_implementation_recommendations(self, contract: InterfaceContract) -> List[str]:
        """Generate implementation recommendations"""
        recommendations = []
        
        complexity = self._assess_contract_complexity(contract)
        
        if complexity['level'] == 'high':
            recommendations.append("Consider using layered architecture pattern")
            recommendations.append("Implement comprehensive error handling")
            recommendations.append("Add extensive logging for debugging")
        
        if len(contract.methods) > 10:
            recommendations.append("Consider splitting into multiple smaller contracts")
        
        performance_analysis = self._analyze_performance_requirements(contract)
        if performance_analysis['has_performance_constraints']:
            recommendations.append("Implement performance monitoring and optimization")
            recommendations.append("Use efficient data structures and algorithms")
        
        return recommendations
    
    def get_cached_contract(self, contract_name: str) -> Optional[InterfaceContract]:
        """Get cached contract by name"""
        return self.contract_cache.get(contract_name)
    
    def list_cached_contracts(self) -> List[str]:
        """List names of all cached contracts"""
        return list(self.contract_cache.keys())
    
    def clear_cache(self):
        """Clear the contract cache"""
        self.contract_cache.clear()
        self.logger.info("Contract cache cleared")