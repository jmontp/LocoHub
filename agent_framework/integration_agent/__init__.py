"""
Integration Agent Framework

Created: 2025-01-16 with user permission
Purpose: Core Integration Agent framework for three-agent development orchestration

Intent: Provides systematic coordination between Test Agent and Code Agent outputs,
executing tests against implementations, analyzing failures, resolving conflicts,
and ensuring integration quality without bias toward either agent.
"""

from .core import IntegrationAgent
from .test_execution import TestExecutionOrchestrator, TestExecutionEngine, TestResultCollector
from .failure_analysis import FailureDiagnosisFramework, FailureCategorizer, RootCauseAnalyzer
from .conflict_resolution import ConflictDetectionFramework, ConflictResolutionOrchestrator
from .performance_validation import PerformanceAssessmentFramework, PerformanceOptimizationEngine
from .success_criteria import IntegrationSuccessCriteria, IntegrationSignOffFramework
from .monitoring import IntegrationMonitor, OrchestrationMonitor
from .communication import OrchestrationCommunicator

__all__ = [
    'IntegrationAgent',
    'TestExecutionOrchestrator',
    'TestExecutionEngine', 
    'TestResultCollector',
    'FailureDiagnosisFramework',
    'FailureCategorizer',
    'RootCauseAnalyzer',
    'ConflictDetectionFramework',
    'ConflictResolutionOrchestrator',
    'PerformanceAssessmentFramework',
    'PerformanceOptimizationEngine',
    'IntegrationSuccessCriteria',
    'IntegrationSignOffFramework',
    'IntegrationMonitor',
    'OrchestrationMonitor',
    'OrchestrationCommunicator'
]