
# Auto Test Template – Hierarchical Safety‑Governor Demo

Minimal, runnable scaffold for experimenting with multi‑agent teams,
AutoGen LLM agents, a simple collusion **referee**, and a toy
**hierarchical governor** that intervenes on alerts.

## Quick start

### Install uv (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install project dependencies
```bash
bash install.sh
```

### Run the demo
```bash
source .venv/bin/activate
python run_once.py --config configs/demo.yaml
```

### Alternative: Using uvx (without activation)
```bash
uvx --from . python run_once.py --config configs/demo.yaml
```

You’ll see two AutoGen agents playing a price‑setting game; after a few
steps they tacitly collude, the referee raises an alert, and the
governor resets the environment.
