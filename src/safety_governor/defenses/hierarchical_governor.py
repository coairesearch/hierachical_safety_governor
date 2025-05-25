
"""Governor that resets environment on first alert."""
from ..utils import event_bus

class HierarchicalGovernor:
    def __init__(self):
        self.alert_flag = False
        event_bus.subscribe("alert", self._on_alert)

    def _on_alert(self, event_type, payload):
        print("[Governor] ALERT:", payload)
        self.alert_flag = True

    def intervene(self, env):
        if self.alert_flag:
            print("[Governor] Intervening – resetting environment")
            env.reset()
            self.alert_flag = False
