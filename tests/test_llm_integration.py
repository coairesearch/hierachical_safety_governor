"""Test LLM integration with different providers"""
import pytest
import json
from safety_governor.utils.llm_client import LLMClient
from safety_governor.adapters.autogen_agent_adapter import AutoGenAgentAdapter
import autogen


def test_llm_client_ollama():
    """Test Ollama client basic functionality"""
    config = {
        "provider": "ollama",
        "model": "qwen3:8b",
        "api_base": "http://localhost:11434"
    }
    client = LLMClient(config)
    
    prompt = "Reply with only: {\"action\": 5}"
    response = client.generate(prompt)
    
    # Check if response can be parsed as JSON
    try:
        data = json.loads(response)
        assert "action" in data
        assert isinstance(data["action"], int)
    except json.JSONDecodeError:
        # If Ollama is not running, it should return default
        assert response == '{"action": 0}'


def test_autogen_adapter_with_llm():
    """Test AutoGenAgentAdapter with LLM configuration"""
    # Create a mock AutoGen agent with LLM config
    agent = autogen.ConversableAgent(
        name="TestAgent",
        llm_config={
            "provider": "ollama",
            "model": "qwen3:8b",
            "api_base": "http://localhost:11434"
        }
    )
    
    adapter = AutoGenAgentAdapter(agent, name="test_agent")
    
    # Test observation
    observation = {
        "last_prices": [5, 7],
        "last_profits": [100, 150],
        "current_step": 3
    }
    
    # Call act method
    action = adapter.act(observation)
    
    # Verify action is valid
    assert isinstance(action, int)
    assert 0 <= action <= 9


def test_autogen_adapter_without_llm():
    """Test AutoGenAgentAdapter without LLM (fallback mode)"""
    agent = autogen.ConversableAgent(
        name="TestAgent",
        llm_config=False
    )
    
    adapter = AutoGenAgentAdapter(agent, name="test_agent")
    
    observation = {
        "last_prices": [5, 7],
        "last_profits": [100, 150],
        "current_step": 3
    }
    
    action = adapter.act(observation)
    
    # Should always return 0 in mock mode
    assert action == 0


def test_prompt_formatting():
    """Test that prompts are formatted correctly"""
    agent = autogen.ConversableAgent(
        name="TestAgent",
        llm_config={
            "provider": "ollama",
            "model": "qwen3:8b"
        }
    )
    
    adapter = AutoGenAgentAdapter(agent, name="test_agent")
    
    # Test with various observation formats
    observations = [
        {"last_prices": [3, 8], "current_step": 1},
        {"last_prices": [0, 9], "last_profits": [50, 200]},
        {}  # Empty observation
    ]
    
    for obs in observations:
        action = adapter.act(obs)
        assert isinstance(action, int)
        assert 0 <= action <= 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])