#!/usr/bin/env python
"""Test LLM connectivity directly."""

import requests
import json
import sys

def test_ollama_direct():
    """Test Ollama API directly."""
    url = "http://localhost:11434/api/generate"
    
    prompt = """You are playing a pricing game. Choose a price between 0 and 9.
0 = lowest price, 9 = highest price.

Respond with ONLY a JSON object like: {"action": 5}

Your response:"""
    
    payload = {
        "model": "qwen3:8b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 50
        }
    }
    
    print("Testing Ollama API...")
    print(f"Prompt: {prompt}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')}")
            
            # Try to parse the action
            response_text = result.get('response', '')
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                try:
                    action = json.loads(json_str)
                    print(f"Parsed action: {action}")
                except:
                    print("Failed to parse JSON from response")
        else:
            print(f"Error: Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ollama_direct()