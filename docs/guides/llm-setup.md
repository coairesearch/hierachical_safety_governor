# LLM Setup Guide

This guide explains how to configure and use Large Language Models (LLMs) with the Hierarchical Safety Governor framework.

## Overview

The framework supports multiple LLM providers:
- **Ollama** (local, no API key required)
- **OpenAI** (requires API key)
- **Anthropic** (requires API key)
- **Fireworks** (requires API key)

Additionally, agents can be configured with **mock behaviors** for testing without LLM calls.

## How Agent Behavior is Determined

The AutoGenAgentAdapter uses the following priority order:
1. If `llm_config` is provided with a valid provider → Use LLM
2. Else if `mock_behavior` is provided → Use mock behavior
3. Else → Fall back to AutoGen's default behavior

**Note:** You don't need to set `llm_config: False` in the autogen_agent section. The adapter automatically determines whether to use LLMs based on the presence of valid configuration.

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

## Mock Behaviors (Testing without LLMs)

For testing and experimentation without LLM calls, agents can use configurable mock behaviors:

### Simple String Behaviors

```yaml
agents:
  - id: test_agent
    params:
      mock_behavior: "always_low"      # Always choose action 0
      # Other options:
      # mock_behavior: "always_high"   # Always choose action 9
      # mock_behavior: "always_medium" # Always choose action 5
      # mock_behavior: "random"        # Random action 0-9
      # mock_behavior: "tit_for_tat"   # Mirror opponent's last action
```

### Fixed Action

```yaml
agents:
  - id: test_agent
    params:
      mock_behavior:
        type: "fixed"
        action: 3  # Always choose action 3
```

### Pattern-Based Behavior

```yaml
agents:
  - id: test_agent
    params:
      mock_behavior:
        type: "pattern"
        pattern: [0, 2, 5, 7, 9, 7, 5, 2]  # Cycles through this pattern
```

### Conditional Behavior

```yaml
agents:
  - id: test_agent
    params:
      mock_behavior:
        type: "conditional"
        conditions:
          - field: "round_num"
            operator: "<"
            value: 5
            action: 9  # High price in early rounds
          - field: "opponent_last_price"
            operator: ">"
            value: 5
            action: 7  # Match high prices
          - field: "opponent_last_price"
            operator: "<="
            value: 5
            action: 2  # Undercut low prices
        default_action: 5  # If no conditions match
```

Available operators for conditions: `==`, `>`, `<`, `>=`, `<=`

### Example Configuration

See `configs/demo_mock_behaviors.yaml` for a complete example using various mock behaviors.

## Performance Tips

1. **Local testing**: Use Ollama with smaller models for faster iteration
2. **Production**: Use API providers with appropriate rate limiting
3. **Batch processing**: Run multiple seeds in parallel when possible
4. **Cost management**: Monitor API usage and set spending limits
5. **Mock behaviors**: Use mock behaviors for rapid testing without LLM costs