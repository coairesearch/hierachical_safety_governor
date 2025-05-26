#!/usr/bin/env python
"""Visualize communication patterns with clear distinctions."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_governor.core import ParallelOrchestrator
from safety_governor.utils import MessageType
import yaml
from datetime import datetime

def visualize_communication(config_path):
    """Run demo and visualize communication patterns."""
    
    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Configure for clear visualization
    config['seeds'] = '0'
    config['max_steps'] = 2
    
    # Create orchestrator
    orchestrator = ParallelOrchestrator(config)
    
    print("\n" + "="*80)
    print("🔊 AGENT COMMUNICATION VISUALIZATION")
    print("="*80)
    
    # Subscribe to communication events
    messages_log = []
    
    def log_message(event_type, payload):
        if event_type == "message_sent":
            messages_log.append(payload)
    
    from safety_governor.utils import event_bus
    event_bus.subscribe("message_sent", log_message)
    
    # Run the experiment
    print("\n📊 Running experiment...")
    results = orchestrator.run()
    
    # Get detailed message history
    all_messages = orchestrator.comm_manager.get_message_history()
    
    print(f"\n📨 Total messages: {len(all_messages)}")
    print("-"*80)
    
    # Group messages by type
    broadcasts = []
    private_messages = []
    group_messages = []
    
    for msg in reversed(all_messages):  # Chronological order
        if msg.message_type == MessageType.BROADCAST:
            broadcasts.append(msg)
        elif len(msg.recipients) == 1:
            private_messages.append(msg)
        else:
            group_messages.append(msg)
    
    # Display broadcasts
    if broadcasts:
        print("\n📢 BROADCAST MESSAGES (sent to all agents):")
        print("-"*50)
        for i, msg in enumerate(broadcasts):
            print(f"\nBroadcast #{i+1}:")
            print(f"  🗣️  {msg.sender} → ALL AGENTS")
            print(f"  📄 Content: {msg.content}")
            print(f"  🏷️  Strategy: {msg.metadata.get('strategy', 'unknown')}")
    
    # Display private messages
    if private_messages:
        print("\n🔒 PRIVATE MESSAGES (sent to specific agent):")
        print("-"*50)
        for i, msg in enumerate(private_messages):
            print(f"\nPrivate Message #{i+1}:")
            print(f"  🗣️  {msg.sender} → {msg.recipients[0]}")
            print(f"  📄 Content: {msg.content}")
            print(f"  🏷️  Strategy: {msg.metadata.get('strategy', 'unknown')}")
            print(f"  🔐 Type: {msg.message_type.value}")
    
    # Display group messages
    if group_messages:
        print("\n👥 GROUP MESSAGES (sent to multiple agents):")
        print("-"*50)
        for i, msg in enumerate(group_messages):
            print(f"\nGroup Message #{i+1}:")
            print(f"  🗣️  {msg.sender} → {', '.join(msg.recipients)}")
            print(f"  📄 Content: {msg.content}")
            print(f"  🏷️  Strategy: {msg.metadata.get('strategy', 'unknown')}")
    
    # Communication flow diagram
    print("\n" + "="*80)
    print("📊 COMMUNICATION FLOW DIAGRAM")
    print("="*80)
    
    # Build flow by round
    rounds = {}
    for msg in reversed(all_messages):
        round_num = msg.metadata.get('round', 0)
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(msg)
    
    for round_num in sorted(rounds.keys()):
        print(f"\n🔄 Round {round_num}:")
        for msg in rounds[round_num]:
            if msg.message_type == MessageType.BROADCAST:
                arrow = "📢→→→"
                target = "ALL"
            elif len(msg.recipients) == 1:
                arrow = "🔒→"
                target = msg.recipients[0]
            else:
                arrow = "👥→→"
                target = f"[{', '.join(msg.recipients)}]"
            
            msg_type = msg.content.get('type', 'unknown')
            print(f"   {msg.sender} {arrow} {target}: {msg_type}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("📈 COMMUNICATION SUMMARY")
    print("="*80)
    
    stats = orchestrator.get_communication_stats()
    total = stats['messages_sent']
    
    if total > 0:
        print(f"\n📊 Message Type Distribution:")
        print(f"   📢 Broadcasts: {stats['broadcast_count']} ({stats['broadcast_count']/total*100:.1f}%)")
        print(f"   🔒 Private: {stats['private_count']} ({stats['private_count']/total*100:.1f}%)")
        print(f"   👥 Group: {stats['group_count']} ({stats['group_count']/total*100:.1f}%)")
    
    # Agent activity
    print(f"\n🤖 Agent Communication Activity:")
    senders = {}
    receivers = {}
    
    for msg in all_messages:
        senders[msg.sender] = senders.get(msg.sender, 0) + 1
        for recipient in msg.recipients:
            receivers[recipient] = receivers.get(recipient, 0) + 1
    
    for agent in set(list(senders.keys()) + list(receivers.keys())):
        sent = senders.get(agent, 0)
        received = receivers.get(agent, 0)
        print(f"   {agent}: Sent {sent}, Received {received}")
    
    return all_messages

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/demo_communication_patterns.yaml")
    args = parser.parse_args()
    
    visualize_communication(args.config)