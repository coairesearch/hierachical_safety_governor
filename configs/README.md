# Configuration Files

## Available Configurations

### For Learning & Experimentation

1. **`example_basic.yaml`**
   - Start here! Simplest configuration
   - Single agent in price-setting game
   - Tests your LLM connection

2. **`example_communication.yaml`**
   - Two agents that can communicate
   - Shows cooperation and deception
   - Good for understanding agent interactions

3. **`example_collusion_study.yaml`**
   - Full research configuration
   - Studies emergent collusion behaviors
   - Multiple runs for statistical analysis

### For Testing

4. **`test_minimal.yaml`**
   - Minimal config for automated tests
   - Not for regular use

## Quick Start

```bash
# Test your setup
python scripts/test_llm_connection.py

# Run basic example
python scripts/run.py --config configs/example_basic.yaml

# Analyze collusion
python scripts/analyze.py --mode collusion --config configs/example_collusion_study.yaml
```

See `docs/USAGE.md` for detailed instructions.