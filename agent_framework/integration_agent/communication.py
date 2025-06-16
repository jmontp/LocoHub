"""
Orchestration Communication Framework for Integration Agent

Created: 2025-01-16 with user permission
Purpose: Communication coordination with Implementation Orchestrator

Intent: Provides systematic communication protocols between Integration Agent
and Implementation Orchestrator, including progress reporting, escalation
management, feedback loops, and coordination messaging for three-agent workflows.
"""

import time
import json
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import logging
import queue
import threading


class MessageType(Enum):
    """Types of orchestration messages"""
    INTEGRATION_STARTED = "integration_started"
    PROGRESS_UPDATE = "progress_update"
    INTEGRATION_COMPLETED = "integration_completed"
    CONFLICT_DETECTED = "conflict_detected"
    ESCALATION_REQUIRED = "escalation_required"
    QUALITY_GATE_STATUS = "quality_gate_status"
    SIGN_OFF_REQUEST = "sign_off_request"
    SIGN_OFF_COMPLETED = "sign_off_completed"
    SYSTEM_ALERT = "system_alert"
    COORDINATION_REQUEST = "coordination_request"
    STATUS_INQUIRY = "status_inquiry"
    FEEDBACK_SUBMISSION = "feedback_submission"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class CommunicationChannel(Enum):
    """Communication channels for different message types"""
    PROGRESS_REPORTS = "progress_reports"
    ESCALATIONS = "escalations"
    QUALITY_GATES = "quality_gates"
    COORDINATION = "coordination"
    ALERTS = "alerts"
    FEEDBACK = "feedback"


@dataclass
class OrchestrationMessage:
    """Message for orchestration communication"""
    
    message_id: str
    message_type: MessageType
    priority: MessagePriority
    timestamp: float
    
    # Message content
    sender: str = "integration_agent"
    recipient: str = "implementation_orchestrator"
    subject: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    
    # Message metadata
    session_id: str = ""
    channel: CommunicationChannel = CommunicationChannel.COORDINATION
    requires_response: bool = False
    response_deadline: Optional[float] = None
    
    # Message tracking
    sent_timestamp: Optional[float] = None
    received_timestamp: Optional[float] = None
    acknowledged_timestamp: Optional[float] = None
    response_message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrchestrationMessage':
        """Create message from dictionary"""
        # Convert enum strings back to enums
        if 'message_type' in data:
            data['message_type'] = MessageType(data['message_type'])
        if 'priority' in data:
            data['priority'] = MessagePriority(data['priority'])
        if 'channel' in data:
            data['channel'] = CommunicationChannel(data['channel'])
        
        return cls(**data)


@dataclass
class CommunicationConfiguration:
    """Configuration for orchestration communication"""
    
    # Connection settings
    orchestrator_endpoint: str = "localhost:8080"
    communication_protocol: str = "http"
    authentication_token: Optional[str] = None
    
    # Message handling
    message_queue_size: int = 1000
    message_retry_attempts: int = 3
    message_timeout_seconds: float = 30.0
    
    # Response handling
    response_timeout_seconds: float = 60.0
    acknowledgment_required: bool = True
    
    # Channel configuration
    channel_priorities: Dict[CommunicationChannel, int] = field(default_factory=lambda: {
        CommunicationChannel.ESCALATIONS: 1,
        CommunicationChannel.ALERTS: 2,
        CommunicationChannel.QUALITY_GATES: 3,
        CommunicationChannel.COORDINATION: 4,
        CommunicationChannel.PROGRESS_REPORTS: 5,
        CommunicationChannel.FEEDBACK: 6
    })


@dataclass
class IntegrationProgressReport:
    """Progress report for integration session"""
    
    session_id: str
    current_phase: str
    progress_percentage: float
    status: str
    timestamp: float
    
    # Progress details
    completed_phases: List[str] = field(default_factory=list)
    remaining_phases: List[str] = field(default_factory=list)
    estimated_completion_time: Optional[float] = None
    
    # Performance metrics
    execution_time_so_far: float = 0.0
    current_phase_duration: float = 0.0
    
    # Issues and blockers
    current_issues: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    
    # Quality metrics
    test_pass_rate: Optional[float] = None
    quality_score: Optional[float] = None
    critical_failures: int = 0


@dataclass
class ConflictEscalationRequest:
    """Request for conflict escalation to orchestrator"""
    
    session_id: str
    conflict_id: str
    conflict_type: str
    escalation_reason: str
    timestamp: float
    
    # Conflict details
    conflict_description: str = ""
    affected_agents: List[str] = field(default_factory=list)
    attempted_resolutions: List[str] = field(default_factory=list)
    
    # Escalation context
    urgency_level: str = "normal"
    business_impact: str = "medium"
    suggested_actions: List[str] = field(default_factory=list)
    
    # Resolution requirements
    requires_specification_clarification: bool = False
    requires_stakeholder_decision: bool = False
    requires_external_expertise: bool = False


@dataclass
class QualityGateNotification:
    """Notification about quality gate status"""
    
    session_id: str
    gate_name: str
    gate_status: str
    timestamp: float
    
    # Gate details
    gate_criteria: List[str] = field(default_factory=list)
    passed_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    
    # Quality metrics
    overall_quality_score: float = 0.0
    compliance_percentage: float = 0.0
    
    # Actions required
    required_actions: List[str] = field(default_factory=list)
    recommended_improvements: List[str] = field(default_factory=list)


@dataclass
class SignOffRequest:
    """Request for integration sign-off"""
    
    session_id: str
    sign_off_type: str
    requestor: str
    timestamp: float
    
    # Sign-off details
    validation_results: Dict[str, Any] = field(default_factory=dict)
    success_criteria_met: bool = False
    conditional_requirements: List[str] = field(default_factory=list)
    
    # Supporting documentation
    test_results_summary: Dict[str, Any] = field(default_factory=dict)
    performance_validation: Dict[str, Any] = field(default_factory=dict)
    quality_assessment: Dict[str, Any] = field(default_factory=dict)
    
    # Approval context
    deployment_readiness: bool = False
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


class MessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    def can_handle(self, message_type: MessageType) -> bool:
        """Check if handler can process message type"""
        pass
    
    @abstractmethod
    def handle_message(self, message: OrchestrationMessage) -> Optional[OrchestrationMessage]:
        """Handle message and optionally return response"""
        pass


class ProgressReportHandler(MessageHandler):
    """Handles progress report messages"""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.PROGRESS_UPDATE
    
    def handle_message(self, message: OrchestrationMessage) -> Optional[OrchestrationMessage]:
        """Handle progress report message"""
        
        progress_data = message.content.get('progress_report', {})
        
        # Log progress update
        logging.getLogger(__name__).info(
            f"Progress update for session {message.session_id}: "
            f"{progress_data.get('progress_percentage', 0):.1f}% complete"
        )
        
        # Send acknowledgment if required
        if message.requires_response:
            response = OrchestrationMessage(
                message_id=f"ack_{message.message_id}",
                message_type=MessageType.STATUS_INQUIRY,  # Reusing for acknowledgment
                priority=MessagePriority.LOW,
                timestamp=time.time(),
                recipient=message.sender,
                subject=f"Progress update acknowledged",
                content={'acknowledged': True, 'original_message_id': message.message_id},
                session_id=message.session_id
            )
            return response
        
        return None


class EscalationHandler(MessageHandler):
    """Handles escalation messages"""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.ESCALATION_REQUIRED
    
    def handle_message(self, message: OrchestrationMessage) -> Optional[OrchestrationMessage]:
        """Handle escalation message"""
        
        escalation_data = message.content.get('escalation_request', {})
        
        # Log escalation
        logging.getLogger(__name__).warning(
            f"Escalation required for session {message.session_id}: "
            f"{escalation_data.get('escalation_reason', 'Unknown reason')}"
        )
        
        # Acknowledge escalation receipt
        response = OrchestrationMessage(
            message_id=f"escalation_ack_{message.message_id}",
            message_type=MessageType.STATUS_INQUIRY,
            priority=MessagePriority.HIGH,
            timestamp=time.time(),
            recipient=message.sender,
            subject="Escalation received and being processed",
            content={
                'escalation_acknowledged': True,
                'original_message_id': message.message_id,
                'estimated_response_time': time.time() + 3600  # 1 hour
            },
            session_id=message.session_id
        )
        
        return response


class QualityGateHandler(MessageHandler):
    """Handles quality gate messages"""
    
    def can_handle(self, message_type: MessageType) -> bool:
        return message_type == MessageType.QUALITY_GATE_STATUS
    
    def handle_message(self, message: OrchestrationMessage) -> Optional[OrchestrationMessage]:
        """Handle quality gate message"""
        
        gate_data = message.content.get('quality_gate', {})
        gate_status = gate_data.get('gate_status', 'unknown')
        
        # Log quality gate status
        logging.getLogger(__name__).info(
            f"Quality gate status for session {message.session_id}: {gate_status}"
        )
        
        # If gate failed, may require coordination response
        if gate_status == 'failed':
            response = OrchestrationMessage(
                message_id=f"gate_response_{message.message_id}",
                message_type=MessageType.COORDINATION_REQUEST,
                priority=MessagePriority.HIGH,
                timestamp=time.time(),
                recipient=message.sender,
                subject="Quality gate failure - coordination required",
                content={
                    'coordination_type': 'quality_gate_failure',
                    'failed_criteria': gate_data.get('failed_criteria', []),
                    'recommended_actions': gate_data.get('required_actions', [])
                },
                session_id=message.session_id
            )
            return response
        
        return None


class MessageRouter:
    """Routes messages to appropriate handlers"""
    
    def __init__(self):
        self.handlers = [
            ProgressReportHandler(),
            EscalationHandler(),
            QualityGateHandler()
        ]
        self.logger = logging.getLogger(__name__)
    
    def route_message(self, message: OrchestrationMessage) -> Optional[OrchestrationMessage]:
        """Route message to appropriate handler"""
        
        for handler in self.handlers:
            if handler.can_handle(message.message_type):
                try:
                    response = handler.handle_message(message)
                    if response:
                        self.logger.debug(f"Generated response for message {message.message_id}")
                    return response
                
                except Exception as e:
                    self.logger.error(f"Error handling message {message.message_id}: {e}")
                    
                    # Generate error response
                    error_response = OrchestrationMessage(
                        message_id=f"error_{message.message_id}",
                        message_type=MessageType.SYSTEM_ALERT,
                        priority=MessagePriority.HIGH,
                        timestamp=time.time(),
                        recipient=message.sender,
                        subject="Message handling error",
                        content={
                            'error': str(e),
                            'original_message_id': message.message_id
                        },
                        session_id=message.session_id
                    )
                    return error_response
        
        self.logger.warning(f"No handler found for message type: {message.message_type}")
        return None


class MessageQueue:
    """Thread-safe message queue for orchestration communication"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.message_index = {}  # Track messages by ID
        self.pending_responses = {}  # Track pending responses
        self.logger = logging.getLogger(__name__)
    
    def enqueue_message(self, message: OrchestrationMessage):
        """Add message to queue with priority ordering"""
        
        # Convert priority to numeric value for queue ordering
        priority_values = {
            MessagePriority.CRITICAL: 1,
            MessagePriority.URGENT: 2,
            MessagePriority.HIGH: 3,
            MessagePriority.NORMAL: 4,
            MessagePriority.LOW: 5
        }
        
        priority_value = priority_values.get(message.priority, 4)
        
        try:
            # Queue item is (priority, timestamp, message) for ordering
            self.queue.put((priority_value, message.timestamp, message), block=False)
            self.message_index[message.message_id] = message
            
            if message.requires_response:
                self.pending_responses[message.message_id] = {
                    'message': message,
                    'deadline': message.response_deadline or (time.time() + 60.0)
                }
            
            self.logger.debug(f"Enqueued message {message.message_id} with priority {message.priority.value}")
            
        except queue.Full:
            self.logger.error(f"Message queue full, dropping message {message.message_id}")
    
    def dequeue_message(self, timeout: float = 1.0) -> Optional[OrchestrationMessage]:
        """Get next message from queue"""
        
        try:
            priority_value, timestamp, message = self.queue.get(timeout=timeout)
            self.logger.debug(f"Dequeued message {message.message_id}")
            return message
        
        except queue.Empty:
            return None
    
    def get_message_by_id(self, message_id: str) -> Optional[OrchestrationMessage]:
        """Retrieve message by ID"""
        return self.message_index.get(message_id)
    
    def mark_response_received(self, original_message_id: str, response_message: OrchestrationMessage):
        """Mark that response was received for message"""
        
        if original_message_id in self.pending_responses:
            del self.pending_responses[original_message_id]
            self.logger.debug(f"Response received for message {original_message_id}")
    
    def get_overdue_responses(self) -> List[OrchestrationMessage]:
        """Get messages with overdue responses"""
        
        current_time = time.time()
        overdue = []
        
        for message_id, response_info in list(self.pending_responses.items()):
            if current_time > response_info['deadline']:
                overdue.append(response_info['message'])
                del self.pending_responses[message_id]
        
        return overdue
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        
        return {
            'queue_size': self.queue.qsize(),
            'pending_responses': len(self.pending_responses),
            'total_messages_processed': len(self.message_index)
        }


class OrchestrationCommunicator:
    """Main communication coordinator for Integration Agent"""
    
    def __init__(self, config: Optional[CommunicationConfiguration] = None):
        self.config = config or CommunicationConfiguration()
        self.message_queue = MessageQueue(self.config.message_queue_size)
        self.message_router = MessageRouter()
        
        # Communication state
        self.connected = False
        self.last_heartbeat = 0.0
        self.communication_stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'responses_sent': 0,
            'errors': 0
        }
        
        # Background processing
        self.processing_active = False
        self.processing_thread = None
        
        self.logger = logging.getLogger(__name__)
    
    def start_communication(self):
        """Start communication processing"""
        
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self.connected = True
        self.last_heartbeat = time.time()
        
        self.logger.info("Started orchestration communication")
    
    def stop_communication(self):
        """Stop communication processing"""
        
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10.0)
        
        self.connected = False
        
        self.logger.info("Stopped orchestration communication")
    
    def report_integration_started(self, session_id: str, integration_context: Dict[str, Any]):
        """Report integration session started"""
        
        message = OrchestrationMessage(
            message_id=f"integration_started_{session_id}_{int(time.time())}",
            message_type=MessageType.INTEGRATION_STARTED,
            priority=MessagePriority.NORMAL,
            timestamp=time.time(),
            subject=f"Integration started: {session_id}",
            content={
                'session_id': session_id,
                'integration_context': integration_context,
                'start_timestamp': time.time()
            },
            session_id=session_id,
            channel=CommunicationChannel.COORDINATION
        )
        
        self._send_message(message)
    
    def report_progress_update(self, progress_report: IntegrationProgressReport):
        """Report integration progress update"""
        
        message = OrchestrationMessage(
            message_id=f"progress_{progress_report.session_id}_{int(time.time())}",
            message_type=MessageType.PROGRESS_UPDATE,
            priority=MessagePriority.NORMAL,
            timestamp=time.time(),
            subject=f"Progress update: {progress_report.current_phase}",
            content={
                'progress_report': asdict(progress_report)
            },
            session_id=progress_report.session_id,
            channel=CommunicationChannel.PROGRESS_REPORTS
        )
        
        self._send_message(message)
    
    def report_integration_completion(self, context: Any, results: Any):
        """Report integration completion"""
        
        session_id = getattr(context, 'session_id', 'unknown')
        
        message = OrchestrationMessage(
            message_id=f"integration_completed_{session_id}_{int(time.time())}",
            message_type=MessageType.INTEGRATION_COMPLETED,
            priority=MessagePriority.HIGH,
            timestamp=time.time(),
            subject=f"Integration completed: {session_id}",
            content={
                'session_id': session_id,
                'completion_status': 'success' if getattr(results, 'overall_success', False) else 'failed',
                'completion_timestamp': time.time(),
                'execution_duration': getattr(results, 'execution_duration', 0),
                'quality_metrics': getattr(results, 'quality_metrics', {}),
                'recommendations': getattr(results, 'recommendations', [])
            },
            session_id=session_id,
            channel=CommunicationChannel.COORDINATION,
            requires_response=True,
            response_deadline=time.time() + self.config.response_timeout_seconds
        )
        
        self._send_message(message)
    
    def escalate_conflict(self, escalation_request: ConflictEscalationRequest):
        """Escalate conflict to orchestrator"""
        
        message = OrchestrationMessage(
            message_id=f"escalation_{escalation_request.conflict_id}_{int(time.time())}",
            message_type=MessageType.ESCALATION_REQUIRED,
            priority=MessagePriority.URGENT if escalation_request.urgency_level == 'high' else MessagePriority.HIGH,
            timestamp=time.time(),
            subject=f"Conflict escalation required: {escalation_request.conflict_type}",
            content={
                'escalation_request': asdict(escalation_request)
            },
            session_id=escalation_request.session_id,
            channel=CommunicationChannel.ESCALATIONS,
            requires_response=True,
            response_deadline=time.time() + 1800  # 30 minutes for escalations
        )
        
        self._send_message(message)
    
    def notify_quality_gate_status(self, quality_gate: QualityGateNotification):
        """Notify orchestrator of quality gate status"""
        
        priority = MessagePriority.HIGH if quality_gate.gate_status == 'failed' else MessagePriority.NORMAL
        
        message = OrchestrationMessage(
            message_id=f"quality_gate_{quality_gate.session_id}_{int(time.time())}",
            message_type=MessageType.QUALITY_GATE_STATUS,
            priority=priority,
            timestamp=time.time(),
            subject=f"Quality gate {quality_gate.gate_status}: {quality_gate.gate_name}",
            content={
                'quality_gate': asdict(quality_gate)
            },
            session_id=quality_gate.session_id,
            channel=CommunicationChannel.QUALITY_GATES
        )
        
        self._send_message(message)
    
    def request_sign_off(self, sign_off_request: SignOffRequest):
        """Request integration sign-off"""
        
        message = OrchestrationMessage(
            message_id=f"sign_off_request_{sign_off_request.session_id}_{int(time.time())}",
            message_type=MessageType.SIGN_OFF_REQUEST,
            priority=MessagePriority.HIGH,
            timestamp=time.time(),
            subject=f"Sign-off request: {sign_off_request.sign_off_type}",
            content={
                'sign_off_request': asdict(sign_off_request)
            },
            session_id=sign_off_request.session_id,
            channel=CommunicationChannel.COORDINATION,
            requires_response=True,
            response_deadline=time.time() + 3600  # 1 hour for sign-off
        )
        
        self._send_message(message)
    
    def send_system_alert(self, alert_message: str, severity: str, context: Dict[str, Any] = None):
        """Send system alert to orchestrator"""
        
        context = context or {}
        
        priority_map = {
            'critical': MessagePriority.CRITICAL,
            'error': MessagePriority.URGENT,
            'warning': MessagePriority.HIGH,
            'info': MessagePriority.NORMAL
        }
        
        message = OrchestrationMessage(
            message_id=f"alert_{int(time.time())}",
            message_type=MessageType.SYSTEM_ALERT,
            priority=priority_map.get(severity, MessagePriority.NORMAL),
            timestamp=time.time(),
            subject=f"System alert: {severity}",
            content={
                'alert_message': alert_message,
                'severity': severity,
                'context': context
            },
            session_id=context.get('session_id', 'system'),
            channel=CommunicationChannel.ALERTS
        )
        
        self._send_message(message)
    
    def submit_feedback(self, feedback_content: Dict[str, Any]):
        """Submit feedback to orchestrator"""
        
        message = OrchestrationMessage(
            message_id=f"feedback_{int(time.time())}",
            message_type=MessageType.FEEDBACK_SUBMISSION,
            priority=MessagePriority.LOW,
            timestamp=time.time(),
            subject="Integration feedback submission",
            content={
                'feedback': feedback_content,
                'submission_timestamp': time.time()
            },
            session_id=feedback_content.get('session_id', 'feedback'),
            channel=CommunicationChannel.FEEDBACK
        )
        
        self._send_message(message)
    
    def get_communication_status(self) -> Dict[str, Any]:
        """Get current communication status"""
        
        return {
            'connected': self.connected,
            'last_heartbeat': self.last_heartbeat,
            'statistics': self.communication_stats.copy(),
            'queue_status': self.message_queue.get_queue_status(),
            'pending_responses': len(self.message_queue.pending_responses),
            'processing_active': self.processing_active
        }
    
    def _send_message(self, message: OrchestrationMessage):
        """Send message through communication system"""
        
        try:
            # Set sent timestamp
            message.sent_timestamp = time.time()
            
            # Add to queue for processing
            self.message_queue.enqueue_message(message)
            
            # Update statistics
            self.communication_stats['messages_sent'] += 1
            
            self.logger.debug(f"Queued message {message.message_id} for transmission")
            
        except Exception as e:
            self.logger.error(f"Error sending message {message.message_id}: {e}")
            self.communication_stats['errors'] += 1
    
    def _processing_loop(self):
        """Main message processing loop"""
        
        while self.processing_active:
            try:
                # Process outgoing messages
                message = self.message_queue.dequeue_message(timeout=1.0)
                if message:
                    self._transmit_message(message)
                
                # Check for overdue responses
                overdue_messages = self.message_queue.get_overdue_responses()
                for overdue_message in overdue_messages:
                    self.logger.warning(f"Response overdue for message {overdue_message.message_id}")
                    self._handle_overdue_response(overdue_message)
                
                # Send heartbeat periodically
                current_time = time.time()
                if current_time - self.last_heartbeat > 300:  # 5 minutes
                    self._send_heartbeat()
                    self.last_heartbeat = current_time
                
            except Exception as e:
                self.logger.error(f"Error in communication processing loop: {e}")
                time.sleep(1.0)
    
    def _transmit_message(self, message: OrchestrationMessage):
        """Transmit message to orchestrator"""
        
        try:
            # Simulate message transmission
            # In real implementation, would use HTTP, message queue, or other protocol
            
            self.logger.info(f"Transmitting message {message.message_id} to {message.recipient}")
            
            # Simulate transmission delay
            time.sleep(0.1)
            
            # Update statistics
            self.communication_stats['messages_sent'] += 1
            
            # If this is a response, handle it specially
            if message.response_message_id:
                self.message_queue.mark_response_received(message.response_message_id, message)
                self.communication_stats['responses_sent'] += 1
            
        except Exception as e:
            self.logger.error(f"Error transmitting message {message.message_id}: {e}")
            self.communication_stats['errors'] += 1
            
            # Retry logic could be implemented here
            self._retry_message_transmission(message)
    
    def _retry_message_transmission(self, message: OrchestrationMessage):
        """Retry message transmission"""
        
        # Simple retry logic - in production would be more sophisticated
        retry_count = message.content.get('retry_count', 0)
        
        if retry_count < self.config.message_retry_attempts:
            message.content['retry_count'] = retry_count + 1
            
            # Re-queue message for retry
            self.message_queue.enqueue_message(message)
            
            self.logger.info(f"Retrying message transmission: {message.message_id} (attempt {retry_count + 1})")
        else:
            self.logger.error(f"Message transmission failed after {self.config.message_retry_attempts} attempts: {message.message_id}")
    
    def _handle_overdue_response(self, message: OrchestrationMessage):
        """Handle overdue response"""
        
        self.logger.warning(f"Response overdue for message {message.message_id}")
        
        # Send alert about overdue response
        self.send_system_alert(
            f"Response overdue for message {message.message_id}",
            "warning",
            {
                'message_id': message.message_id,
                'message_type': message.message_type.value,
                'session_id': message.session_id
            }
        )
    
    def _send_heartbeat(self):
        """Send heartbeat to orchestrator"""
        
        heartbeat_message = OrchestrationMessage(
            message_id=f"heartbeat_{int(time.time())}",
            message_type=MessageType.STATUS_INQUIRY,
            priority=MessagePriority.LOW,
            timestamp=time.time(),
            subject="Integration Agent heartbeat",
            content={
                'heartbeat': True,
                'status': 'active',
                'statistics': self.communication_stats.copy()
            },
            session_id="system",
            channel=CommunicationChannel.COORDINATION
        )
        
        self._send_message(heartbeat_message)
    
    def receive_message(self, message_data: Dict[str, Any]) -> Optional[OrchestrationMessage]:
        """Receive and process incoming message"""
        
        try:
            # Convert dictionary to message object
            message = OrchestrationMessage.from_dict(message_data)
            message.received_timestamp = time.time()
            
            # Update statistics
            self.communication_stats['messages_received'] += 1
            
            # Route message to appropriate handler
            response = self.message_router.route_message(message)
            
            # Send acknowledgment if required
            if self.config.acknowledgment_required and not response:
                ack_message = OrchestrationMessage(
                    message_id=f"ack_{message.message_id}",
                    message_type=MessageType.STATUS_INQUIRY,
                    priority=MessagePriority.LOW,
                    timestamp=time.time(),
                    recipient=message.sender,
                    subject="Message acknowledged",
                    content={'acknowledged': True, 'original_message_id': message.message_id},
                    session_id=message.session_id
                )
                self._send_message(ack_message)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
            self.communication_stats['errors'] += 1
            return None