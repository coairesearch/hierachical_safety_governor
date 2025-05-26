"""LLM client for multiple providers (Ollama, OpenAI, Anthropic, Fireworks)"""
from __future__ import annotations
import json
import requests
from typing import Dict, Any, Optional, Union
import os


class LLMClient:
    """Unified LLM client supporting multiple providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "qwen3:8b")
        self.api_base = config.get("api_base", "http://localhost:11434")
        self.api_key = config.get("api_key", os.getenv(f"{self.provider.upper()}_API_KEY"))
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 150)
        self.mock_responses = config.get("mock_responses", [])
        
    def generate(self, prompt: str) -> str:
        """Generate response from LLM"""
        if self.provider == "mock":
            return self._mock_generate(prompt)
        elif self.provider == "ollama":
            return self._ollama_generate(prompt)
        elif self.provider == "openai":
            return self._openai_generate(prompt)
        elif self.provider == "anthropic":
            return self._anthropic_generate(prompt)
        elif self.provider == "fireworks":
            return self._fireworks_generate(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _mock_generate(self, prompt: str) -> str:
        """Generate using mock responses based on pattern matching"""
        # Check each mock response for pattern match
        for mock in self.mock_responses:
            pattern = mock.get("pattern", "")
            if pattern.lower() in prompt.lower():
                return mock.get("response", '{"action": 0}')
        
        # Default response if no pattern matches
        return '{"action": 0}'
    
    def _ollama_generate(self, prompt: str) -> str:
        """Generate using Ollama API"""
        url = f"{self.api_base}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()["response"]
            
            # Clean up response - remove thinking tags if present
            if "<think>" in result and "</think>" in result:
                # Extract content after </think>
                parts = result.split("</think>")
                if len(parts) > 1:
                    result = parts[1].strip()
            
            return result
        except Exception as e:
            print(f"Ollama API error: {e}")
            return '{"action": 0}'  # Default fallback
    
    def _openai_generate(self, prompt: str) -> str:
        """Generate using OpenAI API"""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return '{"action": 0}'
    
    def _anthropic_generate(self, prompt: str) -> str:
        """Generate using Anthropic API"""
        import anthropic
        
        client = anthropic.Anthropic(api_key=self.api_key)
        try:
            response = client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return '{"action": 0}'
    
    def _fireworks_generate(self, prompt: str) -> str:
        """Generate using Fireworks API"""
        url = "https://api.fireworks.ai/inference/v1/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["text"]
        except Exception as e:
            print(f"Fireworks API error: {e}")
            return '{"action": 0}'