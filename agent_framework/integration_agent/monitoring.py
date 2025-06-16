"""
Monitoring and Reporting Framework for Integration Agent

Created: 2025-01-16 with user permission
Purpose: Real-time integration progress tracking and comprehensive reporting

Intent: Provides comprehensive monitoring of integration processes, real-time
progress tracking, performance metrics collection, and detailed reporting
capabilities for systematic integration oversight and continuous improvement.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timedelta
import queue
import json


class MonitoringLevel(Enum):
    """Monitoring detail levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    DEBUG = "debug"


class MetricType(Enum):
    """Types of monitoring metrics"""
    PERFORMANCE = "performance"
    PROGRESS = "progress"
    QUALITY = "quality"
    RESOURCE = "resource"
    ERROR = "error"
    SUCCESS = "success"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MonitoringMetric:
    """Individual monitoring metric"""
    
    metric_name: str
    metric_type: MetricType
    value: Union[float, int, str, bool]
    timestamp: float
    
    # Context information
    source_component: str = ""
    integration_session: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    unit: str = ""
    description: str = ""
    threshold_value: Optional[float] = None
    
    @property
    def exceeds_threshold(self) -> bool:
        """Check if metric exceeds threshold"""
        if self.threshold_value is None or not isinstance(self.value, (int, float)):
            return False
        return self.value > self.threshold_value


@dataclass
class ProgressUpdate:
    """Progress update for integration monitoring"""
    
    session_id: str
    phase: str
    progress_percentage: float
    status: str
    timestamp: float
    
    # Progress details
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    estimated_completion: Optional[float] = None
    
    # Performance metrics
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0
    
    # Context
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if progress is complete"""
        return self.progress_percentage >= 100.0


@dataclass
class AlertEvent:
    """Alert event for monitoring system"""
    
    alert_id: str
    severity: AlertSeverity
    message: str
    timestamp: float
    
    # Alert context
    source_component: str = ""
    integration_session: str = ""
    error_details: Optional[str] = None
    
    # Resolution information
    auto_resolvable: bool = False
    resolution_actions: List[str] = field(default_factory=list)
    escalation_required: bool = False
    
    # Metadata
    alert_category: str = "general"
    related_metrics: List[str] = field(default_factory=list)


@dataclass
class IntegrationHealthStatus:
    """Overall health status of integration process"""
    
    session_id: str
    overall_health: str  # "healthy", "warning", "critical", "failed"
    health_score: float
    timestamp: float
    
    # Component health
    component_health: Dict[str, str] = field(default_factory=dict)
    
    # Key indicators
    test_execution_health: str = "unknown"
    performance_health: str = "unknown"
    resource_health: str = "unknown"
    
    # Trends
    health_trend: str = "stable"  # "improving", "stable", "degrading"
    recent_issues: List[str] = field(default_factory=list)
    
    # Recommendations
    health_recommendations: List[str] = field(default_factory=list)


@dataclass
class MonitoringReport:
    """Comprehensive monitoring report"""
    
    report_id: str
    session_id: str
    report_type: str
    generation_timestamp: float
    
    # Time range
    start_time: float
    end_time: float
    
    # Metrics summary
    metrics_summary: Dict[str, Any] = field(default_factory=dict)
    performance_trends: Dict[str, Any] = field(default_factory=dict)
    quality_indicators: Dict[str, Any] = field(default_factory=dict)
    
    # Progress analysis
    progress_analysis: Dict[str, Any] = field(default_factory=dict)
    milestone_achievements: List[str] = field(default_factory=list)
    
    # Issues and alerts
    alert_summary: Dict[str, int] = field(default_factory=dict)
    critical_issues: List[str] = field(default_factory=list)
    
    # Recommendations
    optimization_opportunities: List[str] = field(default_factory=list)
    process_improvements: List[str] = field(default_factory=list)


class MonitoringCollector(ABC):
    """Abstract base class for monitoring data collectors"""
    
    @abstractmethod
    def collect_metrics(self, context: Dict[str, Any]) -> List[MonitoringMetric]:
        """Collect monitoring metrics"""
        pass
    
    @abstractmethod
    def get_collector_name(self) -> str:
        """Get collector name"""
        pass


class PerformanceMetricsCollector(MonitoringCollector):
    """Collector for performance monitoring metrics"""
    
    def get_collector_name(self) -> str:
        return "performance_metrics"
    
    def collect_metrics(self, context: Dict[str, Any]) -> List[MonitoringMetric]:
        """Collect performance metrics"""
        
        metrics = []
        current_time = time.time()
        session_id = context.get('session_id', 'unknown')
        
        # Collect CPU usage
        cpu_usage = self._get_cpu_usage()
        metrics.append(MonitoringMetric(
            metric_name="cpu_usage_percent",
            metric_type=MetricType.PERFORMANCE,
            value=cpu_usage,
            timestamp=current_time,
            source_component="performance_collector",
            integration_session=session_id,
            unit="percent",
            description="Current CPU usage percentage",
            threshold_value=80.0
        ))
        
        # Collect memory usage
        memory_usage = self._get_memory_usage()
        metrics.append(MonitoringMetric(
            metric_name="memory_usage_mb",
            metric_type=MetricType.PERFORMANCE,
            value=memory_usage,
            timestamp=current_time,
            source_component="performance_collector",
            integration_session=session_id,
            unit="MB",
            description="Current memory usage in megabytes",
            threshold_value=1000.0
        ))
        
        # Collect response time
        response_time = context.get('response_time', 0.0)
        if response_time > 0:
            metrics.append(MonitoringMetric(
                metric_name="response_time_ms",
                metric_type=MetricType.PERFORMANCE,
                value=response_time * 1000,  # Convert to milliseconds
                timestamp=current_time,
                source_component="performance_collector",
                integration_session=session_id,
                unit="ms",
                description="Operation response time",
                threshold_value=5000.0  # 5 second threshold
            ))
        
        return metrics
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=None)
        except ImportError:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0


class QualityMetricsCollector(MonitoringCollector):
    """Collector for quality monitoring metrics"""
    
    def get_collector_name(self) -> str:
        return "quality_metrics"
    
    def collect_metrics(self, context: Dict[str, Any]) -> List[MonitoringMetric]:
        """Collect quality metrics"""
        
        metrics = []
        current_time = time.time()
        session_id = context.get('session_id', 'unknown')
        
        # Test pass rate
        test_pass_rate = context.get('test_pass_rate', 0.0)
        metrics.append(MonitoringMetric(
            metric_name="test_pass_rate",
            metric_type=MetricType.QUALITY,
            value=test_pass_rate,
            timestamp=current_time,
            source_component="quality_collector",
            integration_session=session_id,
            unit="percentage",
            description="Current test pass rate",
            threshold_value=0.95
        ))
        
        # Error count
        error_count = context.get('error_count', 0)
        metrics.append(MonitoringMetric(
            metric_name="error_count",
            metric_type=MetricType.ERROR,
            value=error_count,
            timestamp=current_time,
            source_component="quality_collector",
            integration_session=session_id,
            unit="count",
            description="Number of errors encountered",
            threshold_value=5.0
        ))
        
        # Success rate
        success_rate = context.get('success_rate', 0.0)
        metrics.append(MonitoringMetric(
            metric_name="success_rate",
            metric_type=MetricType.SUCCESS,
            value=success_rate,
            timestamp=current_time,
            source_component="quality_collector",
            integration_session=session_id,
            unit="percentage",
            description="Overall success rate",
            threshold_value=0.90
        ))
        
        return metrics


class ProgressMetricsCollector(MonitoringCollector):
    """Collector for progress monitoring metrics"""
    
    def get_collector_name(self) -> str:
        return "progress_metrics"
    
    def collect_metrics(self, context: Dict[str, Any]) -> List[MonitoringMetric]:
        """Collect progress metrics"""
        
        metrics = []
        current_time = time.time()
        session_id = context.get('session_id', 'unknown')
        
        # Progress percentage
        progress_percentage = context.get('progress_percentage', 0.0)
        metrics.append(MonitoringMetric(
            metric_name="progress_percentage",
            metric_type=MetricType.PROGRESS,
            value=progress_percentage,
            timestamp=current_time,
            source_component="progress_collector",
            integration_session=session_id,
            unit="percentage",
            description="Overall progress percentage"
        ))
        
        # Completion velocity
        completion_velocity = context.get('completion_velocity', 0.0)
        metrics.append(MonitoringMetric(
            metric_name="completion_velocity",
            metric_type=MetricType.PROGRESS,
            value=completion_velocity,
            timestamp=current_time,
            source_component="progress_collector",
            integration_session=session_id,
            unit="percent_per_hour",
            description="Rate of progress completion"
        ))
        
        return metrics


class AlertManager:
    """Manages alert generation and processing"""
    
    def __init__(self):
        self.alert_queue = queue.Queue()
        self.alert_handlers = []
        self.alert_history = []
        self.logger = logging.getLogger(__name__)
        
        # Alert thresholds
        self.alert_thresholds = {
            'cpu_usage_percent': 80.0,
            'memory_usage_mb': 1000.0,
            'error_count': 5.0,
            'response_time_ms': 5000.0
        }
    
    def check_metric_for_alerts(self, metric: MonitoringMetric) -> Optional[AlertEvent]:
        """Check if metric should generate an alert"""
        
        if metric.exceeds_threshold:
            alert = AlertEvent(
                alert_id=f"alert_{metric.metric_name}_{int(time.time())}",
                severity=self._determine_alert_severity(metric),
                message=f"{metric.metric_name} exceeded threshold: {metric.value} > {metric.threshold_value}",
                timestamp=time.time(),
                source_component=metric.source_component,
                integration_session=metric.integration_session,
                alert_category="threshold_violation",
                related_metrics=[metric.metric_name]
            )
            
            self.alert_queue.put(alert)
            self.alert_history.append(alert)
            
            return alert
        
        return None
    
    def generate_custom_alert(self, severity: AlertSeverity, message: str, context: Dict[str, Any] = None) -> AlertEvent:
        """Generate custom alert"""
        
        context = context or {}
        
        alert = AlertEvent(
            alert_id=f"custom_alert_{int(time.time())}",
            severity=severity,
            message=message,
            timestamp=time.time(),
            source_component=context.get('source_component', 'integration_agent'),
            integration_session=context.get('session_id', 'unknown'),
            alert_category=context.get('category', 'custom'),
            auto_resolvable=context.get('auto_resolvable', False),
            escalation_required=severity == AlertSeverity.CRITICAL
        )
        
        self.alert_queue.put(alert)
        self.alert_history.append(alert)
        
        return alert
    
    def _determine_alert_severity(self, metric: MonitoringMetric) -> AlertSeverity:
        """Determine alert severity based on metric"""
        
        if not isinstance(metric.value, (int, float)) or metric.threshold_value is None:
            return AlertSeverity.INFO
        
        excess_ratio = metric.value / metric.threshold_value
        
        if excess_ratio > 2.0:
            return AlertSeverity.CRITICAL
        elif excess_ratio > 1.5:
            return AlertSeverity.ERROR
        elif excess_ratio > 1.2:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def get_recent_alerts(self, time_window_seconds: int = 300) -> List[AlertEvent]:
        """Get alerts from recent time window"""
        
        cutoff_time = time.time() - time_window_seconds
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def get_critical_alerts(self) -> List[AlertEvent]:
        """Get all critical alerts"""
        
        return [alert for alert in self.alert_history if alert.severity == AlertSeverity.CRITICAL]


class IntegrationMonitor:
    """Core integration monitoring system"""
    
    def __init__(self, monitoring_level: MonitoringLevel = MonitoringLevel.DETAILED):
        self.monitoring_level = monitoring_level
        self.collectors = {
            'performance': PerformanceMetricsCollector(),
            'quality': QualityMetricsCollector(),
            'progress': ProgressMetricsCollector()
        }
        self.alert_manager = AlertManager()
        self.metrics_history = []
        self.progress_history = []
        self.health_history = []
        
        # Monitoring thread control
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 5.0  # seconds
        
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self, session_id: str):
        """Start monitoring for integration session"""
        
        self.monitoring_active = True
        self.session_id = session_id
        
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(session_id,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info(f"Started monitoring for session: {session_id}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10.0)
        
        self.logger.info("Stopped integration monitoring")
    
    def record_progress_update(self, progress_update: ProgressUpdate):
        """Record progress update"""
        
        self.progress_history.append(progress_update)
        
        # Generate progress-related metrics
        context = {
            'session_id': progress_update.session_id,
            'progress_percentage': progress_update.progress_percentage,
            'completion_velocity': self._calculate_completion_velocity(progress_update)
        }
        
        # Collect progress metrics
        if 'progress' in self.collectors:
            progress_metrics = self.collectors['progress'].collect_metrics(context)
            self.metrics_history.extend(progress_metrics)
    
    def record_integration_completion(self, context: Any, results: Any):
        """Record integration completion metrics"""
        
        completion_metrics = []
        current_time = time.time()
        session_id = getattr(context, 'session_id', 'unknown')
        
        # Record completion status
        completion_metrics.append(MonitoringMetric(
            metric_name="integration_completed",
            metric_type=MetricType.SUCCESS,
            value=1 if getattr(results, 'overall_success', False) else 0,
            timestamp=current_time,
            source_component="integration_monitor",
            integration_session=session_id,
            description="Integration completion status"
        ))
        
        # Record completion time
        if hasattr(results, 'execution_duration') and results.execution_duration:
            completion_metrics.append(MonitoringMetric(
                metric_name="integration_duration_seconds",
                metric_type=MetricType.PERFORMANCE,
                value=results.execution_duration,
                timestamp=current_time,
                source_component="integration_monitor",
                integration_session=session_id,
                unit="seconds",
                description="Total integration duration"
            ))
        
        self.metrics_history.extend(completion_metrics)
        
        # Generate completion alert
        if getattr(results, 'overall_success', False):
            self.alert_manager.generate_custom_alert(
                AlertSeverity.INFO,
                f"Integration completed successfully: {session_id}",
                {'session_id': session_id, 'source_component': 'integration_monitor'}
            )
        else:
            self.alert_manager.generate_custom_alert(
                AlertSeverity.ERROR,
                f"Integration failed: {session_id}",
                {'session_id': session_id, 'source_component': 'integration_monitor'}
            )
    
    def get_current_health_status(self, session_id: str) -> IntegrationHealthStatus:
        """Get current health status of integration"""
        
        current_time = time.time()
        
        # Calculate overall health score
        recent_metrics = self._get_recent_metrics(300)  # Last 5 minutes
        health_score = self._calculate_health_score(recent_metrics)
        
        # Determine overall health
        if health_score >= 0.9:
            overall_health = "healthy"
        elif health_score >= 0.7:
            overall_health = "warning"
        elif health_score >= 0.5:
            overall_health = "critical"
        else:
            overall_health = "failed"
        
        # Get component health
        component_health = self._assess_component_health(recent_metrics)
        
        # Get recent issues
        recent_alerts = self.alert_manager.get_recent_alerts(300)
        recent_issues = [alert.message for alert in recent_alerts if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]]
        
        # Generate health recommendations
        health_recommendations = self._generate_health_recommendations(overall_health, recent_metrics, recent_alerts)
        
        health_status = IntegrationHealthStatus(
            session_id=session_id,
            overall_health=overall_health,
            health_score=health_score,
            timestamp=current_time,
            component_health=component_health,
            recent_issues=recent_issues,
            health_recommendations=health_recommendations
        )
        
        self.health_history.append(health_status)
        
        return health_status
    
    def generate_monitoring_report(self, report_type: str = "comprehensive") -> MonitoringReport:
        """Generate comprehensive monitoring report"""
        
        report_id = f"monitoring_report_{int(time.time())}"
        current_time = time.time()
        
        # Determine time range based on available data
        if self.metrics_history:
            start_time = min(metric.timestamp for metric in self.metrics_history)
            end_time = max(metric.timestamp for metric in self.metrics_history)
        else:
            start_time = current_time - 3600  # Last hour
            end_time = current_time
        
        # Generate metrics summary
        metrics_summary = self._generate_metrics_summary()
        
        # Analyze performance trends
        performance_trends = self._analyze_performance_trends()
        
        # Generate quality indicators
        quality_indicators = self._generate_quality_indicators()
        
        # Analyze progress
        progress_analysis = self._analyze_progress()
        
        # Summarize alerts
        alert_summary = self._summarize_alerts()
        
        # Identify critical issues
        critical_issues = [alert.message for alert in self.alert_manager.get_critical_alerts()]
        
        # Generate recommendations
        optimization_opportunities = self._identify_optimization_opportunities()
        process_improvements = self._identify_process_improvements()
        
        return MonitoringReport(
            report_id=report_id,
            session_id=getattr(self, 'session_id', 'unknown'),
            report_type=report_type,
            generation_timestamp=current_time,
            start_time=start_time,
            end_time=end_time,
            metrics_summary=metrics_summary,
            performance_trends=performance_trends,
            quality_indicators=quality_indicators,
            progress_analysis=progress_analysis,
            alert_summary=alert_summary,
            critical_issues=critical_issues,
            optimization_opportunities=optimization_opportunities,
            process_improvements=process_improvements
        )
    
    def _monitoring_loop(self, session_id: str):
        """Main monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Collect metrics from all collectors
                context = {
                    'session_id': session_id,
                    'monitoring_level': self.monitoring_level.value
                }
                
                for collector_name, collector in self.collectors.items():
                    try:
                        metrics = collector.collect_metrics(context)
                        self.metrics_history.extend(metrics)
                        
                        # Check for alerts
                        for metric in metrics:
                            self.alert_manager.check_metric_for_alerts(metric)
                    
                    except Exception as e:
                        self.logger.error(f"Error in collector {collector_name}: {e}")
                
                # Sleep until next collection
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _calculate_completion_velocity(self, progress_update: ProgressUpdate) -> float:
        """Calculate completion velocity"""
        
        if not self.progress_history:
            return 0.0
        
        # Find previous progress update
        previous_updates = [p for p in self.progress_history if p.timestamp < progress_update.timestamp]
        if not previous_updates:
            return 0.0
        
        previous_update = max(previous_updates, key=lambda p: p.timestamp)
        
        # Calculate velocity
        time_diff = progress_update.timestamp - previous_update.timestamp
        progress_diff = progress_update.progress_percentage - previous_update.progress_percentage
        
        if time_diff > 0:
            return progress_diff / (time_diff / 3600)  # percent per hour
        else:
            return 0.0
    
    def _get_recent_metrics(self, time_window_seconds: int) -> List[MonitoringMetric]:
        """Get metrics from recent time window"""
        
        cutoff_time = time.time() - time_window_seconds
        return [metric for metric in self.metrics_history if metric.timestamp >= cutoff_time]
    
    def _calculate_health_score(self, metrics: List[MonitoringMetric]) -> float:
        """Calculate overall health score from metrics"""
        
        if not metrics:
            return 0.5  # Neutral score when no data
        
        # Calculate score based on threshold violations
        total_metrics = len(metrics)
        violation_count = sum(1 for metric in metrics if metric.exceeds_threshold)
        
        if total_metrics == 0:
            return 0.5
        
        violation_rate = violation_count / total_metrics
        health_score = 1.0 - violation_rate
        
        return max(0.0, min(1.0, health_score))
    
    def _assess_component_health(self, metrics: List[MonitoringMetric]) -> Dict[str, str]:
        """Assess health of individual components"""
        
        component_health = {}
        
        # Group metrics by component
        components = set(metric.source_component for metric in metrics)
        
        for component in components:
            component_metrics = [m for m in metrics if m.source_component == component]
            violation_count = sum(1 for m in component_metrics if m.exceeds_threshold)
            
            if not component_metrics:
                component_health[component] = "unknown"
            elif violation_count == 0:
                component_health[component] = "healthy"
            elif violation_count / len(component_metrics) < 0.2:
                component_health[component] = "warning"
            else:
                component_health[component] = "critical"
        
        return component_health
    
    def _generate_health_recommendations(self, overall_health: str, metrics: List[MonitoringMetric], alerts: List[AlertEvent]) -> List[str]:
        """Generate health improvement recommendations"""
        
        recommendations = []
        
        if overall_health in ["critical", "failed"]:
            recommendations.append("Immediate attention required - investigate critical issues")
        
        if overall_health == "warning":
            recommendations.append("Monitor closely - address warning conditions")
        
        # Check for specific metric patterns
        high_cpu_metrics = [m for m in metrics if m.metric_name == "cpu_usage_percent" and m.value > 80]
        if high_cpu_metrics:
            recommendations.append("High CPU usage detected - consider optimization")
        
        high_memory_metrics = [m for m in metrics if m.metric_name == "memory_usage_mb" and m.value > 1000]
        if high_memory_metrics:
            recommendations.append("High memory usage detected - check for memory leaks")
        
        return recommendations
    
    def _generate_metrics_summary(self) -> Dict[str, Any]:
        """Generate summary of metrics"""
        
        if not self.metrics_history:
            return {}
        
        summary = {
            'total_metrics_collected': len(self.metrics_history),
            'metric_types': {},
            'threshold_violations': 0,
            'collection_time_range': {
                'start': min(m.timestamp for m in self.metrics_history),
                'end': max(m.timestamp for m in self.metrics_history)
            }
        }
        
        # Count by metric type
        for metric in self.metrics_history:
            metric_type = metric.metric_type.value
            summary['metric_types'][metric_type] = summary['metric_types'].get(metric_type, 0) + 1
            
            if metric.exceeds_threshold:
                summary['threshold_violations'] += 1
        
        return summary
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends"""
        
        performance_metrics = [m for m in self.metrics_history if m.metric_type == MetricType.PERFORMANCE]
        
        if not performance_metrics:
            return {}
        
        trends = {}
        
        # Group by metric name and analyze trends
        metric_names = set(m.metric_name for m in performance_metrics)
        
        for metric_name in metric_names:
            metric_values = [(m.timestamp, m.value) for m in performance_metrics 
                           if m.metric_name == metric_name and isinstance(m.value, (int, float))]
            
            if len(metric_values) >= 2:
                # Calculate trend (simplified linear regression)
                recent_values = sorted(metric_values, key=lambda x: x[0])[-10:]  # Last 10 values
                if len(recent_values) >= 2:
                    first_value = recent_values[0][1]
                    last_value = recent_values[-1][1]
                    
                    if last_value > first_value * 1.1:
                        trend = "increasing"
                    elif last_value < first_value * 0.9:
                        trend = "decreasing"
                    else:
                        trend = "stable"
                    
                    trends[metric_name] = {
                        'trend': trend,
                        'first_value': first_value,
                        'last_value': last_value,
                        'change_percentage': ((last_value - first_value) / first_value * 100) if first_value > 0 else 0
                    }
        
        return trends
    
    def _generate_quality_indicators(self) -> Dict[str, Any]:
        """Generate quality indicators"""
        
        quality_metrics = [m for m in self.metrics_history if m.metric_type in [MetricType.QUALITY, MetricType.SUCCESS, MetricType.ERROR]]
        
        if not quality_metrics:
            return {}
        
        indicators = {}
        
        # Latest quality metrics
        for metric in quality_metrics:
            if metric.metric_name not in indicators:
                indicators[metric.metric_name] = {
                    'latest_value': metric.value,
                    'timestamp': metric.timestamp,
                    'threshold_met': not metric.exceeds_threshold
                }
            elif metric.timestamp > indicators[metric.metric_name]['timestamp']:
                indicators[metric.metric_name] = {
                    'latest_value': metric.value,
                    'timestamp': metric.timestamp,
                    'threshold_met': not metric.exceeds_threshold
                }
        
        return indicators
    
    def _analyze_progress(self) -> Dict[str, Any]:
        """Analyze progress data"""
        
        if not self.progress_history:
            return {}
        
        latest_progress = max(self.progress_history, key=lambda p: p.timestamp)
        
        analysis = {
            'current_progress': latest_progress.progress_percentage,
            'current_phase': latest_progress.phase,
            'estimated_completion': latest_progress.estimated_completion,
            'is_on_track': latest_progress.progress_percentage > 0,
        }
        
        # Calculate average velocity
        if len(self.progress_history) >= 2:
            velocities = []
            for i in range(1, len(self.progress_history)):
                current = self.progress_history[i]
                previous = self.progress_history[i-1]
                time_diff = current.timestamp - previous.timestamp
                progress_diff = current.progress_percentage - previous.progress_percentage
                
                if time_diff > 0:
                    velocity = progress_diff / (time_diff / 3600)  # percent per hour
                    velocities.append(velocity)
            
            if velocities:
                analysis['average_velocity'] = sum(velocities) / len(velocities)
        
        return analysis
    
    def _summarize_alerts(self) -> Dict[str, int]:
        """Summarize alert counts by severity"""
        
        alert_summary = {
            AlertSeverity.INFO.value: 0,
            AlertSeverity.WARNING.value: 0,
            AlertSeverity.ERROR.value: 0,
            AlertSeverity.CRITICAL.value: 0
        }
        
        for alert in self.alert_manager.alert_history:
            alert_summary[alert.severity.value] += 1
        
        return alert_summary
    
    def _identify_optimization_opportunities(self) -> List[str]:
        """Identify optimization opportunities"""
        
        opportunities = []
        
        # Check performance trends
        performance_trends = self._analyze_performance_trends()
        
        for metric_name, trend_data in performance_trends.items():
            if trend_data['trend'] == 'increasing' and 'cpu' in metric_name.lower():
                opportunities.append(f"CPU optimization opportunity: {metric_name} increasing")
            elif trend_data['trend'] == 'increasing' and 'memory' in metric_name.lower():
                opportunities.append(f"Memory optimization opportunity: {metric_name} increasing")
            elif trend_data['trend'] == 'increasing' and 'response_time' in metric_name.lower():
                opportunities.append(f"Performance optimization opportunity: {metric_name} increasing")
        
        return opportunities
    
    def _identify_process_improvements(self) -> List[str]:
        """Identify process improvement opportunities"""
        
        improvements = []
        
        # Check alert patterns
        recent_alerts = self.alert_manager.get_recent_alerts(3600)  # Last hour
        
        if len(recent_alerts) > 10:
            improvements.append("High alert frequency - consider adjusting thresholds or improving monitoring")
        
        critical_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            improvements.append("Critical alerts detected - improve error handling and monitoring")
        
        # Check progress patterns
        if self.progress_history:
            latest_progress = max(self.progress_history, key=lambda p: p.timestamp)
            if latest_progress.progress_percentage < 50 and (time.time() - latest_progress.timestamp) > 1800:  # 30 minutes
                improvements.append("Slow progress detected - consider process optimization")
        
        return improvements


class OrchestrationMonitor:
    """Monitors three-agent development orchestration"""
    
    def __init__(self):
        self.integration_monitors = {}
        self.orchestration_metrics = []
        self.logger = logging.getLogger(__name__)
    
    def monitor_orchestration_health(self) -> Dict[str, Any]:
        """Monitor overall orchestration health and efficiency"""
        
        # Collect health from all active integration monitors
        orchestration_health = {
            'active_integrations': len(self.integration_monitors),
            'healthy_integrations': 0,
            'warning_integrations': 0,
            'critical_integrations': 0,
            'overall_health': 'unknown',
            'timestamp': time.time()
        }
        
        for session_id, monitor in self.integration_monitors.items():
            health_status = monitor.get_current_health_status(session_id)
            
            if health_status.overall_health == 'healthy':
                orchestration_health['healthy_integrations'] += 1
            elif health_status.overall_health == 'warning':
                orchestration_health['warning_integrations'] += 1
            else:
                orchestration_health['critical_integrations'] += 1
        
        # Determine overall orchestration health
        total_integrations = orchestration_health['active_integrations']
        if total_integrations == 0:
            orchestration_health['overall_health'] = 'no_active_integrations'
        elif orchestration_health['critical_integrations'] > 0:
            orchestration_health['overall_health'] = 'critical'
        elif orchestration_health['warning_integrations'] > total_integrations * 0.5:
            orchestration_health['overall_health'] = 'warning'
        else:
            orchestration_health['overall_health'] = 'healthy'
        
        return orchestration_health
    
    def detect_orchestration_issues(self) -> Dict[str, Any]:
        """Detect and alert on orchestration issues"""
        
        issues = {
            'stream_issues': [],
            'integration_issues': [],
            'quality_issues': [],
            'timestamp': time.time()
        }
        
        # Check for integration stream delays or blockages
        for session_id, monitor in self.integration_monitors.items():
            recent_progress = monitor.progress_history[-5:] if monitor.progress_history else []
            
            if recent_progress:
                latest_progress = recent_progress[-1]
                time_since_update = time.time() - latest_progress.timestamp
                
                if time_since_update > 1800:  # 30 minutes without update
                    issues['stream_issues'].append(f"No progress update for {session_id} in {time_since_update/60:.1f} minutes")
                
                if latest_progress.progress_percentage < 10 and time_since_update > 3600:  # 1 hour
                    issues['stream_issues'].append(f"Integration {session_id} appears stalled")
        
        return issues
    
    def register_integration_monitor(self, session_id: str, monitor: IntegrationMonitor):
        """Register integration monitor for orchestration tracking"""
        
        self.integration_monitors[session_id] = monitor
        self.logger.info(f"Registered integration monitor for session: {session_id}")
    
    def unregister_integration_monitor(self, session_id: str):
        """Unregister integration monitor"""
        
        if session_id in self.integration_monitors:
            del self.integration_monitors[session_id]
            self.logger.info(f"Unregistered integration monitor for session: {session_id}")
    
    def generate_orchestration_report(self) -> Dict[str, Any]:
        """Generate comprehensive orchestration report"""
        
        report = {
            'report_id': f"orchestration_report_{int(time.time())}",
            'generation_timestamp': time.time(),
            'orchestration_health': self.monitor_orchestration_health(),
            'orchestration_issues': self.detect_orchestration_issues(),
            'integration_summaries': {},
            'recommendations': []
        }
        
        # Generate individual integration summaries
        for session_id, monitor in self.integration_monitors.items():
            integration_report = monitor.generate_monitoring_report("summary")
            report['integration_summaries'][session_id] = {
                'overall_health': monitor.get_current_health_status(session_id).overall_health,
                'progress': integration_report.progress_analysis,
                'alerts': integration_report.alert_summary,
                'critical_issues': integration_report.critical_issues
            }
        
        # Generate orchestration recommendations
        if report['orchestration_health']['critical_integrations'] > 0:
            report['recommendations'].append("Address critical integration issues immediately")
        
        if report['orchestration_health']['warning_integrations'] > len(self.integration_monitors) * 0.3:
            report['recommendations'].append("High proportion of warning integrations - review process effectiveness")
        
        return report