"""
Agent Communication Infrastructure

Created: 2025-06-16 with user permission  
Purpose: Inter-agent message passing and coordination protocols

Intent: Implements the complete communication architecture from AGENT_COMMUNICATION_STANDARDS.md
including message transport, handoff validation, status tracking, and conflict resolution.
"""

from .message_transport import MessageTransportLayer, MessageRouter
from .handoff_management import HandoffTriggerFramework, HandoffPackageValidator
from .status_communication import StatusCommunicationProtocols, AgentProgressTracker
from .conflict_escalation import ConflictEscalationFramework, ConflictResolutionCoordinator
from .quality_metrics import QualityMetricsTrackingFramework, QualityReportingEngine

__all__ = [
    'MessageTransportLayer',
    'MessageRouter',
    'HandoffTriggerFramework', 
    'HandoffPackageValidator',
    'StatusCommunicationProtocols',
    'AgentProgressTracker',
    'ConflictEscalationFramework',
    'ConflictResolutionCoordinator',
    'QualityMetricsTrackingFramework',
    'QualityReportingEngine'
]