#!/usr/bin/env python
"""Integration tests for the orchestrator module."""

import os
import sys
import pytest
import tempfile
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator, load


class TestLoad:
    """Test the dynamic loading function."""
    
    def test_load_valid_module(self):
        """Test loading a valid module and class."""
        cls = load("adapters.autogen_agent_adapter:AutoGenAgentAdapter")
        assert cls.__name__ == "AutoGenAgentAdapter"
    
    def test_load_invalid_format(self):
        """Test loading with invalid format (no colon)."""
        with pytest.raises(ValueError, match="Invalid path format"):
            load("invalid.path")
    
    def test_load_missing_module(self):
        """Test loading a non-existent module."""
        with pytest.raises(ImportError):
            load("nonexistent.module:Class")
    
    def test_load_missing_class(self):
        """Test loading a non-existent class from valid module."""
        with pytest.raises(AttributeError):
            load("orchestrator:NonExistentClass")


class TestOrchestrator:
    """Test the Orchestrator class."""
    
    @pytest.fixture
    def valid_config(self):
        """Create a valid test configuration."""
        return {
            'base_env': 'PriceGame-v0',
            'seeds': [42],
            'agents': [
                {
                    'id': 'firm_a',
                    'impl': 'adapters.autogen_agent_adapter:AutoGenAgentAdapter',
                    'params': {
                        'autogen_agent': {
                            '_factory': 'autogen.ConversableAgent',
                            'name': 'FirmA',
                            'llm_config': False
                        }
                    }
                },
                {
                    'id': 'firm_b',
                    'impl': 'adapters.autogen_agent_adapter:AutoGenAgentAdapter',
                    'params': {
                        'autogen_agent': {
                            '_factory': 'autogen.ConversableAgent',
                            'name': 'FirmB',
                            'llm_config': False
                        }
                    }
                }
            ],
            'defenses': []
        }
    
    def test_init(self, valid_config):
        """Test orchestrator initialization."""
        orch = Orchestrator(valid_config)
        assert orch.cfg == valid_config
        assert orch.shutdown_requested is False
    
    def test_build_components(self, valid_config):
        """Test building components from specs."""
        orch = Orchestrator(valid_config)
        
        # Test building defenses (empty)
        defenses = orch._build('defenses')
        assert defenses == {}
        
        # Test with invalid component spec
        valid_config['defenses'] = [{'invalid': 'spec'}]
        defenses = orch._build('defenses')
        assert defenses == {}
    
    def test_make_agents_success(self, valid_config):
        """Test successful agent creation."""
        orch = Orchestrator(valid_config)
        agents = orch._make_agents()
        assert 'firm_a' in agents
        assert 'firm_b' in agents
        assert agents['firm_a'].__class__.__name__ == 'AutoGenAgentAdapter'
        assert agents['firm_b'].__class__.__name__ == 'AutoGenAgentAdapter'
    
    def test_make_agents_missing_config(self):
        """Test agent creation with missing agents config."""
        config = {'base_env': 'PriceGame-v0', 'seeds': [42]}
        orch = Orchestrator(config)
        agents = orch._make_agents()
        assert agents == {}
    
    def test_run_seed_single(self, valid_config):
        """Test running a single seed simulation."""
        orch = Orchestrator(valid_config)
        result = orch.run_seed(42)
        assert isinstance(result, dict)
        assert 'firm_a' in result
        assert 'firm_b' in result
        assert isinstance(result['firm_a'], (int, float))
        assert isinstance(result['firm_b'], (int, float))
    
    def test_run_seed_invalid_env(self):
        """Test running with invalid environment."""
        config = {
            'base_env': 'InvalidEnv',
            'seeds': [42],
            'agents': []
        }
        orch = Orchestrator(config)
        with pytest.raises(KeyError):
            orch.run_seed(42)
    
    def test_run_with_seed_range(self, valid_config):
        """Test running with seed range."""
        valid_config['seeds'] = '0-2'
        orch = Orchestrator(valid_config)
        results = orch.run()
        assert len(results) == 3
    
    def test_run_with_single_seed(self, valid_config):
        """Test running with single seed."""
        valid_config['seeds'] = 42
        orch = Orchestrator(valid_config)
        results = orch.run()
        assert len(results) == 1
    
    def test_run_with_seed_list(self, valid_config):
        """Test running with seed list."""
        valid_config['seeds'] = [1, 2, 3]
        orch = Orchestrator(valid_config)
        results = orch.run()
        assert len(results) == 3
    
    def test_run_missing_seeds(self, valid_config):
        """Test running without seeds config."""
        del valid_config['seeds']
        orch = Orchestrator(valid_config)
        with pytest.raises(ValueError, match="Missing 'seeds'"):
            orch.run()
    
    def test_graceful_shutdown(self, valid_config):
        """Test graceful shutdown handling."""
        import signal
        orch = Orchestrator(valid_config)
        
        # Simulate SIGINT
        orch._handle_shutdown(signal.SIGINT, None)
        assert orch.shutdown_requested is True
        
        # Run should stop early
        valid_config['seeds'] = '0-10'
        results = orch.run()
        assert len(results) == 0  # Should stop immediately


class TestErrorScenarios:
    """Test various error scenarios."""
    
    def test_missing_config_file(self):
        """Test with non-existent config file."""
        from orchestrator import main
        with pytest.raises(SystemExit):
            main("nonexistent.yaml")
    
    def test_invalid_yaml(self):
        """Test with invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            from orchestrator import main
            with pytest.raises(SystemExit):
                main(f.name)
            
            os.unlink(f.name)
    
    def test_empty_config(self):
        """Test with empty config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            f.flush()
            
            from orchestrator import main
            with pytest.raises(SystemExit):
                main(f.name)
            
            os.unlink(f.name)
    
    def test_agent_creation_failure(self):
        """Test agent creation with invalid implementation."""
        config = {
            'base_env': 'PriceGame-v0',
            'seeds': [42],
            'agents': [
                {
                    'id': 'bad_agent',
                    'impl': 'invalid.module:BadClass',
                    'params': {}
                }
            ],
            'fail_fast': True
        }
        orch = Orchestrator(config)
        with pytest.raises(ImportError):
            orch._make_agents()
    
    def test_defense_creation_failure(self):
        """Test defense creation with invalid parameters."""
        config = {
            'base_env': 'PriceGame-v0',
            'seeds': [42],
            'agents': [
                {
                    'id': 'firm_a',
                    'impl': 'adapters.autogen_agent_adapter:AutoGenAgentAdapter',
                    'params': {
                        'autogen_agent': {
                            '_factory': 'autogen.ConversableAgent',
                            'name': 'FirmA',
                            'llm_config': False
                        }
                    }
                },
                {
                    'id': 'firm_b',
                    'impl': 'adapters.autogen_agent_adapter:AutoGenAgentAdapter',
                    'params': {
                        'autogen_agent': {
                            '_factory': 'autogen.ConversableAgent',
                            'name': 'FirmB',
                            'llm_config': False
                        }
                    }
                }
            ],
            'defenses': [
                {
                    'id': 'bad_defense',
                    'impl': 'defenses.hierarchical_governor:HierarchicalGovernor',
                    'params': {'invalid_param': 123}
                }
            ],
            'fail_fast': True
        }
        orch = Orchestrator(config)
        with pytest.raises(TypeError):
            orch.run_seed(42)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])