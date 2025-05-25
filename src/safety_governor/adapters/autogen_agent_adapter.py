
"""Adapter: wraps an AutoGen Agent (or GroupChat) so orchestrator can call .act()"""
from __future__ import annotations
import asyncio, json, uuid, copy
# import logging # Not needed as per instruction to use print()
from typing import Any, Dict, Optional, Union
import autogen  # type: ignore

class AutoGenAgentAdapter:
    def __init__(self, autogen_agent: Union[autogen.Agent, autogen.GroupChat],
                 name: Optional[str] = None, system_prompt: Optional[str] = None):
        self.agent = autogen_agent
        self.name = name or f"agent_{uuid.uuid4().hex[:6]}"
        if system_prompt:
            self.agent.send(system_prompt, recipient=self.agent, request_reply=False)

    async def act_async(self, observation: Dict[str, Any],
                        info: Optional[Dict[str, Any]] = None) -> Any:
        original_info_for_logging = info.copy() if info is not None else None
        if info is None:
            info = {}
        info["predicted_opponent_price"] = "low"

        print(f"AGENT [{self.name}] - Observation: {observation}")
        print(f"AGENT [{self.name}] - Original Info: {original_info_for_logging}")
        print(f"AGENT [{self.name}] - Manipulated Info: {info}")

        # Convert numpy arrays in observation to lists for JSON serialization
        observation_for_json = copy.deepcopy(observation)
        if 'last_prices' in observation_for_json and hasattr(observation_for_json['last_prices'], 'tolist'):
            observation_for_json['last_prices'] = observation_for_json['last_prices'].tolist()

        prompt = json.dumps({"observation": observation_for_json, "info": info})
        # print(f"AGENT {self.name} Prompt: {prompt}") # Commenting out as not specified in new reqs

        if self.agent.llm_config is False:
            # Mock reply for llm_config: False, always choose lowest price (action 0)
            reply_content = {"action": 0} 
            reply = json.dumps(reply_content) # Simulate the string reply format
        else:
            # some versions of AutoGen provide async chat; fallback to sync
            if asyncio.iscoroutinefunction(self.agent.chat):
                reply = await self.agent.chat(prompt)
            else:
                loop = asyncio.get_running_loop()
                reply = await loop.run_in_executor(None, self.agent.chat, prompt)
        
        content = str(reply).splitlines()[0] # Assumes reply is a string, potentially multi-line
        action_dict = json.loads(content) # Renamed to avoid confusion

        print(f"AGENT [{self.name}] - Chosen Action: {action_dict}") # Log the full dict
        
        return action_dict['action'] # Return the integer action

    def act(self, observation: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Any:
        return asyncio.run(self.act_async(observation, info))
