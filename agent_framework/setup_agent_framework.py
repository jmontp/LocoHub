"""
Agent Framework Setup Script

Created: 2025-01-16 with user permission
Purpose: Initialize and configure the three-agent framework

Intent: Sets up the complete agent framework infrastructure including
communication, configuration, and workspace management.
"""

import sys
import os
from pathlib import Path
import yaml

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir.parent))

from shared.config.agent_config import create_default_config, save_config
from shared.communication.agent_communication import create_communication_infrastructure


def setup_workspace_structure(workspace_root: Path) -> None:
    """Create complete workspace directory structure"""
    
    print("Setting up agent framework workspace structure...")
    
    # Create main directories
    directories = [
        workspace_root / "test_agent" / "workspace",
        workspace_root / "test_agent" / "templates", 
        workspace_root / "test_agent" / "output",
        workspace_root / "code_agent" / "workspace",
        workspace_root / "code_agent" / "templates",
        workspace_root / "code_agent" / "output",
        workspace_root / "integration_agent" / "workspace",
        workspace_root / "integration_agent" / "templates",
        workspace_root / "integration_agent" / "output",
        workspace_root / "shared" / "communication",
        workspace_root / "shared" / "templates",
        workspace_root / "shared" / "monitoring",
        workspace_root / "shared" / "config"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created: {directory}")
    
    # Create __init__.py files for Python packages
    init_files = [
        workspace_root / "__init__.py",
        workspace_root / "test_agent" / "__init__.py",
        workspace_root / "code_agent" / "__init__.py", 
        workspace_root / "integration_agent" / "__init__.py",
        workspace_root / "shared" / "__init__.py",
        workspace_root / "shared" / "communication" / "__init__.py",
        workspace_root / "shared" / "config" / "__init__.py"
    ]
    
    for init_file in init_files:
        if not init_file.exists():
            init_file.touch()
            print(f"Created: {init_file}")


def create_configuration(workspace_root: Path) -> None:
    """Create and save agent framework configuration"""
    
    print("Creating agent framework configuration...")
    
    # Create default configuration
    config = create_default_config(workspace_root)
    
    # Save configuration
    config_path = workspace_root / "shared" / "config" / "agent_config.yaml"
    save_config(config, config_path)
    
    print(f"Configuration saved to: {config_path}")
    
    # Create individual agent configurations
    for agent_name in ['test_agent', 'code_agent', 'integration_agent']:
        agent_config_path = workspace_root / agent_name / "config.yaml"
        agent_config = config[agent_name]
        
        with open(agent_config_path, 'w') as f:
            yaml.dump(agent_config, f, default_flow_style=False, indent=2)
        
        print(f"Created {agent_name} config: {agent_config_path}")


def initialize_communication(workspace_root: Path) -> None:
    """Initialize communication infrastructure"""
    
    print("Initializing communication infrastructure...")
    
    try:
        message_bus = create_communication_infrastructure(workspace_root)
        print("Communication infrastructure initialized successfully")
        
        # Create communication status file
        status_file = workspace_root / "shared" / "communication" / "status.yaml"
        status = {
            "initialized": True,
            "message_bus_active": True,
            "workspace_path": str(workspace_root)
        }
        
        with open(status_file, 'w') as f:
            yaml.dump(status, f, default_flow_style=False, indent=2)
        
        print(f"Communication status saved to: {status_file}")
        
    except Exception as e:
        print(f"Warning: Communication initialization failed: {e}")
        print("Agents will still function but without inter-agent communication")


def create_templates(workspace_root: Path) -> None:
    """Create template files for agent operations"""
    
    print("Creating agent template files...")
    
    # Test Agent templates
    test_template = workspace_root / "test_agent" / "templates" / "test_case_template.py"
    test_template_content = '''"""
Test Case Template

This template provides the structure for generating test cases
from user stories and interface contracts.
"""

import pytest
import unittest.mock as mock


class TestTemplate:
    """Template for generated test classes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.mock_data = {}
        self.expected_outcomes = {}
    
    def test_acceptance_criterion(self):
        """Template for acceptance criterion tests"""
        # Mock dependencies
        with mock.patch('sys.modules'):
            # Test the acceptance criterion
            assert True, "Implement specific test logic"
    
    def test_error_handling(self):
        """Template for error handling tests"""
        with pytest.raises(Exception):
            # Test error conditions
            pass


if __name__ == "__main__":
    pytest.main([__file__])
'''
    
    with open(test_template, 'w') as f:
        f.write(test_template_content)
    
    # Code Agent templates
    code_template = workspace_root / "code_agent" / "templates" / "implementation_template.py"
    code_template_content = '''"""
Implementation Template

This template provides the structure for generating code implementations
from interface contracts and technical specifications.
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class ImplementationTemplate(ABC):
    """Template for generated implementation classes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration parameters"""
        # Implement configuration validation
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Main processing method - implement based on interface contract"""
        pass
    
    def _handle_error(self, error: Exception, context: str) -> None:
        """Standard error handling pattern"""
        # Implement error handling based on specifications
        raise error


# Example implementation class
class ExampleImplementation(ImplementationTemplate):
    """Example implementation following template pattern"""
    
    def process(self, input_data: Any) -> Any:
        """Process input according to interface contract"""
        try:
            # Implement processing logic
            result = self._core_processing(input_data)
            return result
        except Exception as e:
            self._handle_error(e, "process")
    
    def _core_processing(self, input_data: Any) -> Any:
        """Core processing logic"""
        # Implement based on technical specifications
        return input_data
'''
    
    with open(code_template, 'w') as f:
        f.write(code_template_content)
    
    # Integration Agent templates
    integration_template = workspace_root / "integration_agent" / "templates" / "integration_test_template.py"
    integration_template_content = '''"""
Integration Test Template

This template provides the structure for integration testing
between test suites and implementations.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any


class IntegrationTestTemplate:
    """Template for integration testing operations"""
    
    def __init__(self, test_path: Path, code_path: Path):
        self.test_path = test_path
        self.code_path = code_path
        self.results = {}
    
    def execute_tests(self) -> Dict[str, Any]:
        """Execute test suite against implementation"""
        try:
            # Run tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", str(self.test_path), "-v"
            ], capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_failures(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze test failures and categorize them"""
        failures = []
        
        if not test_results.get("success", False):
            # Parse failure information
            failures.append({
                "type": "execution_failure",
                "description": "Test execution failed",
                "details": test_results.get("stderr", "")
            })
        
        return failures
    
    def generate_report(self) -> str:
        """Generate integration test report"""
        return """
# Integration Test Report

## Test Execution Results
- Test Path: {test_path}
- Code Path: {code_path}
- Status: {status}

## Summary
{summary}
""".format(
            test_path=self.test_path,
            code_path=self.code_path,
            status="PENDING",
            summary="Integration test template - implement specific reporting logic"
        )


if __name__ == "__main__":
    # Example usage
    template = IntegrationTestTemplate(Path("tests"), Path("src"))
    results = template.execute_tests()
    print(template.generate_report())
'''
    
    with open(integration_template, 'w') as f:
        f.write(integration_template_content)
    
    print(f"Created templates in: {workspace_root / 'test_agent' / 'templates'}")
    print(f"Created templates in: {workspace_root / 'code_agent' / 'templates'}")
    print(f"Created templates in: {workspace_root / 'integration_agent' / 'templates'}")


def create_readme(workspace_root: Path) -> None:
    """Create README with usage instructions"""
    
    readme_content = '''# Three-Agent Framework

## Overview

This framework implements the three-agent orchestration approach for autonomous software development:

- **Test Agent**: Creates comprehensive test suites from requirements without implementation knowledge
- **Code Agent**: Implements code from interface contracts without seeing test implementations  
- **Integration Agent**: Executes tests against implementations and resolves conflicts

## Directory Structure

```
agent_framework/
├── test_agent/           # Test Agent workspace and implementation
├── code_agent/           # Code Agent workspace and implementation
├── integration_agent/    # Integration Agent workspace and implementation
├── shared/               # Shared infrastructure
│   ├── communication/    # Inter-agent communication
│   ├── config/          # Configuration management
│   ├── monitoring/      # Progress and quality monitoring
│   └── templates/       # Shared templates
└── setup_agent_framework.py  # Setup script
```

## Quick Start

1. **Initialize Framework**:
   ```bash
   python agent_framework/setup_agent_framework.py
   ```

2. **Run Test Agent**:
   ```bash
   python agent_framework/test_agent/test_agent.py
   ```

3. **Check Configuration**:
   ```bash
   cat agent_framework/shared/config/agent_config.yaml
   ```

## Configuration

Agent configurations are stored in:
- `shared/config/agent_config.yaml` - Main framework configuration
- `{agent_name}/config.yaml` - Individual agent configurations

## Communication

Agents communicate through:
- Message passing system in `shared/communication/`
- Shared workspace for handoffs
- Quality monitoring and progress tracking

## Quality Gates

The framework enforces quality gates:
- Test coverage: >90% of acceptance criteria
- Interface compliance: 100% contract adherence
- Integration success: >95% success rate
- Code quality: >85% quality score

## Usage Examples

### Test Agent
Generates tests from user stories and interface contracts:
```python
from test_agent.test_agent import TestAgent

agent = TestAgent(workspace_path, config)
test_suite = agent.process_requirements(user_stories_path, interface_specs_path)
```

### Code Agent
Implements code from interface contracts:
```python
from code_agent.code_agent import CodeAgent

agent = CodeAgent(workspace_path, config)  
implementation = agent.generate_implementation(interface_contracts, technical_specs)
```

### Integration Agent
Integrates tests and implementations:
```python
from integration_agent.integration_agent import IntegrationAgent

agent = IntegrationAgent(workspace_path, config)
results = agent.integrate_and_test(test_suite, implementation)
```

## Documentation

Complete specifications available in:
- `docs/software_engineering/COMPREHENSIVE_AGENT_SPECIFICATIONS.md`
- `docs/software_engineering/IMPLEMENTATION_ORCHESTRATOR_MANUAL.md`
- `docs/software_engineering/AGENT_COMMUNICATION_STANDARDS.md`

## Support

For issues or questions:
1. Check agent workspace logs
2. Review configuration files
3. Consult implementation specifications
'''
    
    readme_path = workspace_root / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"Created README: {readme_path}")


def main():
    """Main setup function"""
    
    print("🤖 Initializing Three-Agent Framework")
    print("=" * 50)
    
    # Get workspace root
    workspace_root = Path(__file__).parent
    
    try:
        # Setup workspace structure
        setup_workspace_structure(workspace_root)
        print("✅ Workspace structure created")
        
        # Create configuration
        create_configuration(workspace_root)
        print("✅ Configuration created")
        
        # Initialize communication
        initialize_communication(workspace_root)
        print("✅ Communication initialized")
        
        # Create templates
        create_templates(workspace_root)
        print("✅ Templates created")
        
        # Create documentation
        create_readme(workspace_root)
        print("✅ Documentation created")
        
        print("\n🎉 Agent Framework Setup Complete!")
        print(f"Workspace: {workspace_root}")
        print("\nNext steps:")
        print("1. Review configuration: shared/config/agent_config.yaml")
        print("2. Run Test Agent: python test_agent/test_agent.py")
        print("3. Check framework status in agent workspaces")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())