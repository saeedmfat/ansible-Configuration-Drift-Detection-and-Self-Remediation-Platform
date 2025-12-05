#!/usr/bin/env python3
"""
Validate remediation results.
"""

import os
import json
from datetime import datetime, timedelta

def validate_remediation():
    """Validate that remediation was successful."""
    reports_dir = "reports"
    
    if not os.path.exists(reports_dir):
        print("No reports directory found")
        return False
    
    # Find latest remediation report
    remediation_dirs = [d for d in os.listdir(reports_dir) if d.startswith('remediation_')]
    if not remediation_dirs:
        print("No remediation reports found")
        return False
    
    latest_dir = max(remediation_dirs)
    report_path = os.path.join(reports_dir, latest_dir, "consolidated_report.md")
    
    if not os.path.exists(report_path):
        print(f"No consolidated report in {latest_dir}")
        return False
    
    # Read and analyze report
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Simple validation
    if "Canary Phase: SUCCESS" in content:
        print("✓ Canary phase successful")
        canary_ok = True
    else:
        print("✗ Canary phase failed")
        canary_ok = False
    
    if "Full Remediation: COMPLETED" in content:
        print("✓ Full remediation completed")
        full_ok = True
    else:
        print("✗ Full remediation not completed")
        full_ok = False
    
    # Check for critical alerts
    if "CRITICAL:" in content:
        print("✗ Critical issues found in report")
        critical_ok = False
    else:
        print("✓ No critical issues in report")
        critical_ok = True
    
    # Overall validation
    if canary_ok and full_ok and critical_ok:
        print("\n✅ Remediation validation PASSED")
        return True
    else:
        print("\n❌ Remediation validation FAILED")
        return False

if __name__ == "__main__":
    import sys
    success = validate_remediation()
    sys.exit(0 if success else 1)
