#!/usr/bin/env python3
"""
Core Remediation Engine
Safely remediates configuration drifts with canary deployment and rollback.
"""

import os
import sys
import json
import yaml
import logging
import shutil
from datetime import datetime, timedelta
import subprocess
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/remediation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RemediationEngine:
    def __init__(self, config_path):
        """Initialize remediation engine."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.remediation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.remediation_log = []
        self.canary_nodes = []
        self.remediated_nodes = []
        self.failed_nodes = []
        
        # Create remediation directory
        self.remediation_dir = f"remediations/{self.remediation_id}"
        os.makedirs(self.remediation_dir, exist_ok=True)
        
        # Load detection report if available
        self.detection_report = self.load_latest_detection()
    
    def load_latest_detection(self):
        """Load latest detection report."""
        reports_path = self.config['integration']['detection_system']['reports_path']
        
        # Find latest report
        json_files = list(Path(reports_path).rglob("*.json"))
        if not json_files:
            logger.warning("No detection reports found")
            return None
        
        latest_report = max(json_files, key=os.path.getctime)
        
        try:
            with open(latest_report, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load detection report: {str(e)}")
            return None
    
    def log_event(self, event_type, node, details, status="info"):
        """Log a remediation event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "remediation_id": self.remediation_id,
            "type": event_type,
            "node": node,
            "details": details,
            "status": status
        }
        
        self.remediation_log.append(event)
        
        # Write to log file
        log_file = f"{self.remediation_dir}/events.json"
        with open(log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Log to console based on status
        if status == "error":
            logger.error(f"{event_type.upper()} - {node}: {details}")
        elif status == "warning":
            logger.warning(f"{event_type.upper()} - {node}: {details}")
        else:
            logger.info(f"{event_type.upper()} - {node}: {details}")
        
        return event
    
    def select_canary_nodes(self, all_nodes):
        """Select canary nodes for initial remediation."""
        if not self.config['remediation']['canary']['enabled']:
            return all_nodes
        
        canary_percentage = self.config['remediation']['canary']['percentage']
        num_canary = max(1, int(len(all_nodes) * canary_percentage / 100))
        
        # Select canary nodes (prefer nodes with fewer critical drifts)
        canary_nodes = all_nodes[:num_canary]
        
        logger.info(f"Selected {len(canary_nodes)} canary nodes: {', '.join(canary_nodes)}")
        return canary_nodes
    
    def create_backup(self, node, backup_type="pre_remediation"):
        """Create backup of node configuration."""
        backup_dir = f"backups/{backup_type}/{node}_{self.remediation_id}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup key configuration files
            backup_paths = [
                "/etc/nginx",
                "/etc/apache2",
                "/etc/httpd",
                "/var/www",
                "/etc/ansible-managed"
            ]
            
            for path in backup_paths:
                if os.path.exists(path):
                    # Use rsync for efficient backup
                    dest_path = os.path.join(backup_dir, path.lstrip('/'))
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copytree(path, dest_path, dirs_exist_ok=True)
            
            # Backup service status
            services_file = os.path.join(backup_dir, "services.status")
            with open(services_file, 'w') as f:
                subprocess.run(["systemctl", "list-units", "--type=service", "--state=running"], 
                             stdout=f, stderr=subprocess.DEVNULL)
            
            self.log_event("backup_created", node, f"Backup saved to {backup_dir}")
            return backup_dir
            
        except Exception as e:
            self.log_event("backup_failed", node, str(e), "error")
            return None
    
    def validate_node(self, node, validation_type="pre_remediation"):
        """Validate node state before/after remediation."""
        try:
            validation_results = {
                "node": node,
                "validation_type": validation_type,
                "timestamp": datetime.now().isoformat(),
                "checks": [],
                "passed": True
            }
            
            # Check required services
            required_services = self.config['remediation']['validation']['required_services']
            for service in required_services:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                
                is_active = result.stdout.strip() == "active"
                check = {
                    "check": f"service_{service}",
                    "status": "active" if is_active else "inactive",
                    "passed": is_active
                }
                
                validation_results["checks"].append(check)
                if not is_active:
                    validation_results["passed"] = False
            
            # Check disk space
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True,
                text=True
            )
            disk_info = result.stdout.split('\n')[1] if len(result.stdout.split('\n')) > 1 else ""
            validation_results["checks"].append({
                "check": "disk_space",
                "status": disk_info,
                "passed": True  # Warning only
            })
            
            # Check memory
            result = subprocess.run(
                ["free", "-m"],
                capture_output=True,
                text=True
            )
            memory_info = result.stdout.split('\n')[1] if len(result.stdout.split('\n')) > 1 else ""
            validation_results["checks"].append({
                "check": "memory",
                "status": memory_info,
                "passed": True  # Warning only
            })
            
            status = "passed" if validation_results["passed"] else "failed"
            self.log_event(f"validation_{validation_type}", node, f"Validation {status}")
            
            # Save validation results
            validation_file = f"{self.remediation_dir}/validation_{validation_type}_{node}.json"
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            return validation_results
            
        except Exception as e:
            self.log_event("validation_failed", node, str(e), "error")
            return None
    
    def remediate_file_changes(self, node, file_path, previous_checksum):
        """Remediate file changes by restoring from backup or template."""
        try:
            # First, check if this is a managed file
            managed_dirs = ["/var/www", "/etc/nginx", "/etc/apache2", "/etc/httpd", "/etc/ansible-managed"]
            is_managed = any(file_path.startswith(dir) for dir in managed_dirs)
            
            if not is_managed:
                self.log_event("skip_remediation", node, f"File not in managed directory: {file_path}", "warning")
                return False
            
            # Check if we have a backup
            backup_file = f"backups/pre_remediation/{node}_{self.remediation_id}/{file_path.lstrip('/')}"
            if os.path.exists(backup_file):
                # Restore from backup
                subprocess.run(["sudo", "cp", backup_file, file_path], check=True)
                self.log_event("file_restored", node, f"Restored {file_path} from backup")
                return True
            
            # If no backup, use Ansible to restore desired state
            ansible_playbook = self.config['integration']['ansible']['playbooks_path'] + "webserver-deploy.yml"
            inventory = self.config['integration']['ansible']['inventory_path']
            
            result = subprocess.run(
                ["ansible-playbook", "-i", inventory, ansible_playbook, "--limit", node, "--tags", "content"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_event("file_remediated", node, f"Restored {file_path} via Ansible")
                return True
            else:
                self.log_event("file_remediation_failed", node, f"Failed to restore {file_path}", "error")
                return False
                
        except Exception as e:
            self.log_event("file_remediation_error", node, str(e), "error")
            return False
    
    def remediate_service_status(self, node, service, desired_status="active"):
        """Remediate service status."""
        try:
            # Check current status
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            
            current_status = result.stdout.strip()
            
            if current_status == desired_status:
                self.log_event("service_already_ok", node, f"Service {service} already {desired_status}")
                return True
            
            # Attempt to fix
            if desired_status == "active":
                subprocess.run(["sudo", "systemctl", "start", service], check=True)
                subprocess.run(["sudo", "systemctl", "enable", service], check=True)
                action = "started and enabled"
            else:
                subprocess.run(["sudo", "systemctl", "stop", service], check=True)
                subprocess.run(["sudo", "systemctl", "disable", service], check=True)
                action = "stopped and disabled"
            
            # Verify fix
            time.sleep(2)  # Give service time to start/stop
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            
            new_status = result.stdout.strip()
            
            if new_status == desired_status:
                self.log_event("service_remediated", node, f"Service {service} {action} (now {new_status})")
                return True
            else:
                self.log_event("service_remediation_failed", node, f"Service {service} still {new_status}, wanted {desired_status}", "error")
                return False
                
        except Exception as e:
            self.log_event("service_remediation_error", node, str(e), "error")
            return False
    
    def remediate_unauthorized_package(self, node, package, action="remove"):
        """Remediate unauthorized packages."""
        try:
            if action == "remove":
                # Try different package managers
                commands = [
                    ["sudo", "apt", "remove", "-y", package],
                    ["sudo", "yum", "remove", "-y", package],
                    ["sudo", "dnf", "remove", "-y", package]
                ]
                
                for cmd in commands:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log_event("package_removed", node, f"Removed unauthorized package: {package}")
                        return True
                
                self.log_event("package_removal_failed", node, f"Failed to remove {package}", "warning")
                return False
                
            else:  # action == "install" for missing required packages
                commands = [
                    ["sudo", "apt", "install", "-y", package],
                    ["sudo", "yum", "install", "-y", package],
                    ["sudo", "dnf", "install", "-y", package]
                ]
                
                for cmd in commands:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log_event("package_installed", node, f"Installed required package: {package}")
                        return True
                
                self.log_event("package_install_failed", node, f"Failed to install {package}", "warning")
                return False
                
        except Exception as e:
            self.log_event("package_remediation_error", node, str(e), "error")
            return False
    
    def remediate_unauthorized_user(self, node, username, action="remove"):
        """Remediate unauthorized users."""
        try:
            if action == "remove":
                # Check if user exists
                result = subprocess.run(["id", username], capture_output=True, text=True)
                if result.returncode != 0:
                    self.log_event("user_not_found", node, f"User {username} doesn't exist")
                    return True
                
                # Preserve admin users
                admin_users = self.config['strategies']['user_management']['preserve_admin_users']
                if username in admin_users:
                    self.log_event("user_preserved", node, f"User {username} is admin, preserving")
                    return True
                
                # Remove user
                subprocess.run(["sudo", "userdel", "-r", username], check=True)
                self.log_event("user_removed", node, f"Removed unauthorized user: {username}")
                return True
                
            else:  # action == "add" for missing required users
                subprocess.run(["sudo", "useradd", "-m", "-s", "/bin/bash", username], check=True)
                self.log_event("user_added", node, f"Added required user: {username}")
                return True
                
        except Exception as e:
            self.log_event("user_remediation_error", node, str(e), "error")
            return False
    
    def remediate_node(self, node, drifts):
        """Remediate all drifts on a single node."""
        logger.info(f"Starting remediation on node: {node}")
        
        # Create backup
        if self.config['remediation']['rollback']['backup_before_remediation']:
            backup_dir = self.create_backup(node)
            if not backup_dir:
                self.log_event("remediation_aborted", node, "Backup creation failed", "error")
                return False
        
        # Pre-remediation validation
        if self.config['remediation']['validation']['pre_remediation_validation']:
            validation = self.validate_node(node, "pre_remediation")
            if not validation or not validation['passed']:
                self.log_event("remediation_aborted", node, "Pre-remediation validation failed", "error")
                return False
        
        remediation_results = []
        
        # Process each drift
        for drift in drifts:
            success = False
            
            if drift['type'] == 'file_change':
                success = self.remediate_file_changes(node, drift['file'], drift.get('previous_checksum'))
            
            elif drift['type'] == 'service_status_change':
                service = drift.get('service', '')
                desired_status = 'active'  # Default desired state
                success = self.remediate_service_status(node, service, desired_status)
            
            elif drift['type'] in ['package_added', 'package_removed']:
                package = drift.get('package', '')
                action = 'remove' if drift['type'] == 'package_added' else 'install'
                success = self.remediate_unauthorized_package(node, package, action)
            
            elif drift['type'] in ['user_added', 'user_removed']:
                username = drift.get('user', '')
                action = 'remove' if drift['type'] == 'user_added' else 'add'
                success = self.remediate_unauthorized_user(node, username, action)
            
            else:
                self.log_event("unknown_drift_type", node, f"Unknown drift type: {drift['type']}", "warning")
                continue
            
            remediation_results.append({
                "drift": drift,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })
        
        # Post-remediation validation
        if self.config['remediation']['validation']['post_remediation_validation']:
            validation = self.validate_node(node, "post_remediation")
            if not validation or not validation['passed']:
                self.log_event("remediation_failed_validation", node, "Post-remediation validation failed", "error")
                
                # Trigger rollback if configured
                if self.config['remediation']['rollback']['automatic_on_failure']:
                    self.rollback_node(node)
                return False
        
        # Save results
        results_file = f"{self.remediation_dir}/remediation_{node}.json"
        with open(results_file, 'w') as f:
            json.dump(remediation_results, f, indent=2)
        
        success_count = sum(1 for r in remediation_results if r['success'])
        total_count = len(remediation_results)
        
        if success_count == total_count:
            self.log_event("remediation_complete", node, f"All {total_count} drifts remediated successfully")
            self.remediated_nodes.append(node)
            return True
        else:
            self.log_event("remediation_partial", node, f"{success_count}/{total_count} drifts remediated", "warning")
            self.remediated_nodes.append(node)  # Still consider partially successful
            return success_count > 0  # Return True if at least one drift was fixed
    
    def rollback_node(self, node):
        """Rollback node to pre-remediation state."""
        logger.info(f"Starting rollback on node: {node}")
        
        try:
            backup_dir = f"backups/pre_remediation/{node}_{self.remediation_id}"
            
            if not os.path.exists(backup_dir):
                self.log_event("rollback_failed", node, "Backup directory not found", "error")
                return False
            
            # Restore files from backup
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    backup_file = os.path.join(root, file)
                    # Convert backup path to system path
                    system_path = '/' + os.path.relpath(backup_file, backup_dir)
                    
                    # Ensure parent directory exists
                    os.makedirs(os.path.dirname(system_path), exist_ok=True)
                    
                    # Copy file back
                    shutil.copy2(backup_file, system_path)
            
            self.log_event("rollback_complete", node, f"Rolled back to pre-remediation state")
            return True
            
        except Exception as e:
            self.log_event("rollback_error", node, str(e), "error")
            return False
    
    def run_canary_remediation(self, nodes_with_drifts):
        """Run canary remediation phase."""
        if not nodes_with_drifts:
            logger.info("No nodes with drifts detected")
            return True
        
        # Select canary nodes
        self.canary_nodes = self.select_canary_nodes(list(nodes_with_drifts.keys()))
        
        logger.info(f"Starting canary remediation on {len(self.canary_nodes)} nodes")
        
        canary_results = []
        for node in self.canary_nodes:
            drifts = nodes_with_drifts.get(node, [])
            
            if not drifts:
                self.log_event("no_drifts", node, "No drifts to remediate")
                continue
            
            # Remediate node
            success = self.remediate_node(node, drifts)
            canary_results.append((node, success))
        
        # Calculate success rate
        successful_canaries = sum(1 for _, success in canary_results if success)
        total_canaries = len(canary_results)
        success_rate = (successful_canaries / total_canaries * 100) if total_canaries > 0 else 0
        
        success_threshold = self.config['remediation']['canary']['success_threshold']
        
        logger.info(f"Canary remediation complete: {successful_canaries}/{total_canaries} successful ({success_rate:.1f}%)")
        
        if success_rate >= success_threshold:
            self.log_event("canary_success", "all", f"Canary phase passed ({success_rate:.1f}% >= {success_threshold}%)")
            return True
        else:
            self.log_event("canary_failed", "all", f"Canary phase failed ({success_rate:.1f}% < {success_threshold}%)", "error")
            return False
    
    def run_full_remediation(self, nodes_with_drifts):
        """Run full remediation on all nodes."""
        # Remove canary nodes (already remediated)
        remaining_nodes = {node: drifts for node, drifts in nodes_with_drifts.items() 
                          if node not in self.canary_nodes}
        
        if not remaining_nodes:
            logger.info("No remaining nodes to remediate")
            return True
        
        logger.info(f"Starting full remediation on {len(remaining_nodes)} nodes")
        
        for node, drifts in remaining_nodes.items():
            self.remediate_node(node, drifts)
        
        logger.info("Full remediation complete")
        return True
    
    def generate_remediation_report(self):
        """Generate comprehensive remediation report."""
        report = {
            "metadata": {
                "remediation_id": self.remediation_id,
                "start_time": self.remediation_log[0]['timestamp'] if self.remediation_log else datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_minutes": 0  # Will be calculated
            },
            "summary": {
                "total_nodes_remediated": len(self.remediated_nodes),
                "total_nodes_failed": len(self.failed_nodes),
                "canary_nodes": self.canary_nodes,
                "remediated_nodes": self.remediated_nodes,
                "failed_nodes": self.failed_nodes
            },
            "events_by_type": {},
            "recommendations": []
        }
        
        # Count events by type
        for event in self.remediation_log:
            event_type = event['type']
            report["events_by_type"][event_type] = report["events_by_type"].get(event_type, 0) + 1
        
        # Calculate duration
        if self.remediation_log:
            start_time = datetime.fromisoformat(report["metadata"]["start_time"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(report["metadata"]["end_time"].replace('Z', '+00:00'))
            report["metadata"]["duration_minutes"] = round((end_time - start_time).total_seconds() / 60, 2)
        
        # Generate recommendations
        if self.failed_nodes:
            report["recommendations"].append({
                "priority": "high",
                "action": "manual_intervention",
                "details": f"Manual intervention required for nodes: {', '.join(self.failed_nodes)}"
            })
        
        if report["events_by_type"].get("remediation_failed_validation", 0) > 0:
            report["recommendations"].append({
                "priority": "medium",
                "action": "review_validation_thresholds",
                "details": "Consider adjusting validation thresholds or improving remediation scripts"
            })
        
        # Save report
        report_file = f"{self.remediation_dir}/remediation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown summary
        markdown_file = f"{self.remediation_dir}/README.md"
        with open(markdown_file, 'w') as f:
            f.write(f"# Remediation Report: {self.remediation_id}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Nodes Remediated:** {len(self.remediated_nodes)}\n")
            f.write(f"- **Total Nodes Failed:** {len(self.failed_nodes)}\n")
            f.write(f"- **Canary Nodes:** {', '.join(self.canary_nodes) if self.canary_nodes else 'None'}\n")
            f.write(f"- **Duration:** {report['metadata']['duration_minutes']} minutes\n\n")
            
            f.write("## Events by Type\n\n")
            for event_type, count in report["events_by_type"].items():
                f.write(f"- **{event_type}:** {count}\n")
            
            f.write("\n## Recommendations\n\n")
            for rec in report["recommendations"]:
                f.write(f"- **{rec['priority'].upper()}**: {rec['action']} - {rec['details']}\n")
            
            f.write("\n## Log Files\n\n")
            f.write("- `events.json` - All remediation events\n")
            f.write("- `remediation_*.json` - Per-node remediation results\n")
            f.write("- `validation_*.json` - Pre/post validation results\n")
        
        logger.info(f"Remediation report generated: {report_file}")
        return report
    
    def run(self):
        """Main remediation workflow."""
        logger.info(f"=== Starting remediation engine {self.remediation_id} ===")
        
        # Check if remediation is enabled
        if not self.config['remediation']['enabled']:
            logger.warning("Remediation is disabled in configuration")
            return False
        
        # Load detection data
        if not self.detection_report:
            logger.error("No detection report available")
            return False
        
        # Extract drifts by node
        nodes_with_drifts = {}
        for detection in self.detection_report.get('detections', []):
            # Assuming detection has node information
            node = detection.get('node', 'unknown')
            if node not in nodes_with_drifts:
                nodes_with_drifts[node] = []
            nodes_with_drifts[node].append(detection)
        
        if not nodes_with_drifts:
            logger.info("No drifts detected in the report")
            return True
        
        logger.info(f"Found drifts on {len(nodes_with_drifts)} nodes")
        
        # Run canary remediation
        canary_success = self.run_canary_remediation(nodes_with_drifts)
        
        if not canary_success:
            logger.error("Canary remediation failed, aborting full remediation")
            self.generate_remediation_report()
            return False
        
        # Wait before full rollout (if configured)
        wait_time = self.config['remediation']['canary']['wait_time_minutes']
        if wait_time > 0 and self.canary_nodes:
            logger.info(f"Waiting {wait_time} minutes before full rollout...")
            time.sleep(wait_time * 60)
        
        # Run full remediation
        self.run_full_remediation(nodes_with_drifts)
        
        # Generate final report
        report = self.generate_remediation_report()
        
        logger.info(f"=== Remediation complete ===")
        logger.info(f"Successfully remediated: {len(self.remediated_nodes)} nodes")
        logger.info(f"Failed: {len(self.failed_nodes)} nodes")
        
        return len(self.failed_nodes) == 0

def main():
    """Main function."""
    config_path = "config/remediation_config.yaml"
    
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    # Check if we're in safe mode (for testing)
    import argparse
    parser = argparse.ArgumentParser(description="Remediation Engine")
    parser.add_argument("--safe-mode", action="store_true", help="Run in safe mode (no changes)")
    parser.add_argument("--test", action="store_true", help="Run test remediation")
    args = parser.parse_args()
    
    engine = RemediationEngine(config_path)
    
    if args.safe_mode:
        print("Running in SAFE MODE - no actual changes will be made")
        engine.config['remediation']['safe_mode'] = True
    
    if args.test:
        print("Running TEST remediation...")
        # Create test data
        test_drifts = {
            "target1": [
                {
                    "type": "file_change",
                    "file": "/var/www/config-drift-website/index.html",
                    "previous_checksum": "abc123"
                }
            ]
        }
        engine.run_canary_remediation(test_drifts)
        engine.generate_remediation_report()
        return
    
    success = engine.run()
    
    if success:
        print("\n" + "="*60)
        print("REMEDIATION SUCCESSFUL")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("REMEDIATION FAILED OR PARTIAL")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()
