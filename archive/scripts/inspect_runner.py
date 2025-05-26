import asyncio
import yaml
import inspect_ai
from inspect_ai.solver import solver
from inspect_ai.dataset._dataset import MemoryDataset, Sample
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.core import Orchestrator

@solver
def run_env():
    async def solve(state, generate):
        seed = int(state.input_text)
        config_path = state.metadata.get("config")
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        orch = Orchestrator(cfg)
        result = await asyncio.to_thread(orch.run_seed, seed)
        state.metadata["result"] = result
        state.completed = True
        return state
    return solve

def run(config_path, seeds):
    samples = [Sample(input=str(s), metadata={"config": config_path}) for s in seeds]
    dataset = MemoryDataset(samples=samples, name="seeds")
    task = inspect_ai.Task(dataset=dataset, solver=run_env(), name="orchestrator_run")
    evaluation, logs = inspect_ai.eval_set([task], log_dir="inspect_logs", display=None)
    totals = [sample.metadata.get("result") for sample in dataset]
    cumulative = {}
    for t in totals:
        if t:
            for k, v in t.items():
                cumulative[k] = cumulative.get(k, 0.0) + v
    print("Totals per seed:", totals)
    print("Cumulative totals:", cumulative)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--config")
    p.add_argument("--seeds", default="0-1")
    args = p.parse_args()
    if "-" in args.seeds:
        lo, hi = map(int, args.seeds.split("-"))
        seed_list = range(lo, hi + 1)
    else:
        seed_list = [int(s) for s in args.seeds.split(",") if s]
    run(args.config, seed_list)