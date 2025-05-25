"""Hierarchical Safety Governor - A research framework for AI safety in multi-agent systems."""

__version__ = "0.1.0"

# Import main components for easier access
from .core.orchestrator import Orchestrator
from .utils.event_bus import publish, subscribe

__all__ = [
    "Orchestrator",
    "publish",
    "subscribe",
]