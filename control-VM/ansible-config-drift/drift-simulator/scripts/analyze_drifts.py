#!/usr/bin/env python3
"""
Analyze drift simulation results and generate reports.
"""

import json
import glob
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import pandas as pd

def analyze_drift_logs():
    """Analyze all drift log files."""
    log_files = glob.glob("logs/drift_*.json")
    
    if not log_files:
        print("No drift log files found.")
        return
    
    all_drifts = []
    for log_file in log_files:
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    all_drifts.append(json.loads(line))
    
    print(f"Total drift events: {len(all_drifts)}")
    print()
    
    # Analyze by action type
    action_counter = Counter([d['action'] for d in all_drifts])
    print("Drift actions distribution:")
    for action, count in action_counter.most_common():
        print(f"  {action}: {count}")
    
    print()
    
    # Analyze by severity
    severity_counter = Counter([d['severity'] for d in all_drifts])
    print("Severity distribution:")
    for severity, count in severity_counter.most_common():
        print(f"  {severity}: {count}")
    
    print()
    
    # Analyze by time
    drifts_by_hour = defaultdict(int)
    for drift in all_drifts:
        hour = datetime.fromisoformat(drift['timestamp'].replace('Z', '+00:00')).hour
        drifts_by_hour[hour] += 1
    
    print("Drifts by hour:")
    for hour in sorted(drifts_by_hour.keys()):
        print(f"  {hour:02d}:00 - {drifts_by_hour[hour]} drifts")
    
    # Generate summary report
    summary = {
        "total_drifts": len(all_drifts),
        "date_range": {
            "first": min([d['timestamp'] for d in all_drifts]),
            "last": max([d['timestamp'] for d in all_drifts])
        },
        "by_action": dict(action_counter),
        "by_severity": dict(severity_counter),
        "simulations_analyzed": len(log_files)
    }
    
    # Save summary
    with open("logs/drift_analysis.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print()
    print(f"Analysis saved to logs/drift_analysis.json")
    
    # Create simple visualization (optional)
    try:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Action distribution
        actions = list(action_counter.keys())
        counts = list(action_counter.values())
        axes[0].bar(actions, counts)
        axes[0].set_title('Drift Actions Distribution')
        axes[0].set_xlabel('Action Type')
        axes[0].set_ylabel('Count')
        axes[0].tick_params(axis='x', rotation=45)
        
        # Severity distribution
        severities = list(severity_counter.keys())
        sev_counts = list(severity_counter.values())
        colors = ['green', 'yellow', 'orange', 'red']
        axes[1].pie(sev_counts, labels=severities, autopct='%1.1f%%', colors=colors[:len(severities)])
        axes[1].set_title('Drift Severity Distribution')
        
        plt.tight_layout()
        plt.savefig('logs/drift_analysis.png', dpi=100)
        print("Visualization saved to logs/drift_analysis.png")
        
    except ImportError:
        print("Matplotlib not available. Skipping visualization.")

if __name__ == "__main__":
    analyze_drift_logs()
