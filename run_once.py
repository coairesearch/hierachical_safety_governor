#!/usr/bin/env python
"""Simple runner script for the orchestrator."""

import argparse
import logging
import orchestrator

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run hierarchical safety governor experiments")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument("--log-level", default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set logging level")
    args = parser.parse_args()
    
    # Update logging level if specified
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    orchestrator.main(args.config)