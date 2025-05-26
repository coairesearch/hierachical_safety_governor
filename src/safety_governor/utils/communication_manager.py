"""
Communication Manager for agent-to-agent communication.

This module provides a centralized communication system for multi-agent interactions,
supporting various message types, routing strategies, and integration with the
hierarchical safety governor.
"""
import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from collections import defaultdict
import json

from . import event_bus


class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    BROADCAST = "broadcast"      # Message to all agents
    PRIVATE = "private"          # Message to specific agent(s)
    GROUP = "group"             # Message to a group of agents
    SYSTEM = "system"           # System-level messages
    NEGOTIATION = "negotiation"  # Negotiation-specific messages
    OBSERVATION = "observation"  # Environment observations


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Message:
    """Represents a message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipients: List[str] = field(default_factory=list)
    message_type: MessageType = MessageType.PRIVATE
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: MessagePriority = MessagePriority.NORMAL
    requires_ack: bool = False
    reply_to: Optional[str] = None  # ID of message being replied to


@dataclass
class MessageAck:
    """Acknowledgment for a received message."""
    message_id: str
    receiver: str
    timestamp: float = field(default_factory=time.time)
    status: str = "received"  # received, processed, failed
    error: Optional[str] = None


class MessageFilter(ABC):
    """Base class for message filters."""
    
    @abstractmethod
    def should_allow(self, message: Message) -> bool:
        """Return True if message should be allowed."""
        pass


class CommunicationManager:
    """
    Manages all communication between agents with support for:
    - Message routing (broadcast, private, group)
    - Message logging and history
    - Async operations for parallel communication
    - Integration with EventBus for communication events
    - Message filtering and security
    - Rate limiting and flow control
    """
    
    def __init__(
        self,
        max_history_size: int = 10000,
        enable_logging: bool = True,
        log_level: str = "INFO",
        rate_limit_window: int = 60,  # seconds
        rate_limit_max_messages: int = 100,
        enable_encryption: bool = False,
        enable_event_bus: bool = True
    ):
        """
        Initialize the CommunicationManager.
        
        Args:
            max_history_size: Maximum number of messages to keep in history
            enable_logging: Whether to log all communications
            log_level: Logging level for the communication logger
            rate_limit_window: Time window for rate limiting (seconds)
            rate_limit_max_messages: Max messages per agent in rate limit window
            enable_encryption: Whether to encrypt message contents
            enable_event_bus: Whether to publish events to the event bus
        """
        self.max_history_size = max_history_size
        self.enable_logging = enable_logging
        self.rate_limit_window = rate_limit_window
        self.rate_limit_max_messages = rate_limit_max_messages
        self.enable_encryption = enable_encryption
        self.enable_event_bus = enable_event_bus
        
        # Message storage
        self._message_history: List[Message] = []
        self._acknowledgments: Dict[str, List[MessageAck]] = defaultdict(list)
        
        # Agent registry
        self._agents: Dict[str, Any] = {}  # agent_id -> agent instance
        self._agent_groups: Dict[str, Set[str]] = defaultdict(set)  # group_name -> agent_ids
        self._agent_callbacks: Dict[str, Callable] = {}  # agent_id -> message callback
        
        # Message queues for async processing
        self._message_queues: Dict[str, asyncio.Queue] = {}  # agent_id -> queue
        self._pending_acks: Dict[str, asyncio.Event] = {}  # message_id -> event
        
        # Rate limiting
        self._rate_limit_counters: Dict[str, List[float]] = defaultdict(list)
        
        # Filters and middleware
        self._filters: List[MessageFilter] = []
        self._middleware: List[Callable] = []
        
        # Statistics
        self._stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_filtered': 0,
            'messages_failed': 0,
            'broadcast_count': 0,
            'private_count': 0,
            'group_count': 0
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.CommunicationManager")
        self.logger.setLevel(getattr(logging, log_level))
        
        # Running flag for async operations
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def register_agent(
        self, 
        agent_id: str, 
        agent_instance: Any,
        message_callback: Optional[Callable] = None,
        groups: Optional[List[str]] = None
    ) -> None:
        """
        Register an agent with the communication manager.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_instance: The agent instance
            message_callback: Callback function for incoming messages
            groups: List of groups this agent belongs to
        """
        self._agents[agent_id] = agent_instance
        
        if message_callback:
            self._agent_callbacks[agent_id] = message_callback
        
        if groups:
            for group in groups:
                self._agent_groups[group].add(agent_id)
                
        # Create message queue for async processing
        self._message_queues[agent_id] = asyncio.Queue()
        
        self.logger.info(f"Registered agent '{agent_id}' with groups: {groups}")
        
        # Publish event
        if self.enable_event_bus:
            event_bus.publish("agent_registered", {
            "agent_id": agent_id,
            "groups": groups,
            "timestamp": time.time()
        })

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the communication manager."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            
        if agent_id in self._agent_callbacks:
            del self._agent_callbacks[agent_id]
            
        if agent_id in self._message_queues:
            del self._message_queues[agent_id]
            
        # Remove from all groups
        for group_agents in self._agent_groups.values():
            group_agents.discard(agent_id)
            
        self.logger.info(f"Unregistered agent '{agent_id}'")
        
        # Publish event
        if self.enable_event_bus:
            event_bus.publish("agent_unregistered", {
            "agent_id": agent_id,
            "timestamp": time.time()
        })

    def add_filter(self, filter: MessageFilter) -> None:
        """Add a message filter."""
        self._filters.append(filter)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware for message processing."""
        self._middleware.append(middleware)

    async def send_message(
        self,
        sender: str,
        recipients: Union[str, List[str]],
        content: Any,
        message_type: MessageType = MessageType.PRIVATE,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        requires_ack: bool = False,
        reply_to: Optional[str] = None
    ) -> Message:
        """
        Send a message from one agent to others.
        
        Args:
            sender: ID of the sending agent
            recipients: Single recipient ID or list of recipient IDs
            content: Message content (any serializable object)
            message_type: Type of message
            priority: Message priority
            metadata: Additional metadata
            requires_ack: Whether acknowledgment is required
            reply_to: ID of message being replied to
            
        Returns:
            The sent Message object
        """
        # Normalize recipients to list
        if isinstance(recipients, str):
            recipients = [recipients]
            
        # Create message
        message = Message(
            sender=sender,
            recipients=recipients,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            priority=priority,
            requires_ack=requires_ack,
            reply_to=reply_to
        )
        
        # Check rate limiting
        if not self._check_rate_limit(sender):
            self.logger.warning(f"Rate limit exceeded for agent '{sender}'")
            self._stats['messages_failed'] += 1
            raise Exception(f"Rate limit exceeded for agent '{sender}'")
        
        # Apply filters
        for filter in self._filters:
            if not filter.should_allow(message):
                self.logger.info(f"Message {message.id} filtered by {filter.__class__.__name__}")
                self._stats['messages_filtered'] += 1
                return message
                
        # Apply middleware
        for middleware in self._middleware:
            message = await middleware(message)
            
        # Log message
        if self.enable_logging:
            self._log_message(message)
            
        # Store in history
        self._add_to_history(message)
        
        # Update statistics
        self._stats['messages_sent'] += 1
        self._stats[f'{message_type.value}_count'] += 1
        
        # Route message based on type
        if message_type == MessageType.BROADCAST:
            await self._broadcast_message(message)
        elif message_type == MessageType.GROUP:
            await self._group_message(message)
        else:
            await self._route_message(message)
            
        # Publish event
        if self.enable_event_bus:
            event_bus.publish("message_sent", {
            "message_id": message.id,
            "sender": sender,
            "recipients": recipients,
            "message_type": message_type.value,
            "timestamp": message.timestamp
        })
            
        return message

    async def broadcast(
        self,
        sender: str,
        content: Any,
        exclude: Optional[List[str]] = None,
        **kwargs
    ) -> Message:
        """
        Broadcast a message to all registered agents.
        
        Args:
            sender: ID of the sending agent
            content: Message content
            exclude: List of agent IDs to exclude from broadcast
            **kwargs: Additional arguments passed to send_message
        """
        all_agents = set(self._agents.keys())
        if exclude:
            all_agents -= set(exclude)
        all_agents.discard(sender)  # Don't send to self
        
        return await self.send_message(
            sender=sender,
            recipients=list(all_agents),
            content=content,
            message_type=MessageType.BROADCAST,
            **kwargs
        )

    async def send_to_group(
        self,
        sender: str,
        group_name: str,
        content: Any,
        **kwargs
    ) -> Message:
        """
        Send a message to all agents in a specific group.
        
        Args:
            sender: ID of the sending agent
            group_name: Name of the target group
            content: Message content
            **kwargs: Additional arguments passed to send_message
        """
        group_agents = list(self._agent_groups.get(group_name, set()))
        
        return await self.send_message(
            sender=sender,
            recipients=group_agents,
            content=content,
            message_type=MessageType.GROUP,
            metadata={"group": group_name},
            **kwargs
        )

    async def _route_message(self, message: Message) -> None:
        """Route a message to its recipients."""
        tasks = []
        for recipient in message.recipients:
            if recipient in self._message_queues:
                task = asyncio.create_task(
                    self._deliver_to_agent(message, recipient)
                )
                tasks.append(task)
            else:
                self.logger.warning(f"Recipient '{recipient}' not found")
                
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _broadcast_message(self, message: Message) -> None:
        """Handle broadcast messages."""
        await self._route_message(message)

    async def _group_message(self, message: Message) -> None:
        """Handle group messages."""
        await self._route_message(message)

    async def _deliver_to_agent(self, message: Message, agent_id: str) -> None:
        """Deliver a message to a specific agent."""
        try:
            # Add to agent's queue
            await self._message_queues[agent_id].put(message)
            
            # Call callback if registered
            if agent_id in self._agent_callbacks:
                callback = self._agent_callbacks[agent_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, callback, message
                    )
                    
            self._stats['messages_delivered'] += 1
            
            # Send acknowledgment if required
            if message.requires_ack:
                ack = MessageAck(
                    message_id=message.id,
                    receiver=agent_id,
                    status="received"
                )
                self._acknowledgments[message.id].append(ack)
                
                if message.id in self._pending_acks:
                    self._pending_acks[message.id].set()
                    
        except Exception as e:
            self.logger.error(f"Failed to deliver message to '{agent_id}': {e}")
            self._stats['messages_failed'] += 1
            
            if message.requires_ack:
                ack = MessageAck(
                    message_id=message.id,
                    receiver=agent_id,
                    status="failed",
                    error=str(e)
                )
                self._acknowledgments[message.id].append(ack)

    async def wait_for_acknowledgments(
        self,
        message_id: str,
        timeout: Optional[float] = None
    ) -> List[MessageAck]:
        """
        Wait for all acknowledgments for a message.
        
        Args:
            message_id: ID of the message to wait for
            timeout: Maximum time to wait (seconds)
            
        Returns:
            List of acknowledgments received
        """
        event = asyncio.Event()
        self._pending_acks[message_id] = event
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for acknowledgments for message {message_id}")
            
        return self._acknowledgments.get(message_id, [])

    async def get_messages_for_agent(
        self,
        agent_id: str,
        max_messages: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> List[Message]:
        """
        Get pending messages for an agent.
        
        Args:
            agent_id: ID of the agent
            max_messages: Maximum number of messages to retrieve
            timeout: Maximum time to wait for messages
            
        Returns:
            List of messages
        """
        if agent_id not in self._message_queues:
            return []
            
        messages = []
        queue = self._message_queues[agent_id]
        
        try:
            end_time = time.time() + timeout if timeout else None
            
            while True:
                if max_messages and len(messages) >= max_messages:
                    break
                    
                remaining_timeout = None
                if end_time:
                    remaining_timeout = end_time - time.time()
                    if remaining_timeout <= 0:
                        break
                        
                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=remaining_timeout
                    )
                    messages.append(message)
                except asyncio.TimeoutError:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error retrieving messages for '{agent_id}': {e}")
            
        return messages

    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        since: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get message history with optional filters.
        
        Args:
            agent_id: Filter by sender or recipient
            message_type: Filter by message type
            since: Only messages after this timestamp
            limit: Maximum number of messages to return
            
        Returns:
            Filtered list of messages
        """
        history = self._message_history
        
        # Apply filters
        if agent_id:
            history = [
                m for m in history
                if m.sender == agent_id or agent_id in m.recipients
            ]
            
        if message_type:
            history = [m for m in history if m.message_type == message_type]
            
        if since:
            history = [m for m in history if m.timestamp >= since]
            
        # Sort by timestamp (newest first)
        history = sorted(history, key=lambda m: m.timestamp, reverse=True)
        
        if limit:
            history = history[:limit]
            
        return history

    def get_statistics(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            **self._stats,
            'total_agents': len(self._agents),
            'total_groups': len(self._agent_groups),
            'history_size': len(self._message_history),
            'pending_messages': sum(
                q.qsize() for q in self._message_queues.values()
            )
        }

    def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within rate limits."""
        now = time.time()
        window_start = now - self.rate_limit_window
        
        # Clean old timestamps
        self._rate_limit_counters[agent_id] = [
            ts for ts in self._rate_limit_counters[agent_id]
            if ts > window_start
        ]
        
        # Check limit
        if len(self._rate_limit_counters[agent_id]) >= self.rate_limit_max_messages:
            return False
            
        # Add current timestamp
        self._rate_limit_counters[agent_id].append(now)
        return True

    def _add_to_history(self, message: Message) -> None:
        """Add message to history with size limit."""
        self._message_history.append(message)
        
        # Trim history if needed
        if len(self._message_history) > self.max_history_size:
            self._message_history = self._message_history[-self.max_history_size:]

    def _log_message(self, message: Message) -> None:
        """Log a message for audit purposes."""
        log_entry = {
            'id': message.id,
            'timestamp': datetime.fromtimestamp(message.timestamp).isoformat(),
            'sender': message.sender,
            'recipients': message.recipients,
            'type': message.message_type.value,
            'priority': message.priority.value,
            'content_preview': str(message.content)[:100] if message.content else None,
            'metadata': message.metadata
        }
        
        self.logger.info(f"Message: {json.dumps(log_entry)}")

    async def start(self) -> None:
        """Start the communication manager's async operations."""
        self._running = True
        self.logger.info("CommunicationManager started")
        
        # Start background tasks if needed
        # For example: message cleanup, statistics collection, etc.

    async def stop(self) -> None:
        """Stop the communication manager."""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self.logger.info("CommunicationManager stopped")

    def __repr__(self) -> str:
        return (
            f"CommunicationManager("
            f"agents={len(self._agents)}, "
            f"messages_sent={self._stats['messages_sent']}, "
            f"messages_delivered={self._stats['messages_delivered']})"
        )


# Example filters
class ContentFilter(MessageFilter):
    """Filter messages based on content."""
    
    def __init__(self, blocked_words: List[str]):
        self.blocked_words = set(w.lower() for w in blocked_words)
        
    def should_allow(self, message: Message) -> bool:
        if not message.content:
            return True
            
        content_str = str(message.content).lower()
        return not any(word in content_str for word in self.blocked_words)


class RateLimitFilter(MessageFilter):
    """Additional rate limiting filter."""
    
    def __init__(self, max_messages_per_minute: int = 60):
        self.max_messages = max_messages_per_minute
        self.message_times: Dict[str, List[float]] = defaultdict(list)
        
    def should_allow(self, message: Message) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        self.message_times[message.sender] = [
            t for t in self.message_times[message.sender]
            if t > minute_ago
        ]
        
        # Check limit
        if len(self.message_times[message.sender]) >= self.max_messages:
            return False
            
        self.message_times[message.sender].append(now)
        return True