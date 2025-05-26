#!/usr/bin/env python3
"""
Test LLM connectivity for different providers.

Usage:
    python scripts/test_llm_connection.py --provider ollama
    python scripts/test_llm_connection.py --provider openai --model gpt-4
    python scripts/test_llm_connection.py --provider anthropic --model claude-3-opus-20240229
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.safety_governor.utils.llm_client import LLMClient


def test_connection(provider: str, model: str = None, api_key: str = None):
    """Test LLM connection and basic functionality."""
    print(f"\n🔌 Testing {provider.upper()} connection...")
    
    # Default models
    default_models = {
        "ollama": "deepseek-r1:1.5b",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-sonnet-20240229",
        "fireworks": "accounts/fireworks/models/llama-v3-70b-instruct"
    }
    
    # Configure client
    config = {
        "provider": provider,
        "model": model or default_models.get(provider, ""),
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    if api_key:
        config["api_key"] = api_key
    
    if provider == "ollama":
        config["api_base"] = "http://localhost:11434"
    
    print(f"Model: {config['model']}")
    
    try:
        # Create client
        client = LLMClient(config)
        
        # Test prompt
        test_prompt = """You are playing a price-setting game. 
        Your current price is 5. Your competitor's price is 6.
        What price (1-10) will you set next? 
        Respond with JSON: {"price": X}"""
        
        print("\n📤 Sending test prompt...")
        response = client.generate(test_prompt)
        
        print("\n📥 Response received:")
        print(response)
        
        # Validate response
        if "{" in response and "}" in response:
            print("\n✅ Connection successful! LLM is responding correctly.")
        else:
            print("\n⚠️  Connection works but response format may need adjustment.")
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        
        if provider == "ollama":
            print("   1. Is Ollama running? Check with: ollama list")
            print("   2. Is the model installed? Try: ollama pull qwen3:8b")
            print("   3. Is Ollama accessible at http://localhost:11434?")
        elif provider == "openai":
            print("   1. Is OPENAI_API_KEY environment variable set?")
            print("   2. Do you have API credits?")
            print("   3. Is the model name correct?")
        elif provider == "anthropic":
            print("   1. Is ANTHROPIC_API_KEY environment variable set?")
            print("   2. Do you have API access?")
            print("   3. Is the model name correct?")


def main():
    parser = argparse.ArgumentParser(description="Test LLM connection")
    parser.add_argument("--provider", 
                       choices=["ollama", "openai", "anthropic", "fireworks"],
                       default="ollama",
                       help="LLM provider to test")
    parser.add_argument("--model", help="Model name (uses defaults if not specified)")
    parser.add_argument("--api-key", help="API key (uses environment variable if not specified)")
    
    args = parser.parse_args()
    test_connection(args.provider, args.model, args.api_key)


if __name__ == "__main__":
    main()