
"""Synchronous pub/sub event bus used by referees & governor."""
from typing import Callable, Any, Dict, List
_subs: Dict[str, List[Callable[[str, Any], None]]] = {}
def subscribe(event_type: str, handler: Callable[[str, Any], None]) -> None:
    _subs.setdefault(event_type, []).append(handler)
def publish(event_type: str, payload: Any) -> None:
    for h in _subs.get(event_type, []):
        h(event_type, payload)
