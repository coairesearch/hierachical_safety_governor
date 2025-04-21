
from .price_game_env import PriceGameEnv
_REGISTRY = {"PriceGame-v0": PriceGameEnv}
def get_env_cls(name: str):
    return _REGISTRY[name]
