"""
Integration Agent Core Framework

Created: 2025-01-16 with user permission
Purpose: Core Integration Agent class providing main orchestration interface

Intent: Central orchestrator that coordinates test execution, failure analysis, 
conflict resolution, and quality assurance for three-agent development workflows.
Maintains neutrality between Test and Code agents while ensuring integration success.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .test_execution import TestExecutionOrchestrator, TestPackage, ImplementationPackage
from .failure_analysis import FailureDiagnosisFramework
from .conflict_resolution import ConflictDetectionFramework, ConflictResolutionOrchestrator
from .performance_validation import PerformanceAssessmentFramework
from .success_criteria import IntegrationSuccessCriteria, IntegrationSignOffFramework
from .monitoring import IntegrationMonitor
from .communication import OrchestrationCommunicator


class IntegrationPhase(Enum):
    """Integration workflow phases"""
    INITIALIZATION = "initialization"
    TEST_EXECUTION = "test_execution"
    FAILURE_ANALYSIS = "failure_analysis"
    CONFLICT_RESOLUTION = "conflict_resolution"
    PERFORMANCE_VALIDATION = "performance_validation"
    SUCCESS_VALIDATION = "success_validation"
    SIGN_OFF = "sign_off"
    COMPLETION = "completion"


class IntegrationStatus(Enum):
    """Integration status indicators"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CONFLICT_RESOLUTION_REQUIRED = "conflict_resolution_required"
    PERFORMANCE_ISSUES = "performance_issues"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class IntegrationConfiguration:
    """Configuration for Integration Agent execution"""
    
    # Neutrality settings
    bias_detection_enabled: bool = True
    neutral_analysis_required: bool = True
    
    # Quality gates
    minimum_test_pass_rate: float = 0.95
    minimum_performance_compliance: float = 0.90
    minimum_quality_score: float = 0.85
    
    # Execution settings
    parallel_execution_enabled: bool = True
    detailed_logging_enabled: bool = True
    comprehensive_reporting: bool = True
    
    # Escalation thresholds
    max_conflict_resolution_attempts: int = 3
    max_performance_optimization_cycles: int = 2
    escalation_timeout_hours: int = 24


@dataclass
class IntegrationContext:
    """Context for integration execution session"""
    
    session_id: str
    start_time: datetime
    test_package: TestPackage
    implementation_package: ImplementationPackage
    configuration: IntegrationConfiguration
    
    # Runtime state
    current_phase: IntegrationPhase = IntegrationPhase.INITIALIZATION
    status: IntegrationStatus = IntegrationStatus.PENDING
    execution_log: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def log_event(self, message: str, level: str = "INFO"):
        """Log integration event with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.execution_log.append(log_entry)
        
        # Also log to standard logger
        logger = logging.getLogger(__name__)
        getattr(logger, level.lower(), logger.info)(message)


@dataclass 
class IntegrationResults:
    """Comprehensive results from integration execution"""
    
    session_id: str
    overall_success: bool
    integration_status: IntegrationStatus
    
    # Phase results
    test_execution_results: Optional[Any] = None
    failure_analysis_results: Optional[Any] = None
    conflict_resolution_results: Optional[Any] = None
    performance_validation_results: Optional[Any] = None
    success_validation_results: Optional[Any] = None
    sign_off_results: Optional[Any] = None
    
    # Metrics and reporting
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    
    # Timestamps
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def execution_duration(self) -> Optional[float]:
        """Calculate execution duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class IntegrationAgent:
    """
    Core Integration Agent for three-agent development orchestration
    
    Coordinates test execution, failure analysis, conflict resolution, and quality
    assurance between Test Agent and Code Agent outputs while maintaining neutrality.
    """
    
    def __init__(self, configuration: Optional[IntegrationConfiguration] = None):
        """Initialize Integration Agent with configuration"""
        self.configuration = configuration or IntegrationConfiguration()
        
        # Initialize core components
        self.test_executor = TestExecutionOrchestrator()
        self.failure_analyzer = FailureDiagnosisFramework()
        self.conflict_detector = ConflictDetectionFramework()
        self.conflict_resolver = ConflictResolutionOrchestrator()
        self.performance_validator = PerformanceAssessmentFramework()
        self.success_criteria = IntegrationSuccessCriteria()
        self.sign_off_framework = IntegrationSignOffFramework()
        self.monitor = IntegrationMonitor()
        self.communicator = OrchestrationCommunicator()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if self.configuration.detailed_logging_enabled:
            self.logger.setLevel(logging.DEBUG)
    
    def execute_integration_cycle(
        self, 
        test_package: TestPackage, 
        implementation_package: ImplementationPackage,
        session_id: Optional[str] = None
    ) -> IntegrationResults:
        """
        Execute complete integration cycle with systematic coordination
        
        Args:
            test_package: Test Agent output package
            implementation_package: Code Agent output package
            session_id: Optional session identifier
            
        Returns:
            Comprehensive integration results
        """
        # Initialize integration context
        session_id = session_id or f"integration_{int(time.time())}"
        context = IntegrationContext(
            session_id=session_id,
            start_time=datetime.now(),
            test_package=test_package,
            implementation_package=implementation_package,
            configuration=self.configuration
        )
        
        results = IntegrationResults(
            session_id=session_id,
            overall_success=False,
            integration_status=IntegrationStatus.IN_PROGRESS,
            start_time=context.start_time
        )
        
        try:
            # Phase 1: Test Execution
            context.log_event("Starting test execution phase")
            context.current_phase = IntegrationPhase.TEST_EXECUTION
            context.status = IntegrationStatus.IN_PROGRESS
            
            test_results = self._execute_test_phase(context)
            results.test_execution_results = test_results
            
            # Phase 2: Failure Analysis (if needed)
            if test_results.has_failures():
                context.log_event("Starting failure analysis phase")
                context.current_phase = IntegrationPhase.FAILURE_ANALYSIS
                
                failure_analysis = self._execute_failure_analysis_phase(context, test_results)
                results.failure_analysis_results = failure_analysis
                
                # Phase 3: Conflict Resolution (if needed)
                if failure_analysis.has_conflicts():
                    context.log_event("Starting conflict resolution phase")
                    context.current_phase = IntegrationPhase.CONFLICT_RESOLUTION
                    context.status = IntegrationStatus.CONFLICT_RESOLUTION_REQUIRED
                    
                    conflict_resolution = self._execute_conflict_resolution_phase(context, failure_analysis)
                    results.conflict_resolution_results = conflict_resolution
            
            # Phase 4: Performance Validation
            context.log_event("Starting performance validation phase")
            context.current_phase = IntegrationPhase.PERFORMANCE_VALIDATION
            
            performance_results = self._execute_performance_validation_phase(context)
            results.performance_validation_results = performance_results
            
            if not performance_results.meets_requirements():
                context.status = IntegrationStatus.PERFORMANCE_ISSUES
                context.log_event("Performance requirements not met", "WARNING")
            
            # Phase 5: Success Validation
            context.log_event("Starting success validation phase")
            context.current_phase = IntegrationPhase.SUCCESS_VALIDATION
            
            success_validation = self._execute_success_validation_phase(context, results)
            results.success_validation_results = success_validation
            
            if not success_validation.overall_success:
                context.status = IntegrationStatus.QUALITY_GATE_FAILED
                context.log_event("Quality gates not passed", "WARNING")
            
            # Phase 6: Sign-off (if validation successful)
            if success_validation.overall_success:
                context.log_event("Starting sign-off phase")
                context.current_phase = IntegrationPhase.SIGN_OFF
                
                sign_off_results = self._execute_sign_off_phase(context, success_validation)
                results.sign_off_results = sign_off_results
                
                if sign_off_results.final_approval.approved:
                    context.status = IntegrationStatus.SUCCESS
                    results.overall_success = True
                    context.log_event("Integration completed successfully")
                else:
                    context.status = IntegrationStatus.QUALITY_GATE_FAILED
                    context.log_event("Sign-off requirements not met", "WARNING")
            
            # Completion
            context.current_phase = IntegrationPhase.COMPLETION
            results.integration_status = context.status
            
        except Exception as e:
            context.log_event(f"Integration failed with error: {str(e)}", "ERROR")
            context.status = IntegrationStatus.FAILED
            results.integration_status = IntegrationStatus.FAILED
            self.logger.error(f"Integration execution failed: {e}", exc_info=True)
        
        finally:
            # Finalize results
            results.end_time = datetime.now()
            results.execution_metrics = self._collect_execution_metrics(context)
            results.quality_metrics = self._collect_quality_metrics(context, results)
            results.recommendations = self._generate_recommendations(context, results)
            results.lessons_learned = self._extract_lessons_learned(context, results)
            
            # Report completion
            self._report_integration_completion(context, results)
        
        return results
    
    def _execute_test_phase(self, context: IntegrationContext):
        """Execute comprehensive test execution phase"""
        context.log_event("Executing Test Agent tests against Code Agent implementation")
        
        return self.test_executor.execute_complete_test_suite(
            context.test_package,
            context.implementation_package
        )
    
    def _execute_failure_analysis_phase(self, context: IntegrationContext, test_results):
        """Execute systematic failure analysis phase"""
        context.log_event("Analyzing integration failures for categorization and diagnosis")
        
        failures = test_results.get_failures()
        failure_analyses = []
        
        for failure in failures:
            diagnosis = self.failure_analyzer.diagnose_integration_failure(failure)
            failure_analyses.append(diagnosis)
        
        return {
            'individual_analyses': failure_analyses,
            'summary': self._summarize_failure_analysis(failure_analyses),
            'resolution_priorities': self._prioritize_failure_resolutions(failure_analyses)
        }
    
    def _execute_conflict_resolution_phase(self, context: IntegrationContext, failure_analysis):
        """Execute systematic conflict resolution phase"""
        context.log_event("Coordinating resolution of integration conflicts")
        
        # Detect conflicts
        conflicts = self.conflict_detector.detect_and_classify_conflicts(
            context.test_package,
            context.implementation_package
        )
        
        # Orchestrate resolution
        resolution_results = self.conflict_resolver.orchestrate_conflict_resolution(conflicts)
        
        return resolution_results
    
    def _execute_performance_validation_phase(self, context: IntegrationContext):
        """Execute performance validation phase"""
        context.log_event("Validating implementation performance against requirements")
        
        return self.performance_validator.assess_implementation_performance(
            context.implementation_package,
            context.test_package.performance_requirements
        )
    
    def _execute_success_validation_phase(self, context: IntegrationContext, results: IntegrationResults):
        """Execute integration success validation phase"""
        context.log_event("Validating integration success criteria")
        
        # Combine all results for comprehensive validation
        integration_results_for_validation = {
            'test_results': results.test_execution_results,
            'performance_results': results.performance_validation_results,
            'conflict_resolution': results.conflict_resolution_results
        }
        
        return self.success_criteria.validate_integration_success(integration_results_for_validation)
    
    def _execute_sign_off_phase(self, context: IntegrationContext, success_validation):
        """Execute integration sign-off phase"""
        context.log_event("Executing comprehensive sign-off procedures")
        
        return self.sign_off_framework.execute_sign_off_process(success_validation)
    
    def _collect_execution_metrics(self, context: IntegrationContext) -> Dict[str, Any]:
        """Collect execution metrics from integration session"""
        return {
            'execution_duration': (datetime.now() - context.start_time).total_seconds(),
            'phases_completed': context.current_phase.value,
            'log_entries': len(context.execution_log),
            'final_status': context.status.value
        }
    
    def _collect_quality_metrics(self, context: IntegrationContext, results: IntegrationResults) -> Dict[str, Any]:
        """Collect quality metrics from integration results"""
        metrics = {}
        
        if results.test_execution_results:
            metrics['test_pass_rate'] = results.test_execution_results.get_pass_rate()
        
        if results.performance_validation_results:
            metrics['performance_compliance'] = results.performance_validation_results.get_compliance_rate()
        
        if results.success_validation_results:
            metrics['overall_quality_score'] = results.success_validation_results.get_quality_score()
        
        return metrics
    
    def _generate_recommendations(self, context: IntegrationContext, results: IntegrationResults) -> List[str]:
        """Generate recommendations based on integration results"""
        recommendations = []
        
        if not results.overall_success:
            if results.test_execution_results and results.test_execution_results.has_failures():
                recommendations.append("Address test failures through targeted implementation fixes")
            
            if results.performance_validation_results and not results.performance_validation_results.meets_requirements():
                recommendations.append("Optimize implementation performance to meet benchmarks")
            
            if results.conflict_resolution_results and results.conflict_resolution_results.has_unresolved_conflicts():
                recommendations.append("Complete conflict resolution before proceeding")
        
        return recommendations
    
    def _extract_lessons_learned(self, context: IntegrationContext, results: IntegrationResults) -> List[str]:
        """Extract lessons learned from integration session"""
        lessons = []
        
        if results.execution_duration and results.execution_duration > 3600:  # > 1 hour
            lessons.append("Consider breaking down integration into smaller phases for efficiency")
        
        if results.conflict_resolution_results and len(results.conflict_resolution_results.get_conflicts()) > 5:
            lessons.append("High conflict count suggests need for better specification clarity")
        
        return lessons
    
    def _report_integration_completion(self, context: IntegrationContext, results: IntegrationResults):
        """Report integration completion to orchestrator and stakeholders"""
        context.log_event(f"Integration completed with status: {results.integration_status.value}")
        
        # Communicate results to Implementation Orchestrator
        self.communicator.report_integration_completion(context, results)
        
        # Update monitoring systems
        self.monitor.record_integration_completion(context, results)
    
    def _summarize_failure_analysis(self, failure_analyses: List) -> Dict[str, Any]:
        """Summarize failure analysis results"""
        return {
            'total_failures': len(failure_analyses),
            'failure_categories': self._categorize_failures(failure_analyses),
            'resolution_complexity': self._assess_resolution_complexity(failure_analyses)
        }
    
    def _prioritize_failure_resolutions(self, failure_analyses: List) -> List:
        """Prioritize failure resolutions by impact and complexity"""
        # Sort by urgency and complexity
        return sorted(failure_analyses, key=lambda x: (x.urgency, x.complexity))
    
    def _categorize_failures(self, failure_analyses: List) -> Dict[str, int]:
        """Categorize failures by type"""
        categories = {}
        for analysis in failure_analyses:
            category = analysis.failure_category.primary_type.value
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _assess_resolution_complexity(self, failure_analyses: List) -> str:
        """Assess overall resolution complexity"""
        high_complexity_count = sum(1 for analysis in failure_analyses 
                                  if analysis.failure_category.complexity.value == 'HIGH')
        
        if high_complexity_count > len(failure_analyses) * 0.5:
            return "HIGH"
        elif high_complexity_count > 0:
            return "MEDIUM"
        else:
            return "LOW"