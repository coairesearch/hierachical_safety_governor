"""
Communicating Agent Adapter that extends AutoGenAgentAdapter with communication capabilities.

This adapter adds inter-agent communication support to the base AutoGen adapter,
enabling agents to send and receive messages during communication phases.
"""
import asyncio
import json
import random
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .autogen_agent_adapter import AutoGenAgentAdapter
from ..utils import CommunicationManager, Message, MessageType, MessagePriority


@dataclass
class CommunicationStrategy:
    """Configuration for an agent's communication strategy."""
    strategy_type: str = "honest"  # honest, deceptive, strategic, silent
    broadcast_probability: float = 0.3
    private_message_probability: float = 0.5
    deception_rate: float = 0.0  # Probability of sending false information
    cooperation_threshold: float = 0.7  # Threshold for proposing cooperation
    message_templates: Optional[Dict[str, str]] = None


class CommunicatingAgentAdapter(AutoGenAgentAdapter):
    """
    Agent adapter with communication capabilities.
    
    Extends the base AutoGenAgentAdapter to support:
    - Sending and receiving messages through CommunicationManager
    - Different communication strategies (honest, deceptive, strategic)
    - Message handling and context management
    - Communication-aware decision making
    """
    
    def __init__(
        self,
        *args,
        communication_strategy: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Initialize the communicating agent adapter.
        
        Args:
            *args: Arguments passed to AutoGenAgentAdapter
            communication_strategy: Communication strategy configuration
            **kwargs: Keyword arguments passed to AutoGenAgentAdapter
        """
        super().__init__(*args, **kwargs)
        
        # Initialize communication attributes
        self._comm_manager: Optional[CommunicationManager] = None
        self._agent_id: Optional[str] = None
        self._received_messages: List[Message] = []
        self._sent_messages: List[Message] = []
        
        # Parse communication strategy
        if isinstance(communication_strategy, str):
            self.comm_strategy = CommunicationStrategy(strategy_type=communication_strategy)
        elif isinstance(communication_strategy, dict):
            self.comm_strategy = CommunicationStrategy(**communication_strategy)
        else:
            self.comm_strategy = CommunicationStrategy()
            
        print(f"AGENT [{self.name}] - Initialized with communication strategy: {self.comm_strategy.strategy_type}")

    async def handle_message(self, message: Message) -> None:
        """
        Handle an incoming message.
        
        Args:
            message: The message received
        """
        self._received_messages.append(message)
        
        # Log message receipt
        print(f"AGENT [{self.name}] - Received message from {message.sender}: {message.content}")
        
        # Process message based on type
        if message.message_type == MessageType.NEGOTIATION:
            await self._handle_negotiation_message(message)
        elif message.message_type == MessageType.BROADCAST:
            await self._handle_broadcast_message(message)
        else:
            await self._handle_private_message(message)

    async def communicate(
        self,
        environment_state: Dict[str, Any],
        round_num: int,
        comm_round: int
    ) -> None:
        """
        Participate in a communication round.
        
        Args:
            environment_state: Current state of the environment
            round_num: Current game round
            comm_round: Current communication round within this game round
        """
        if not self._comm_manager or not self._agent_id:
            return
            
        # Decide whether to communicate based on strategy
        if self.comm_strategy.strategy_type == "silent":
            return
            
        # Get recent messages for context
        recent_messages = self._received_messages[-5:] if self._received_messages else []
        
        # Decide on communication action
        import random
        
        # Broadcast decision
        if random.random() < self.comm_strategy.broadcast_probability:
            await self._send_broadcast(environment_state, round_num)
            
        # Private message decision
        if random.random() < self.comm_strategy.private_message_probability:
            await self._send_private_messages(environment_state, round_num, recent_messages)

    async def _send_broadcast(
        self,
        environment_state: Dict[str, Any],
        round_num: int
    ) -> None:
        """Send a broadcast message to all agents."""
        observation = environment_state.get('observation', {})
        
        # Create message content based on strategy
        if self.comm_strategy.strategy_type == "honest":
            content = {
                "type": "status_update",
                "round": round_num,
                "my_last_action": observation.get(f'agent_{self.agent_index}_last_price', None),
                "strategy": "cooperative"
            }
        elif self.comm_strategy.strategy_type == "deceptive":
            # Send misleading information
            actual_action = observation.get(f'agent_{self.agent_index}_last_price', 5)
            fake_action = 9 - actual_action if actual_action < 5 else 0
            content = {
                "type": "status_update",
                "round": round_num,
                "my_last_action": fake_action,
                "strategy": "competitive"
            }
        else:  # strategic
            content = {
                "type": "proposal",
                "round": round_num,
                "message": "Suggest we maintain moderate prices for mutual benefit"
            }
            
        try:
            message = await self._comm_manager.broadcast(
                sender=self._agent_id,
                content=content,
                metadata={"round": round_num, "strategy": self.comm_strategy.strategy_type}
            )
            self._sent_messages.append(message)
            print(f"AGENT [{self.name}] - Sent broadcast: {content}")
        except Exception as e:
            print(f"AGENT [{self.name}] - Failed to send broadcast: {e}")

    async def _send_private_messages(
        self,
        environment_state: Dict[str, Any],
        round_num: int,
        recent_messages: List[Message]
    ) -> None:
        """Send private messages to specific agents."""
        # Identify potential recipients based on recent interactions
        recipients = set()
        for msg in recent_messages:
            if msg.sender != self._agent_id:
                recipients.add(msg.sender)
                
        if not recipients:
            # No one to send private messages to
            return
            
        observation = environment_state.get('observation', {})
        
        for recipient in recipients:
            # Decide on message content
            if self.comm_strategy.strategy_type == "honest":
                content = {
                    "type": "cooperation_proposal",
                    "round": round_num,
                    "proposal": "Let's both choose medium prices",
                    "my_intended_action": 5
                }
            elif self.comm_strategy.strategy_type == "deceptive":
                # Try to mislead
                content = {
                    "type": "cooperation_proposal",
                    "round": round_num,
                    "proposal": "I'll choose high price if you do",
                    "my_intended_action": 9  # But actually planning to choose low
                }
            else:  # strategic
                # Analyze recipient's behavior
                content = {
                    "type": "conditional_cooperation",
                    "round": round_num,
                    "proposal": "I'll match your price level",
                    "condition": "mutual_cooperation"
                }
                
            try:
                message = await self._comm_manager.send_message(
                    sender=self._agent_id,
                    recipients=recipient,
                    content=content,
                    message_type=MessageType.NEGOTIATION,
                    metadata={"round": round_num, "private": True}
                )
                self._sent_messages.append(message)
                print(f"AGENT [{self.name}] - Sent private message to {recipient}: {content}")
            except Exception as e:
                print(f"AGENT [{self.name}] - Failed to send private message: {e}")

    async def _handle_negotiation_message(self, message: Message) -> None:
        """Handle negotiation messages from other agents."""
        content = message.content
        
        # Store negotiation proposals for decision-making
        if not hasattr(self, '_negotiation_proposals'):
            self._negotiation_proposals = []
            
        self._negotiation_proposals.append({
            "sender": message.sender,
            "content": content,
            "timestamp": message.timestamp
        })
        
        # Optionally send a response
        if content.get("type") == "cooperation_proposal":
            # Decide whether to accept based on strategy
            if self.comm_strategy.strategy_type == "honest":
                accept = random.random() < self.comm_strategy.cooperation_threshold
            elif self.comm_strategy.strategy_type == "deceptive":
                accept = True  # Accept but may not follow through
            else:
                # Strategic: analyze if cooperation is beneficial
                accept = self._analyze_cooperation_benefit(content)
                
            if accept and self._comm_manager:
                try:
                    await self._comm_manager.send_message(
                        sender=self._agent_id,
                        recipients=message.sender,
                        content={
                            "type": "cooperation_response",
                            "accept": accept,
                            "proposal_id": message.id
                        },
                        message_type=MessageType.NEGOTIATION,
                        reply_to=message.id
                    )
                except Exception as e:
                    print(f"AGENT [{self.name}] - Failed to send response: {e}")

    async def _handle_broadcast_message(self, message: Message) -> None:
        """Handle broadcast messages."""
        # Store broadcast information for context
        if not hasattr(self, '_broadcast_context'):
            self._broadcast_context = []
            
        self._broadcast_context.append({
            "sender": message.sender,
            "content": message.content,
            "timestamp": message.timestamp
        })

    async def _handle_private_message(self, message: Message) -> None:
        """Handle private messages."""
        # Store private message information
        if not hasattr(self, '_private_messages'):
            self._private_messages = []
            
        self._private_messages.append({
            "sender": message.sender,
            "content": message.content,
            "timestamp": message.timestamp
        })

    def _analyze_cooperation_benefit(self, proposal: Dict[str, Any]) -> bool:
        """
        Analyze whether accepting a cooperation proposal is beneficial.
        
        Args:
            proposal: The cooperation proposal
            
        Returns:
            True if cooperation seems beneficial
        """
        # Simple analysis - can be made more sophisticated
        import random
        
        # Consider factors like:
        # - Past interactions with this agent
        # - Current game state
        # - Potential payoff from cooperation
        
        # For now, use a probabilistic approach
        return random.random() < self.comm_strategy.cooperation_threshold

    async def act_async(
        self,
        observation: Dict[str, Any],
        info: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make a decision considering communication context.
        
        Args:
            observation: Current game observation
            info: Additional information
            
        Returns:
            The chosen action
        """
        # First get the base action from parent class
        base_action = await super().act_async(observation, info)
        
        # If no communication context, return base action
        if not self._received_messages:
            return base_action
            
        # Consider communication context in decision
        if hasattr(self, '_negotiation_proposals') and self._negotiation_proposals:
            # Check recent cooperation proposals
            recent_proposals = [
                p for p in self._negotiation_proposals
                if observation.get('round_num', 0) - p.get('round', 0) <= 2
            ]
            
            if recent_proposals:
                # If we have active cooperation agreements, consider them
                if self.comm_strategy.strategy_type == "honest":
                    # Honor agreements
                    for proposal in recent_proposals:
                        if proposal['content'].get('my_intended_action') is not None:
                            return proposal['content']['my_intended_action']
                elif self.comm_strategy.strategy_type == "deceptive":
                    # Might defect
                    import random
                    if random.random() < self.comm_strategy.deception_rate:
                        # Defect by choosing opposite action
                        agreed_action = recent_proposals[0]['content'].get('my_intended_action', 5)
                        return 0 if agreed_action > 5 else 9
                        
        return base_action

    def get_communication_summary(self) -> Dict[str, Any]:
        """Get a summary of communication activity."""
        return {
            "messages_sent": len(self._sent_messages),
            "messages_received": len(self._received_messages),
            "strategy": self.comm_strategy.strategy_type,
            "recent_messages": [
                {
                    "type": msg.message_type.value,
                    "sender": msg.sender,
                    "timestamp": msg.timestamp
                }
                for msg in self._received_messages[-10:]
            ]
        }