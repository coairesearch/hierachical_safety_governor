# Safety Governor Usage Guide

## Quick Start

### 1. Install Dependencies
```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### 2. Set up LLM Provider

#### Option A: Ollama (Local, Free)
```bash
# Install Ollama from https://ollama.ai
# Pull a model
ollama pull deepseek-r1:1.5b

# Verify it's running
ollama list
```

#### Option B: OpenAI
```bash
export OPENAI_API_KEY="your-api-key"
```

#### Option C: Anthropic
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 3. Test LLM Connection
```bash
python scripts/test_llm_connection.py --provider ollama
```

### 4. Run Your First Experiment
```bash
# With communication between agents
python scripts/run.py --config configs/example_communication.yaml
```

## Configuration Guide

### When to Use Each Config


2. **`example_communication.yaml`** - Agent coordination
   - Two agents that can communicate
   - Shows cooperation vs competition dynamics
   - Demonstrates communication strategies

3. **`example_collusion_study.yaml`** - Research experiments
   - Detailed study of emergent collusion
   - Multiple seeds for statistical analysis
   - Comprehensive logging and analysis

4. **`test_minimal.yaml`** - Testing only
   - For automated tests
   - Not for regular experiments

## Running Experiments

### Basic Run
```bash
# Run a single configuration
python scripts/run.py --config configs/example_basic.yaml

# Run with specific seed
python scripts/run.py --config configs/example_basic.yaml --seed 42
```

### Batch Runs
```bash
# Run multiple seeds (if configured in yaml)
python scripts/run.py --config configs/example_collusion_study.yaml
```

### Web UI
```bash
# Launch interactive web interface
streamlit run scripts/stream_ui.py
```

## Analyzing Results

### Collusion Analysis
```bash
# Analyze collusion patterns in real-time
python scripts/analyze.py --mode collusion --config configs/example_collusion_study.yaml
```

### Communication Analysis
```bash
# Analyze saved communication logs
python scripts/analyze.py --mode communication --results results/experiment_123/
```

### Viewing Communication Messages
Communication messages are logged at INFO level. To see them:
```bash
# Run with INFO logging (shows communication messages)
python scripts/run.py --config configs/example_communication.yaml --log-level INFO

# Look for lines like:
# CommunicationManager - INFO - Message: {"sender": "firm_a", "recipients": ["firm_b"], ...}
# AGENT [FirmA] - Sent broadcast: {'type': 'proposal', ...}
```

### Summary of All Experiments
```bash
# Get overview of all past experiments
python scripts/analyze.py --mode summary --results results/
```

## Key Concepts

### Communication Strategies
- **`honest`**: Agents communicate truthfully
- **`deceptive`**: Agents may lie to gain advantage
- **`strategic`**: Mixed strategy based on context

### Environment: Price Game
- Agents set prices from 0-9
- Higher prices = higher profit margins
- But competitors can undercut
- Nash equilibrium ≈ 5
- Collusion price ≈ 8

### Collusion Detection
- Monitors sustained high prices
- Tracks coordination in communications
- Alerts when threshold exceeded

## Troubleshooting

### LLM Not Responding
```bash
# Test connection
python scripts/test_llm_connection.py --provider ollama

# Check Ollama is running
ollama list

# Try different model
python scripts/run.py --config configs/example_basic.yaml
# Then edit the yaml to use a different model
```

### Out of Memory
- Reduce `max_steps` in config
- Use smaller LLM model
- Run fewer seeds

### Slow Performance
- Ollama is fastest for local testing
- Reduce `max_tokens` in LLM config
- Disable communication for faster runs

## Advanced Usage

### Custom LLM Models
Edit the `llm_config` section in any yaml:
```yaml
llm_config:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.5
  max_tokens: 150
```

### Custom Analysis
```python
# Create custom analysis script
from scripts.analyze import analyze_collusion

# Run with custom parameters
analyze_collusion("configs/my_experiment.yaml")
```

## Next Steps

1. Start with `example_basic.yaml`
2. Try `example_communication.yaml` 
3. Run research experiments with `example_collusion_study.yaml`
4. Analyze results to understand agent behaviors
5. Modify configs for your own experiments