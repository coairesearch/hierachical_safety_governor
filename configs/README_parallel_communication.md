# Running Parallel Communication Demos

This directory contains several demo configurations for testing agent communication with and without LLMs.

## Available Demos

### 1. Simple Mock Demo (No LLMs Required)
```bash
uv run scripts/run_parallel_demo.py --config configs/demo_parallel_communication_simple.yaml
```
- Uses mock behaviors (no LLMs needed)
- 2 agents with different strategies
- Quick to run and test

### 2. Full LLM Demo (Requires Ollama)
```bash
# First, check if Ollama is running
uv run scripts/check_ollama.py

# If needed, start Ollama
ollama serve

# Pull the model if you don't have it
ollama pull qwen2.5:8b

# Run the demo
uv run scripts/run_parallel_demo.py --config configs/demo_parallel_communication_llm.yaml
```
- Uses Ollama LLMs for all 3 agents
- Different communication strategies (honest, deceptive, strategic)
- Shows real LLM-based negotiation

### 3. Mixed Demo (1 LLM + 1 Mock)
```bash
uv run scripts/run_parallel_demo.py --config configs/demo_parallel_mixed.yaml
```
- Combines LLM and mock agents
- Good for testing when Ollama is slow
- Shows interaction between different agent types

## Understanding the Output

When you run a demo, you'll see:

1. **Agent Registration**: 
   ```
   Registered agent 'firm_a' with groups: []
   ```

2. **Communication Messages**:
   ```
   AGENT [FirmA_Honest] - Sent broadcast: {'type': 'status_update', ...}
   AGENT [FirmB_Strategic] - Received message from firm_a: ...
   ```

3. **Decision Making**:
   ```
   AGENT [FirmA_Honest] - Observation: {'last_prices': array([1, 1], ...}
   AGENT [FirmA_Honest] - Chosen Action: {'action': 5}
   ```

4. **Final Statistics**:
   ```
   Communication statistics: {'messages_sent': 42, 'messages_delivered': 42, ...}
   ```

## Customizing Demos

### Change LLM Model
Edit the `llm_config` section:
```yaml
llm_config:
  provider: "ollama"
  model: "llama3.2"  # or any model you have
  temperature: 0.7
```

### Adjust Communication Frequency
Edit the `communication` section:
```yaml
communication:
  max_rounds: 3  # More rounds = more messages
  broadcast_probability: 0.8  # Higher = more broadcasts
```

### Add More Agents
Just add more entries to the `agents` list with unique IDs.

## Troubleshooting

### "Ollama is not running"
Start Ollama with:
```bash
ollama serve
```

### "Model not found"
Pull the model first:
```bash
ollama pull qwen2.5:8b
# or
ollama pull llama3.2
```

### Timeout Errors
Increase timeouts in the config:
```yaml
action_timeout: 60.0  # Longer timeout for slow LLMs
communication:
  timeout_per_round: 30.0
```

### High CPU/Memory Usage
- Reduce number of agents
- Use smaller models (e.g., qwen2.5:3b)
- Use mock behaviors for some agents

## Next Steps

1. Try different communication strategies
2. Analyze the message logs to spot collusion patterns
3. Add custom referees to detect specific behaviors
4. Experiment with different LLM models and temperatures