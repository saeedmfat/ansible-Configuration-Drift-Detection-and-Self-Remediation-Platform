#!/usr/bin/env python3
"""
Git-based audit trail system for drift detection reports.
"""

import os
import sys
import json
import shutil
from datetime import datetime
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitAuditTrail:
    def __init__(self, repo_path, branch="reports"):
        self.repo_path = repo_path
        self.branch = branch
        self.working_dir = "/tmp/drift-reports"
        
        # Create working directory
        os.makedirs(self.working_dir, exist_ok=True)
    
    def initialize_repo(self):
        """Initialize or clone the Git repository."""
        if not os.path.exists(self.repo_path):
            logger.info(f"Creating new Git repository at {self.repo_path}")
            os.makedirs(self.repo_path, exist_ok=True)
            subprocess.run(["git", "init", "--bare", self.repo_path], check=True)
        
        # Clone to working directory
        if os.path.exists(os.path.join(self.working_dir, ".git")):
            # Pull latest
            os.chdir(self.working_dir)
            subprocess.run(["git", "pull", "origin", self.branch], check=False)
        else:
            # Clone fresh
            if os.path.exists(self.working_dir):
                shutil.rmtree(self.working_dir)
            subprocess.run(["git", "clone", self.repo_path, self.working_dir], check=True)
            os.chdir(self.working_dir)
            
            # Checkout reports branch
            subprocess.run(["git", "checkout", "-b", self.branch], check=False)
            subprocess.run(["git", "checkout", self.branch], check=True)
    
    def add_report(self, report_path, report_type="detection"):
        """Add a report to the audit trail."""
        try:
            # Generate timestamp and filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}.json"
            dest_path = os.path.join(self.working_dir, "reports", filename)
            
            # Create reports directory
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy report
            shutil.copy2(report_path, dest_path)
            
            # Generate commit message
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            
            total_detections = report_data.get('summary', {}).get('total_detections', 0)
            
            commit_msg = f"[DRIFT] {report_type.capitalize()} report: {total_detections} detections at {timestamp}"
            
            # Add, commit, and push
            subprocess.run(["git", "add", dest_path], check=True)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push", "origin", self.branch], check=True)
            
            logger.info(f"Report added to audit trail: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add report to audit trail: {str(e)}")
            return False
    
    def get_audit_log(self, days=7):
        """Get audit log for the specified number of days."""
        os.chdir(self.working_dir)
        
        # Update from remote
        subprocess.run(["git", "pull"], check=False)
        
        # Get commit history
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", f"--since={since_date}", "--pretty=format:%H|%ad|%s", "--date=iso"],
            capture_output=True,
            text=True
        )
        
        audit_log = []
        for line in result.stdout.strip().split('\n'):
            if line:
                commit_hash, date, message = line.split('|', 2)
                audit_log.append({
                    "hash": commit_hash,
                    "date": date,
                    "message": message
                })
        
        return audit_log
    
    def generate_audit_report(self, output_file):
        """Generate an audit report."""
        audit_log = self.get_audit_log(days=30)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "time_period_days": 30,
            "total_commits": len(audit_log),
            "commits": audit_log,
            "summary": {
                "detection_reports": len([c for c in audit_log if "[DRIFT] Detection" in c['message']]),
                "remediation_reports": len([c for c in audit_log if "[DRIFT] Remediation" in c['message']]),
                "other_reports": len([c for c in audit_log if "[DRIFT]" not in c['message']])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Audit report generated: {output_file}")
        return report

def main():
    """Main function."""
    repo_path = "/opt/git/repos/drift-audit.git"
    
    # Create if doesn't exist
    if not os.path.exists(repo_path):
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        subprocess.run(["git", "init", "--bare", repo_path], check=True)
        print(f"Created new audit repository at {repo_path}")
    
    auditor = GitAuditTrail(repo_path)
    auditor.initialize_repo()
    
    # Test with a sample report
    sample_report = {
        "metadata": {
            "detection_id": "test_123",
            "timestamp": datetime.now().isoformat(),
            "hostname": "testhost"
        },
        "summary": {
            "total_detections": 3,
            "by_severity": {"high": 1, "medium": 2}
        }
    }
    
    sample_path = "/tmp/sample_report.json"
    with open(sample_path, 'w') as f:
        json.dump(sample_report, f)
    
    # Add to audit trail
    auditor.add_report(sample_path, "test")
    
    # Generate audit report
    audit_report = auditor.generate_audit_report("/tmp/audit_report.json")
    
    print("\nAudit Trail Status:")
    print(f"Repository: {repo_path}")
    print(f"Total commits (30 days): {audit_report['total_commits']}")
    print(f"Detection reports: {audit_report['summary']['detection_reports']}")
    print(f"Remediation reports: {audit_report['summary']['remediation_reports']}")

if __name__ == "__main__":
    main()
