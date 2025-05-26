# Repository Cleanup Plan

## Current Issues
1. **Too many config files** (18 configs) - unclear which to use when
2. **Too many scripts** (11 scripts) - redundant functionality
3. **Mock/dummy code** making it complicated - need real LLM integration only
4. **AutoGen version** - need to ensure 0.9.1 compatibility
5. **No clear usage documentation** - users don't know where to start

## Cleanup Strategy

### Phase 1: Config Consolidation
**Goal**: Reduce from 18 configs to 3-4 essential ones

#### Configs to KEEP:
1. `config/example_basic.yaml` - Simple single-agent demo with LLM
2. `config/example_communication.yaml` - Agent communication demo
3. `config/example_collusion_study.yaml` - Research-focused collusion detection
4. `config/test_minimal.yaml` - For automated testing only

#### Configs to REMOVE:
- All `demo_*.yaml` files (too many variations)
- All mock/mixed strategy configs
- All provider-specific configs (ollama, openai specific)

### Phase 2: Script Consolidation
**Goal**: Reduce from 11 scripts to 4-5 essential ones

#### Scripts to KEEP:
1. `scripts/run.py` - Main entry point (rename from run_once.py)
2. `scripts/analyze.py` - Unified analysis tool
3. `scripts/stream_ui.py` - Web UI (already clean)
4. `scripts/test_llm_connection.py` - Simple LLM connectivity test

#### Scripts to REMOVE:
- `check_ollama.py`, `test_llm_direct.py`, `test_single_llm_agent.py` (redundant)
- `debug_llm_agent.py` (debugging only)
- `run_parallel_demo.py` (functionality in main run.py)
- `analyze_collusion.py`, `analyze_communication.py`, `visualize_communication.py` (merge into analyze.py)
- `inspect_runner.py` (unclear purpose)

### Phase 3: Code Simplification
**Goal**: Remove all mock/dummy code, focus on real LLM integration

#### Changes needed:
1. **Remove mock provider** from `llm_client.py`
2. **Remove mock_behavior** from agents
3. **Remove mock_responses** from configs
4. **Simplify CommunicatingAgentAdapter** - remove complex strategies
5. **Update to AutoGen 0.9.1** in pyproject.toml

### Phase 4: Documentation Update
**Goal**: Clear usage guide

Create `docs/USAGE.md` with:
1. **Quick Start** - How to run your first experiment
2. **Configuration Guide** - When to use which config
3. **LLM Setup** - How to configure Ollama/OpenAI/Anthropic
4. **Analysis Guide** - How to analyze results

### Phase 5: Directory Structure
Final structure:
```
hierachical_safety_governor/
├── configs/
│   ├── example_basic.yaml
│   ├── example_communication.yaml
│   ├── example_collusion_study.yaml
│   └── test_minimal.yaml
├── scripts/
│   ├── run.py
│   ├── analyze.py
│   ├── stream_ui.py
│   └── test_llm_connection.py
├── src/safety_governor/
│   └── [keep existing structure]
├── docs/
│   ├── README.md
│   ├── USAGE.md
│   └── [other docs]
└── tests/
    └── [keep existing]
```

## Implementation Order
1. Update AutoGen to 0.9.1
2. Remove mock/dummy code from source
3. Consolidate scripts
4. Clean up configs
5. Update documentation
6. Test everything works with real LLMs