
# Auto Test Template – Hierarchical Safety‑Governor Demo

Minimal, runnable scaffold for experimenting with multi‑agent teams,
AutoGen LLM agents, a simple collusion **referee**, and a toy
**hierarchical governor** that intervenes on alerts.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run_once.py --config configs/demo.yaml
```

You’ll see two AutoGen agents playing a price‑setting game; after a few
steps they tacitly collude, the referee raises an alert, and the
governor resets the environment.
