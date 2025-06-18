"""
Deploy Agent Framework

Created: 2025-06-16 with user permission
Purpose: Deploy and configure complete three-agent framework

Intent: Orchestrates the complete deployment of the three-agent framework including
communication infrastructure, workspace initialization, and agent configuration.
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging
import json

# Add framework to path
framework_path = Path(__file__).parent
if str(framework_path) not in sys.path:
    sys.path.insert(0, str(framework_path))

from setup_communication_infrastructure import CommunicationInfrastructureSetup
from initialize_agent_workspaces import AgentWorkspaceInitializer
from shared.config.agent_config import ConfigurationManager


class AgentFrameworkDeployer:
    """Complete deployment orchestrator for three-agent framework"""
    
    def __init__(self, deployment_path: Path):
        self.deployment_path = deployment_path
        self.framework_path = framework_path
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Deployment components
        self.communication_setup = None
        self.workspace_initializer = None
        self.config_manager = None
        
        # Deployment results
        self.deployment_results = {
            'start_time': datetime.utcnow(),
            'deployment_path': str(deployment_path),
            'phases_completed': [],
            'phase_results': {},
            'success': False,
            'errors': []
        }
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        
        # Create logs directory
        logs_dir = self.deployment_path / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / 'deployment.log'),
                logging.StreamHandler()
            ]
        )
    
    def deploy_complete_framework(self) -> Dict[str, Any]:
        """Deploy complete three-agent framework"""
        
        self.logger.info("Starting complete three-agent framework deployment...")
        
        try:
            # Phase 1: Pre-deployment validation
            self._execute_phase("pre_deployment_validation", self._pre_deployment_validation)
            
            # Phase 2: Setup communication infrastructure
            self._execute_phase("communication_infrastructure", self._setup_communication_infrastructure)
            
            # Phase 3: Initialize agent workspaces
            self._execute_phase("workspace_initialization", self._initialize_agent_workspaces)
            
            # Phase 4: Configure agent framework
            self._execute_phase("framework_configuration", self._configure_agent_framework)
            
            # Phase 5: Deploy monitoring and alerting
            self._execute_phase("monitoring_deployment", self._deploy_monitoring_system)
            
            # Phase 6: Validate complete deployment
            self._execute_phase("deployment_validation", self._validate_complete_deployment)
            
            # Phase 7: Generate deployment documentation
            self._execute_phase("documentation_generation", self._generate_deployment_documentation)
            
            # Phase 8: Create management scripts
            self._execute_phase("management_scripts", self._create_management_scripts)
            
            self.deployment_results['success'] = True
            self.deployment_results['end_time'] = datetime.utcnow()
            
            self.logger.info("Three-agent framework deployment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Framework deployment failed: {e}")
            self.deployment_results['errors'].append(str(e))
            self.deployment_results['success'] = False
            self.deployment_results['end_time'] = datetime.utcnow()
        
        # Save deployment results
        self._save_deployment_results()
        
        return self.deployment_results
    
    def _execute_phase(self, phase_name: str, phase_function):
        """Execute deployment phase with error handling"""
        
        self.logger.info(f"Executing phase: {phase_name}")
        
        try:
            phase_result = phase_function()
            self.deployment_results['phases_completed'].append(phase_name)
            self.deployment_results['phase_results'][phase_name] = phase_result
            
            self.logger.info(f"Phase {phase_name} completed successfully")
            
        except Exception as e:
            error_msg = f"Phase {phase_name} failed: {e}"
            self.logger.error(error_msg)
            self.deployment_results['errors'].append(error_msg)
            raise
    
    def _pre_deployment_validation(self) -> Dict[str, Any]:
        """Validate pre-deployment requirements"""
        
        validation_results = {
            'python_version': self._check_python_version(),
            'required_packages': self._check_required_packages(),
            'directory_permissions': self._check_directory_permissions(),
            'system_resources': self._check_system_resources()
        }
        
        all_valid = all(result['valid'] for result in validation_results.values())
        
        if not all_valid:
            raise Exception("Pre-deployment validation failed")
        
        return {
            'success': True,
            'validations': validation_results
        }
    
    def _check_python_version(self) -> Dict[str, Any]:
        """Check Python version requirements"""
        
        import sys
        
        required_version = (3, 8)
        current_version = sys.version_info[:2]
        
        valid = current_version >= required_version
        
        return {
            'valid': valid,
            'required': f"{required_version[0]}.{required_version[1]}+",
            'current': f"{current_version[0]}.{current_version[1]}",
            'message': 'Python version check passed' if valid else f'Python {required_version[0]}.{required_version[1]}+ required'
        }
    
    def _check_required_packages(self) -> Dict[str, Any]:
        """Check required Python packages"""
        
        required_packages = ['yaml', 'pathlib', 'dataclasses', 'typing', 'datetime', 'json']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        valid = len(missing_packages) == 0
        
        return {
            'valid': valid,
            'required_packages': required_packages,
            'missing_packages': missing_packages,
            'message': 'All required packages available' if valid else f'Missing packages: {missing_packages}'
        }
    
    def _check_directory_permissions(self) -> Dict[str, Any]:
        """Check directory permissions"""
        
        try:
            # Test directory creation
            test_dir = self.deployment_path / '.permission_test'
            test_dir.mkdir(exist_ok=True)
            
            # Test file creation
            test_file = test_dir / 'test_file.txt'
            test_file.write_text('test')
            
            # Test file reading
            content = test_file.read_text()
            
            # Cleanup
            test_file.unlink()
            test_dir.rmdir()
            
            return {
                'valid': True,
                'message': 'Directory permissions are sufficient'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Insufficient directory permissions: {e}'
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources"""
        
        import shutil
        
        # Check disk space (require at least 1GB)
        try:
            free_space = shutil.disk_usage(self.deployment_path).free
            required_space = 1024 * 1024 * 1024  # 1GB
            
            space_sufficient = free_space >= required_space
            
            return {
                'valid': space_sufficient,
                'free_space_gb': round(free_space / (1024**3), 2),
                'required_space_gb': 1.0,
                'message': 'Sufficient disk space' if space_sufficient else 'Insufficient disk space'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Could not check disk space: {e}'
            }
    
    def _setup_communication_infrastructure(self) -> Dict[str, Any]:
        """Setup communication infrastructure"""
        
        self.logger.info("Setting up communication infrastructure...")
        
        self.communication_setup = CommunicationInfrastructureSetup(self.deployment_path)
        infrastructure_result = self.communication_setup.initialize_infrastructure()
        
        if not infrastructure_result['success']:
            raise Exception("Communication infrastructure setup failed")
        
        return infrastructure_result
    
    def _initialize_agent_workspaces(self) -> Dict[str, Any]:
        """Initialize agent workspaces"""
        
        self.logger.info("Initializing agent workspaces...")
        
        self.workspace_initializer = AgentWorkspaceInitializer(self.deployment_path)
        workspace_result = self.workspace_initializer.initialize_all_workspaces()
        
        if not workspace_result['success']:
            raise Exception("Agent workspace initialization failed")
        
        return workspace_result
    
    def _configure_agent_framework(self) -> Dict[str, Any]:
        """Configure agent framework"""
        
        self.logger.info("Configuring agent framework...")
        
        # Initialize configuration manager
        config_path = self.deployment_path / 'shared' / 'config'
        self.config_manager = ConfigurationManager(config_path)
        
        # Configure framework settings
        framework_settings = {
            'deployment_date': datetime.utcnow().isoformat(),
            'deployment_path': str(self.deployment_path),
            'framework_version': '1.0.0',
            'agents_enabled': ['test_agent', 'code_agent', 'integration_agent'],
            'communication_enabled': True,
            'monitoring_enabled': True,
            'logging_level': 'INFO'
        }
        
        for setting, value in framework_settings.items():
            self.config_manager.set_global_setting(setting, value)
        
        # Validate configuration
        validation_issues = self.config_manager.validate_configuration()
        
        if validation_issues:
            raise Exception(f"Configuration validation failed: {validation_issues}")
        
        return {
            'success': True,
            'framework_settings': framework_settings,
            'validation_issues': validation_issues
        }
    
    def _deploy_monitoring_system(self) -> Dict[str, Any]:
        """Deploy monitoring and alerting system"""
        
        self.logger.info("Deploying monitoring system...")
        
        # Create monitoring configuration
        monitoring_config = {
            'enabled': True,
            'collection_interval_seconds': 300,  # 5 minutes
            'retention_days': 90,
            'metrics': {
                'progress_tracking': True,
                'performance_monitoring': True,
                'quality_assessment': True,
                'communication_monitoring': True
            },
            'alerts': {
                'enabled': True,
                'email_notifications': False,
                'log_notifications': True,
                'thresholds': {
                    'completion_delay_hours': 24,
                    'quality_score_minimum': 0.8,
                    'error_rate_maximum': 0.05
                }
            }
        }
        
        # Save monitoring configuration
        monitoring_path = self.deployment_path / 'shared' / 'monitoring'
        monitoring_path.mkdir(parents=True, exist_ok=True)
        
        with open(monitoring_path / 'monitoring_config.json', 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        
        # Create monitoring directories
        monitoring_dirs = [
            'metrics',
            'logs',
            'alerts',
            'reports'
        ]
        
        for directory in monitoring_dirs:
            (monitoring_path / directory).mkdir(exist_ok=True)
        
        return {
            'success': True,
            'monitoring_config': monitoring_config,
            'monitoring_path': str(monitoring_path)
        }
    
    def _validate_complete_deployment(self) -> Dict[str, Any]:
        """Validate complete deployment"""
        
        self.logger.info("Validating complete deployment...")
        
        validation_results = {
            'communication_infrastructure': self._validate_communication_infrastructure(),
            'agent_workspaces': self._validate_agent_workspaces(),
            'framework_configuration': self._validate_framework_configuration(),
            'monitoring_system': self._validate_monitoring_system()
        }
        
        overall_success = all(result['success'] for result in validation_results.values())
        
        if not overall_success:
            failed_components = [name for name, result in validation_results.items() if not result['success']]
            raise Exception(f"Deployment validation failed for: {failed_components}")
        
        return {
            'success': overall_success,
            'component_validations': validation_results
        }
    
    def _validate_communication_infrastructure(self) -> Dict[str, Any]:
        """Validate communication infrastructure"""
        
        if not self.communication_setup:
            return {'success': False, 'message': 'Communication setup not initialized'}
        
        status = self.communication_setup.get_infrastructure_status()
        
        return {
            'success': status['infrastructure_initialized'],
            'status': status
        }
    
    def _validate_agent_workspaces(self) -> Dict[str, Any]:
        """Validate agent workspaces"""
        
        if not self.workspace_initializer:
            return {'success': False, 'message': 'Workspace initializer not available'}
        
        validation_result = self.workspace_initializer._validate_all_workspaces()
        
        return {
            'success': validation_result['overall_success'],
            'validation_details': validation_result
        }
    
    def _validate_framework_configuration(self) -> Dict[str, Any]:
        """Validate framework configuration"""
        
        if not self.config_manager:
            return {'success': False, 'message': 'Configuration manager not available'}
        
        validation_issues = self.config_manager.validate_configuration()
        
        return {
            'success': len(validation_issues) == 0,
            'validation_issues': validation_issues
        }
    
    def _validate_monitoring_system(self) -> Dict[str, Any]:
        """Validate monitoring system"""
        
        monitoring_path = self.deployment_path / 'shared' / 'monitoring'
        
        if not monitoring_path.exists():
            return {'success': False, 'message': 'Monitoring directory not found'}
        
        config_file = monitoring_path / 'monitoring_config.json'
        
        if not config_file.exists():
            return {'success': False, 'message': 'Monitoring configuration not found'}
        
        return {
            'success': True,
            'monitoring_path': str(monitoring_path),
            'config_file': str(config_file)
        }
    
    def _generate_deployment_documentation(self) -> Dict[str, Any]:
        """Generate deployment documentation"""
        
        self.logger.info("Generating deployment documentation...")
        
        # Create documentation directory
        docs_path = self.deployment_path / 'docs'
        docs_path.mkdir(exist_ok=True)
        
        # Generate deployment guide
        deployment_guide = self._create_deployment_guide()
        with open(docs_path / 'deployment_guide.md', 'w') as f:
            f.write(deployment_guide)
        
        # Generate user manual
        user_manual = self._create_user_manual()
        with open(docs_path / 'user_manual.md', 'w') as f:
            f.write(user_manual)
        
        # Generate troubleshooting guide
        troubleshooting_guide = self._create_troubleshooting_guide()
        with open(docs_path / 'troubleshooting.md', 'w') as f:
            f.write(troubleshooting_guide)
        
        # Generate API reference
        api_reference = self._create_api_reference()
        with open(docs_path / 'api_reference.md', 'w') as f:
            f.write(api_reference)
        
        return {
            'success': True,
            'documentation_path': str(docs_path),
            'generated_documents': [
                'deployment_guide.md',
                'user_manual.md', 
                'troubleshooting.md',
                'api_reference.md'
            ]
        }
    
    def _create_deployment_guide(self) -> str:
        """Create deployment guide documentation"""
        
        return f"""# Three-Agent Framework Deployment Guide

**Deployment Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
**Framework Version:** 1.0.0
**Deployment Path:** {self.deployment_path}

## Overview

This document provides a complete guide for the deployed three-agent implementation framework.

## Architecture

The framework consists of three specialized agents:

1. **Test Agent**: Creates comprehensive test suites and validation frameworks
2. **Code Agent**: Implements interface contracts and algorithms with performance optimization
3. **Integration Agent**: Executes tests, resolves conflicts, and validates system quality

## Directory Structure

```
{self.deployment_path.name}/
├── test_agent/           # Test Agent workspace
├── code_agent/           # Code Agent workspace  
├── integration_agent/    # Integration Agent workspace
├── shared/               # Shared resources and communication
├── logs/                 # Framework logs
├── docs/                 # Documentation
└── scripts/              # Management scripts
```

## Communication Infrastructure

The framework uses a multi-layer communication architecture:

- **Message Transport Layer**: Reliable message passing between agents
- **Handoff Management**: Automated validation and processing of work handoffs
- **Status Communication**: Real-time progress tracking and coordination
- **Quality Monitoring**: Continuous quality metrics collection and reporting

## Agent Workspaces

Each agent has an isolated workspace with:

- **workspace/**: Main development environment
- **templates/**: Handoff package templates
- **output/**: Generated results and reports
- **tools/**: Agent-specific development tools
- **examples/**: Example packages and workflows

## Configuration

Framework configuration is managed centrally:

- **Global Settings**: `shared/config/global_settings.yaml`
- **Agent Configurations**: `shared/config/agents/*.yaml`
- **Monitoring Config**: `shared/monitoring/monitoring_config.json`

## Starting the Framework

To start working with the framework:

1. Review agent workspaces and templates
2. Configure agent settings as needed
3. Use management scripts for common operations
4. Monitor progress through status reports

## Quality Gates

The framework enforces quality gates at each handoff:

- Requirements coverage validation
- Implementation completeness checks
- Performance benchmark verification
- Quality metrics assessment

## Support

For support:

1. Check troubleshooting guide
2. Review agent workspace documentation
3. Consult API reference
4. Contact implementation orchestrator

---

*Generated by Three-Agent Framework Deployer v1.0.0*
"""
    
    def _create_user_manual(self) -> str:
        """Create user manual"""
        
        return """# Three-Agent Framework User Manual

## Getting Started

### Overview

The Three-Agent Framework enables systematic development through specialized agents:

- **Test Agent**: Focus on comprehensive testing and validation
- **Code Agent**: Focus on implementation and performance
- **Integration Agent**: Focus on integration and quality assurance

### Basic Workflow

1. **Requirements Analysis**: Break down user stories into agent tasks
2. **Parallel Development**: Test and Code agents work simultaneously
3. **Integration**: Integration agent validates and resolves conflicts
4. **Quality Assurance**: Framework ensures all quality gates are met

### Using Agent Workspaces

Each agent workspace provides:

- **Templates**: Pre-structured handoff packages
- **Tools**: Agent-specific development utilities
- **Examples**: Reference implementations and workflows
- **Documentation**: Workspace-specific guides

### Handoff Packages

Work is transferred between agents using structured handoff packages:

- **Test Agent Packages**: Test requirements and behavioral specifications
- **Code Agent Packages**: Interface contracts and implementation specifications
- **Integration Agent Packages**: Integration plans and success criteria

### Communication

Agents communicate through:

- **Status Updates**: Regular progress reporting
- **Blocking Issues**: Escalation of problems requiring assistance
- **Milestone Completion**: Notification of completed work phases
- **Dependency Requests**: Coordination of cross-agent dependencies

### Quality Monitoring

The framework continuously monitors:

- **Progress Metrics**: Completion percentages and timeline adherence
- **Quality Metrics**: Code quality, test coverage, performance benchmarks
- **Communication Metrics**: Response times and coordination effectiveness

### Best Practices

1. **Clear Requirements**: Ensure acceptance criteria are quantifiable
2. **Regular Communication**: Provide frequent status updates
3. **Quality Focus**: Maintain high standards throughout development
4. **Documentation**: Document all assumptions and design decisions

### Troubleshooting

Common issues and solutions:

- **Handoff Validation Failures**: Check package completeness and format
- **Communication Issues**: Verify agent configurations and workspace paths
- **Quality Gate Failures**: Review quality metrics and improvement recommendations

---

*For detailed technical information, see the API Reference and Troubleshooting Guide*
"""
    
    def _create_troubleshooting_guide(self) -> str:
        """Create troubleshooting guide"""
        
        return """# Three-Agent Framework Troubleshooting Guide

## Common Issues

### Framework Deployment Issues

**Issue**: Deployment fails during infrastructure setup
**Solution**: 
1. Check Python version (3.8+ required)
2. Verify directory permissions
3. Ensure sufficient disk space (1GB+)
4. Review deployment logs

**Issue**: Agent workspace initialization fails
**Solution**:
1. Verify base workspace path exists
2. Check file system permissions
3. Review workspace initialization logs
4. Validate configuration settings

### Communication Issues

**Issue**: Messages not being delivered between agents
**Solution**:
1. Check agent workspace paths in configuration
2. Verify message transport layer initialization
3. Review communication logs
4. Test message routing configuration

**Issue**: Handoff package validation fails
**Solution**:
1. Validate package structure against templates
2. Check required fields and sections
3. Verify package content completeness
4. Review validation error messages

### Agent Workspace Issues

**Issue**: Agent tools not working correctly
**Solution**:
1. Verify tool script permissions (should be executable)
2. Check Python environment and dependencies
3. Validate workspace directory structure
4. Review tool-specific error messages

**Issue**: Configuration validation fails
**Solution**:
1. Check configuration file format (YAML syntax)
2. Verify all required fields are present
3. Validate configuration values and types
4. Review global and agent-specific settings

### Quality and Performance Issues

**Issue**: Quality gates failing repeatedly
**Solution**:
1. Review quality thresholds and requirements
2. Check implementation against interface contracts
3. Validate test coverage and quality metrics
4. Improve code quality and documentation

**Issue**: Performance benchmarks not being met
**Solution**:
1. Profile implementation performance
2. Optimize algorithms and data structures
3. Review resource constraints and limits
4. Update performance requirements if necessary

### Monitoring and Logging Issues

**Issue**: Monitoring not collecting metrics
**Solution**:
1. Check monitoring configuration settings
2. Verify monitoring system deployment
3. Review monitoring logs for errors
4. Validate metrics collection permissions

**Issue**: Log files not being generated
**Solution**:
1. Check logging configuration
2. Verify log directory permissions
3. Review log level settings
4. Ensure proper logger initialization

## Diagnostic Commands

### Check Framework Status

```bash
# Check overall framework status
python scripts/framework_status.py

# Check specific agent workspace
python scripts/agent_status.py test_agent

# Validate configuration
python scripts/validate_config.py
```

### Debug Communication

```bash
# Test message transport
python scripts/test_communication.py

# Check message queues
python scripts/check_messages.py

# Validate handoff packages
python scripts/validate_handoff.py <package_path>
```

### Monitor Quality Metrics

```bash
# Generate quality report
python scripts/quality_report.py

# Check performance metrics
python scripts/performance_check.py

# Validate quality gates
python scripts/quality_gates.py
```

## Log Analysis

### Key Log Locations

- **Framework Logs**: `logs/deployment.log`
- **Communication Logs**: `shared/communication/logs/`
- **Agent Logs**: `<agent_name>/logs/`
- **Monitoring Logs**: `shared/monitoring/logs/`

### Important Log Patterns

- `ERROR`: Critical issues requiring immediate attention
- `WARNING`: Issues that may impact functionality
- `INFO`: Normal operational information
- `DEBUG`: Detailed diagnostic information

## Getting Help

1. **Check Documentation**: Review deployment guide and user manual
2. **Search Logs**: Look for error messages and warnings
3. **Validate Configuration**: Ensure all settings are correct
4. **Test Components**: Use diagnostic commands to isolate issues
5. **Contact Support**: Reach out to implementation orchestrator

---

*Keep this guide handy for quick issue resolution*
"""
    
    def _create_api_reference(self) -> str:
        """Create API reference"""
        
        return """# Three-Agent Framework API Reference

## Core Components

### ConfigurationManager

Manages framework and agent configurations.

```python
from shared.config.agent_config import ConfigurationManager

# Initialize configuration manager
config_manager = ConfigurationManager(config_path)

# Create agent configuration
config = config_manager.create_agent_configuration(
    agent_name="test_agent",
    agent_type="test_agent", 
    workspace_path=workspace_path
)

# Get agent configuration
config = config_manager.get_agent_configuration("test_agent")

# Update configuration
config_manager.update_agent_configuration("test_agent", updates)
```

### MessageTransportLayer

Handles message transport between agents.

```python
from shared.communication.message_transport import MessageTransportLayer, AgentMessage

# Initialize transport layer
transport = MessageTransportLayer(workspace_path)

# Create message
message = AgentMessage(
    message_id="msg_001",
    sender="test_agent",
    recipient="code_agent",
    message_type="progress_update",
    content={"status": "in_progress"},
    timestamp=datetime.utcnow(),
    priority=MessagePriority.NORMAL
)

# Send message
result = transport.send_message(message, transport_requirements)
```

### HandoffTriggerFramework

Manages handoff validation and processing.

```python
from shared.communication.handoff_management import HandoffTriggerFramework, HandoffRequest

# Initialize handoff framework
handoff_framework = HandoffTriggerFramework()

# Evaluate handoff readiness
evaluation = handoff_framework.evaluate_handoff_readiness(
    agent="test_agent",
    handoff_request=handoff_request
)

# Check if ready for handoff
if evaluation.is_ready_for_handoff():
    # Process handoff
    pass
```

### StatusCommunicationProtocols

Handles status communication between agents.

```python
from shared.communication.status_communication import StatusCommunicationProtocols, AgentProgress

# Initialize status protocols
status_protocols = StatusCommunicationProtocols(workspace_path)

# Send status update
result = status_protocols.send_status_update(
    sender_agent="test_agent",
    message_type="progress_update",
    message_content=agent_progress
)

# Get status messages
messages = status_protocols.get_status_messages("test_agent")
```

### AgentProgressTracker

Tracks agent progress and milestones.

```python
from shared.communication.status_communication import AgentProgressTracker, Milestone

# Initialize progress tracker
tracker = AgentProgressTracker("test_agent", workspace_path)

# Add milestone
milestone = Milestone(
    milestone_id="milestone_001",
    name="Test Suite Creation",
    description="Create comprehensive test suite",
    target_date=datetime.utcnow() + timedelta(days=7)
)
tracker.add_milestone(milestone)

# Update progress
tracker.update_milestone_progress("milestone_001", 75.0)

# Get current progress
progress = tracker.get_current_progress()
```

## Data Structures

### AgentMessage

```python
@dataclass
class AgentMessage:
    message_id: str
    sender: str
    recipient: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority
    correlation_id: Optional[str] = None
```

### HandoffPackage

```python
@dataclass
class HandoffPackage:
    package_id: str
    package_type: str  # test_agent, code_agent, integration_agent
    user_story_id: str
    created_date: datetime
    version: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### AgentProgress

```python
@dataclass
class AgentProgress:
    agent_name: str
    current_milestone: str
    completion_percentage: float
    estimated_completion_time: Optional[datetime]
    recent_achievements: List[str] = field(default_factory=list)
    blocking_issues: List[BlockingIssue] = field(default_factory=list)
```

## Enumerations

### MessagePriority

```python
class MessagePriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
```

### ValidationStatus

```python
class ValidationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"
```

### ProgressStatus

```python
class ProgressStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
```

## Configuration Files

### Global Settings

`shared/config/global_settings.yaml`

```yaml
framework_version: '1.0.0'
communication_enabled: true
monitoring_enabled: true
logging_level: 'INFO'
max_concurrent_agents: 3
```

### Agent Configuration

`shared/config/agents/test_agent.yaml`

```yaml
agent_name: test_agent
agent_type: test_agent
workspace_path: /path/to/test_agent
communication_settings:
  transport_protocol: synchronous
  message_timeout_seconds: 300
monitoring_settings:
  progress_update_interval_seconds: 900
  metrics_collection_enabled: true
```

---

*This API reference covers the core framework components. For detailed implementation examples, see the agent workspace examples directories.*
"""
    
    def _create_management_scripts(self) -> Dict[str, Any]:
        """Create management scripts"""
        
        self.logger.info("Creating management scripts...")
        
        scripts_path = self.deployment_path / 'scripts'
        scripts_path.mkdir(exist_ok=True)
        
        # Framework status script
        framework_status_script = '''#!/usr/bin/env python3
"""
Framework Status Script

Check overall framework status and health
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add framework to path
framework_path = Path(__file__).parent.parent
sys.path.insert(0, str(framework_path))

from shared.config.agent_config import ConfigurationManager


def main():
    """Check framework status"""
    
    print("Three-Agent Framework Status")
    print("=" * 40)
    
    # Check configuration
    config_path = framework_path / 'shared' / 'config'
    if config_path.exists():
        config_manager = ConfigurationManager(config_path)
        
        # Get global settings
        framework_version = config_manager.get_global_setting('framework_version', 'Unknown')
        deployment_date = config_manager.get_global_setting('deployment_date', 'Unknown')
        
        print(f"Framework Version: {framework_version}")
        print(f"Deployment Date: {deployment_date}")
        print()
        
        # Check agent configurations
        print("Agent Configurations:")
        agents = ['test_agent', 'code_agent', 'integration_agent']
        
        for agent in agents:
            config = config_manager.get_agent_configuration(agent)
            if config:
                workspace_exists = config.workspace_path.exists()
                status = "✓ Active" if workspace_exists else "✗ Workspace Missing"
                print(f"  {agent}: {status}")
            else:
                print(f"  {agent}: ✗ Configuration Missing")
        
        print()
        
        # Validation
        validation_issues = config_manager.validate_configuration()
        if validation_issues:
            print("Configuration Issues:")
            for agent, issues in validation_issues.items():
                print(f"  {agent}:")
                for issue in issues:
                    print(f"    - {issue}")
        else:
            print("✓ Configuration Valid")
    
    else:
        print("✗ Framework configuration not found")


if __name__ == "__main__":
    main()
'''
        
        with open(scripts_path / 'framework_status.py', 'w') as f:
            f.write(framework_status_script)
        
        # Make executable
        (scripts_path / 'framework_status.py').chmod(0o755)
        
        # Agent status script
        agent_status_script = '''#!/usr/bin/env python3
"""
Agent Status Script

Check specific agent status and workspace
"""

import sys
import json
from pathlib import Path

# Add framework to path
framework_path = Path(__file__).parent.parent
sys.path.insert(0, str(framework_path))

from shared.config.agent_config import ConfigurationManager


def main():
    """Check agent status"""
    
    if len(sys.argv) != 2:
        print("Usage: agent_status.py <agent_name>")
        print("Available agents: test_agent, code_agent, integration_agent")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    
    print(f"Agent Status: {agent_name}")
    print("=" * 40)
    
    # Check configuration
    config_path = framework_path / 'shared' / 'config'
    if not config_path.exists():
        print("✗ Framework configuration not found")
        sys.exit(1)
    
    config_manager = ConfigurationManager(config_path)
    agent_config = config_manager.get_agent_configuration(agent_name)
    
    if not agent_config:
        print(f"✗ Configuration not found for {agent_name}")
        sys.exit(1)
    
    print(f"Agent Type: {agent_config.agent_type}")
    print(f"Workspace: {agent_config.workspace_path}")
    print()
    
    # Check workspace
    if agent_config.workspace_path.exists():
        print("✓ Workspace exists")
        
        # Check workspace structure
        required_dirs = ['workspace', 'templates', 'output', 'tools']
        for directory in required_dirs:
            dir_path = agent_config.workspace_path / directory
            status = "✓" if dir_path.exists() else "✗"
            print(f"  {status} {directory}/")
    else:
        print("✗ Workspace does not exist")
    
    print()
    
    # Check recent activity
    logs_path = agent_config.workspace_path / 'logs'
    if logs_path.exists():
        log_files = list(logs_path.glob('*.log'))
        print(f"Log files: {len(log_files)}")
    
    # Check configuration
    print("Configuration:")
    print(f"  Communication: {agent_config.communication_settings.get('transport_protocol', 'Not configured')}")
    print(f"  Monitoring: {'Enabled' if agent_config.monitoring_settings.get('metrics_collection_enabled') else 'Disabled'}")


if __name__ == "__main__":
    main()
'''
        
        with open(scripts_path / 'agent_status.py', 'w') as f:
            f.write(agent_status_script)
        
        # Make executable
        (scripts_path / 'agent_status.py').chmod(0o755)
        
        return {
            'success': True,
            'scripts_path': str(scripts_path),
            'scripts_created': [
                'framework_status.py',
                'agent_status.py'
            ]
        }
    
    def _save_deployment_results(self):
        """Save deployment results"""
        
        results_file = self.deployment_path / 'deployment_results.json'
        
        # Convert datetime objects to strings for JSON serialization
        serializable_results = {}
        for key, value in self.deployment_results.items():
            if isinstance(value, datetime):
                serializable_results[key] = value.isoformat()
            else:
                serializable_results[key] = value
        
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        self.logger.info(f"Deployment results saved to: {results_file}")


def main():
    """Main deployment function"""
    
    # Get deployment path from environment or use default
    import os
    deployment_path = Path(os.getenv('AGENT_DEPLOYMENT_PATH', 
                                    Path(__file__).parent.parent / 'agent_workspaces'))
    
    print(f"Deploying three-agent framework to: {deployment_path}")
    print()
    
    # Deploy framework
    deployer = AgentFrameworkDeployer(deployment_path)
    results = deployer.deploy_complete_framework()
    
    # Print results
    print("\n" + "="*60)
    print("THREE-AGENT FRAMEWORK DEPLOYMENT RESULTS")
    print("="*60)
    print(f"Success: {results['success']}")
    print(f"Deployment Path: {results['deployment_path']}")
    
    if 'end_time' in results:
        duration = (results['end_time'] - results['start_time']).total_seconds()
        print(f"Duration: {duration:.2f} seconds")
    
    print(f"\nPhases Completed ({len(results['phases_completed'])}):")
    for phase in results['phases_completed']:
        print(f"  ✓ {phase}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  ✗ {error}")
    
    # Print summary of what was deployed
    if results['success']:
        print(f"\n🎉 DEPLOYMENT SUCCESSFUL!")
        print(f"\nWhat was deployed:")
        print(f"  • Communication infrastructure with message transport and routing")
        print(f"  • Three agent workspaces with templates and tools")
        print(f"  • Configuration management system")
        print(f"  • Monitoring and alerting system")
        print(f"  • Complete documentation and management scripts")
        
        print(f"\nNext steps:")
        print(f"  1. Review agent workspaces and templates")
        print(f"  2. Check framework status: python scripts/framework_status.py")
        print(f"  3. Explore agent workspaces: {deployment_path}/*/README.md")
        print(f"  4. Read user manual: {deployment_path}/docs/user_manual.md")
    
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"\nCheck logs and errors above for troubleshooting guidance")
        print(f"See: {deployment_path}/logs/deployment.log")
    
    print("\n" + "="*60)
    
    return results


if __name__ == "__main__":
    main()