#!/usr/bin/env python
"""Runner script for parallel communication demo."""

import argparse
import logging
import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.core import ParallelOrchestrator

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run parallel communication experiments")
    parser.add_argument("--config", default="configs/demo_parallel_communication.yaml",
                        help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set logging level")
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Loading configuration from {args.config}")
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
            
        if not cfg:
            raise ValueError("Configuration file is empty")
            
        # Use ParallelOrchestrator
        orchestrator = ParallelOrchestrator(cfg)
        results = orchestrator.run()
        
        # Print results
        logger.info("Experiment completed successfully")
        for i, result in enumerate(results):
            logger.info(f"Seed {i}: {result}")
            
        # Print communication statistics
        comm_stats = orchestrator.get_communication_stats()
        logger.info(f"Communication statistics: {comm_stats}")
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)