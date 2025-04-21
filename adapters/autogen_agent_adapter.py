
"""Adapter: wraps an AutoGen Agent (or GroupChat) so orchestrator can call .act()"""
from __future__ import annotations
import asyncio, json, uuid
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
        prompt = json.dumps({"observation": observation, "info": info})
        # some versions of AutoGen provide async chat; fallback to sync
        if asyncio.iscoroutinefunction(self.agent.chat):
            reply = await self.agent.chat(prompt)
        else:
            loop = asyncio.get_running_loop()
            reply = await loop.run_in_executor(None, self.agent.chat, prompt)
        content = str(reply).splitlines()[0]
        return json.loads(content)

    def act(self, observation: Dict[str, Any], info: Optional[Dict[str, Any]] = None) -> Any:
        return asyncio.run(self.act_async(observation, info))
