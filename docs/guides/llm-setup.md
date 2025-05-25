# LLM Setup Guide

This guide explains how to configure and use Large Language Models (LLMs) with the Hierarchical Safety Governor framework.

## Overview

The framework supports multiple LLM providers:
- **Ollama** (local, no API key required)
- **OpenAI** (requires API key)
- **Anthropic** (requires API key)
- **Fireworks** (requires API key)

## Setting up Ollama (Recommended for local testing)

1. **Install Ollama**
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama service**
   ```bash
   ollama serve
   ```

3. **Pull the qwen3:8b model**
   ```bash
   ollama pull qwen3:8b
   ```

4. **Verify installation**
   ```bash
   curl http://localhost:11434/api/tags
   ```

## Configuration

### Using Ollama

Create or modify a config file (e.g., `configs/demo_ollama.yaml`):

```yaml
agents:
  - id: firm_a
    impl: safety_governor.adapters.autogen_agent_adapter:AutoGenAgentAdapter
    params:
      llm_config:
        provider: "ollama"
        model: "qwen3:8b"
        api_base: "http://localhost:11434"
        temperature: 0.7
      autogen_agent:
        _factory: autogen.ConversableAgent
        name: "FirmA"
        llm_config: False  # We handle LLM in adapter
```

### Using OpenAI

```yaml
agents:
  - id: firm_a
    impl: safety_governor.adapters.autogen_agent_adapter:AutoGenAgentAdapter
    params:
      llm_config:
        provider: "openai"
        model: "gpt-3.5-turbo"
        temperature: 0.7
        # api_key will be read from OPENAI_API_KEY env var
      autogen_agent:
        _factory: autogen.ConversableAgent
        name: "FirmA"
        llm_config: False
```

Set your API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Using Anthropic

```yaml
agents:
  - id: firm_a
    impl: safety_governor.adapters.autogen_agent_adapter:AutoGenAgentAdapter
    params:
      llm_config:
        provider: "anthropic"
        model: "claude-3-haiku-20240307"
        temperature: 0.7
        # api_key will be read from ANTHROPIC_API_KEY env var
      autogen_agent:
        _factory: autogen.ConversableAgent
        name: "FirmA"
        llm_config: False
```

Set your API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Using Fireworks

```yaml
agents:
  - id: firm_a
    impl: safety_governor.adapters.autogen_agent_adapter:AutoGenAgentAdapter
    params:
      llm_config:
        provider: "fireworks"
        model: "accounts/fireworks/models/llama-v3-8b-instruct"
        temperature: 0.7
        # api_key will be read from FIREWORKS_API_KEY env var
      autogen_agent:
        _factory: autogen.ConversableAgent
        name: "FirmA"
        llm_config: False
```

Set your API key:
```bash
export FIREWORKS_API_KEY="your-api-key-here"
```

## Running Experiments

1. **With Ollama (local)**
   ```bash
   python scripts/run_once.py --config configs/demo_ollama.yaml
   ```

2. **With OpenAI**
   ```bash
   export OPENAI_API_KEY="your-key"
   python scripts/run_once.py --config configs/demo_openai.yaml
   ```

## Customizing Agent Behavior

### Using Built-in Game Templates

The framework includes templates for different game types. Specify the game type in your configuration:

```yaml
agents:
  - id: firm_a
    params:
      game_type: "price_game"  # Options: price_game, commons_game, auction_game, trust_game
      agent_index: 0  # Agent's position in the game (0-based)
```

### Custom Prompts per Agent

You can define custom prompts for each agent to create different strategies or personalities:

```yaml
agents:
  - id: aggressive_firm
    params:
      prompt_template: |
        You are an aggressive competitor focused on market share.
        
        Current state:
        - Your price: {my_last_price}
        - Competitor price: {opponent_last_price}
        - Round: {round_num}
        
        Strategy: Always try to undercut the competitor unless
        they're already at rock bottom prices.
        
        Reply with ONLY: {{"action": <number>}}
```

### Available Template Variables

The following variables are automatically extracted from game observations:

**Price Game:**
- `{my_last_price}` - Your previous price (0-9)
- `{opponent_last_price}` - Opponent's previous price
- `{last_profits}` - Profit array from last round
- `{round_num}` - Current round number

**Commons Game:**
- `{available_resources}` - Remaining shared resources
- `{my_last_extraction}` - Your last extraction amount
- `{others_avg_extraction}` - Average extraction by others

**Auction Game:**
- `{item_value}` - Estimated value of item
- `{last_winning_bid}` - Previous winning bid
- `{budget_remaining}` - Your remaining budget

### Example: Mixed Strategy Agents

See `configs/demo_mixed_strategies.yaml` for an example with:
- A cooperative firm that prefers stable high prices
- An adaptive firm that uses tit-for-tat strategy
- Custom temperature settings for behavior consistency

## Troubleshooting

### Ollama not responding
- Ensure Ollama is running: `ollama serve`
- Check if model is downloaded: `ollama list`
- Verify API endpoint: `curl http://localhost:11434/api/tags`

### API key errors
- Ensure environment variables are set
- Check API key validity with provider's dashboard
- Verify you have credits/quota available

### Slow performance
- Ollama: Use smaller models (e.g., qwen3:8b instead of qwen3:14b)
- API providers: Reduce temperature or max_tokens
- Consider caching responses for repeated scenarios

## Performance Tips

1. **Local testing**: Use Ollama with smaller models for faster iteration
2. **Production**: Use API providers with appropriate rate limiting
3. **Batch processing**: Run multiple seeds in parallel when possible
4. **Cost management**: Monitor API usage and set spending limits