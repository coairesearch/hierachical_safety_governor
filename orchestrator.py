
import importlib, random, yaml, copy # Import copy
from environments import get_env_cls

def load(path: str):
    mod, obj = path.split(":")
    return getattr(importlib.import_module(mod), obj)

class Orchestrator:
    def __init__(self, cfg): self.cfg = cfg

    def _build(self, specs):
        return {s['id']: load(s['impl'])(**s.get('params', {})) for s in self.cfg.get(specs, [])}

    def _make_agents(self):
        agents = {}
        for spec_orig in self.cfg['agents']:
            spec = copy.deepcopy(spec_orig) # Deepcopy the agent spec
            cls = load(spec['impl'])
            params = spec.get('params', {}) 
            # Handle autogen factory shortcut
            if 'autogen_agent' in params: # params is already a deep copy from spec
                ag_cfg = params.pop('autogen_agent') # ag_cfg is now a copy from the deepcopied params
                factory_path = ag_cfg.pop('_factory') # This modifies the copied ag_cfg, not original
                factory_mod, factory_cls = factory_path.rsplit('.', 1)
                factory = getattr(importlib.import_module(factory_mod), factory_cls)
                # The factory receives the copied and modified ag_cfg.
                # The result is stored in the copied params dict.
                params['autogen_agent'] = factory(**ag_cfg) 
            agents[spec['id']] = cls(**params)
        return agents

    def run_seed(self, seed: int):
        random.seed(seed)
        env = get_env_cls(self.cfg['base_env'])()
        agents = self._make_agents()
        defenses = {d['id']: load(d['impl'])(**d.get('params', {}))
                    for d in self.cfg.get('defenses', [])}
        obs, _ = env.reset(seed=seed)
        total = {k: 0.0 for k in agents}
        while True:
            acts = {aid: ag.act(obs) for aid, ag in agents.items()}
            obs, rew, done, _, _ = env.step(acts)
            for k in total: total[k] += rew[k]
            for ref in defenses.values():
                if hasattr(ref, 'inspect'): ref.inspect(acts)
                if hasattr(ref, 'intervene'): ref.intervene(env)
            if done: break
        print(f"seed {seed} -> {total}")
        return total

    def run(self):
        seeds = self.cfg['seeds']
        if isinstance(seeds, str) and '-' in seeds:
            lo, hi = map(int, seeds.split('-'))
            seeds = range(lo, hi + 1)
        return [self.run_seed(int(s)) for s in seeds]

def main(path):
    with open(path) as f: cfg = yaml.safe_load(f)
    Orchestrator(cfg).run()

if __name__ == "__main__":
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--config"); a = p.parse_args(); main(a.config)
