# Creating Environments Guide

## Overview

Environments are the simulation spaces where agents interact. This guide shows how to create custom environments for your research scenarios.

## Environment Interface

All environments must implement the Gymnasium interface:

```python
import gymnasium as gym
import numpy as np
from typing import Dict, Tuple, Any, Optional

class CustomEnvironment(gym.Env):
    """Base template for a custom environment."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        
        # Define action and observation spaces
        self.action_space = gym.spaces.Box(
            low=0.0, high=10.0, shape=(1,), dtype=np.float32
        )
        
        self.observation_space = gym.spaces.Dict({
            'market_state': gym.spaces.Box(
                low=0.0, high=np.inf, shape=(4,), dtype=np.float32
            ),
            'agent_history': gym.spaces.Box(
                low=0.0, high=np.inf, shape=(10, 2), dtype=np.float32
            )
        })
        
        # Initialize state
        self.reset()
    
    def reset(self, seed: Optional[int] = None) -> Tuple[Dict, Dict]:
        """Reset environment to initial state."""
        super().reset(seed=seed)
        
        # Initialize your environment state
        self.state = self._initialize_state()
        
        # Return initial observation and info
        return self._get_observation(), self._get_info()
    
    def step(self, action: np.ndarray) -> Tuple[Dict, float, bool, bool, Dict]:
        """Execute one environment step."""
        # Update state based on action
        self.state = self._update_state(action)
        
        # Calculate reward
        reward = self._calculate_reward(action)
        
        # Check termination conditions
        terminated = self._is_terminated()
        truncated = self._is_truncated()
        
        # Get observation and info
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, reward, terminated, truncated, info
```

## Example: Auction Environment

```python
from typing import List
import numpy as np
import gymnasium as gym
from utils.event_bus import EventBus

class AuctionEnvironment(gym.Env):
    """Sealed-bid auction environment."""
    
    def __init__(self, 
                 num_agents: int = 4,
                 num_items: int = 3,
                 reserve_price: float = 10.0,
                 budget_range: Tuple[float, float] = (50.0, 200.0),
                 event_bus: Optional[EventBus] = None):
        super().__init__()
        
        self.num_agents = num_agents
        self.num_items = num_items
        self.reserve_price = reserve_price
        self.budget_range = budget_range
        self.event_bus = event_bus or EventBus()
        
        # Action: bid amount for current item
        self.action_space = gym.spaces.Box(
            low=0.0, 
            high=budget_range[1], 
            shape=(1,), 
            dtype=np.float32
        )
        
        # Observation: current item value, remaining budget, past winning bids
        self.observation_space = gym.spaces.Dict({
            'item_value': gym.spaces.Box(low=0, high=1000, shape=(1,)),
            'my_budget': gym.spaces.Box(low=0, high=budget_range[1], shape=(1,)),
            'winning_bids': gym.spaces.Box(low=0, high=budget_range[1], 
                                         shape=(num_items,)),
            'items_remaining': gym.spaces.Discrete(num_items + 1)
        })
        
        self.reset()
    
    def reset(self, seed=None):
        super().reset(seed=seed)
        
        # Initialize auction state
        self.current_item = 0
        self.item_values = self.np_random.uniform(20, 100, self.num_items)
        self.agent_budgets = self.np_random.uniform(
            *self.budget_range, self.num_agents
        )
        self.winning_bids = np.zeros(self.num_items)
        self.winners = [-1] * self.num_items
        self.bids = {}
        
        # Emit reset event
        self.event_bus.emit('environment_reset', {
            'environment': 'auction',
            'num_items': self.num_items,
            'item_values': self.item_values.tolist()
        })
        
        return self._get_observation(0), {}
    
    def step(self, actions: Dict[int, float]):
        """Process bids from all agents for current item."""
        
        # Collect all bids
        valid_bids = {}
        for agent_id, bid in actions.items():
            if bid <= self.agent_budgets[agent_id] and bid >= self.reserve_price:
                valid_bids[agent_id] = bid
            
            # Emit bid event
            self.event_bus.emit('agent_bid', {
                'agent_id': agent_id,
                'item': self.current_item,
                'bid': bid,
                'valid': agent_id in valid_bids
            })
        
        # Determine winner (highest bidder)
        if valid_bids:
            winner = max(valid_bids, key=valid_bids.get)
            winning_bid = valid_bids[winner]
            self.winners[self.current_item] = winner
            self.winning_bids[self.current_item] = winning_bid
            self.agent_budgets[winner] -= winning_bid
            
            # Emit auction result
            self.event_bus.emit('auction_result', {
                'item': self.current_item,
                'winner': winner,
                'winning_bid': winning_bid,
                'item_value': self.item_values[self.current_item]
            })
        
        # Calculate rewards (value - price for winner, 0 for others)
        rewards = {}
        for agent_id in range(self.num_agents):
            if agent_id == self.winners[self.current_item]:
                profit = self.item_values[self.current_item] - winning_bid
                rewards[agent_id] = profit
            else:
                rewards[agent_id] = 0
        
        # Move to next item
        self.current_item += 1
        terminated = self.current_item >= self.num_items
        
        # Get observations for all agents
        observations = {
            agent_id: self._get_observation(agent_id) 
            for agent_id in range(self.num_agents)
        }
        
        infos = {
            agent_id: {
                'budget_remaining': self.agent_budgets[agent_id],
                'items_won': sum(1 for w in self.winners if w == agent_id)
            }
            for agent_id in range(self.num_agents)
        }
        
        return observations, rewards, terminated, False, infos
    
    def _get_observation(self, agent_id: int) -> Dict:
        """Get observation for specific agent."""
        if self.current_item < self.num_items:
            current_value = self.item_values[self.current_item]
        else:
            current_value = 0
            
        return {
            'item_value': np.array([current_value]),
            'my_budget': np.array([self.agent_budgets[agent_id]]),
            'winning_bids': self.winning_bids.copy(),
            'items_remaining': self.num_items - self.current_item
        }
```

## Environment Best Practices

### 1. Clear State Management

```python
class EnvironmentState:
    """Encapsulate environment state for clarity."""
    def __init__(self):
        self.round = 0
        self.agent_positions = {}
        self.resource_levels = {}
        self.history = []
    
    def to_dict(self) -> Dict:
        """Serialize state for logging."""
        return {
            'round': self.round,
            'positions': self.agent_positions,
            'resources': self.resource_levels
        }
```

### 2. Configurable Dynamics

```python
def __init__(self, config: Dict[str, Any]):
    # Make key parameters configurable
    self.regeneration_rate = config.get('regeneration_rate', 0.1)
    self.decay_rate = config.get('decay_rate', 0.05)
    self.interaction_radius = config.get('interaction_radius', 2.0)
    
    # Support different game modes
    self.mode = config.get('mode', 'competitive')
    if self.mode == 'cooperative':
        self.reward_function = self._cooperative_reward
    else:
        self.reward_function = self._competitive_reward
```

### 3. Rich Observations

```python
def _get_observation(self, agent_id: int) -> Dict:
    """Provide informative observations."""
    return {
        # Current state
        'my_position': self.agent_positions[agent_id],
        'my_resources': self.agent_resources[agent_id],
        
        # Other agents (with partial observability)
        'visible_agents': self._get_visible_agents(agent_id),
        
        # Environment state
        'resource_map': self._get_local_resource_map(agent_id),
        'round': self.round,
        
        # Historical context
        'recent_actions': self.action_history[agent_id][-5:],
        'average_resources': np.mean(list(self.agent_resources.values()))
    }
```

### 4. Meaningful Metrics

```python
def _get_info(self) -> Dict:
    """Return metrics for analysis."""
    return {
        'total_resources': sum(self.resource_levels.values()),
        'resource_inequality': self._calculate_gini(),
        'cooperation_index': self._measure_cooperation(),
        'sustainability_score': self._check_sustainability(),
        'nash_equilibrium_distance': self._distance_from_nash()
    }
```

## Integration with Safety Components

### Emitting Events for Referees

```python
def step(self, actions):
    # ... process actions ...
    
    # Emit events for referee monitoring
    if self._detect_suspicious_pattern(actions):
        self.event_bus.emit('suspicious_behavior', {
            'agents': list(actions.keys()),
            'pattern': 'coordinated_action',
            'evidence': self._gather_evidence(actions)
        })
    
    # Emit state updates
    self.event_bus.emit('environment_state', {
        'round': self.round,
        'prices': current_prices,
        'trades': current_trades
    })
```

### Supporting Interventions

```python
def apply_intervention(self, intervention: Dict[str, Any]):
    """Handle governor interventions."""
    intervention_type = intervention['type']
    
    if intervention_type == 'reset_prices':
        self.prices = self.default_prices.copy()
        
    elif intervention_type == 'limit_actions':
        self.action_limits = intervention['limits']
        
    elif intervention_type == 'modify_rewards':
        self.reward_modifier = intervention['modifier']
    
    # Log intervention
    self.intervention_history.append({
        'round': self.round,
        'intervention': intervention
    })
```

## Testing Your Environment

### Unit Tests

```python
import pytest
import numpy as np

class TestCustomEnvironment:
    def test_action_space(self):
        env = CustomEnvironment({})
        assert env.action_space.contains(np.array([5.0]))
        assert not env.action_space.contains(np.array([15.0]))
    
    def test_reset(self):
        env = CustomEnvironment({})
        obs, info = env.reset(seed=42)
        assert 'market_state' in obs
        assert obs['market_state'].shape == (4,)
    
    def test_step_dynamics(self):
        env = CustomEnvironment({})
        env.reset(seed=42)
        
        action = env.action_space.sample()
        obs, reward, term, trunc, info = env.step(action)
        
        assert isinstance(reward, float)
        assert isinstance(term, bool)
        assert 'metric' in info
```

### Integration Tests

```python
def test_with_agents():
    env = CustomEnvironment({})
    agents = [MockAgent() for _ in range(4)]
    
    obs, _ = env.reset()
    for round in range(100):
        actions = {i: agent.act(obs) for i, agent in enumerate(agents)}
        obs, rewards, term, _, _ = env.step(actions)
        
        if term:
            break
    
    assert round > 0  # Environment ran successfully
```

## Performance Optimization

### Vectorized Operations

```python
# Slow
for i in range(self.num_agents):
    for j in range(self.num_resources):
        self.distances[i, j] = np.linalg.norm(
            self.agent_positions[i] - self.resource_positions[j]
        )

# Fast
self.distances = np.linalg.norm(
    self.agent_positions[:, None, :] - self.resource_positions[None, :, :],
    axis=2
)
```

### Caching Expensive Computations

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def _calculate_market_equilibrium(self, supply: float, demand: float) -> float:
    """Cache equilibrium calculations."""
    # Expensive computation
    return self._solve_equilibrium(supply, demand)
```

## Common Patterns

### Multi-Agent Synchronization

```python
def step(self, actions: Dict[int, Any]):
    """Handle simultaneous actions from multiple agents."""
    # Collect all actions first
    self.pending_actions = actions
    
    # Resolve conflicts
    resolved_actions = self._resolve_conflicts(actions)
    
    # Apply all actions simultaneously
    new_state = self._apply_actions(resolved_actions)
    
    # Calculate individual rewards
    rewards = {
        agent_id: self._calculate_reward(agent_id, new_state)
        for agent_id in actions
    }
    
    return observations, rewards, False, False, infos
```

### Partial Observability

```python
def _get_observation(self, agent_id: int) -> Dict:
    """Implement fog of war or limited information."""
    visible_range = self.agent_vision_range[agent_id]
    agent_pos = self.agent_positions[agent_id]
    
    # Only show nearby information
    visible_agents = [
        other_id for other_id, pos in self.agent_positions.items()
        if np.linalg.norm(pos - agent_pos) <= visible_range
    ]
    
    return {
        'local_map': self._get_local_map(agent_pos, visible_range),
        'visible_agents': visible_agents,
        'global_metric': self.public_information
    }
```

## Next Steps

- Implement [referees](./referees.md) to monitor your environment
- Add [governors](./governors.md) for interventions
- Create [custom agents](./agents.md) for your environment
- Run [experiments](../guides/running-experiments.md) with your environment