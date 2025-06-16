"""
Monitor Agent Progress

Created: 2025-06-16 with user permission
Purpose: Real-time progress tracking and monitoring for all agents

Intent: Provides comprehensive monitoring capabilities including progress tracking,
quality metrics collection, and automated reporting for the three-agent framework.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from threading import Thread, Event
from dataclasses import dataclass, asdict

# Add framework to path
framework_path = Path(__file__).parent
if str(framework_path) not in sys.path:
    sys.path.insert(0, str(framework_path))

from shared.config.agent_config import ConfigurationManager
from shared.communication.status_communication import StatusCommunicationProtocols, AgentProgressTracker


@dataclass
class MonitoringMetrics:
    """Monitoring metrics collection"""
    timestamp: datetime
    agent_name: str
    completion_percentage: float
    active_milestones: int
    blocking_issues: int
    quality_score: float
    communication_activity: int
    last_update: datetime


@dataclass
class FrameworkStatus:
    """Overall framework status"""
    timestamp: datetime
    overall_completion: float
    active_agents: int
    total_blocking_issues: int
    average_quality_score: float
    communication_health: str
    agent_metrics: Dict[str, MonitoringMetrics]


class AgentProgressMonitor:
    """Real-time progress monitoring for agent framework"""
    
    def __init__(self, deployment_path: Path):
        self.deployment_path = deployment_path
        self.framework_path = framework_path
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.config_manager = None
        self.status_protocols = None
        self.agent_trackers: Dict[str, AgentProgressTracker] = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.stop_event = Event()
        
        # Metrics storage
        self.metrics_history: List[FrameworkStatus] = []
        self.monitoring_config = {}
        
        self._initialize_monitoring()
    
    def setup_logging(self):
        """Setup monitoring logging"""
        
        # Create logs directory
        logs_dir = self.deployment_path / 'shared' / 'monitoring' / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / 'monitoring.log'),
                logging.StreamHandler()
            ]
        )
    
    def _initialize_monitoring(self):
        """Initialize monitoring components"""
        
        try:
            # Initialize configuration manager
            config_path = self.deployment_path / 'shared' / 'config'
            if config_path.exists():
                self.config_manager = ConfigurationManager(config_path)
            
            # Initialize status communication
            communication_path = self.deployment_path / 'shared' / 'communication'
            if communication_path.exists():
                self.status_protocols = StatusCommunicationProtocols(communication_path)
            
            # Initialize agent trackers
            agents = ['test_agent', 'code_agent', 'integration_agent']
            for agent_name in agents:
                agent_workspace = self.deployment_path / agent_name
                if agent_workspace.exists():
                    self.agent_trackers[agent_name] = AgentProgressTracker(
                        agent_name, self.deployment_path
                    )
            
            # Load monitoring configuration
            self._load_monitoring_config()
            
            self.logger.info("Monitoring components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring: {e}")
    
    def _load_monitoring_config(self):
        """Load monitoring configuration"""
        
        config_file = self.deployment_path / 'shared' / 'monitoring' / 'monitoring_config.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.monitoring_config = json.load(f)
        else:
            # Default configuration
            self.monitoring_config = {
                'enabled': True,
                'collection_interval_seconds': 300,  # 5 minutes
                'retention_days': 90,
                'alerts': {
                    'enabled': True,
                    'thresholds': {
                        'completion_delay_hours': 24,
                        'quality_score_minimum': 0.8,
                        'error_rate_maximum': 0.05
                    }
                }
            }
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        
        if self.monitoring_active:
            self.logger.warning("Monitoring is already active")
            return
        
        if not self.monitoring_config.get('enabled', True):
            self.logger.info("Monitoring is disabled in configuration")
            return
        
        self.logger.info("Starting agent progress monitoring...")
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        # Start monitoring thread
        self.monitoring_thread = Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info("Agent progress monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.logger.info("Stopping agent progress monitoring...")
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=10)
        
        self.logger.info("Agent progress monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        interval = self.monitoring_config.get('collection_interval_seconds', 300)
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Collect metrics
                framework_status = self.collect_framework_metrics()
                
                # Store metrics
                self._store_metrics(framework_status)
                
                # Check alerts
                self._check_alerts(framework_status)
                
                # Generate periodic reports
                self._generate_periodic_reports(framework_status)
                
                # Clean old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            # Wait for next collection interval
            if not self.stop_event.wait(interval):
                continue
            else:
                break
    
    def collect_framework_metrics(self) -> FrameworkStatus:
        """Collect comprehensive framework metrics"""
        
        timestamp = datetime.utcnow()
        agent_metrics = {}
        
        # Collect metrics for each agent
        for agent_name, tracker in self.agent_trackers.items():
            try:
                agent_metrics[agent_name] = self._collect_agent_metrics(agent_name, tracker)
            except Exception as e:
                self.logger.error(f"Failed to collect metrics for {agent_name}: {e}")
                # Create default metrics for failed collection
                agent_metrics[agent_name] = MonitoringMetrics(
                    timestamp=timestamp,
                    agent_name=agent_name,
                    completion_percentage=0.0,
                    active_milestones=0,
                    blocking_issues=0,
                    quality_score=0.0,
                    communication_activity=0,
                    last_update=timestamp
                )
        
        # Calculate framework-level metrics
        overall_completion = self._calculate_overall_completion(agent_metrics)
        active_agents = len([m for m in agent_metrics.values() if m.completion_percentage > 0])
        total_blocking_issues = sum(m.blocking_issues for m in agent_metrics.values())
        average_quality_score = self._calculate_average_quality(agent_metrics)
        communication_health = self._assess_communication_health(agent_metrics)
        
        return FrameworkStatus(
            timestamp=timestamp,
            overall_completion=overall_completion,
            active_agents=active_agents,
            total_blocking_issues=total_blocking_issues,
            average_quality_score=average_quality_score,
            communication_health=communication_health,
            agent_metrics=agent_metrics
        )
    
    def _collect_agent_metrics(self, agent_name: str, tracker: AgentProgressTracker) -> MonitoringMetrics:
        """Collect metrics for specific agent"""
        
        timestamp = datetime.utcnow()
        
        # Get current progress
        progress = tracker.get_current_progress()
        
        # Count active milestones
        active_milestones = len([
            m for m in tracker.milestones.values()
            if m.status.value in ['pending', 'in_progress']
        ])
        
        # Count blocking issues
        blocking_issues = len([
            issue for issue in tracker.blocking_issues.values()
            if not issue.is_resolved()
        ])
        
        # Calculate quality score (placeholder - would be based on actual quality metrics)
        quality_score = self._calculate_agent_quality_score(agent_name)
        
        # Get communication activity
        communication_activity = self._get_communication_activity(agent_name)
        
        # Get last update time
        last_update = self._get_last_update_time(agent_name)
        
        return MonitoringMetrics(
            timestamp=timestamp,
            agent_name=agent_name,
            completion_percentage=progress.completion_percentage,
            active_milestones=active_milestones,
            blocking_issues=blocking_issues,
            quality_score=quality_score,
            communication_activity=communication_activity,
            last_update=last_update
        )
    
    def _calculate_overall_completion(self, agent_metrics: Dict[str, MonitoringMetrics]) -> float:
        """Calculate overall framework completion percentage"""
        
        if not agent_metrics:
            return 0.0
        
        total_completion = sum(m.completion_percentage for m in agent_metrics.values())
        return total_completion / len(agent_metrics)
    
    def _calculate_average_quality(self, agent_metrics: Dict[str, MonitoringMetrics]) -> float:
        """Calculate average quality score across agents"""
        
        if not agent_metrics:
            return 0.0
        
        total_quality = sum(m.quality_score for m in agent_metrics.values())
        return total_quality / len(agent_metrics)
    
    def _assess_communication_health(self, agent_metrics: Dict[str, MonitoringMetrics]) -> str:
        """Assess communication health"""
        
        # Check recent communication activity
        recent_activity = sum(m.communication_activity for m in agent_metrics.values())
        
        # Check last update times
        current_time = datetime.utcnow()
        stale_agents = 0
        
        for metrics in agent_metrics.values():
            time_since_update = (current_time - metrics.last_update).total_seconds()
            if time_since_update > 3600:  # 1 hour
                stale_agents += 1
        
        if stale_agents == 0 and recent_activity > 0:
            return "healthy"
        elif stale_agents <= 1:
            return "warning"
        else:
            return "unhealthy"
    
    def _calculate_agent_quality_score(self, agent_name: str) -> float:
        """Calculate quality score for agent (placeholder implementation)"""
        
        # This would integrate with actual quality metrics collection
        # For now, return a mock score based on workspace activity
        
        agent_workspace = self.deployment_path / agent_name
        
        if not agent_workspace.exists():
            return 0.0
        
        # Simple heuristic based on workspace content
        output_files = len(list((agent_workspace / 'output').glob('*'))) if (agent_workspace / 'output').exists() else 0
        workspace_files = len(list((agent_workspace / 'workspace').glob('*'))) if (agent_workspace / 'workspace').exists() else 0
        
        # Basic quality score calculation
        base_score = min((output_files + workspace_files) / 10.0, 1.0)
        return max(0.6, base_score)  # Minimum score of 0.6
    
    def _get_communication_activity(self, agent_name: str) -> int:
        """Get recent communication activity for agent"""
        
        if not self.status_protocols:
            return 0
        
        try:
            # Get recent status messages
            messages = self.status_protocols.get_status_messages(agent_name)
            
            # Count messages from last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_messages = [
                m for m in messages
                if datetime.fromisoformat(m.get('timestamp', '')) > one_hour_ago
            ]
            
            return len(recent_messages)
            
        except Exception as e:
            self.logger.debug(f"Could not get communication activity for {agent_name}: {e}")
            return 0
    
    def _get_last_update_time(self, agent_name: str) -> datetime:
        """Get last update time for agent"""
        
        if not self.status_protocols:
            return datetime.utcnow() - timedelta(hours=24)  # Default to 24 hours ago
        
        try:
            # Get latest status message
            messages = self.status_protocols.get_status_messages(agent_name)
            
            if messages:
                # Get most recent message timestamp
                latest_message = max(messages, key=lambda m: m.get('timestamp', ''))
                return datetime.fromisoformat(latest_message['timestamp'])
            
        except Exception as e:
            self.logger.debug(f"Could not get last update time for {agent_name}: {e}")
        
        return datetime.utcnow() - timedelta(hours=24)
    
    def _store_metrics(self, framework_status: FrameworkStatus):
        """Store metrics to persistent storage"""
        
        # Add to in-memory history
        self.metrics_history.append(framework_status)
        
        # Save to file
        metrics_dir = self.deployment_path / 'shared' / 'monitoring' / 'metrics'
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Save current metrics
        current_metrics_file = metrics_dir / 'current_metrics.json'
        with open(current_metrics_file, 'w') as f:
            json.dump(self._serialize_framework_status(framework_status), f, indent=2)
        
        # Save to daily metrics file
        date_str = framework_status.timestamp.strftime('%Y-%m-%d')
        daily_metrics_file = metrics_dir / f'metrics_{date_str}.jsonl'
        
        with open(daily_metrics_file, 'a') as f:
            f.write(json.dumps(self._serialize_framework_status(framework_status)) + '\n')
    
    def _serialize_framework_status(self, status: FrameworkStatus) -> Dict[str, Any]:
        """Serialize framework status for storage"""
        
        serialized = asdict(status)
        
        # Convert datetime objects to ISO format
        serialized['timestamp'] = status.timestamp.isoformat()
        
        for agent_name, metrics in serialized['agent_metrics'].items():
            metrics['timestamp'] = status.agent_metrics[agent_name].timestamp.isoformat()
            metrics['last_update'] = status.agent_metrics[agent_name].last_update.isoformat()
        
        return serialized
    
    def _check_alerts(self, framework_status: FrameworkStatus):
        """Check for alert conditions"""
        
        if not self.monitoring_config.get('alerts', {}).get('enabled', True):
            return
        
        thresholds = self.monitoring_config.get('alerts', {}).get('thresholds', {})
        alerts = []
        
        # Check completion delays
        completion_delay_threshold = thresholds.get('completion_delay_hours', 24)
        for agent_name, metrics in framework_status.agent_metrics.items():
            time_since_update = (framework_status.timestamp - metrics.last_update).total_seconds() / 3600
            
            if time_since_update > completion_delay_threshold:
                alerts.append({
                    'type': 'completion_delay',
                    'agent': agent_name,
                    'severity': 'high',
                    'message': f'Agent {agent_name} has not updated progress in {time_since_update:.1f} hours'
                })
        
        # Check quality scores
        quality_threshold = thresholds.get('quality_score_minimum', 0.8)
        for agent_name, metrics in framework_status.agent_metrics.items():
            if metrics.quality_score < quality_threshold:
                alerts.append({
                    'type': 'quality_score',
                    'agent': agent_name,
                    'severity': 'medium',
                    'message': f'Agent {agent_name} quality score ({metrics.quality_score:.2f}) below threshold ({quality_threshold})'
                })
        
        # Check blocking issues
        if framework_status.total_blocking_issues > 0:
            alerts.append({
                'type': 'blocking_issues',
                'severity': 'high' if framework_status.total_blocking_issues > 2 else 'medium',
                'message': f'Framework has {framework_status.total_blocking_issues} active blocking issues'
            })
        
        # Process alerts
        if alerts:
            self._process_alerts(alerts)
    
    def _process_alerts(self, alerts: List[Dict[str, Any]]):
        """Process and log alerts"""
        
        alerts_dir = self.deployment_path / 'shared' / 'monitoring' / 'alerts'
        alerts_dir.mkdir(parents=True, exist_ok=True)
        
        # Log alerts
        for alert in alerts:
            severity = alert['severity']
            message = alert['message']
            
            if severity == 'high':
                self.logger.error(f"ALERT: {message}")
            elif severity == 'medium':
                self.logger.warning(f"ALERT: {message}")
            else:
                self.logger.info(f"ALERT: {message}")
        
        # Save alerts to file
        timestamp = datetime.utcnow()
        alert_file = alerts_dir / f"alerts_{timestamp.strftime('%Y-%m-%d')}.jsonl"
        
        with open(alert_file, 'a') as f:
            for alert in alerts:
                alert_record = {
                    'timestamp': timestamp.isoformat(),
                    **alert
                }
                f.write(json.dumps(alert_record) + '\n')
    
    def _generate_periodic_reports(self, framework_status: FrameworkStatus):
        """Generate periodic monitoring reports"""
        
        # Generate hourly summary
        if framework_status.timestamp.minute == 0:  # Top of the hour
            self._generate_hourly_summary(framework_status)
        
        # Generate daily report
        if framework_status.timestamp.hour == 0 and framework_status.timestamp.minute < 10:  # Early morning
            self._generate_daily_report()
    
    def _generate_hourly_summary(self, framework_status: FrameworkStatus):
        """Generate hourly monitoring summary"""
        
        summary = {
            'timestamp': framework_status.timestamp.isoformat(),
            'overall_completion': framework_status.overall_completion,
            'active_agents': framework_status.active_agents,
            'blocking_issues': framework_status.total_blocking_issues,
            'quality_score': framework_status.average_quality_score,
            'communication_health': framework_status.communication_health
        }
        
        reports_dir = self.deployment_path / 'shared' / 'monitoring' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = framework_status.timestamp.strftime('%Y-%m-%d')
        hourly_file = reports_dir / f'hourly_summary_{date_str}.jsonl'
        
        with open(hourly_file, 'a') as f:
            f.write(json.dumps(summary) + '\n')
        
        self.logger.info(f"Hourly summary: {framework_status.overall_completion:.1f}% complete, "
                        f"{framework_status.active_agents} active agents, "
                        f"{framework_status.total_blocking_issues} blocking issues")
    
    def _generate_daily_report(self):
        """Generate daily monitoring report"""
        
        if not self.metrics_history:
            return
        
        # Get yesterday's metrics
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday_metrics = [
            m for m in self.metrics_history
            if m.timestamp.date() == yesterday.date()
        ]
        
        if not yesterday_metrics:
            return
        
        # Calculate daily statistics
        daily_stats = {
            'date': yesterday.strftime('%Y-%m-%d'),
            'completion_progress': {
                'start': yesterday_metrics[0].overall_completion,
                'end': yesterday_metrics[-1].overall_completion,
                'change': yesterday_metrics[-1].overall_completion - yesterday_metrics[0].overall_completion
            },
            'average_quality': sum(m.average_quality_score for m in yesterday_metrics) / len(yesterday_metrics),
            'blocking_issues': {
                'max': max(m.total_blocking_issues for m in yesterday_metrics),
                'average': sum(m.total_blocking_issues for m in yesterday_metrics) / len(yesterday_metrics)
            },
            'agent_activity': {
                agent: len([m for m in yesterday_metrics if agent in m.agent_metrics])
                for agent in ['test_agent', 'code_agent', 'integration_agent']
            }
        }
        
        # Save daily report
        reports_dir = self.deployment_path / 'shared' / 'monitoring' / 'reports'
        daily_report_file = reports_dir / f"daily_report_{yesterday.strftime('%Y-%m-%d')}.json"
        
        with open(daily_report_file, 'w') as f:
            json.dump(daily_stats, f, indent=2)
        
        self.logger.info(f"Daily report generated for {yesterday.strftime('%Y-%m-%d')}")
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics based on retention policy"""
        
        retention_days = self.monitoring_config.get('retention_days', 90)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Clean in-memory history
        self.metrics_history = [
            m for m in self.metrics_history
            if m.timestamp > cutoff_date
        ]
        
        # Clean old files
        metrics_dir = self.deployment_path / 'shared' / 'monitoring' / 'metrics'
        if metrics_dir.exists():
            for metrics_file in metrics_dir.glob('metrics_*.jsonl'):
                try:
                    # Extract date from filename
                    date_str = metrics_file.stem.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        metrics_file.unlink()
                        self.logger.debug(f"Deleted old metrics file: {metrics_file}")
                        
                except Exception as e:
                    self.logger.debug(f"Could not process metrics file {metrics_file}: {e}")
    
    def get_current_status(self) -> Optional[FrameworkStatus]:
        """Get current framework status"""
        
        if self.metrics_history:
            return self.metrics_history[-1]
        else:
            return self.collect_framework_metrics()
    
    def generate_status_report(self) -> str:
        """Generate formatted status report"""
        
        current_status = self.get_current_status()
        
        if not current_status:
            return "No monitoring data available"
        
        report = f"""
Three-Agent Framework Status Report
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

FRAMEWORK OVERVIEW
==================
Overall Completion: {current_status.overall_completion:.1f}%
Active Agents: {current_status.active_agents}/3
Blocking Issues: {current_status.total_blocking_issues}
Average Quality Score: {current_status.average_quality_score:.2f}
Communication Health: {current_status.communication_health.upper()}

AGENT STATUS
============
"""
        
        for agent_name, metrics in current_status.agent_metrics.items():
            time_since_update = (current_status.timestamp - metrics.last_update).total_seconds() / 3600
            
            report += f"""
{agent_name.upper()}:
  Completion: {metrics.completion_percentage:.1f}%
  Active Milestones: {metrics.active_milestones}
  Blocking Issues: {metrics.blocking_issues}
  Quality Score: {metrics.quality_score:.2f}
  Last Update: {time_since_update:.1f} hours ago
  Communication Activity: {metrics.communication_activity} messages/hour
"""
        
        report += f"""
MONITORING STATUS
=================
Monitoring Active: {self.monitoring_active}
Collection Interval: {self.monitoring_config.get('collection_interval_seconds', 0)} seconds
Metrics Retained: {len(self.metrics_history)} data points
Alerts Enabled: {self.monitoring_config.get('alerts', {}).get('enabled', False)}
"""
        
        return report


def main():
    """Main monitoring function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor Three-Agent Framework Progress')
    parser.add_argument('--deployment-path', type=Path, 
                       help='Path to agent framework deployment')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous monitoring (Ctrl+C to stop)')
    parser.add_argument('--status', action='store_true',
                       help='Show current status and exit')
    parser.add_argument('--report', action='store_true',
                       help='Generate status report and exit')
    
    args = parser.parse_args()
    
    # Get deployment path
    if args.deployment_path:
        deployment_path = args.deployment_path
    else:
        import os
        deployment_path = Path(os.getenv('AGENT_DEPLOYMENT_PATH', 
                                        Path(__file__).parent.parent / 'agent_workspaces'))
    
    if not deployment_path.exists():
        print(f"Deployment path does not exist: {deployment_path}")
        sys.exit(1)
    
    # Initialize monitor
    monitor = AgentProgressMonitor(deployment_path)
    
    if args.status or args.report:
        # Show current status
        current_status = monitor.get_current_status()
        
        if args.status:
            if current_status:
                print(f"Framework Completion: {current_status.overall_completion:.1f}%")
                print(f"Active Agents: {current_status.active_agents}/3")
                print(f"Blocking Issues: {current_status.total_blocking_issues}")
                print(f"Quality Score: {current_status.average_quality_score:.2f}")
                print(f"Communication: {current_status.communication_health}")
            else:
                print("No status data available")
        
        if args.report:
            report = monitor.generate_status_report()
            print(report)
    
    elif args.continuous:
        # Run continuous monitoring
        print(f"Starting continuous monitoring of: {deployment_path}")
        print("Press Ctrl+C to stop...")
        
        try:
            monitor.start_monitoring()
            
            # Keep main thread alive
            while monitor.monitoring_active:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            monitor.stop_monitoring()
            print("Monitoring stopped")
    
    else:
        # Single status check
        current_status = monitor.get_current_status()
        
        if current_status:
            print(f"Three-Agent Framework Status")
            print(f"Overall Completion: {current_status.overall_completion:.1f}%")
            print(f"Active Agents: {current_status.active_agents}/3")
            print(f"Blocking Issues: {current_status.total_blocking_issues}")
            
            print(f"\nAgent Details:")
            for agent_name, metrics in current_status.agent_metrics.items():
                print(f"  {agent_name}: {metrics.completion_percentage:.1f}% complete")
        else:
            print("No monitoring data available")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())