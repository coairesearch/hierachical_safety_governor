# Auto Test Template – Hierarchical Safety‑Governor Demo

Minimal, runnable scaffold for experimenting with multi‑agent teams,
AutoGen LLM agents, a simple collusion **referee**, and a toy
**hierarchical governor** that intervenes on alerts.

## Quick start

### Install uv (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install project dependencies
```bash
bash install.sh
```

### Test LLM Connection
```bash
source .venv/bin/activate

# For Ollama (local, free)
ollama pull qwen3:8b
python scripts/test_llm_connection.py --provider ollama

# For OpenAI
export OPENAI_API_KEY="your-api-key-here"
python scripts/test_llm_connection.py --provider openai
```

### Run the demo
```bash
# Basic example
python scripts/run.py --config configs/example_basic.yaml

# With agent communication
python scripts/run.py --config configs/example_communication.yaml

# Full collusion study
python scripts/run.py --config configs/example_collusion_study.yaml
```

You'll see two AutoGen agents playing a price‑setting game; after a few
steps they tacitly collude, the referee raises an alert, and the
governor resets the environment.

For a step‑by‑step demonstration with charts and progress bars, run the
Streamlit UI:

```bash
streamlit run scripts/stream_ui.py
```