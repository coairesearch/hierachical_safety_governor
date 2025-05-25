import yaml
import streamlit as st
from orchestrator import Orchestrator

st.set_page_config(page_title="Safety-Governor Demo", layout="wide")
st.title("Hierarchical Safety-Governor Demo")

cfg_path = st.sidebar.text_input("Config file", "configs/demo.yaml")
run_btn = st.sidebar.button("Run Simulation")

if run_btn:
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    orch = Orchestrator(cfg)
    seeds = cfg["seeds"]
    if isinstance(seeds, str) and '-' in seeds:
        lo, hi = map(int, seeds.split('-'))
        seeds_list = list(range(lo, hi + 1))
    elif isinstance(seeds, (list, range)):
        seeds_list = list(seeds)
    else:
        seeds_list = [int(seeds)]
    for seed in seeds_list:
        st.header(f"Seed {seed}")
        chart_placeholder = st.empty()
        table_placeholder = st.empty()
        progress = st.progress(0.0)
        chart_data = []
        table_rows = []
        max_steps = None
        for info in orch.run_seed_stream(seed):
            if info["type"] == "reset":
                st.write(f"Initial observation: {info['observation']}")
                max_steps = info.get("max_steps")
            elif info["type"] == "step":
                table_rows.append({"step": info["step"],
                                   "actions": str(info["actions"]),
                                   "reward": info["reward"]})
                chart_data.append({"step": info["step"], **info["total"]})
                table_placeholder.table(table_rows)
                chart_placeholder.line_chart(chart_data, x="step")
                if max_steps:
                    progress.progress(min(info["step"] / max_steps, 1.0))
            elif info["type"] == "summary":
                st.success(f"Total reward: {info['total']}")
        progress.empty()

