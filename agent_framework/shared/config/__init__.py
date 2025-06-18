"""
Configuration Management Module

Created: 2025-06-16 with user permission
Purpose: Centralized configuration for agent framework

Intent: Provides configuration management capabilities for agents,
communication settings, security, and environment isolation.
"""

from .agent_config import (
    AgentConfiguration,
    CommunicationConfiguration,
    MonitoringConfiguration,
    SecurityConfiguration,
    ConfigurationManager
)

__all__ = [
    'AgentConfiguration',
    'CommunicationConfiguration', 
    'MonitoringConfiguration',
    'SecurityConfiguration',
    'ConfigurationManager'
]