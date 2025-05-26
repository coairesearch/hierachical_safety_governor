"""Tests for parallel agent communication functionality."""
import os
import sys
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety_governor.utils import (
    CommunicationManager, 
    Message, 
    MessageType, 
    MessagePriority,
    ContentFilter,
    RateLimitFilter
)
from safety_governor.core import ParallelOrchestrator
from safety_governor.adapters import CommunicatingAgentAdapter, CommunicationStrategy


class TestCommunicationManager:
    """Test suite for CommunicationManager."""
    
    @pytest.fixture
    def comm_manager(self):
        """Create a CommunicationManager instance for testing."""
        return CommunicationManager(
            max_history_size=100,
            enable_logging=False,
            rate_limit_window=60,
            rate_limit_max_messages=10
        )
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, comm_manager):
        """Test agent registration and unregistration."""
        # Register agent
        callback = AsyncMock()
        comm_manager.register_agent(
            agent_id="agent1",
            agent_instance=Mock(),
            message_callback=callback,
            groups=["group1", "group2"]
        )
        
        assert "agent1" in comm_manager._agents
        assert "agent1" in comm_manager._agent_groups["group1"]
        assert "agent1" in comm_manager._agent_groups["group2"]
        
        # Unregister agent
        comm_manager.unregister_agent("agent1")
        assert "agent1" not in comm_manager._agents
        assert "agent1" not in comm_manager._agent_groups["group1"]
    
    @pytest.mark.asyncio
    async def test_send_private_message(self, comm_manager):
        """Test sending private messages between agents."""
        # Register two agents
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        
        comm_manager.register_agent("agent1", Mock(), callback1)
        comm_manager.register_agent("agent2", Mock(), callback2)
        
        # Send message
        message = await comm_manager.send_message(
            sender="agent1",
            recipients="agent2",
            content={"action": "cooperate"},
            message_type=MessageType.PRIVATE
        )
        
        assert message.sender == "agent1"
        assert message.recipients == ["agent2"]
        assert message.content == {"action": "cooperate"}
        
        # Check callback was called
        await asyncio.sleep(0.1)  # Allow async delivery
        callback2.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_broadcast_message(self, comm_manager):
        """Test broadcasting messages to all agents."""
        # Register three agents
        callbacks = [AsyncMock() for _ in range(3)]
        for i, callback in enumerate(callbacks):
            comm_manager.register_agent(f"agent{i}", Mock(), callback)
        
        # Broadcast message
        message = await comm_manager.broadcast(
            sender="agent0",
            content={"announcement": "high_price"},
            exclude=["agent0"]  # Don't send to self
        )
        
        assert message.message_type == MessageType.BROADCAST
        assert "agent0" not in message.recipients
        assert "agent1" in message.recipients
        assert "agent2" in message.recipients
        
        # Check callbacks
        await asyncio.sleep(0.1)
        callbacks[0].assert_not_called()  # Sender shouldn't receive
        callbacks[1].assert_called_once()
        callbacks[2].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_group_messaging(self, comm_manager):
        """Test sending messages to groups."""
        # Register agents in groups
        comm_manager.register_agent("agent1", Mock(), groups=["cooperative"])
        comm_manager.register_agent("agent2", Mock(), groups=["cooperative"])
        comm_manager.register_agent("agent3", Mock(), groups=["competitive"])
        
        # Send to group
        message = await comm_manager.send_to_group(
            sender="agent1",
            group_name="cooperative",
            content={"proposal": "maintain_prices"}
        )
        
        assert message.message_type == MessageType.GROUP
        assert set(message.recipients) == {"agent1", "agent2"}
        
    @pytest.mark.asyncio
    async def test_message_filtering(self, comm_manager):
        """Test message filtering functionality."""
        # Add content filter
        filter = ContentFilter(blocked_words=["cheat", "collude"])
        comm_manager.add_filter(filter)
        
        # Register agents
        comm_manager.register_agent("agent1", Mock())
        comm_manager.register_agent("agent2", Mock())
        
        # Try to send filtered message
        message = await comm_manager.send_message(
            sender="agent1",
            recipients="agent2",
            content="Let's collude on prices"
        )
        
        # Message should be filtered
        stats = comm_manager.get_statistics()
        assert stats['messages_filtered'] == 1
        
    @pytest.mark.asyncio
    async def test_rate_limiting(self, comm_manager):
        """Test rate limiting functionality."""
        comm_manager.rate_limit_max_messages = 3
        
        # Register agents
        comm_manager.register_agent("agent1", Mock())
        comm_manager.register_agent("agent2", Mock())
        
        # Send messages up to limit
        for i in range(3):
            await comm_manager.send_message(
                sender="agent1",
                recipients="agent2",
                content=f"Message {i}"
            )
        
        # Next message should fail
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await comm_manager.send_message(
                sender="agent1",
                recipients="agent2",
                content="Too many messages"
            )
    
    @pytest.mark.asyncio
    async def test_message_history(self, comm_manager):
        """Test message history retrieval."""
        # Register agents and send messages
        comm_manager.register_agent("agent1", Mock())
        comm_manager.register_agent("agent2", Mock())
        
        for i in range(5):
            await comm_manager.send_message(
                sender="agent1" if i % 2 == 0 else "agent2",
                recipients="agent2" if i % 2 == 0 else "agent1",
                content=f"Message {i}"
            )
        
        # Get history
        history = comm_manager.get_message_history()
        assert len(history) == 5
        
        # Filter by agent
        agent1_history = comm_manager.get_message_history(agent_id="agent1")
        assert all(m.sender == "agent1" or "agent1" in m.recipients for m in agent1_history)
        
        # Filter by type and limit
        private_history = comm_manager.get_message_history(
            message_type=MessageType.PRIVATE,
            limit=3
        )
        assert len(private_history) <= 3


class TestCommunicatingAgentAdapter:
    """Test suite for CommunicatingAgentAdapter."""
    
    @pytest.fixture
    def mock_autogen_agent(self):
        """Create a mock AutoGen agent."""
        agent = Mock()
        agent.name = "TestAgent"
        agent.send = Mock()
        agent.chat = Mock(return_value='{"action": 5}')
        return agent
    
    @pytest.fixture
    def comm_adapter(self, mock_autogen_agent):
        """Create a CommunicatingAgentAdapter instance."""
        return CommunicatingAgentAdapter(
            autogen_agent=mock_autogen_agent,
            name="TestCommAgent",
            communication_strategy="honest",
            mock_behavior="always_medium"
        )
    
    @pytest.mark.asyncio
    async def test_handle_message(self, comm_adapter):
        """Test message handling."""
        message = Message(
            sender="other_agent",
            recipients=["TestCommAgent"],
            content={"proposal": "cooperate"},
            message_type=MessageType.NEGOTIATION
        )
        
        await comm_adapter.handle_message(message)
        
        assert len(comm_adapter._received_messages) == 1
        assert comm_adapter._received_messages[0] == message
    
    @pytest.mark.asyncio
    async def test_communication_strategies(self):
        """Test different communication strategies."""
        strategies = ["honest", "deceptive", "strategic", "silent"]
        
        for strategy in strategies:
            agent = Mock()
            agent.name = f"Agent_{strategy}"
            agent.send = Mock()
            
            adapter = CommunicatingAgentAdapter(
                autogen_agent=agent,
                communication_strategy=strategy,
                mock_behavior="always_medium"
            )
            
            assert adapter.comm_strategy.strategy_type == strategy
    
    @pytest.mark.asyncio
    async def test_act_with_communication_context(self, comm_adapter):
        """Test decision making with communication context."""
        # Add communication manager reference
        comm_adapter._comm_manager = Mock()
        comm_adapter._agent_id = "test_agent"
        
        # Add negotiation proposal
        comm_adapter._negotiation_proposals = [{
            "sender": "other_agent",
            "content": {
                "type": "cooperation_proposal",
                "my_intended_action": 7
            },
            "round": 5
        }]
        
        # Act with recent negotiation
        observation = {"round_num": 6}
        action = await comm_adapter.act_async(observation)
        
        # Honest agent should honor agreement
        assert action == 7  # As per negotiation


class TestParallelOrchestrator:
    """Test suite for ParallelOrchestrator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "communication": {
                "enabled": True,
                "max_rounds": 2,
                "timeout_per_round": 1.0
            },
            "environment": {
                "_target": "safety_governor.environments.PriceGameEnvironment",
                "n_agents": 2
            },
            "agents": [
                {
                    "id": "agent1",
                    "params": {
                        "mock_behavior": "always_low"
                    }
                },
                {
                    "id": "agent2", 
                    "params": {
                        "mock_behavior": "always_high"
                    }
                }
            ],
            "defenses": [],
            "referees": [],
            "max_steps": 5,
            "action_timeout": 5.0
        }
    
    @pytest.mark.asyncio
    async def test_parallel_action_collection(self, config):
        """Test parallel action collection from agents."""
        orchestrator = ParallelOrchestrator(config)
        
        # Create mock agents
        agents = {
            "agent1": AsyncMock(act_async=AsyncMock(return_value={"action": 0})),
            "agent2": AsyncMock(act_async=AsyncMock(return_value={"action": 9}))
        }
        
        # Collect actions in parallel
        observations = {"agent1": {"obs": 1}, "agent2": {"obs": 2}}
        actions = await orchestrator.collect_actions_parallel(agents, observations)
        
        assert actions["agent1"] == {"action": 0}
        assert actions["agent2"] == {"action": 9}
        
        # Both agents should be called concurrently
        agents["agent1"].act_async.assert_called_once()
        agents["agent2"].act_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_communication_phase(self, config):
        """Test communication phase execution."""
        orchestrator = ParallelOrchestrator(config)
        
        # Create mock agents with communication
        agents = {}
        for i in range(2):
            agent = Mock()
            agent.communicate = AsyncMock()
            agents[f"agent{i}"] = agent
        
        # Run communication phase
        messages = await orchestrator.run_communication_phase(
            agents=agents,
            environment_state={"step": 0},
            round_num=0
        )
        
        # Agents should have been called to communicate
        for agent in agents.values():
            assert agent.communicate.call_count == 2  # max_rounds = 2
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, config):
        """Test timeout handling in parallel execution."""
        orchestrator = ParallelOrchestrator(config)
        
        # Create agent that times out
        async def slow_act(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return {"action": 5}
        
        agents = {
            "agent1": Mock(act_async=slow_act),
            "agent2": AsyncMock(act_async=AsyncMock(return_value={"action": 3}))
        }
        
        # Set short timeout
        orchestrator.config['action_timeout'] = 0.1
        
        # Should handle timeout gracefully
        actions = await orchestrator.collect_actions_parallel(agents, {})
        
        # Slow agent should get default action
        assert actions["agent1"] == {"action": 0}
        assert actions["agent2"] == {"action": 3}


@pytest.mark.asyncio
async def test_end_to_end_communication():
    """Test end-to-end communication flow."""
    # Create communication manager
    comm_manager = CommunicationManager(enable_logging=False)
    
    # Create and register communicating agents
    agents = {}
    for i in range(3):
        agent = Mock()
        agent.name = f"Agent{i}"
        
        adapter = CommunicatingAgentAdapter(
            autogen_agent=agent,
            communication_strategy="honest" if i == 0 else "strategic",
            mock_behavior="always_medium"
        )
        
        # Give adapter reference to comm manager
        adapter._comm_manager = comm_manager
        adapter._agent_id = f"agent{i}"
        
        agents[f"agent{i}"] = adapter
        
        # Register with comm manager
        comm_manager.register_agent(
            agent_id=f"agent{i}",
            agent_instance=adapter,
            message_callback=adapter.handle_message
        )
    
    # Simulate communication
    await agents["agent0"]._send_broadcast(
        environment_state={"observation": {}},
        round_num=1
    )
    
    # Allow message delivery
    await asyncio.sleep(0.1)
    
    # Check other agents received broadcast
    for i in [1, 2]:
        assert len(agents[f"agent{i}"]._received_messages) > 0
    
    # Get communication stats
    stats = comm_manager.get_statistics()
    assert stats['messages_sent'] > 0
    assert stats['broadcast_count'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])