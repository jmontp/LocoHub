"""
Status Communication Protocols

Created: 2025-06-16 with user permission
Purpose: Real-time progress tracking and status communication

Intent: Implements systematic status communication protocols from AGENT_COMMUNICATION_STANDARDS.md
including progress updates, milestone tracking, and dependency coordination.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import uuid


class ProgressStatus(Enum):
    """Progress status values"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class MilestoneStatus(Enum):
    """Milestone completion status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class BlockingSeverity(Enum):
    """Severity levels for blocking issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Milestone:
    """Milestone definition and tracking"""
    milestone_id: str
    name: str
    description: str
    target_date: datetime
    status: MilestoneStatus = MilestoneStatus.PENDING
    completion_date: Optional[datetime] = None
    completion_percentage: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    
    def is_overdue(self) -> bool:
        """Check if milestone is overdue"""
        return (self.status != MilestoneStatus.COMPLETED and 
                datetime.utcnow() > self.target_date)
    
    def days_until_due(self) -> int:
        """Calculate days until milestone is due"""
        if self.status == MilestoneStatus.COMPLETED:
            return 0
        
        delta = self.target_date - datetime.utcnow()
        return max(0, delta.days)


@dataclass
class BlockingIssue:
    """Blocking issue definition"""
    issue_id: str
    description: str
    severity: BlockingSeverity
    affected_milestones: List[str]
    estimated_impact: str
    proposed_resolution: Optional[str] = None
    required_assistance: List[str] = field(default_factory=list)
    escalation_needed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    def is_resolved(self) -> bool:
        """Check if blocking issue is resolved"""
        return self.resolved_at is not None
    
    def days_since_created(self) -> int:
        """Days since issue was created"""
        delta = datetime.utcnow() - self.created_at
        return delta.days


@dataclass
class Dependency:
    """Dependency tracking"""
    dependency_id: str
    description: str
    provider: str
    consumer: str
    needed_by: datetime
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    delivery_date: Optional[datetime] = None
    
    def is_overdue(self) -> bool:
        """Check if dependency is overdue"""
        return (self.status != ProgressStatus.COMPLETED and
                datetime.utcnow() > self.needed_by)
    
    def impact_if_delayed(self) -> str:
        """Calculate impact if dependency is delayed"""
        if self.is_overdue():
            return "CRITICAL - Already overdue"
        
        days_remaining = (self.needed_by - datetime.utcnow()).days
        if days_remaining <= 1:
            return "HIGH - Due within 1 day"
        elif days_remaining <= 3:
            return "MEDIUM - Due within 3 days"
        else:
            return "LOW - Sufficient time remaining"


@dataclass
class AgentProgress:
    """Base agent progress tracking"""
    agent_name: str
    current_milestone: str
    completion_percentage: float
    estimated_completion_time: Optional[datetime]
    recent_achievements: List[str] = field(default_factory=list)
    blocking_issues: List[BlockingIssue] = field(default_factory=list)
    next_activities: List[str] = field(default_factory=list)
    resource_requirements: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestAgentProgress(AgentProgress):
    """Test Agent specific progress tracking"""
    test_creation_progress: Dict[str, float] = field(default_factory=dict)
    requirements_coverage: float = 0.0
    test_quality_score: float = 0.0
    mock_framework_progress: float = 0.0
    documentation_progress: float = 0.0
    
    def calculate_overall_completion(self) -> float:
        """Calculate overall Test Agent completion percentage"""
        components = [
            self.test_creation_progress.get('overall', 0.0),
            self.requirements_coverage,
            self.test_quality_score,
            self.mock_framework_progress,
            self.documentation_progress
        ]
        
        return sum(components) / len(components) if components else 0.0


@dataclass
class CodeAgentProgress(AgentProgress):
    """Code Agent specific progress tracking"""
    implementation_progress: Dict[str, float] = field(default_factory=dict)
    performance_optimization_progress: float = 0.0
    code_quality_score: float = 0.0
    error_handling_progress: float = 0.0
    integration_readiness: float = 0.0
    
    def calculate_overall_completion(self) -> float:
        """Calculate overall Code Agent completion percentage"""
        components = [
            self.implementation_progress.get('overall', 0.0),
            self.performance_optimization_progress,
            self.code_quality_score,
            self.error_handling_progress,
            self.integration_readiness
        ]
        
        return sum(components) / len(components) if components else 0.0


@dataclass
class IntegrationAgentProgress(AgentProgress):
    """Integration Agent specific progress tracking"""
    test_execution_progress: float = 0.0
    integration_success_rate: float = 0.0
    conflict_resolution_progress: float = 0.0
    quality_validation_progress: float = 0.0
    
    def calculate_overall_completion(self) -> float:
        """Calculate overall Integration Agent completion percentage"""
        components = [
            self.test_execution_progress,
            self.integration_success_rate,
            self.conflict_resolution_progress,
            self.quality_validation_progress
        ]
        
        return sum(components) / len(components) if components else 0.0


class ProgressUpdateMessage:
    """Structured message for progress updates"""
    
    def __init__(self, sender: str, progress: AgentProgress, priority: str = "normal"):
        self.message_id = str(uuid.uuid4())
        self.sender = sender
        self.message_type = 'progress_update'
        self.timestamp = datetime.utcnow()
        self.priority = priority
        
        # Structured progress content
        self.current_milestone = progress.current_milestone
        self.completion_percentage = progress.completion_percentage
        self.estimated_completion_time = progress.estimated_completion_time
        self.recent_achievements = progress.recent_achievements
        self.blocking_issues = progress.blocking_issues
        self.next_activities = progress.next_activities
        self.resource_requirements = progress.resource_requirements
        self.agent_specific_progress = progress
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority,
            'current_milestone': self.current_milestone,
            'completion_percentage': self.completion_percentage,
            'estimated_completion_time': self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
            'recent_achievements': self.recent_achievements,
            'blocking_issues': [asdict(issue) for issue in self.blocking_issues],
            'next_activities': self.next_activities,
            'resource_requirements': self.resource_requirements,
            'agent_specific_progress': asdict(self.agent_specific_progress)
        }
    
    def validate_message_content(self) -> Dict[str, Any]:
        """Validate message content completeness and consistency"""
        validation_issues = []
        
        # Required field validation
        required_fields = ['current_milestone', 'completion_percentage']
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                validation_issues.append(f"Required field missing: {field}")
        
        # Content consistency validation
        if hasattr(self, 'completion_percentage'):
            if not (0 <= self.completion_percentage <= 100):
                validation_issues.append("Completion percentage must be between 0 and 100")
        
        return {
            'is_valid': len(validation_issues) == 0,
            'issues': validation_issues
        }


class BlockingIssueMessage:
    """Structured message for blocking issue notifications"""
    
    def __init__(self, sender: str, blocking_issue: BlockingIssue):
        self.message_id = str(uuid.uuid4())
        self.sender = sender
        self.message_type = 'blocking_issue'
        self.timestamp = datetime.utcnow()
        self.priority = "high"  # Always high priority
        
        # Structured blocking issue content
        self.issue_id = blocking_issue.issue_id
        self.issue_type = blocking_issue.severity.value
        self.issue_description = blocking_issue.description
        self.affected_milestones = blocking_issue.affected_milestones
        self.estimated_impact = blocking_issue.estimated_impact
        self.proposed_resolution = blocking_issue.proposed_resolution
        self.required_assistance = blocking_issue.required_assistance
        self.escalation_needed = blocking_issue.escalation_needed
    
    def requires_immediate_attention(self) -> bool:
        """Determine if blocking issue requires immediate attention"""
        immediate_attention_criteria = [
            self.escalation_needed,
            'critical' in self.issue_type.lower(),
            len(self.affected_milestones) > 2,
            'integration' in self.estimated_impact.lower()
        ]
        
        return any(immediate_attention_criteria)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority,
            'issue_id': self.issue_id,
            'issue_type': self.issue_type,
            'issue_description': self.issue_description,
            'affected_milestones': self.affected_milestones,
            'estimated_impact': self.estimated_impact,
            'proposed_resolution': self.proposed_resolution,
            'required_assistance': self.required_assistance,
            'escalation_needed': self.escalation_needed
        }


class MilestoneCompletionMessage:
    """Structured message for milestone completion notifications"""
    
    def __init__(self, sender: str, milestone: Milestone):
        self.message_id = str(uuid.uuid4())
        self.sender = sender
        self.message_type = 'milestone_completion'
        self.timestamp = datetime.utcnow()
        self.priority = "normal"
        
        self.milestone_id = milestone.milestone_id
        self.milestone_name = milestone.name
        self.completion_date = milestone.completion_date
        self.deliverables = milestone.deliverables
        self.next_dependencies = milestone.dependencies
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority,
            'milestone_id': self.milestone_id,
            'milestone_name': self.milestone_name,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'deliverables': self.deliverables,
            'next_dependencies': self.next_dependencies
        }


class DependencyRequestMessage:
    """Structured message for dependency requests"""
    
    def __init__(self, sender: str, dependency: Dependency):
        self.message_id = str(uuid.uuid4())
        self.sender = sender
        self.message_type = 'dependency_request'
        self.timestamp = datetime.utcnow()
        self.priority = "normal"
        
        self.dependency_id = dependency.dependency_id
        self.description = dependency.description
        self.provider = dependency.provider
        self.needed_by = dependency.needed_by
        self.impact_if_delayed = dependency.impact_if_delayed()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority,
            'dependency_id': self.dependency_id,
            'description': self.description,
            'provider': self.provider,
            'needed_by': self.needed_by.isoformat(),
            'impact_if_delayed': self.impact_if_delayed
        }


class StatusCommunicationProtocols:
    """Protocols for systematic status communication between agents"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.message_types = {
            'progress_update': ProgressUpdateMessage,
            'milestone_completion': MilestoneCompletionMessage,
            'blocking_issue': BlockingIssueMessage,
            'dependency_request': DependencyRequestMessage
        }
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def send_status_update(self, sender_agent: str, message_type: str, message_content: Union[AgentProgress, Milestone, BlockingIssue, Dependency]) -> Dict[str, Any]:
        """Send status update message using appropriate protocol"""
        
        # Create typed message
        if message_type == 'progress_update' and isinstance(message_content, AgentProgress):
            message = ProgressUpdateMessage(sender_agent, message_content)
        elif message_type == 'milestone_completion' and isinstance(message_content, Milestone):
            message = MilestoneCompletionMessage(sender_agent, message_content)
        elif message_type == 'blocking_issue' and isinstance(message_content, BlockingIssue):
            message = BlockingIssueMessage(sender_agent, message_content)
        elif message_type == 'dependency_request' and isinstance(message_content, Dependency):
            message = DependencyRequestMessage(sender_agent, message_content)
        else:
            raise ValueError(f"Invalid message type or content: {message_type}")
        
        # Determine recipients
        recipients = self._determine_message_recipients(sender_agent, message_type)
        
        # Save message for each recipient
        delivery_results = []
        for recipient in recipients:
            result = self._save_message_for_recipient(message, recipient)
            delivery_results.append(result)
        
        return {
            'message_id': message.message_id,
            'sender': sender_agent,
            'recipients': recipients,
            'delivery_results': delivery_results,
            'message_type': message_type
        }
    
    def _determine_message_recipients(self, sender: str, message_type: str) -> List[str]:
        """Determine message recipients based on type and sender"""
        
        # Default recipients for each message type
        recipient_map = {
            'progress_update': ['integration_agent', 'orchestrator'],
            'milestone_completion': ['test_agent', 'code_agent', 'integration_agent', 'orchestrator'],
            'blocking_issue': ['integration_agent', 'orchestrator'],
            'dependency_request': []  # Determined by dependency provider
        }
        
        recipients = recipient_map.get(message_type, [])
        
        # Remove sender from recipients
        recipients = [r for r in recipients if r != sender]
        
        return recipients
    
    def _save_message_for_recipient(self, message, recipient: str) -> Dict[str, Any]:
        """Save message for specific recipient"""
        try:
            # Create recipient inbox
            recipient_inbox = self.workspace_path / recipient / "status_messages"
            recipient_inbox.mkdir(parents=True, exist_ok=True)
            
            # Save message
            message_file = recipient_inbox / f"{message.message_id}.json"
            with open(message_file, 'w') as f:
                json.dump(message.to_dict(), f, indent=2)
            
            return {
                'recipient': recipient,
                'status': 'delivered',
                'file_path': str(message_file),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'recipient': recipient,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_status_messages(self, agent_name: str, message_type: str = None) -> List[Dict[str, Any]]:
        """Get status messages for specific agent"""
        agent_inbox = self.workspace_path / agent_name / "status_messages"
        
        if not agent_inbox.exists():
            return []
        
        messages = []
        
        for message_file in agent_inbox.glob("*.json"):
            try:
                with open(message_file, 'r') as f:
                    message_data = json.load(f)
                
                # Filter by message type if specified
                if message_type and message_data.get('message_type') != message_type:
                    continue
                
                messages.append(message_data)
                
            except Exception as e:
                print(f"Error reading message {message_file}: {e}")
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.get('timestamp', ''))
        return messages
    
    def mark_message_processed(self, agent_name: str, message_id: str):
        """Mark message as processed"""
        agent_inbox = self.workspace_path / agent_name / "status_messages"
        message_file = agent_inbox / f"{message_id}.json"
        
        if message_file.exists():
            # Move to processed folder
            processed_folder = agent_inbox / "processed"
            processed_folder.mkdir(exist_ok=True)
            
            processed_file = processed_folder / f"{message_id}.json"
            message_file.rename(processed_file)


class AgentProgressTracker:
    """Tracker for agent progress and milestone management"""
    
    def __init__(self, agent_name: str, workspace_path: Path):
        self.agent_name = agent_name
        self.workspace_path = workspace_path
        self.milestones: Dict[str, Milestone] = {}
        self.dependencies: Dict[str, Dependency] = {}
        self.blocking_issues: Dict[str, BlockingIssue] = {}
        
        # Ensure workspace exists
        agent_workspace = self.workspace_path / agent_name
        agent_workspace.mkdir(parents=True, exist_ok=True)
    
    def add_milestone(self, milestone: Milestone):
        """Add milestone to tracking"""
        self.milestones[milestone.milestone_id] = milestone
        self._save_milestones()
    
    def update_milestone_progress(self, milestone_id: str, completion_percentage: float, status: MilestoneStatus = None):
        """Update milestone progress"""
        if milestone_id in self.milestones:
            self.milestones[milestone_id].completion_percentage = completion_percentage
            
            if status:
                self.milestones[milestone_id].status = status
            
            if completion_percentage >= 100.0:
                self.milestones[milestone_id].status = MilestoneStatus.COMPLETED
                self.milestones[milestone_id].completion_date = datetime.utcnow()
            
            self._save_milestones()
    
    def add_blocking_issue(self, issue: BlockingIssue):
        """Add blocking issue"""
        self.blocking_issues[issue.issue_id] = issue
        self._save_blocking_issues()
    
    def resolve_blocking_issue(self, issue_id: str):
        """Resolve blocking issue"""
        if issue_id in self.blocking_issues:
            self.blocking_issues[issue_id].resolved_at = datetime.utcnow()
            self._save_blocking_issues()
    
    def add_dependency(self, dependency: Dependency):
        """Add dependency"""
        self.dependencies[dependency.dependency_id] = dependency
        self._save_dependencies()
    
    def update_dependency_status(self, dependency_id: str, status: ProgressStatus, delivery_date: datetime = None):
        """Update dependency status"""
        if dependency_id in self.dependencies:
            self.dependencies[dependency_id].status = status
            
            if delivery_date:
                self.dependencies[dependency_id].delivery_date = delivery_date
            
            if status == ProgressStatus.COMPLETED and not delivery_date:
                self.dependencies[dependency_id].delivery_date = datetime.utcnow()
            
            self._save_dependencies()
    
    def get_current_progress(self) -> AgentProgress:
        """Get current agent progress"""
        
        # Calculate overall completion percentage
        if self.milestones:
            total_completion = sum(m.completion_percentage for m in self.milestones.values())
            completion_percentage = total_completion / len(self.milestones)
        else:
            completion_percentage = 0.0
        
        # Get current milestone
        current_milestone = self._get_current_milestone()
        
        # Get active blocking issues
        active_blocking_issues = [
            issue for issue in self.blocking_issues.values()
            if not issue.is_resolved()
        ]
        
        # Estimate completion time
        estimated_completion = self._estimate_completion_time()
        
        return AgentProgress(
            agent_name=self.agent_name,
            current_milestone=current_milestone,
            completion_percentage=completion_percentage,
            estimated_completion_time=estimated_completion,
            blocking_issues=active_blocking_issues
        )
    
    def _get_current_milestone(self) -> str:
        """Get current active milestone"""
        # Find milestone that is in progress
        for milestone in self.milestones.values():
            if milestone.status == MilestoneStatus.IN_PROGRESS:
                return milestone.name
        
        # If no in-progress milestone, find next pending milestone
        pending_milestones = [
            m for m in self.milestones.values()
            if m.status == MilestoneStatus.PENDING
        ]
        
        if pending_milestones:
            # Sort by target date and return earliest
            pending_milestones.sort(key=lambda m: m.target_date)
            return pending_milestones[0].name
        
        return "No active milestone"
    
    def _estimate_completion_time(self) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        incomplete_milestones = [
            m for m in self.milestones.values()
            if m.status not in [MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED]
        ]
        
        if not incomplete_milestones:
            return None
        
        # Use latest target date as estimate
        latest_target = max(m.target_date for m in incomplete_milestones)
        return latest_target
    
    def _save_milestones(self):
        """Save milestones to file"""
        milestones_file = self.workspace_path / self.agent_name / "milestones.json"
        
        milestones_data = {
            milestone_id: {
                **asdict(milestone),
                'target_date': milestone.target_date.isoformat(),
                'completion_date': milestone.completion_date.isoformat() if milestone.completion_date else None,
                'status': milestone.status.value
            }
            for milestone_id, milestone in self.milestones.items()
        }
        
        with open(milestones_file, 'w') as f:
            json.dump(milestones_data, f, indent=2)
    
    def _save_blocking_issues(self):
        """Save blocking issues to file"""
        issues_file = self.workspace_path / self.agent_name / "blocking_issues.json"
        
        issues_data = {
            issue_id: {
                **asdict(issue),
                'severity': issue.severity.value,
                'created_at': issue.created_at.isoformat(),
                'resolved_at': issue.resolved_at.isoformat() if issue.resolved_at else None
            }
            for issue_id, issue in self.blocking_issues.items()
        }
        
        with open(issues_file, 'w') as f:
            json.dump(issues_data, f, indent=2)
    
    def _save_dependencies(self):
        """Save dependencies to file"""
        dependencies_file = self.workspace_path / self.agent_name / "dependencies.json"
        
        dependencies_data = {
            dep_id: {
                **asdict(dependency),
                'needed_by': dependency.needed_by.isoformat(),
                'delivery_date': dependency.delivery_date.isoformat() if dependency.delivery_date else None,
                'status': dependency.status.value
            }
            for dep_id, dependency in self.dependencies.items()
        }
        
        with open(dependencies_file, 'w') as f:
            json.dump(dependencies_data, f, indent=2)