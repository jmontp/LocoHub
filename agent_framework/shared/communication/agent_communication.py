"""
Agent Communication Infrastructure

Created: 2025-01-16 with user permission
Purpose: Inter-agent message passing and coordination system

Intent: Provides communication framework for Test Agent, Code Agent, and Integration Agent
to coordinate work without direct coupling, following the orchestrated development approach.
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import queue


class MessageType(Enum):
    """Types of messages between agents"""
    HANDOFF = "handoff"
    STATUS_UPDATE = "status_update"
    QUALITY_REPORT = "quality_report"
    ERROR_REPORT = "error_report"
    COMPLETION = "completion"
    REQUEST = "request"


class AgentRole(Enum):
    """Agent roles in the framework"""
    ORCHESTRATOR = "orchestrator"
    TEST_AGENT = "test_agent"
    CODE_AGENT = "code_agent" 
    INTEGRATION_AGENT = "integration_agent"


@dataclass
class Message:
    """Standard message format for agent communication"""
    id: str
    timestamp: float
    sender: AgentRole
    recipient: AgentRole
    message_type: MessageType
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        result = asdict(self)
        result['sender'] = self.sender.value
        result['recipient'] = self.recipient.value
        result['message_type'] = self.message_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            id=data['id'],
            timestamp=data['timestamp'],
            sender=AgentRole(data['sender']),
            recipient=AgentRole(data['recipient']),
            message_type=MessageType(data['message_type']),
            payload=data['payload'],
            correlation_id=data.get('correlation_id')
        )


class MessageBus:
    """Central message bus for agent communication"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.message_dir = workspace_path / "messages"
        self.message_dir.mkdir(exist_ok=True)
        
        # In-memory queues for real-time communication
        self._queues: Dict[AgentRole, queue.Queue] = {
            role: queue.Queue() for role in AgentRole
        }
        
        # Message persistence
        self._message_log: List[Message] = []
        self._lock = threading.Lock()
    
    def send_message(self, message: Message) -> None:
        """Send message to recipient agent"""
        with self._lock:
            # Add to in-memory queue
            self._queues[message.recipient].put(message)
            
            # Log message
            self._message_log.append(message)
            
            # Persist to disk
            self._persist_message(message)
    
    def receive_messages(self, agent_role: AgentRole, timeout: Optional[float] = None) -> List[Message]:
        """Receive all pending messages for an agent"""
        messages = []
        
        try:
            while True:
                message = self._queues[agent_role].get(timeout=timeout)
                messages.append(message)
                timeout = 0.1  # Quick check for additional messages
        except queue.Empty:
            pass
        
        return messages
    
    def _persist_message(self, message: Message) -> None:
        """Persist message to disk for audit trail"""
        message_file = self.message_dir / f"{message.id}.json"
        with open(message_file, 'w') as f:
            json.dump(message.to_dict(), f, indent=2)
    
    def get_message_history(self, 
                           sender: Optional[AgentRole] = None,
                           recipient: Optional[AgentRole] = None,
                           message_type: Optional[MessageType] = None) -> List[Message]:
        """Get filtered message history"""
        filtered = self._message_log
        
        if sender:
            filtered = [m for m in filtered if m.sender == sender]
        if recipient:
            filtered = [m for m in filtered if m.recipient == recipient]
        if message_type:
            filtered = [m for m in filtered if m.message_type == message_type]
            
        return filtered


class AgentCommunicator:
    """Communication interface for individual agents"""
    
    def __init__(self, agent_role: AgentRole, message_bus: MessageBus):
        self.agent_role = agent_role
        self.message_bus = message_bus
    
    def send_handoff(self, recipient: AgentRole, handoff_data: Dict[str, Any], 
                     correlation_id: Optional[str] = None) -> str:
        """Send handoff package to another agent"""
        message = Message(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=self.agent_role,
            recipient=recipient,
            message_type=MessageType.HANDOFF,
            payload=handoff_data,
            correlation_id=correlation_id
        )
        
        self.message_bus.send_message(message)
        return message.id
    
    def send_status_update(self, status: Dict[str, Any], 
                          correlation_id: Optional[str] = None) -> str:
        """Send status update to orchestrator"""
        message = Message(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=self.agent_role,
            recipient=AgentRole.ORCHESTRATOR,
            message_type=MessageType.STATUS_UPDATE,
            payload=status,
            correlation_id=correlation_id
        )
        
        self.message_bus.send_message(message)
        return message.id
    
    def send_completion(self, completion_data: Dict[str, Any],
                       correlation_id: Optional[str] = None) -> str:
        """Send completion notification"""
        message = Message(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=self.agent_role,
            recipient=AgentRole.ORCHESTRATOR,
            message_type=MessageType.COMPLETION,
            payload=completion_data,
            correlation_id=correlation_id
        )
        
        self.message_bus.send_message(message)
        return message.id
    
    def send_error_report(self, error_data: Dict[str, Any],
                         correlation_id: Optional[str] = None) -> str:
        """Send error report to orchestrator"""
        message = Message(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=self.agent_role,
            recipient=AgentRole.ORCHESTRATOR,
            message_type=MessageType.ERROR_REPORT,
            payload=error_data,
            correlation_id=correlation_id
        )
        
        self.message_bus.send_message(message)
        return message.id
    
    def receive_messages(self, timeout: Optional[float] = None) -> List[Message]:
        """Receive pending messages for this agent"""
        return self.message_bus.receive_messages(self.agent_role, timeout)
    
    def wait_for_handoff(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Wait for handoff message"""
        messages = self.receive_messages(timeout)
        for message in messages:
            if message.message_type == MessageType.HANDOFF:
                return message
        return None


def create_communication_infrastructure(workspace_path: Path) -> MessageBus:
    """Initialize communication infrastructure"""
    return MessageBus(workspace_path)


def create_agent_communicator(agent_role: AgentRole, workspace_path: Path) -> AgentCommunicator:
    """Create communicator for specific agent"""
    message_bus = MessageBus(workspace_path)
    return AgentCommunicator(agent_role, message_bus)