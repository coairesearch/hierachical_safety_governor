"""
Parallel Orchestrator for concurrent agent execution and communication.

This module extends the base Orchestrator to support parallel agent actions
and inter-agent communication using the CommunicationManager.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass
import json

import numpy as np

from .orchestrator import Orchestrator
from ..utils import CommunicationManager, Message, MessageType, event_bus
from ..adapters import AutoGenAgentAdapter


logger = logging.getLogger(__name__)


@dataclass
class CommunicationPhaseConfig:
    """Configuration for communication phases."""
    enabled: bool = True
    max_rounds: int = 3
    timeout_per_round: float = 30.0
    allow_private_messages: bool = True
    allow_broadcast: bool = True
    log_communications: bool = True


class ParallelOrchestrator(Orchestrator):
    """
    Orchestrator that supports parallel agent execution and communication.
    
    This orchestrator enables:
    - Parallel action collection from all agents
    - Inter-agent communication phases before decisions
    - Asynchronous message passing between agents
    - Communication monitoring by the safety governor
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the parallel orchestrator with communication support."""
        super().__init__(config)
        
        # Communication configuration
        comm_config = config.get('communication', {})
        self.comm_phase_config = CommunicationPhaseConfig(**comm_config)
        
        # Initialize communication manager
        self.comm_manager = CommunicationManager(
            enable_logging=self.comm_phase_config.log_communications,
            enable_event_bus=True
        )
        
        # Track async tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        logger.info(f"Initialized ParallelOrchestrator with communication: {self.comm_phase_config}")

    async def setup_agents_with_communication(
        self,
        agents: Dict[str, AutoGenAgentAdapter]
    ) -> None:
        """
        Register agents with the communication manager.
        
        Args:
            agents: Dictionary of agent_id -> agent instance
        """
        for agent_id, agent in agents.items():
            # Define message handler for the agent
            async def handle_message(message: Message, agent=agent, agent_id=agent_id):
                """Handle incoming messages for an agent."""
                # Store messages in agent's context for decision-making
                if not hasattr(agent, '_received_messages'):
                    agent._received_messages = []
                agent._received_messages.append(message)
                
                # If agent has a specific message handler, call it
                if hasattr(agent, 'handle_message'):
                    await agent.handle_message(message)
                else:
                    logger.debug(f"Agent {agent_id} received message: {message.id}")
            
            # Register agent with communication manager
            groups = self.config.get('agent_groups', {}).get(agent_id, [])
            self.comm_manager.register_agent(
                agent_id=agent_id,
                agent_instance=agent,
                message_callback=handle_message,
                groups=groups
            )
            
            # Give agent reference to communication manager for sending messages
            agent._comm_manager = self.comm_manager
            agent._agent_id = agent_id

    async def collect_actions_parallel(
        self,
        agents: Dict[str, AutoGenAgentAdapter],
        observations: Dict[str, Any],
        info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect actions from all agents in parallel.
        
        Args:
            agents: Dictionary of agent_id -> agent instance
            observations: Current observations for agents
            info: Additional information
            
        Returns:
            Dictionary of agent_id -> action
        """
        # Create tasks for parallel execution
        tasks = {}
        for agent_id, agent in agents.items():
            obs = observations.get(agent_id, observations)
            task = asyncio.create_task(
                agent.act_async(obs, info),
                name=f"act_{agent_id}"
            )
            tasks[agent_id] = task
        
        # Wait for all agents to complete with timeout
        timeout = self.config.get('action_timeout', 60.0)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for agent actions after {timeout}s")
            # Cancel remaining tasks
            for task in tasks.values():
                if not task.done():
                    task.cancel()
            results = []
        
        # Collect results
        actions = {}
        for (agent_id, agent), result in zip(agents.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Agent '{agent_id}' failed: {result}")
                # Use default action on failure
                actions[agent_id] = {'action': 0}
            else:
                actions[agent_id] = result
                
        return actions

    async def run_communication_phase(
        self,
        agents: Dict[str, AutoGenAgentAdapter],
        environment_state: Dict[str, Any],
        round_num: int
    ) -> List[Message]:
        """
        Run a communication phase where agents can exchange messages.
        
        Args:
            agents: Dictionary of agent_id -> agent instance
            environment_state: Current state of the environment
            round_num: Current round number
            
        Returns:
            List of all messages exchanged during this phase
        """
        if not self.comm_phase_config.enabled:
            return []
            
        all_messages = []
        
        for comm_round in range(self.comm_phase_config.max_rounds):
            logger.debug(f"Communication round {comm_round + 1}/{self.comm_phase_config.max_rounds}")
            
            # Clear previous round messages
            for agent in agents.values():
                if hasattr(agent, '_received_messages'):
                    agent._received_messages = []
            
            # Let each agent decide if they want to send messages
            comm_tasks = []
            for agent_id, agent in agents.items():
                if hasattr(agent, 'communicate'):
                    task = asyncio.create_task(
                        agent.communicate(
                            environment_state=environment_state,
                            round_num=round_num,
                            comm_round=comm_round
                        ),
                        name=f"comm_{agent_id}_round_{comm_round}"
                    )
                    comm_tasks.append(task)
            
            # Wait for communication with timeout
            if comm_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*comm_tasks, return_exceptions=True),
                        timeout=self.comm_phase_config.timeout_per_round
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Communication round {comm_round} timed out")
            
            # Collect messages from this round
            round_messages = self.comm_manager.get_message_history(
                since=time.time() - self.comm_phase_config.timeout_per_round,
                limit=1000
            )
            all_messages.extend(round_messages)
            
            # Small delay between rounds
            await asyncio.sleep(0.1)
        
        return all_messages

    async def run_seed_async(self, seed: int) -> Dict[str, float]:
        """
        Run a single seed/episode asynchronously with parallel agent execution.
        
        Args:
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary of metrics from the episode
        """
        np.random.seed(seed)
        
        # Create environment and agents
        env = self._create_environment()
        agents = self._create_agents()
        defenses = self._create_defenses()
        referees = self._create_referees()
        
        # Setup agents with communication
        await self.setup_agents_with_communication(agents)
        
        # Initialize
        obs, info = env.reset(seed=seed)
        returns = {aid: 0.0 for aid in agents.keys()}
        
        # Episode loop
        step_count = 0
        max_steps = self.config.get('max_steps', 100)
        
        while not self.shutdown_requested and step_count < max_steps:
            # Communication phase (if enabled)
            if self.comm_phase_config.enabled:
                messages = await self.run_communication_phase(
                    agents=agents,
                    environment_state={'observation': obs, 'step': step_count},
                    round_num=step_count
                )
                
                # Publish communication event
                event_bus.publish("communication_phase_complete", {
                    "step": step_count,
                    "message_count": len(messages),
                    "timestamp": time.time()
                })
            
            # Parallel action collection
            actions = await self.collect_actions_parallel(agents, obs, info)
            
            # Apply defenses (still sequential for now)
            for def_id, defense in defenses.items():
                defense.inspect(actions, env)
            
            # Environment step
            obs, rewards, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            
            # Apply referees
            for ref_id, referee in referees.items():
                violations = referee.check_violations(actions, obs, env)
                event_bus.publish("referee_violations", {
                    "referee_id": ref_id,
                    "violations": violations,
                    "step": step_count
                })
            
            # Update returns
            for aid in agents.keys():
                returns[aid] += rewards.get(aid, 0.0)
            
            # Publish step event
            event_bus.publish("step_complete", {
                "step": step_count,
                "actions": actions,
                "rewards": rewards,
                "done": done
            })
            
            step_count += 1
            
            if done:
                break
        
        # Cleanup
        event_bus.publish("episode_complete", {
            "seed": seed,
            "steps": step_count,
            "returns": returns
        })
        
        # Unregister agents from communication manager
        for agent_id in agents.keys():
            self.comm_manager.unregister_agent(agent_id)
        
        return returns

    def run_seed(self, seed: int) -> Dict[str, float]:
        """
        Run a single seed/episode (synchronous wrapper).
        
        Args:
            seed: Random seed for reproducibility
            
        Returns:
            Dictionary of metrics from the episode
        """
        # Create new event loop if needed
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, create a task
            future = asyncio.ensure_future(self.run_seed_async(seed))
            return loop.run_until_complete(future)
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(self.run_seed_async(seed))

    async def run_seed_stream_async(
        self,
        seed: int
    ) -> Generator[Dict[str, Any], None, Dict[str, float]]:
        """
        Run a single seed/episode with streaming updates (async generator).
        
        Args:
            seed: Random seed for reproducibility
            
        Yields:
            Step information dictionaries
            
        Returns:
            Final episode metrics
        """
        np.random.seed(seed)
        
        # Create environment and agents
        env = self._create_environment()
        agents = self._create_agents()
        defenses = self._create_defenses()
        referees = self._create_referees()
        
        # Setup agents with communication
        await self.setup_agents_with_communication(agents)
        
        # Initialize
        obs, info = env.reset(seed=seed)
        returns = {aid: 0.0 for aid in agents.keys()}
        
        # Yield initial state
        yield {
            "type": "init",
            "observation": obs,
            "agents": list(agents.keys()),
            "seed": seed
        }
        
        # Episode loop
        step_count = 0
        max_steps = self.config.get('max_steps', 100)
        
        while not self.shutdown_requested and step_count < max_steps:
            # Communication phase
            if self.comm_phase_config.enabled:
                messages = await self.run_communication_phase(
                    agents=agents,
                    environment_state={'observation': obs, 'step': step_count},
                    round_num=step_count
                )
                
                # Yield communication info
                yield {
                    "type": "communication",
                    "step": step_count,
                    "message_count": len(messages),
                    "messages": [
                        {
                            "sender": msg.sender,
                            "recipients": msg.recipients,
                            "type": msg.message_type.value,
                            "content_preview": str(msg.content)[:100]
                        }
                        for msg in messages[-5:]  # Last 5 messages
                    ]
                }
            
            # Parallel action collection
            actions = await self.collect_actions_parallel(agents, obs, info)
            
            # Apply defenses
            defense_interventions = {}
            for def_id, defense in defenses.items():
                interventions = defense.inspect(actions, env)
                if interventions:
                    defense_interventions[def_id] = interventions
            
            # Environment step
            obs, rewards, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            
            # Apply referees
            violations = {}
            for ref_id, referee in referees.items():
                ref_violations = referee.check_violations(actions, obs, env)
                if ref_violations:
                    violations[ref_id] = ref_violations
            
            # Update returns
            for aid in agents.keys():
                returns[aid] += rewards.get(aid, 0.0)
            
            # Yield step info
            yield {
                "type": "step",
                "step": step_count,
                "actions": actions,
                "rewards": rewards,
                "observation": obs,
                "defense_interventions": defense_interventions,
                "violations": violations,
                "done": done,
                "returns": returns
            }
            
            step_count += 1
            
            if done:
                break
        
        # Yield final results
        yield {
            "type": "complete",
            "seed": seed,
            "steps": step_count,
            "returns": returns,
            "communication_stats": self.comm_manager.get_statistics()
        }
        
        # Cleanup
        for agent_id in agents.keys():
            self.comm_manager.unregister_agent(agent_id)

    def run_seed_stream(
        self,
        seed: int
    ) -> Generator[Dict[str, Any], None, Dict[str, float]]:
        """
        Run a single seed/episode with streaming updates (synchronous wrapper).
        
        Args:
            seed: Random seed for reproducibility
            
        Yields:
            Step information dictionaries
            
        Returns:
            Final episode metrics
        """
        # Create async generator
        async_gen = self.run_seed_stream_async(seed)
        
        # Run async generator in event loop
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Iterate through async generator
        while True:
            try:
                result = loop.run_until_complete(async_gen.__anext__())
                if result.get("type") == "complete":
                    return result.get("returns", {})
                yield result
            except StopAsyncIteration:
                break
        
        return {}

    async def start(self) -> None:
        """Start the parallel orchestrator's background tasks."""
        self._running = True
        await self.comm_manager.start()
        logger.info("ParallelOrchestrator started")

    async def stop(self) -> None:
        """Stop the parallel orchestrator and cleanup."""
        self._running = False
        await self.comm_manager.stop()
        
        # Cancel any remaining tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("ParallelOrchestrator stopped")

    def get_communication_stats(self) -> Dict[str, Any]:
        """Get statistics about agent communications."""
        return self.comm_manager.get_statistics()

    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get message history for analysis.
        
        Args:
            agent_id: Filter by specific agent
            limit: Maximum number of messages
            
        Returns:
            List of messages
        """
        return self.comm_manager.get_message_history(
            agent_id=agent_id,
            limit=limit
        )