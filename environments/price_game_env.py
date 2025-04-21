
"""Two-firm price competition toy environment."""
import gymnasium as gym
from gymnasium import spaces
import numpy as np

class PriceGameEnv(gym.Env):
    metadata = {}

    def __init__(self, max_steps: int = 40, price_low: int = 1, price_high: int = 10):
        super().__init__()
        self.price_low = price_low
        self.price_high = price_high
        self.action_space = spaces.Dict({
            "firm_a": spaces.Discrete(price_high - price_low + 1),
            "firm_b": spaces.Discrete(price_high - price_low + 1),
        })
        self.observation_space = spaces.Dict({
            "last_prices": spaces.Box(price_low, price_high, shape=(2,), dtype=np.int32)
        })
        self.max_steps = max_steps
        self.reset()

    def demand(self, average_price: float) -> float:
        return max(0.0, 10.0 - average_price)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.t = 0
        self.state = {"last_prices": np.array([self.price_low, self.price_low], dtype=np.int32)}
        return self.state.copy(), {}

    def step(self, actions):
        prices = np.array([
            actions["firm_a"] + self.price_low,
            actions["firm_b"] + self.price_low], dtype=np.int32)
        self.state["last_prices"] = prices
        d = self.demand(float(prices.mean()))
        rev = prices * d
        reward = {"firm_a": float(rev[0]), "firm_b": float(rev[1])}
        self.t += 1
        terminated = self.t >= self.max_steps
        return self.state.copy(), reward, terminated, False, {}
