#!/usr/bin/env python
"""Analyze and visualize agent communication patterns."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.core import ParallelOrchestrator
import yaml

def analyze_communication_demo(config_path):
    """Run demo and analyze communication patterns."""
    
    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Run just 1 seed with detailed analysis
    config['seeds'] = '0'
    config['max_steps'] = 3  # Short run
    
    # Create orchestrator
    orchestrator = ParallelOrchestrator(config)
    
    print("=" * 80)
    print("COMMUNICATION ANALYSIS")
    print("=" * 80)
    
    # Run the experiment
    results = orchestrator.run()
    
    # Get communication history
    messages = orchestrator.comm_manager.get_message_history()
    
    print(f"\nTotal messages exchanged: {len(messages)}")
    print("-" * 80)
    
    # Analyze each message
    for i, msg in enumerate(reversed(messages)):  # Show in chronological order
        print(f"\nMessage {i+1}:")
        print(f"  From: {msg.sender}")
        print(f"  To: {msg.recipients}")
        print(f"  Type: {msg.message_type.value}")
        
        # Determine if it's broadcast or direct
        if msg.message_type.value == "broadcast":
            print(f"  → This is a BROADCAST to all agents")
        elif len(msg.recipients) == 1:
            print(f"  → This is a PRIVATE message to {msg.recipients[0]}")
        else:
            print(f"  → This is a GROUP message to {len(msg.recipients)} agents")
            
        print(f"  Content: {msg.content}")
        print(f"  Strategy: {msg.metadata.get('strategy', 'unknown')}")
    
    # Summary statistics
    stats = orchestrator.get_communication_stats()
    print("\n" + "=" * 80)
    print("COMMUNICATION STATISTICS:")
    print("=" * 80)
    print(f"Broadcast messages: {stats['broadcast_count']}")
    print(f"Private messages: {stats['private_count']}")
    print(f"Group messages: {stats['group_count']}")
    
    # Show who talked to whom
    print("\n" + "=" * 80)
    print("COMMUNICATION MATRIX:")
    print("=" * 80)
    
    # Build communication matrix
    comm_matrix = {}
    for msg in messages:
        sender = msg.sender
        for recipient in msg.recipients:
            key = f"{sender} → {recipient}"
            comm_matrix[key] = comm_matrix.get(key, 0) + 1
    
    for connection, count in comm_matrix.items():
        print(f"{connection}: {count} messages")
    
    return messages

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/demo_parallel_communication_llm.yaml")
    args = parser.parse_args()
    
    analyze_communication_demo(args.config)