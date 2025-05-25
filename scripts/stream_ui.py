import yaml
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.core import Orchestrator

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
        st.subheader(f"Seed: {seed}")
        st.write("Starting simulation...")
        
        # Create columns for displaying real-time results
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Agent Actions**")
            actions_placeholder = st.empty()
        with col2:
            st.write("**Total Rewards**")
            rewards_placeholder = st.empty()
        
        # Stream the simulation
        for event in orch.run_seed_stream(seed):
            if event['type'] == 'step':
                actions_placeholder.write(event['actions'])
                rewards_placeholder.write(event['total'])
            elif event['type'] == 'summary':
                st.success(f"Final rewards: {event['total']}")
                
st.sidebar.markdown("---")
st.sidebar.markdown("**About**")
st.sidebar.info(
    "This demo shows the Hierarchical Safety-Governor in action, "
    "monitoring and intervening in multi-agent interactions."
)