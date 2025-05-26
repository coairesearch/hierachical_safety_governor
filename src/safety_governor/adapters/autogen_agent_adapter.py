"""Adapter: wraps an AutoGen Agent (or GroupChat) so orchestrator can call .act()"""
from __future__ import annotations
import asyncio, json, uuid, copy
# import logging # Not needed as per instruction to use print()
from typing import Any, Dict, Optional, Union
import autogen  # type: ignore
from safety_governor.utils.llm_client import LLMClient
from safety_governor.utils.prompt_templates import get_prompt_template, format_prompt

class AutoGenAgentAdapter:
    def __init__(self, autogen_agent: Union[autogen.Agent, autogen.GroupChat],
                 name: Optional[str] = None, system_prompt: Optional[str] = None,
                 llm_config: Optional[Dict[str, Any]] = None,
                 prompt_template: Optional[str] = None,
                 game_type: Optional[str] = "price_game",
                 agent_index: int = 0,
                 mock_behavior: Optional[Union[str, Dict[str, Any]]] = None):
        self.agent = autogen_agent
        self.name = name or getattr(autogen_agent, 'name', f"agent_{uuid.uuid4().hex[:6]}")
        self.llm_client = None
        self.agent_index = agent_index
        self.mock_behavior = mock_behavior
        
        # Set prompt template - priority: custom > game_type default > price_game default
        if prompt_template:
            self.prompt_template = prompt_template
        else:
            self.prompt_template = get_prompt_template(game_type)
            
        # Initialize LLM client if llm_config is provided
        if llm_config and isinstance(llm_config, dict):
            self.llm_client = LLMClient(llm_config)
            print(f"AGENT [{self.name}] - Initialized with LLM config: {llm_config}")
        
        if system_prompt:
            self.agent.send(system_prompt, recipient=self.agent, request_reply=False)

    async def act_async(self, observation: Dict[str, Any],
                        info: Optional[Dict[str, Any]] = None) -> Any:
        try:
            original_info_for_logging = info.copy() if info is not None else None
            if info is None:
                info = {}
            info["predicted_opponent_price"] = "low"

            print(f"AGENT [{self.name}] - Observation: {observation}")
            print(f"AGENT [{self.name}] - Original Info: {original_info_for_logging}")
            print(f"AGENT [{self.name}] - Manipulated Info: {info}")

            # Convert numpy arrays in observation to lists for JSON serialization
            observation_for_json = copy.deepcopy(observation)
            for key, value in observation_for_json.items():
                if hasattr(value, 'tolist'):
                    observation_for_json[key] = value.tolist()

            # Format the prompt using the template and observation
            # If prompt_template is a game type string, get the actual template
            if self.prompt_template in ["price_game", "commons_game", "auction_game", "trust_game"]:
                actual_template = get_prompt_template(self.prompt_template)
            else:
                actual_template = self.prompt_template
            formatted_prompt = format_prompt(actual_template, observation_for_json, self.agent_index)

            print(f"AGENT [{self.name}] - Has LLM: {self.llm_client is not None}, Has Mock Behavior: {hasattr(self, 'mock_behavior') and self.mock_behavior is not None}")
            
            if self.llm_client:
                # Use our LLM client for generation
                print(f"AGENT [{self.name}] - Calling LLM with prompt length: {len(formatted_prompt)}")
                reply = self.llm_client.generate(formatted_prompt)
                print(f"AGENT [{self.name}] - LLM Response: {reply}")
            elif hasattr(self, 'mock_behavior') and self.mock_behavior is not None:
                # Use configurable mock behavior
                reply_content = self._get_mock_action(observation, info)
                reply = json.dumps(reply_content)
                print(f"AGENT [{self.name}] - Using mock behavior: {self.mock_behavior}")
            else:
                # Fallback to original AutoGen chat
                print(f"AGENT [{self.name}] - Using AutoGen chat")
                if asyncio.iscoroutinefunction(self.agent.chat):
                    reply = await self.agent.chat(formatted_prompt)
                else:
                    loop = asyncio.get_running_loop()
                    reply = await loop.run_in_executor(None, self.agent.chat, formatted_prompt)
            
            # Parse the response
            try:
                content = str(reply).strip()
                # Extract JSON from response (handle case where LLM adds extra text)
                if '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_str = content[json_start:json_end]
                    action_dict = json.loads(json_str)
                else:
                    action_dict = json.loads(content)
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response: {reply}")
                action_dict = {"action": 0}  # Default fallback

            print(f"AGENT [{self.name}] - Chosen Action: {action_dict}") # Log the full dict
            
            # Handle different action formats
            if isinstance(action_dict, dict):
                if 'action' in action_dict:
                    return action_dict['action']
                elif 'price' in action_dict:
                    # For price game, convert price to action (price - 1)
                    return action_dict['price'] - 1
                else:
                    print(f"Unexpected action format: {action_dict}")
                    return 0
            elif isinstance(action_dict, (int, float)):
                return int(action_dict)
            else:
                print(f"Unexpected action format: {action_dict}")
                return 0  # Default action
                
        except Exception as e:
            print(f"AGENT [{self.name}] - Error in act_async: {e}")
            import traceback
            traceback.print_exc()
            return 0  # Default action on error

    def _get_mock_action(self, observation: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate action based on mock behavior configuration."""
        if isinstance(self.mock_behavior, str):
            # Simple string behaviors
            if self.mock_behavior == "always_low":
                return {"action": 0}
            elif self.mock_behavior == "always_high":
                return {"action": 9}
            elif self.mock_behavior == "always_medium":
                return {"action": 5}
            elif self.mock_behavior == "random":
                import random
                return {"action": random.randint(0, 9)}
            elif self.mock_behavior == "tit_for_tat":
                # Mirror opponent's last action
                opponent_price = observation.get('opponent_last_price', 5)
                return {"action": int(opponent_price)}
            else:
                # Default if unknown behavior
                return {"action": 0}
        elif isinstance(self.mock_behavior, dict):
            # Complex configurable behaviors
            behavior_type = self.mock_behavior.get('type', 'fixed')
            
            if behavior_type == 'fixed':
                return {"action": self.mock_behavior.get('action', 0)}
            elif behavior_type == 'pattern':
                # Cycle through a pattern of actions
                pattern = self.mock_behavior.get('pattern', [0])
                round_num = observation.get('round_num', 0)
                action = pattern[round_num % len(pattern)]
                return {"action": action}
            elif behavior_type == 'conditional':
                # Conditional logic based on observation
                conditions = self.mock_behavior.get('conditions', [])
                for condition in conditions:
                    if self._evaluate_condition(condition, observation):
                        return {"action": condition.get('action', 0)}
                # Default action if no conditions match
                return {"action": self.mock_behavior.get('default_action', 0)}
            else:
                return {"action": 0}
        else:
            # Fallback
            return {"action": 0}
    
    def _evaluate_condition(self, condition: Dict[str, Any], observation: Dict[str, Any]) -> bool:
        """Evaluate a condition against the observation."""
        field = condition.get('field')
        operator = condition.get('operator', '==')
        value = condition.get('value')
        
        if field not in observation:
            return False
            
        obs_value = observation[field]
        
        if operator == '==':
            return obs_value == value
        elif operator == '>':
            return obs_value > value
        elif operator == '<':
            return obs_value < value
        elif operator == '>=':
            return obs_value >= value
        elif operator == '<=':
            return obs_value <= value
        else:
            return False

    def act(self, observation: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Any:
        return asyncio.run(self.act_async(observation, info))