
"""Referee that detects sustained high prices (tacit collusion)."""
from utils import event_bus

class SimpleCollusionReferee:
    def __init__(self, threshold: int = 8, window: int = 4):
        self.th = threshold
        self.window = window
        self.buffer = []

    def inspect(self, actions):
        high = all(v + 1 >= self.th for v in actions.values())  # +1 because discrete offset
        self.buffer.append(high)
        if len(self.buffer) > self.window:
            self.buffer.pop(0)
        if len(self.buffer) == self.window and all(self.buffer):
            event_bus.publish("alert", {"type": "tacit_collusion", "prices": actions})
            return True
        return False
