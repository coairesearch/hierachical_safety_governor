#!/usr/bin/env python
"""Debug LLM agent directly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.utils.llm_client import LLMClient
from safety_governor.utils.prompt_templates import format_prompt, get_prompt_template
import numpy as np

# Test LLM client directly
llm_config = {
    "provider": "ollama",
    "model": "qwen3:8b",
    "base_url": "http://localhost:11434",
    "temperature": 0.3,
    "max_tokens": 50
}

print("Creating LLM client...")
client = LLMClient(llm_config)

# Create a test observation
observation = {
    "last_prices": np.array([5, 5], dtype=np.int32),
    "current_step": 1
}

# Get and format prompt
template = get_prompt_template("price_game")
prompt = format_prompt(template, observation, agent_index=0)

print(f"Prompt:\n{prompt}")
print("-" * 50)

print("Calling LLM...")
try:
    response = client.generate(prompt)
    print(f"Response:\n{response}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()