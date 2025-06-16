"""
Message Transport Layer

Created: 2025-06-16 with user permission
Purpose: Reliable message transport between agents

Intent: Implements the message transport layer from the communication architecture
providing synchronous, asynchronous, and priority queue transport with delivery guarantees.
"""

import json
import uuid
import asyncio
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging


class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MessageStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TransportProtocol(Enum):
    """Available transport protocols"""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    RELIABLE_ASYNC = "reliable_async"
    PRIORITY_QUEUE = "priority_queue"


@dataclass
class AgentMessage:
    """Structured message for inter-agent communication"""
    message_id: str
    sender: str
    recipient: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.correlation_id:
            self.correlation_id = self.message_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['priority'] = self.priority.value
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['priority'] = MessagePriority(data['priority'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class TransportRequirements:
    """Requirements for message transport"""
    delivery_guarantee: str = "at_least_once"  # at_least_once, at_most_once, exactly_once
    timeout: timedelta = timedelta(minutes=5)
    retry_count: int = 3
    acknowledgment_required: bool = True
    ordered_delivery: bool = False


@dataclass
class MessageDeliveryResult:
    """Result of message delivery attempt"""
    message_id: str
    status: MessageStatus
    timestamp: datetime
    transport_protocol: str
    delivery_confirmation: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class MessageSerializer:
    """Serializer for agent messages"""
    
    def serialize(self, message: AgentMessage) -> str:
        """Serialize message to JSON string"""
        try:
            return json.dumps(message.to_dict(), indent=2)
        except Exception as e:
            raise ValueError(f"Failed to serialize message {message.message_id}: {e}")
    
    def deserialize(self, data: str) -> AgentMessage:
        """Deserialize message from JSON string"""
        try:
            message_dict = json.loads(data)
            return AgentMessage.from_dict(message_dict)
        except Exception as e:
            raise ValueError(f"Failed to deserialize message: {e}")


class DeliveryGuaranteeManager:
    """Manager for message delivery guarantees"""
    
    def __init__(self):
        self.delivery_log: Dict[str, MessageDeliveryResult] = {}
        self.pending_acknowledgments: Dict[str, datetime] = {}
    
    def apply_guarantees(self, message: AgentMessage, guarantee: str) -> AgentMessage:
        """Apply delivery guarantees to message"""
        if guarantee == "exactly_once":
            # Add deduplication ID
            if not hasattr(message, 'deduplication_id'):
                message.deduplication_id = str(uuid.uuid4())
        
        elif guarantee == "at_least_once":
            # Ensure acknowledgment required
            message.acknowledgment_required = True
        
        return message
    
    def track_delivery(self, message_id: str, result: MessageDeliveryResult):
        """Track message delivery result"""
        self.delivery_log[message_id] = result
        
        if result.status == MessageStatus.DELIVERED:
            # Remove from pending acknowledgments
            self.pending_acknowledgments.pop(message_id, None)
    
    def requires_retry(self, message_id: str, max_retries: int) -> bool:
        """Check if message requires retry"""
        result = self.delivery_log.get(message_id)
        if not result:
            return True
        
        return (result.status == MessageStatus.FAILED and 
                result.retry_count < max_retries)


class SynchronousTransport:
    """Synchronous message transport protocol"""
    
    def __init__(self, workspace_path: Path):
        self.name = "synchronous"
        self.workspace_path = workspace_path
        self.delivery_guarantee = DeliveryGuaranteeManager()
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def send(self, message: AgentMessage, requirements: TransportRequirements) -> MessageDeliveryResult:
        """Send message synchronously"""
        try:
            # Create recipient inbox
            recipient_inbox = self.workspace_path / message.recipient / "inbox"
            recipient_inbox.mkdir(parents=True, exist_ok=True)
            
            # Write message to recipient inbox
            message_file = recipient_inbox / f"{message.message_id}.json"
            serializer = MessageSerializer()
            
            with open(message_file, 'w') as f:
                f.write(serializer.serialize(message))
            
            # Create delivery result
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.DELIVERED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                delivery_confirmation=str(message_file)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)
            return result
            
        except Exception as e:
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.FAILED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                error_message=str(e)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)
            return result


class AsynchronousTransport:
    """Asynchronous message transport protocol"""
    
    def __init__(self, workspace_path: Path):
        self.name = "asynchronous"
        self.workspace_path = workspace_path
        self.delivery_guarantee = DeliveryGuaranteeManager()
        self.message_queue = asyncio.Queue()
        self._running = False
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        """Start async message processing"""
        self._running = True
        await self._process_messages()
    
    def stop(self):
        """Stop async message processing"""
        self._running = False
    
    async def send_async(self, message: AgentMessage, requirements: TransportRequirements) -> MessageDeliveryResult:
        """Send message asynchronously"""
        await self.message_queue.put((message, requirements))
        
        # Return pending result immediately
        return MessageDeliveryResult(
            message_id=message.message_id,
            status=MessageStatus.PENDING,
            timestamp=datetime.utcnow(),
            transport_protocol=self.name
        )
    
    async def _process_messages(self):
        """Process messages asynchronously"""
        while self._running:
            try:
                # Get message from queue with timeout
                message, requirements = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )
                
                # Process message
                await self._deliver_message(message, requirements)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"Error processing async message: {e}")
    
    async def _deliver_message(self, message: AgentMessage, requirements: TransportRequirements):
        """Deliver message asynchronously"""
        try:
            # Create recipient inbox
            recipient_inbox = self.workspace_path / message.recipient / "inbox"
            recipient_inbox.mkdir(parents=True, exist_ok=True)
            
            # Write message to recipient inbox
            message_file = recipient_inbox / f"{message.message_id}.json"
            serializer = MessageSerializer()
            
            with open(message_file, 'w') as f:
                f.write(serializer.serialize(message))
            
            # Update delivery result
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.DELIVERED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                delivery_confirmation=str(message_file)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)
            
        except Exception as e:
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.FAILED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                error_message=str(e)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)


class PriorityQueueTransport:
    """Priority queue message transport protocol"""
    
    def __init__(self, workspace_path: Path):
        self.name = "priority_queue"
        self.workspace_path = workspace_path
        self.delivery_guarantee = DeliveryGuaranteeManager()
        self.priority_queues = {
            MessagePriority.CRITICAL: [],
            MessagePriority.HIGH: [],
            MessagePriority.NORMAL: [],
            MessagePriority.LOW: []
        }
        self._lock = threading.Lock()
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def send(self, message: AgentMessage, requirements: TransportRequirements) -> MessageDeliveryResult:
        """Send message with priority queuing"""
        try:
            with self._lock:
                # Add to appropriate priority queue
                self.priority_queues[message.priority].append((message, requirements))
            
            # Process highest priority messages first
            self._process_priority_queue()
            
            return MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.DELIVERED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name
            )
            
        except Exception as e:
            return MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.FAILED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                error_message=str(e)
            )
    
    def _process_priority_queue(self):
        """Process messages in priority order"""
        priority_order = [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW
        ]
        
        with self._lock:
            for priority in priority_order:
                while self.priority_queues[priority]:
                    message, requirements = self.priority_queues[priority].pop(0)
                    self._deliver_message_sync(message, requirements)
    
    def _deliver_message_sync(self, message: AgentMessage, requirements: TransportRequirements):
        """Deliver message synchronously from priority queue"""
        try:
            # Create recipient inbox
            recipient_inbox = self.workspace_path / message.recipient / "inbox"
            recipient_inbox.mkdir(parents=True, exist_ok=True)
            
            # Write message to recipient inbox
            message_file = recipient_inbox / f"{message.message_id}.json"
            serializer = MessageSerializer()
            
            with open(message_file, 'w') as f:
                f.write(serializer.serialize(message))
            
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.DELIVERED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                delivery_confirmation=str(message_file)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)
            
        except Exception as e:
            result = MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.FAILED,
                timestamp=datetime.utcnow(),
                transport_protocol=self.name,
                error_message=str(e)
            )
            
            self.delivery_guarantee.track_delivery(message.message_id, result)


class MessageTransportLayer:
    """Multi-protocol message transport layer"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.transport_protocols = {
            TransportProtocol.SYNCHRONOUS: SynchronousTransport(workspace_path),
            TransportProtocol.ASYNCHRONOUS: AsynchronousTransport(workspace_path),
            TransportProtocol.PRIORITY_QUEUE: PriorityQueueTransport(workspace_path)
        }
        self.message_serializer = MessageSerializer()
        self.delivery_guarantees = DeliveryGuaranteeManager()
    
    def send_message(self, message: AgentMessage, transport_requirements: TransportRequirements) -> MessageDeliveryResult:
        """Send message with specified transport requirements"""
        
        # Select appropriate transport protocol
        transport_protocol = self._select_transport_protocol(transport_requirements)
        
        # Apply delivery guarantees
        guaranteed_message = self.delivery_guarantees.apply_guarantees(
            message, transport_requirements.delivery_guarantee
        )
        
        # Send message
        if transport_protocol == TransportProtocol.ASYNCHRONOUS:
            # Handle async transport differently
            asyncio.create_task(
                self.transport_protocols[transport_protocol].send_async(
                    guaranteed_message, transport_requirements
                )
            )
            return MessageDeliveryResult(
                message_id=message.message_id,
                status=MessageStatus.PENDING,
                timestamp=datetime.utcnow(),
                transport_protocol=transport_protocol.value
            )
        else:
            # Synchronous and priority queue transports
            return self.transport_protocols[transport_protocol].send(
                guaranteed_message, transport_requirements
            )
    
    def _select_transport_protocol(self, requirements: TransportRequirements) -> TransportProtocol:
        """Select appropriate transport protocol based on requirements"""
        
        # Priority-based selection
        if requirements.ordered_delivery:
            return TransportProtocol.PRIORITY_QUEUE
        
        if requirements.delivery_guarantee == "exactly_once":
            return TransportProtocol.SYNCHRONOUS
        
        if requirements.timeout < timedelta(seconds=30):
            return TransportProtocol.SYNCHRONOUS
        
        return TransportProtocol.ASYNCHRONOUS


class MessageRouter:
    """Router for directing messages to appropriate recipients"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.transport_layer = MessageTransportLayer(workspace_path)
        self.routing_table: Dict[str, List[str]] = {}
        self.message_filters: List[callable] = []
    
    def register_agent(self, agent_name: str, message_types: List[str]):
        """Register agent for specific message types"""
        for message_type in message_types:
            if message_type not in self.routing_table:
                self.routing_table[message_type] = []
            
            if agent_name not in self.routing_table[message_type]:
                self.routing_table[message_type].append(agent_name)
    
    def add_message_filter(self, filter_func: callable):
        """Add message filter function"""
        self.message_filters.append(filter_func)
    
    def route_message(self, message: AgentMessage, transport_requirements: TransportRequirements = None) -> List[MessageDeliveryResult]:
        """Route message to appropriate recipients"""
        
        if transport_requirements is None:
            transport_requirements = TransportRequirements()
        
        # Apply message filters
        for filter_func in self.message_filters:
            if not filter_func(message):
                return []
        
        # Determine recipients
        recipients = self._determine_recipients(message)
        
        # Send to each recipient
        delivery_results = []
        for recipient in recipients:
            # Create recipient-specific message
            recipient_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender=message.sender,
                recipient=recipient,
                message_type=message.message_type,
                content=message.content,
                timestamp=message.timestamp,
                priority=message.priority,
                correlation_id=message.correlation_id
            )
            
            # Send message
            result = self.transport_layer.send_message(recipient_message, transport_requirements)
            delivery_results.append(result)
        
        return delivery_results
    
    def _determine_recipients(self, message: AgentMessage) -> List[str]:
        """Determine message recipients based on routing table"""
        
        # If explicit recipient specified, use it
        if message.recipient and message.recipient != "broadcast":
            return [message.recipient]
        
        # Otherwise, use routing table
        recipients = self.routing_table.get(message.message_type, [])
        
        # Exclude sender from recipients
        return [r for r in recipients if r != message.sender]
    
    def get_messages(self, agent_name: str) -> List[AgentMessage]:
        """Get messages for specific agent"""
        agent_inbox = self.workspace_path / agent_name / "inbox"
        
        if not agent_inbox.exists():
            return []
        
        messages = []
        serializer = MessageSerializer()
        
        for message_file in agent_inbox.glob("*.json"):
            try:
                with open(message_file, 'r') as f:
                    message = serializer.deserialize(f.read())
                    
                # Check if message is expired
                if not message.is_expired():
                    messages.append(message)
                else:
                    # Remove expired message
                    message_file.unlink()
                    
            except Exception as e:
                logging.error(f"Error reading message {message_file}: {e}")
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)
        return messages
    
    def acknowledge_message(self, agent_name: str, message_id: str):
        """Acknowledge message receipt"""
        agent_inbox = self.workspace_path / agent_name / "inbox"
        message_file = agent_inbox / f"{message_id}.json"
        
        if message_file.exists():
            # Move to processed folder
            processed_folder = agent_inbox / "processed"
            processed_folder.mkdir(exist_ok=True)
            
            processed_file = processed_folder / f"{message_id}.json"
            message_file.rename(processed_file)