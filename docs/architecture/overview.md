# Architecture Overview

## System Architecture

The Hierarchical Safety Governor follows a modular, event-driven architecture designed for extensibility and research flexibility.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    ORCHESTRATOR                                       │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ Config Loader │  │ Component Mgr  │  │ Event Manager  │  │ Metrics Logger │  │
│  └───────┬───────┘  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  │
└────────────┴─────────────────────┴─────────────────────┴─────────────────────┴──────────────────┘
            │                        │                        │
            ↓                        ↓                        ↓
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│    ENVIRONMENTS    │  │      AGENTS        │  │     EVENT BUS      │
│ ┌───────────────┐ │  │ ┌───────────────┐ │  │ ┌───────────────┐ │
│ │ PriceGameEnv  │ │  │ │ AutoGenAgent  │ │  │ │  Pub/Sub Core │ │
│ └───────────────┘ │  │ └───────────────┘ │  │ └─────┬─────────┘ │
│ ┌───────────────┐ │  │ ┌───────────────┐ │  │        │          │
│ │ CommonsEnv    │ │  │ │ OllamaAgent   │ │  └────────┬─────────┘
│ └───────────────┘ │  │ └───────────────┘ │           │
└────────────────────┘  └────────────────────┘           │
                                                        │
            ┌──────────────────────────────────────────┴─────────────────────────────────────────┐
            ↓                                                                                                    ↓
┌────────────────────┐                                          ┌────────────────────┐
│      REFEREES      │                                          │     GOVERNORS      │
│ ┌───────────────┐ │                                          │ ┌───────────────┐ │
│ │CollusionRef   │────────────Events───────────────────────>│Hierarchical   │ │
│ └───────────────┘ │                                          │ └───────────────┘ │
│ ┌───────────────┐ │                                          │ ┌───────────────┐ │
│ │DeceptionRef   │────────────Events───────────────────────>│RewardShaping   │ │
│ └───────────────┘ │                                          │ └───────────────┘ │
└────────────────────┘                                          └────────────────────┘
```

## Core Components

### Orchestrator
The central coordinator that:
- Loads configuration from YAML files
- Instantiates all components
- Manages the simulation loop
- Coordinates event flow
- Handles logging and metrics

**Key responsibilities:**
- Component lifecycle management
- Configuration validation
- Error handling and recovery
- Performance monitoring

### Event Bus
The communication backbone:
- Implements publish-subscribe pattern
- Enables loose coupling
- Supports event filtering
- Records event history
- Allows replay for debugging

**Event Types:**
- `agent_action`: Agent decisions
- `environment_update`: State changes
- `referee_alert`: Safety violations
- `governor_intervention`: Corrective actions
- `metrics_update`: Performance data

### Environments
Simulation environments implementing Gymnasium interface:
- Define action and observation spaces
- Implement game dynamics
- Calculate rewards
- Track metrics
- Support reset and intervention

### Agents
AI systems being tested:
- Receive observations
- Select actions
- Can be LLMs, RL models, or rule-based
- Wrapped in adapters for compatibility

### Referees
Specialized monitors:
- Subscribe to relevant events
- Detect specific patterns
- Raise alerts when violations occur
- Maintain detection state
- Log evidence for analysis

### Governors
Intervention mechanisms:
- Subscribe to referee alerts
- Evaluate severity
- Choose intervention strategy
- Execute interventions
- Monitor effectiveness

## Data Flow

### 1. Initialization Phase
```
Config File → Orchestrator → Component Creation → Event Bus Setup
```

### 2. Simulation Loop
```
1. Environment → Observations → Agents
2. Agents → Actions → Environment
3. Environment → State Update → Event Bus
4. Event Bus → Events → Referees
5. Referees → Alerts → Governors
6. Governors → Interventions → Environment
```

### 3. Metrics Collection
```
All Components → Metrics Events → Event Bus → Logger → Output Files
```

## Extension Points

### Adding New Components

1. **New Environment**
   - Implement `gymnasium.Env` interface
   - Define spaces and dynamics
   - Emit appropriate events

2. **New Agent Type**
   - Create adapter implementing agent interface
   - Handle observation/action conversion
   - Manage agent state

3. **New Referee**
   - Implement detection logic
   - Subscribe to relevant events
   - Define alert conditions

4. **New Governor**
   - Implement intervention strategies
   - Subscribe to alerts
   - Define intervention logic

### Configuration System

```yaml
# Example configuration structure
orchestrator:
  max_rounds: 100
  log_level: INFO

environment:
  class: PriceGameEnv
  params:
    num_agents: 2
    market_size: 1000

agents:
  - name: agent_1
    class: AutoGenAgent
    params:
      model: "gpt-3.5-turbo"
  
referees:
  - class: SimpleCollusionReferee
    params:
      threshold: 0.8
      
governors:
  - class: HierarchicalGovernor
    params:
      intervention_threshold: 0.9
```

## Performance Considerations

### Event Bus Optimization
- Use topic-based filtering
- Batch event processing
- Implement backpressure
- Consider async processing

### Memory Management
- Limit event history size
- Implement circular buffers
- Clean up completed episodes
- Profile memory usage

### Scalability
- Support distributed referees
- Enable parallel environments
- Implement checkpointing
- Consider multi-process execution

## Error Handling

### Component Failures
- Graceful degradation
- Fallback strategies
- Error event propagation
- Recovery mechanisms

### Safety Guarantees
- Fail-safe defaults
- Conservative interventions
- Audit trail maintenance
- Human escalation path

## Testing Strategy

### Unit Tests
- Individual component behavior
- Edge case handling
- Error conditions

### Integration Tests
- Event flow verification
- Component interaction
- Configuration validation

### Safety Tests
- Referee detection accuracy
- Governor intervention effectiveness
- System resilience

## Security Considerations

### Agent Isolation
- Sandboxed execution
- Resource limits
- Communication restrictions

### Data Protection
- Secure configuration
- Protected metrics storage
- Access control

## Future Enhancements

### Planned Features
- Distributed execution
- Real-time visualization
- Advanced analytics
- Model interpretability
- Automated hyperparameter tuning

### Research Directions
- Multi-level governance
- Adaptive referees
- Learning interventions
- Adversarial testing