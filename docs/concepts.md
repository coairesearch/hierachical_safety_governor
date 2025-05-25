# Core Concepts

## Overview

The Hierarchical Safety Governor implements a multi-layered approach to AI safety in multi-agent systems. This page explains the key concepts and design principles.

## The Safety Problem

### Why Multi-Agent Safety Matters

When AI agents interact:
- **Emergent behaviors** arise that weren't programmed
- **Nash equilibria** can be harmful (e.g., price fixing)
- **Deception** becomes possible between agents
- **Misalignment** can compound across the team

### Real-World Examples
- Trading algorithms colluding to manipulate markets
- Recommendation systems creating filter bubbles
- Autonomous vehicles implicitly "agreeing" to speed
- Chatbots reinforcing each other's biases

## Hierarchical Oversight Model

```
┌─────────────────┐
│     Human       │  ← Ultimate oversight
└────────┬────────┘
         │
┌────────▼────────┐
│    Governor     │  ← High-level intervention
└────────┬────────┘
         │
┌────────▼────────┐
│    Referee      │  ← Pattern detection
└────────┬────────┘
         │
┌────────▼────────┐
│     Agents      │  ← Task execution
└─────────────────┘
```

### Layer 1: Agents
- Execute tasks in the environment
- May be LLMs, RL agents, or rule-based systems
- Interact through actions and observations
- Subject to monitoring and intervention

### Layer 2: Referees
- Monitor agent behavior for specific patterns
- Each referee specializes in one type of detection:
  - Collusion patterns
  - Deceptive communication
  - Resource hoarding
  - Unfair coordination
- Raise alerts when patterns are detected
- Cannot directly intervene (separation of concerns)

### Layer 3: Governors
- Receive alerts from referees
- Decide on intervention strategies:
  - Reset environment
  - Modify rewards
  - Restrict agent actions
  - Request human oversight
- Log all interventions for analysis
- Can coordinate multiple referees

### Layer 4: Human Oversight
- Reviews governor decisions
- Sets safety policies
- Analyzes long-term patterns
- Updates safety mechanisms

## Key Design Principles

### 1. Separation of Concerns
- Detection (referees) is separate from intervention (governors)
- Allows specialization and modularity
- Easier to test and validate each component

### 2. Composability
- Multiple referees can monitor different patterns
- Governors can implement various intervention strategies
- Components can be mixed and matched

### 3. Transparency
- All decisions are logged and traceable
- Clear chain of responsibility
- Enables post-hoc analysis

### 4. Fail-Safe Design
- Conservative intervention when uncertain
- Graceful degradation under errors
- Human oversight as final backstop

## Event-Driven Architecture

### Event Bus
Central communication system enabling:
- Loose coupling between components
- Real-time monitoring
- Extensibility without modification
- Event replay for analysis

### Key Events
```python
# Agent actions
{"type": "agent_action", "agent": "A", "action": "set_price", "value": 9.5}

# Referee alerts
{"type": "referee_alert", "referee": "collusion", "severity": "high", "evidence": {...}}

# Governor interventions
{"type": "governor_intervention", "action": "reset_environment", "reason": "collusion_detected"}
```

## Safety Patterns

### Detection Patterns

1. **Threshold-Based**: Simple metrics (e.g., sustained high prices)
2. **Statistical**: Deviation from expected distributions
3. **Behavioral**: Sequence analysis of agent actions
4. **Communication**: Analysis of agent messages
5. **Game-Theoretic**: Detection of equilibrium strategies

### Intervention Strategies

1. **Reset**: Return to initial conditions
2. **Reward Shaping**: Modify incentives
3. **Action Restriction**: Limit available actions
4. **Communication Filtering**: Block certain messages
5. **Time-outs**: Pause for human review

## Environments and Scenarios

### Price Competition
- Models market dynamics
- Natural tendency toward collusion
- Clear metrics (prices, profits)

### Resource Commons
- Shared resource management
- Tragedy of the commons scenarios
- Sustainability challenges

### Auction Games
- Bidding strategies
- Information asymmetry
- Coalition formation

### Custom Environments
- Implement Gymnasium interface
- Define action/observation spaces
- Specify reward structure
- Add domain-specific metrics

## Metrics and Evaluation

### Safety Metrics
- **Detection Rate**: How often bad behavior is caught
- **False Positive Rate**: Unnecessary interventions
- **Response Time**: Speed of detection and intervention
- **Prevention Effectiveness**: Behavior change after intervention

### Performance Metrics
- **Task Completion**: Are agents still effective?
- **Efficiency**: Resource usage and time
- **Robustness**: Performance under interventions

### Research Metrics
- **Reproducibility**: Consistent results
- **Generalization**: Transfer across scenarios
- **Scalability**: Performance with more agents

## Best Practices

### For Researchers
1. Start with simple baselines
2. Test components in isolation
3. Use multiple environments
4. Document assumptions
5. Share negative results

### For Developers
1. Follow interface contracts
2. Handle edge cases gracefully
3. Add comprehensive logging
4. Write tests for safety properties
5. Consider adversarial scenarios

## Next Steps

- Implement your first [custom environment](./development/environments.md)
- Design a [referee pattern](./development/referees.md)
- Run [research experiments](./guides/running-experiments.md)
- Explore [advanced scenarios](./research/examples.md)