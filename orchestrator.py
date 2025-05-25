
import importlib
import random
import yaml
import copy
import logging
import sys
import signal
from typing import Dict, Any, List, Optional, Generator
from environments import get_env_cls

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

def load(path: str):
    """Dynamically load a class from module path."""
    try:
        if ':' not in path:
            raise ValueError(f"Invalid path format: {path}. Expected 'module:class'")
        mod, obj = path.split(":")
        module = importlib.import_module(mod)
        return getattr(module, obj)
    except ImportError as e:
        logger.error(f"Failed to import module from path '{path}': {e}")
        raise
    except AttributeError as e:
        logger.error(f"Module '{mod}' has no attribute '{obj}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading '{path}': {e}")
        raise

class Orchestrator:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.shutdown_requested = False
        logger.info("Orchestrator initialized with config")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

    def _build(self, specs: str) -> Dict[str, Any]:
        """Build components from specifications."""
        components = {}
        for spec in self.cfg.get(specs, []):
            try:
                if 'id' not in spec:
                    logger.error(f"Missing 'id' in {specs} specification: {spec}")
                    continue
                if 'impl' not in spec:
                    logger.error(f"Missing 'impl' in {specs} specification: {spec}")
                    continue
                    
                comp_id = spec['id']
                impl_path = spec['impl']
                params = spec.get('params', {})
                
                logger.debug(f"Building {specs} component '{comp_id}' from '{impl_path}'")
                components[comp_id] = load(impl_path)(**params)
                logger.info(f"Successfully built {specs} component '{comp_id}'")
            except Exception as e:
                logger.error(f"Failed to build {specs} component '{spec.get('id', 'unknown')}': {e}")
                if self.cfg.get('fail_fast', True):
                    raise
        return components

    def _make_agents(self) -> Dict[str, Any]:
        """Create agent instances from configuration."""
        agents = {}
        
        if 'agents' not in self.cfg:
            logger.error("No 'agents' section found in configuration")
            return agents
            
        for spec_orig in self.cfg['agents']:
            try:
                spec = copy.deepcopy(spec_orig)
                
                if 'id' not in spec:
                    logger.error(f"Missing 'id' in agent specification: {spec}")
                    continue
                if 'impl' not in spec:
                    logger.error(f"Missing 'impl' in agent specification: {spec}")
                    continue
                    
                agent_id = spec['id']
                logger.debug(f"Creating agent '{agent_id}'")
                
                cls = load(spec['impl'])
                params = spec.get('params', {})
                
                # Handle autogen factory shortcut
                if 'autogen_agent' in params:
                    try:
                        ag_cfg = params.pop('autogen_agent')
                        if '_factory' not in ag_cfg:
                            logger.error(f"Missing '_factory' in autogen_agent config for agent '{agent_id}'")
                            continue
                            
                        factory_path = ag_cfg.pop('_factory')
                        factory_mod, factory_cls = factory_path.rsplit('.', 1)
                        factory = getattr(importlib.import_module(factory_mod), factory_cls)
                        params['autogen_agent'] = factory(**ag_cfg)
                    except Exception as e:
                        logger.error(f"Failed to create autogen agent for '{agent_id}': {e}")
                        if self.cfg.get('fail_fast', True):
                            raise
                        continue
                
                agents[agent_id] = cls(**params)
                logger.info(f"Successfully created agent '{agent_id}'")
            except Exception as e:
                logger.error(f"Failed to create agent '{spec.get('id', 'unknown')}': {e}")
                if self.cfg.get('fail_fast', True):
                    raise
                    
        return agents

    def run_seed(self, seed: int) -> Dict[str, float]:
        """Run a single simulation with the given seed."""
        logger.info(f"Starting simulation with seed {seed}")
        
        try:
            random.seed(seed)
            
            # Create environment
            if 'base_env' not in self.cfg:
                raise ValueError("Missing 'base_env' in configuration")
            env = get_env_cls(self.cfg['base_env'])()
            
            # Create agents and defenses
            agents = self._make_agents()
            if not agents:
                raise ValueError("No agents were successfully created")
                
            defenses = self._build('defenses')
            
            # Initialize environment
            obs, _ = env.reset(seed=seed)
            total = {k: 0.0 for k in agents}
            step_count = 0
            max_steps = getattr(env, 'max_steps', 10000)  # Prevent infinite loops
            
            while not self.shutdown_requested and step_count < max_steps:
                # Collect actions from agents
                acts = {}
                for aid, ag in agents.items():
                    try:
                        acts[aid] = ag.act(obs)
                    except Exception as e:
                        logger.error(f"Agent '{aid}' failed to act: {e}")
                        if self.cfg.get('fail_fast', True):
                            raise
                        # Use a default action if agent fails
                        acts[aid] = {'action': 0}
                
                # Step environment
                try:
                    obs, rew, done, _, _ = env.step(acts)
                except Exception as e:
                    logger.error(f"Environment step failed: {e}")
                    raise
                    
                # Update rewards
                for k in total:
                    total[k] += rew[k]
                    
                # Apply defenses
                for def_id, ref in defenses.items():
                    try:
                        if hasattr(ref, 'inspect'):
                            ref.inspect(acts)
                        if hasattr(ref, 'intervene'):
                            ref.intervene(env)
                    except Exception as e:
                        logger.error(f"Defense '{def_id}' failed: {e}")
                        if self.cfg.get('fail_fast', True):
                            raise
                            
                step_count += 1
                if done:
                    break
                    
            if self.shutdown_requested:
                logger.info(f"Simulation interrupted at step {step_count}")
            elif step_count >= max_steps:
                logger.warning(f"Simulation reached max steps ({max_steps})")
                
            logger.info(f"seed {seed} -> {total}")
            return total
            
        except Exception as e:
            logger.error(f"Simulation failed for seed {seed}: {e}")
            raise

    def run_seed_stream(self, seed: int) -> Generator[Dict[str, Any], None, None]:
        """Yield detailed info for each step of a simulation run.

        The generator yields dictionaries with the following ``type`` values:

        - ``reset``: emitted before the first step. Contains ``observation`` and
          ``max_steps`` (if available).
        - ``step``: emitted after every environment step with ``actions``,
          ``reward`` and cumulative ``total`` rewards.
        - ``summary``: emitted once the environment reaches ``done``.
        """
        logger.info(f"Starting stream simulation with seed {seed}")
        
        try:
            random.seed(seed)
            
            # Create environment
            if 'base_env' not in self.cfg:
                raise ValueError("Missing 'base_env' in configuration")
            env = get_env_cls(self.cfg['base_env'])()
            
            # Create agents and defenses
            agents = self._make_agents()
            if not agents:
                raise ValueError("No agents were successfully created")
                
            defenses = self._build('defenses')
            
            # Initialize environment
            obs, _ = env.reset(seed=seed)
            total = {k: 0.0 for k in agents}
            step_count = 0
            max_steps = getattr(env, 'max_steps', 10000)
            
            yield {
                'type': 'reset',
                'step': step_count,
                'observation': obs.copy(),
                'total': total.copy(),
                'max_steps': max_steps
            }
            
            while not self.shutdown_requested and step_count < max_steps:
                # Collect actions from agents
                acts = {}
                for aid, ag in agents.items():
                    try:
                        acts[aid] = ag.act(obs)
                    except Exception as e:
                        logger.error(f"Agent '{aid}' failed to act: {e}")
                        if self.cfg.get('fail_fast', True):
                            raise
                        acts[aid] = {'action': 0}
                
                # Step environment
                try:
                    obs, rew, done, _, _ = env.step(acts)
                except Exception as e:
                    logger.error(f"Environment step failed: {e}")
                    raise
                    
                # Update rewards
                for k in total:
                    total[k] += rew[k]
                    
                # Apply defenses
                for def_id, ref in defenses.items():
                    try:
                        if hasattr(ref, 'inspect'):
                            ref.inspect(acts)
                        if hasattr(ref, 'intervene'):
                            ref.intervene(env)
                    except Exception as e:
                        logger.error(f"Defense '{def_id}' failed: {e}")
                        if self.cfg.get('fail_fast', True):
                            raise
                            
                step_count += 1
                
                yield {
                    'type': 'step',
                    'step': step_count,
                    'actions': acts,
                    'reward': rew,
                    'observation': obs.copy(),
                    'total': total.copy()
                }
                
                if done:
                    break
                    
            if self.shutdown_requested:
                logger.info(f"Stream simulation interrupted at step {step_count}")
            elif step_count >= max_steps:
                logger.warning(f"Stream simulation reached max steps ({max_steps})")
                
            yield {
                'type': 'summary',
                'step': step_count,
                'total': total.copy()
            }
            
        except Exception as e:
            logger.error(f"Stream simulation failed for seed {seed}: {e}")
            raise

    def run(self) -> List[Dict[str, float]]:
        """Run simulations for all configured seeds."""
        if 'seeds' not in self.cfg:
            raise ValueError("Missing 'seeds' in configuration")
            
        seeds = self.cfg['seeds']
        
        # Handle seed range specification
        if isinstance(seeds, str) and '-' in seeds:
            try:
                lo, hi = map(int, seeds.split('-'))
                seeds = range(lo, hi + 1)
            except ValueError as e:
                logger.error(f"Invalid seed range format '{seeds}': {e}")
                raise
        elif isinstance(seeds, (int, str)):
            seeds = [seeds]
        elif not isinstance(seeds, list):
            raise ValueError(f"Invalid seeds format: {type(seeds)}")
            
        results = []
        for s in seeds:
            if self.shutdown_requested:
                logger.info("Shutdown requested, stopping simulations")
                break
            try:
                result = self.run_seed(int(s))
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run seed {s}: {e}")
                if self.cfg.get('fail_fast', True):
                    raise
                    
        return results

def main(path: str):
    """Main entry point for running orchestrator."""
    try:
        logger.info(f"Loading configuration from {path}")
        with open(path) as f:
            cfg = yaml.safe_load(f)
            
        if not cfg:
            raise ValueError("Configuration file is empty")
            
        orchestrator = Orchestrator(cfg)
        orchestrator.run()
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run hierarchical safety governor experiments")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set logging level")
    args = parser.parse_args()
    
    # Update logging level if specified
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    main(args.config)
