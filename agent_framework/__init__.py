"""
Agent Framework Package

Created: 2025-06-16 with user permission
Purpose: Three-agent implementation framework infrastructure

Intent: Provides complete agent workspace infrastructure with communication,
monitoring, and handoff automation for Test Agent, Code Agent, and Integration Agent
development streams following the Implementation Orchestrator specifications.
"""

__version__ = "1.0.0"
__author__ = "Agent Framework Implementation"

# Core framework components
from .shared.communication import AgentCommunicationFramework
from .shared.monitoring import AgentProgressMonitor
from .shared.config import AgentConfiguration
from .shared.workspace import WorkspaceManager

# Agent-specific components
from .test_agent import TestAgentWorkspace
from .code_agent import CodeAgentWorkspace
from .integration_agent import IntegrationAgentWorkspace

__all__ = [
    'AgentCommunicationFramework',
    'AgentProgressMonitor', 
    'AgentConfiguration',
    'WorkspaceManager',
    'TestAgentWorkspace',
    'CodeAgentWorkspace', 
    'IntegrationAgentWorkspace'
]