#!/usr/bin/env python
"""Check if Ollama is running and has the required model."""

import requests
import sys
import json

def check_ollama():
    """Check Ollama availability and models."""
    base_url = "http://localhost:11434"
    
    print("Checking Ollama status...")
    
    # Check if Ollama is running
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            print(f"❌ Ollama API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama is not running. Please start it with: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {e}")
        return False
    
    print("✅ Ollama is running")
    
    # Check available models
    try:
        models_data = response.json()
        models = models_data.get('models', [])
        model_names = [m['name'] for m in models]
        
        print(f"\nAvailable models ({len(models)}):")
        for model in model_names:
            print(f"  - {model}")
        
        # Check for qwen models
        qwen_models = [m for m in model_names if 'qwen' in m.lower()]
        if qwen_models:
            print(f"\n✅ Found qwen models: {', '.join(qwen_models)}")
            print("\nYou can use any of these in your configuration.")
        else:
            print("\n⚠️  No qwen models found. You can pull one with:")
            print("    ollama pull qwen2.5:8b")
            print("\nOr use one of the available models in your config.")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

if __name__ == "__main__":
    success = check_ollama()
    sys.exit(0 if success else 1)