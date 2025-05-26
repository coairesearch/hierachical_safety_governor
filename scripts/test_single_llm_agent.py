#!/usr/bin/env python
"""Test a single LLM agent directly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.adapters import AutoGenAgentAdapter
import autogen
import numpy as np

# Create a simple AutoGen agent
autogen_agent = autogen.ConversableAgent(
    name="TestAgent",
    human_input_mode="NEVER",
    code_execution_config=False,
    system_message="You are playing a price game. Respond with JSON."
)

# Create adapter with LLM
adapter = AutoGenAgentAdapter(
    autogen_agent=autogen_agent,
    name="TestLLM",
    llm_config={
        "provider": "ollama",
        "model": "qwen3:8b", 
        "base_url": "http://localhost:11434",
        "temperature": 0.3,
        "max_tokens": 50
    },
    prompt_template="price_game",
    game_type="price_game",
    agent_index=0
)

# Test observation
obs = {
    "last_prices": np.array([5, 5], dtype=np.int32),
    "current_step": 1
}

print("Testing LLM agent...")
try:
    action = adapter.act(obs)
    print(f"Action: {action}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()