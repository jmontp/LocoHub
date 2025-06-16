"""
Setup Communication Infrastructure

Created: 2025-06-16 with user permission
Purpose: Initialize agent communication infrastructure

Intent: Sets up the complete communication infrastructure including message transport,
handoff management, status tracking, and quality monitoring for the three-agent framework.
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add framework to path
framework_path = Path(__file__).parent
if str(framework_path) not in sys.path:
    sys.path.insert(0, str(framework_path))

from shared.communication.message_transport import MessageTransportLayer, MessageRouter
from shared.communication.handoff_management import HandoffTriggerFramework
from shared.communication.status_communication import StatusCommunicationProtocols
from shared.config.agent_config import ConfigurationManager


class CommunicationInfrastructureSetup:
    """Setup and initialize communication infrastructure"""
    
    def __init__(self, base_workspace_path: Path):
        self.base_workspace_path = base_workspace_path
        self.framework_path = framework_path
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.config_manager = None
        self.message_router = None
        self.transport_layer = None
        self.handoff_framework = None
        self.status_protocols = None
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.framework_path / 'communication_setup.log'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_infrastructure(self) -> dict:
        """Initialize complete communication infrastructure"""
        
        self.logger.info("Starting communication infrastructure initialization...")
        
        results = {
            'start_time': datetime.utcnow(),
            'success': False,
            'components_initialized': [],
            'errors': [],
            'workspace_path': str(self.base_workspace_path)
        }
        
        try:
            # Step 1: Setup workspace structure
            self._setup_workspace_structure()
            results['components_initialized'].append('workspace_structure')
            
            # Step 2: Initialize configuration management
            self._initialize_configuration_management()
            results['components_initialized'].append('configuration_management')
            
            # Step 3: Setup message transport layer
            self._setup_message_transport()
            results['components_initialized'].append('message_transport')
            
            # Step 4: Initialize message routing
            self._setup_message_routing()
            results['components_initialized'].append('message_routing')
            
            # Step 5: Setup handoff management
            self._setup_handoff_management()
            results['components_initialized'].append('handoff_management')
            
            # Step 6: Initialize status communication
            self._setup_status_communication()
            results['components_initialized'].append('status_communication')
            
            # Step 7: Create agent configurations
            self._create_agent_configurations()
            results['components_initialized'].append('agent_configurations')
            
            # Step 8: Validate infrastructure
            validation_result = self._validate_infrastructure()
            results['validation'] = validation_result
            
            results['success'] = True
            results['end_time'] = datetime.utcnow()
            
            self.logger.info("Communication infrastructure initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Infrastructure initialization failed: {e}")
            results['errors'].append(str(e))
            results['success'] = False
            results['end_time'] = datetime.utcnow()
        
        return results
    
    def _setup_workspace_structure(self):
        """Setup workspace directory structure"""
        self.logger.info("Setting up workspace structure...")
        
        # Create base workspace
        self.base_workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Create agent workspaces
        agent_workspaces = {
            'test_agent': self.base_workspace_path / 'test_agent',
            'code_agent': self.base_workspace_path / 'code_agent', 
            'integration_agent': self.base_workspace_path / 'integration_agent',
            'orchestrator': self.base_workspace_path / 'orchestrator'
        }
        
        for agent_name, workspace_path in agent_workspaces.items():
            # Create main workspace directories
            workspace_dirs = [
                workspace_path / 'workspace',
                workspace_path / 'templates',
                workspace_path / 'output',
                workspace_path / 'inbox',
                workspace_path / 'outbox',
                workspace_path / 'status_messages',
                workspace_path / 'handoff_packages',
                workspace_path / 'logs'
            ]
            
            for directory in workspace_dirs:
                directory.mkdir(parents=True, exist_ok=True)
        
        # Create shared workspace
        shared_workspace = self.base_workspace_path / 'shared'
        shared_dirs = [
            shared_workspace / 'communication',
            shared_workspace / 'templates',
            shared_workspace / 'monitoring',
            shared_workspace / 'config',
            shared_workspace / 'logs'
        ]
        
        for directory in shared_dirs:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Workspace structure created successfully")
    
    def _initialize_configuration_management(self):
        """Initialize configuration management"""
        self.logger.info("Initializing configuration management...")
        
        config_path = self.base_workspace_path / 'shared' / 'config'
        self.config_manager = ConfigurationManager(config_path)
        
        # Create default framework configuration
        self.config_manager.create_default_framework_configuration()
        
        self.logger.info("Configuration management initialized")
    
    def _setup_message_transport(self):
        """Setup message transport layer"""
        self.logger.info("Setting up message transport layer...")
        
        communication_workspace = self.base_workspace_path / 'shared' / 'communication'
        self.transport_layer = MessageTransportLayer(communication_workspace)
        
        self.logger.info("Message transport layer initialized")
    
    def _setup_message_routing(self):
        """Setup message routing"""
        self.logger.info("Setting up message routing...")
        
        communication_workspace = self.base_workspace_path / 'shared' / 'communication'
        self.message_router = MessageRouter(communication_workspace)
        
        # Register agents for message types
        agent_message_types = {
            'test_agent': [
                'handoff_request', 'progress_update', 'test_completion',
                'blocking_issue', 'quality_report'
            ],
            'code_agent': [
                'handoff_request', 'progress_update', 'implementation_completion',
                'blocking_issue', 'performance_report'
            ],
            'integration_agent': [
                'handoff_request', 'progress_update', 'integration_result',
                'conflict_escalation', 'resolution_coordination'
            ],
            'orchestrator': [
                'progress_update', 'milestone_completion', 'blocking_issue',
                'dependency_request', 'quality_alert', 'escalation'
            ]
        }
        
        for agent_name, message_types in agent_message_types.items():
            self.message_router.register_agent(agent_name, message_types)
        
        self.logger.info("Message routing configured")
    
    def _setup_handoff_management(self):
        """Setup handoff management framework"""
        self.logger.info("Setting up handoff management...")
        
        self.handoff_framework = HandoffTriggerFramework()
        
        self.logger.info("Handoff management framework initialized")
    
    def _setup_status_communication(self):
        """Setup status communication protocols"""
        self.logger.info("Setting up status communication...")
        
        communication_workspace = self.base_workspace_path / 'shared' / 'communication'
        self.status_protocols = StatusCommunicationProtocols(communication_workspace)
        
        self.logger.info("Status communication protocols initialized")
    
    def _create_agent_configurations(self):
        """Create configurations for all agents"""
        self.logger.info("Creating agent configurations...")
        
        agents = [
            ('test_agent', 'test_agent'),
            ('code_agent', 'code_agent'),
            ('integration_agent', 'integration_agent'),
            ('orchestrator', 'orchestrator')
        ]
        
        for agent_name, agent_type in agents:
            workspace_path = self.base_workspace_path / agent_name
            
            config = self.config_manager.create_agent_configuration(
                agent_name=agent_name,
                agent_type=agent_type,
                workspace_path=workspace_path
            )
            
            self.logger.info(f"Configuration created for {agent_name}")
        
        self.logger.info("Agent configurations created")
    
    def _validate_infrastructure(self) -> dict:
        """Validate infrastructure setup"""
        self.logger.info("Validating infrastructure setup...")
        
        validation_results = {
            'workspace_structure': self._validate_workspace_structure(),
            'configuration_management': self._validate_configuration_management(),
            'communication_components': self._validate_communication_components(),
            'agent_configurations': self._validate_agent_configurations()
        }
        
        overall_success = all(result['success'] for result in validation_results.values())
        
        validation_results['overall_success'] = overall_success
        
        if overall_success:
            self.logger.info("Infrastructure validation passed")
        else:
            self.logger.warning("Infrastructure validation found issues")
        
        return validation_results
    
    def _validate_workspace_structure(self) -> dict:
        """Validate workspace structure"""
        issues = []
        
        # Check base workspace
        if not self.base_workspace_path.exists():
            issues.append("Base workspace path does not exist")
        
        # Check agent workspaces
        required_agents = ['test_agent', 'code_agent', 'integration_agent', 'orchestrator']
        for agent in required_agents:
            agent_workspace = self.base_workspace_path / agent
            if not agent_workspace.exists():
                issues.append(f"Agent workspace missing: {agent}")
            
            # Check required directories
            required_dirs = ['workspace', 'templates', 'output', 'inbox', 'outbox']
            for directory in required_dirs:
                dir_path = agent_workspace / directory
                if not dir_path.exists():
                    issues.append(f"Missing directory: {agent}/{directory}")
        
        # Check shared workspace
        shared_workspace = self.base_workspace_path / 'shared'
        if not shared_workspace.exists():
            issues.append("Shared workspace missing")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_configuration_management(self) -> dict:
        """Validate configuration management"""
        issues = []
        
        if not self.config_manager:
            issues.append("Configuration manager not initialized")
        else:
            validation_issues = self.config_manager.validate_configuration()
            for agent, agent_issues in validation_issues.items():
                issues.extend([f"{agent}: {issue}" for issue in agent_issues])
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_communication_components(self) -> dict:
        """Validate communication components"""
        issues = []
        
        if not self.transport_layer:
            issues.append("Message transport layer not initialized")
        
        if not self.message_router:
            issues.append("Message router not initialized")
        
        if not self.handoff_framework:
            issues.append("Handoff framework not initialized")
        
        if not self.status_protocols:
            issues.append("Status protocols not initialized")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_agent_configurations(self) -> dict:
        """Validate agent configurations"""
        issues = []
        
        required_agents = ['test_agent', 'code_agent', 'integration_agent', 'orchestrator']
        
        for agent_name in required_agents:
            config = self.config_manager.get_agent_configuration(agent_name)
            if not config:
                issues.append(f"Configuration missing for {agent_name}")
            else:
                if not config.workspace_path.exists():
                    issues.append(f"Workspace path does not exist for {agent_name}")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    def get_infrastructure_status(self) -> dict:
        """Get current infrastructure status"""
        return {
            'infrastructure_initialized': all([
                self.config_manager is not None,
                self.transport_layer is not None,
                self.message_router is not None,
                self.handoff_framework is not None,
                self.status_protocols is not None
            ]),
            'workspace_path': str(self.base_workspace_path),
            'components': {
                'configuration_manager': self.config_manager is not None,
                'transport_layer': self.transport_layer is not None,
                'message_router': self.message_router is not None,
                'handoff_framework': self.handoff_framework is not None,
                'status_protocols': self.status_protocols is not None
            }
        }


def main():
    """Main setup function"""
    
    # Get workspace path from environment or use default
    import os
    workspace_path = Path(os.getenv('AGENT_WORKSPACE_PATH', 
                                   Path(__file__).parent.parent / 'agent_workspaces'))
    
    print(f"Setting up communication infrastructure at: {workspace_path}")
    
    # Initialize infrastructure
    setup = CommunicationInfrastructureSetup(workspace_path)
    results = setup.initialize_infrastructure()
    
    # Print results
    print("\n" + "="*60)
    print("COMMUNICATION INFRASTRUCTURE SETUP RESULTS")
    print("="*60)
    print(f"Success: {results['success']}")
    print(f"Workspace: {results['workspace_path']}")
    print(f"Duration: {(results['end_time'] - results['start_time']).total_seconds():.2f} seconds")
    
    print(f"\nComponents Initialized ({len(results['components_initialized'])}):")
    for component in results['components_initialized']:
        print(f"  ✓ {component}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  ✗ {error}")
    
    if 'validation' in results:
        validation = results['validation']
        print(f"\nValidation: {'✓ PASSED' if validation['overall_success'] else '✗ FAILED'}")
        
        for component, result in validation.items():
            if component != 'overall_success':
                status = "✓" if result['success'] else "✗"
                print(f"  {status} {component}")
                
                if result['issues']:
                    for issue in result['issues']:
                        print(f"      - {issue}")
    
    print("\n" + "="*60)
    
    return results


if __name__ == "__main__":
    main()