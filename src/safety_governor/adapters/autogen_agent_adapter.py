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
                 agent_index: int = 0):
        self.agent = autogen_agent
        self.name = name or getattr(autogen_agent, 'name', f"agent_{uuid.uuid4().hex[:6]}")
        self.llm_client = None
        self.agent_index = agent_index
        
        # Set prompt template - priority: custom > game_type default > price_game default
        if prompt_template:
            self.prompt_template = prompt_template
        else:
            self.prompt_template = get_prompt_template(game_type)
            
        # Initialize LLM client if llm_config is provided
        if llm_config and isinstance(llm_config, dict):
            self.llm_client = LLMClient(llm_config)
            print(f"AGENT [{self.name}] - Initialized with LLM config: {llm_config}")
        elif hasattr(self.agent, 'llm_config') and isinstance(self.agent.llm_config, dict):
            self.llm_client = LLMClient(self.agent.llm_config)
            print(f"AGENT [{self.name}] - Initialized with agent's LLM config")
        
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
            formatted_prompt = format_prompt(self.prompt_template, observation_for_json, self.agent_index)

            print(f"AGENT [{self.name}] - LLM Config: {self.agent.llm_config}, Has Client: {self.llm_client is not None}")
            
            if self.llm_client:
                # Use our LLM client for generation
                print(f"AGENT [{self.name}] - Calling LLM with prompt length: {len(formatted_prompt)}")
                reply = self.llm_client.generate(formatted_prompt)
                print(f"AGENT [{self.name}] - LLM Response: {reply}")
            elif self.agent.llm_config is False:
                # Mock reply for llm_config: False, always choose lowest price (action 0)
                reply_content = {"action": 0} 
                reply = json.dumps(reply_content) # Simulate the string reply format
                print(f"AGENT [{self.name}] - Using mock response")
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
            
            # Handle case where action might be just an integer
            if isinstance(action_dict, dict) and 'action' in action_dict:
                return action_dict['action']
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

    def act(self, observation: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Any:
        return asyncio.run(self.act_async(observation, info))