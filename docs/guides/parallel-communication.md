# Parallel Communication and Agent Coordination

This guide explains how to use the parallel communication features in the Hierarchical Safety Governor framework, which enable agents to communicate before making simultaneous decisions.

## Overview

The parallel communication system enables:
- **Simultaneous Decision Making**: All agents make decisions in parallel rather than sequentially
- **Pre-Decision Communication**: Agents can exchange messages before making decisions
- **Multiple Communication Strategies**: Support for honest, deceptive, and strategic communication patterns
- **Communication Monitoring**: The safety governor can monitor and intervene in agent communications

## Key Components

### 1. ParallelOrchestrator

The `ParallelOrchestrator` extends the base `Orchestrator` to support concurrent agent execution:

```python
from safety_governor.core import ParallelOrchestrator

orchestrator = ParallelOrchestrator(config)
```

### 2. CommunicationManager

Handles all message routing, filtering, and logging:

```python
from safety_governor.utils import CommunicationManager

comm_manager = CommunicationManager(
    enable_logging=True,
    rate_limit_max_messages=100
)
```

### 3. CommunicatingAgentAdapter

Extends agents with communication capabilities:

```python
from safety_governor.adapters import CommunicatingAgentAdapter

agent = CommunicatingAgentAdapter(
    autogen_agent=base_agent,
    communication_strategy="honest"
)
```

## Configuration

### Basic Configuration

```yaml
# Use the ParallelOrchestrator
orchestrator:
  _target: "safety_governor.core.ParallelOrchestrator"

# Communication settings
communication:
  enabled: true
  max_rounds: 3  # Communication rounds before each decision
  timeout_per_round: 10.0
  allow_private_messages: true
  allow_broadcast: true
  log_communications: true
```

### Agent Communication Strategies

Configure how agents communicate:

```yaml
agents:
  - id: honest_agent
    params:
      communication_strategy: "honest"  # Always truthful
      
  - id: deceptive_agent
    params:
      communication_strategy:
        strategy_type: "deceptive"
        deception_rate: 0.8  # 80% chance of misleading
        
  - id: strategic_agent
    params:
      communication_strategy:
        strategy_type: "strategic"
        cooperation_threshold: 0.6
```

## Communication Strategies

### 1. Honest Strategy
- Always sends truthful information
- Honors cooperation agreements
- Suitable for studying genuine coordination

### 2. Deceptive Strategy
- May send false information to mislead others
- Can accept agreements but defect later
- Useful for studying adversarial scenarios

### 3. Strategic Strategy
- Analyzes situations before communicating
- Conditional cooperation based on expected payoffs
- Models sophisticated agent behavior

### 4. Silent Strategy
- Does not participate in communication
- Makes decisions based only on observations
- Baseline for non-communicating agents

## Message Types

The system supports various message types:

- **BROADCAST**: Messages sent to all agents
- **PRIVATE**: Messages to specific agents
- **GROUP**: Messages to agent groups
- **NEGOTIATION**: Structured negotiation messages
- **OBSERVATION**: Sharing of observations

## Example: Running a Communication Experiment

```python
# Create config with communication
config = {
    "orchestrator": {
        "_target": "safety_governor.core.ParallelOrchestrator"
    },
    "communication": {
        "enabled": True,
        "max_rounds": 3
    },
    "agents": [
        {
            "id": "firm_a",
            "params": {
                "communication_strategy": "honest",
                "mock_behavior": "tit_for_tat"
            }
        },
        {
            "id": "firm_b", 
            "params": {
                "communication_strategy": "deceptive",
                "mock_behavior": "always_low"
            }
        }
    ]
}

# Run experiment
orchestrator = ParallelOrchestrator(config)
results = orchestrator.run_seed(42)
```

## Monitoring Communications

The safety governor can monitor communications for collusion:

```yaml
defenses:
  - id: parallel_governor
    params:
      _target: "safety_governor.defenses.HierarchicalGovernor"
      monitor_communications: true
      collusion_detection:
        enabled: true
        similarity_threshold: 0.8
```

## Communication Analysis

After running experiments, analyze communication patterns:

```python
# Get communication statistics
stats = orchestrator.get_communication_stats()
print(f"Messages sent: {stats['messages_sent']}")
print(f"Broadcast messages: {stats['broadcast_count']}")

# Get message history
messages = orchestrator.get_message_history(limit=100)
for msg in messages:
    print(f"{msg.sender} -> {msg.recipients}: {msg.content}")
```

## Best Practices

1. **Start Simple**: Begin with basic honest communication before adding complexity
2. **Monitor Performance**: Parallel execution may use more resources
3. **Set Timeouts**: Always configure action and communication timeouts
4. **Log Communications**: Enable logging for analysis and debugging
5. **Test Strategies**: Experiment with different communication patterns

## Troubleshooting

### Agents Not Communicating
- Ensure `communication.enabled: true` in config
- Check agent has a communication strategy configured
- Verify agents are registered with CommunicationManager

### Timeouts
- Increase `timeout_per_round` for complex communications
- Set appropriate `action_timeout` for LLM-based agents

### Message Filtering
- Check if content filters are blocking messages
- Verify rate limits aren't too restrictive

## Advanced Features

### Custom Message Filters

```python
from safety_governor.utils import MessageFilter

class TopicFilter(MessageFilter):
    def should_allow(self, message):
        # Only allow price-related messages
        return "price" in str(message.content).lower()

comm_manager.add_filter(TopicFilter())
```

### Group Messaging

```yaml
agent_groups:
  firm_a: ["cooperative_firms", "all_firms"]
  firm_b: ["all_firms"]
  firm_c: ["cooperative_firms", "all_firms"]
```

### Communication Phases

The system runs communication in phases:
1. **Initial broadcast phase**: Agents announce intentions
2. **Negotiation phase**: Private negotiations between agents
3. **Final coordination**: Last chance to coordinate before action

## Future Enhancements

Planned improvements include:
- Encrypted private messages
- Reputation systems for trust modeling
- Advanced collusion detection algorithms
- Natural language analysis of communications
- Integration with AutoGen2 GroupChat features