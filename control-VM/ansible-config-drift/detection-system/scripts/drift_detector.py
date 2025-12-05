#!/usr/bin/env python3
"""
Core Drift Detection Engine
Detects configuration changes and generates reports.
"""

import os
import sys
import json
import hashlib
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import jsondiff

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DriftDetector:
    def __init__(self, config_path):
        """Initialize drift detector with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.detection_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.detections = []
        self.report_data = {
            "metadata": {
                "detection_id": self.detection_id,
                "timestamp": datetime.now().isoformat(),
                "hostname": os.uname().nodename
            },
            "summary": {
                "total_detections": 0,
                "by_severity": {},
                "by_category": {}
            },
            "detections": []
        }
        
        # Load previous state if exists
        self.previous_state = self.load_previous_state()
        
    def load_previous_state(self):
        """Load previous detection state."""
        state_file = "database/last_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load previous state: {str(e)}")
        return {}
    
    def save_current_state(self):
        """Save current state for next comparison."""
        state_file = "database/last_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(self.report_data, f, indent=2)
            logger.info(f"Current state saved to {state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
    
    def calculate_checksum(self, filepath, algorithm='sha256'):
        """Calculate checksum of a file."""
        try:
            if algorithm == 'sha256':
                hash_func = hashlib.sha256()
            elif algorithm == 'md5':
                hash_func = hashlib.md5()
            else:
                hash_func = hashlib.sha256()
            
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate checksum for {filepath}: {str(e)}")
            return None
    
    def check_file_changes(self):
        """Check for file changes in monitored paths."""
        logger.info("Checking for file changes...")
        
        for path in self.config['detection']['monitored_paths']:
            if not os.path.exists(path):
                logger.debug(f"Path does not exist: {path}")
                continue
            
            for pattern in self.config['detection']['monitored_patterns']:
                for filepath in Path(path).rglob(pattern):
                    try:
                        # Skip symlinks and directories
                        if not filepath.is_file():
                            continue
                        
                        # Calculate checksum
                        checksum = self.calculate_checksum(str(filepath))
                        if not checksum:
                            continue
                        
                        # Compare with previous state
                        file_key = str(filepath)
                        previous_checksum = self.previous_state.get('files', {}).get(file_key, {}).get('checksum')
                        
                        if previous_checksum and previous_checksum != checksum:
                            # File has changed!
                            detection = {
                                "type": "file_change",
                                "timestamp": datetime.now().isoformat(),
                                "file": file_key,
                                "previous_checksum": previous_checksum,
                                "current_checksum": checksum,
                                "severity": self.assess_severity(file_key),
                                "category": "file_integrity"
                            }
                            
                            self.detections.append(detection)
                            logger.info(f"File change detected: {file_key}")
                        
                        # Update current state
                        if 'files' not in self.report_data:
                            self.report_data['files'] = {}
                        self.report_data['files'][file_key] = {
                            "checksum": checksum,
                            "last_checked": datetime.now().isoformat(),
                            "size": filepath.stat().st_size
                        }
                        
                    except Exception as e:
                        logger.error(f"Error processing {filepath}: {str(e)}")
        
        logger.info(f"File change check complete. Found {len([d for d in self.detections if d['type'] == 'file_change'])} changes.")
    
    def check_service_status(self):
        """Check for service status changes."""
        logger.info("Checking service status...")
        
        for service in self.config['detection']['monitored_services']:
            try:
                # Check service status
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                
                current_status = result.stdout.strip()
                previous_status = self.previous_state.get('services', {}).get(service, {}).get('status')
                
                if previous_status and previous_status != current_status:
                    # Service status changed!
                    detection = {
                        "type": "service_status_change",
                        "timestamp": datetime.now().isoformat(),
                        "service": service,
                        "previous_status": previous_status,
                        "current_status": current_status,
                        "severity": "high" if current_status != "active" else "medium",
                        "category": "service_health"
                    }
                    
                    self.detections.append(detection)
                    logger.info(f"Service status changed: {service} ({previous_status} -> {current_status})")
                
                # Update current state
                if 'services' not in self.report_data:
                    self.report_data['services'] = {}
                
                self.report_data['services'][service] = {
                    "status": current_status,
                    "last_checked": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error checking service {service}: {str(e)}")
    
    def check_package_changes(self):
        """Check for package installation/removal."""
        logger.info("Checking package changes...")
        
        try:
            # Get installed packages
            if os.path.exists('/usr/bin/dpkg'):
                # Debian/Ubuntu
                result = subprocess.run(
                    ["dpkg", "-l"],
                    capture_output=True,
                    text=True
                )
                packages = [line.split()[1] for line in result.stdout.split('\n')[5:] if line]
                package_manager = "dpkg"
            elif os.path.exists('/usr/bin/rpm'):
                # RHEL/Rocky
                result = subprocess.run(
                    ["rpm", "-qa"],
                    capture_output=True,
                    text=True
                )
                packages = result.stdout.strip().split('\n')
                package_manager = "rpm"
            else:
                logger.warning("Unsupported package manager")
                return
            
            current_packages = set(packages)
            previous_packages = set(self.previous_state.get('packages', {}).get('installed', []))
            
            # Find added packages
            added = current_packages - previous_packages
            # Find removed packages
            removed = previous_packages - current_packages
            
            for package in added:
                detection = {
                    "type": "package_added",
                    "timestamp": datetime.now().isoformat(),
                    "package": package,
                    "action": "installed",
                    "severity": "medium",
                    "category": "package_management"
                }
                self.detections.append(detection)
                logger.info(f"Package added: {package}")
            
            for package in removed:
                detection = {
                    "type": "package_removed",
                    "timestamp": datetime.now().isoformat(),
                    "package": package,
                    "action": "removed",
                    "severity": "high",
                    "category": "package_management"
                }
                self.detections.append(detection)
                logger.info(f"Package removed: {package}")
            
            # Update current state
            self.report_data['packages'] = {
                "manager": package_manager,
                "installed": list(current_packages),
                "last_checked": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking packages: {str(e)}")
    
    def check_user_accounts(self):
        """Check for user account changes."""
        logger.info("Checking user accounts...")
        
        try:
            # Get current users
            result = subprocess.run(
                ["getent", "passwd"],
                capture_output=True,
                text=True
            )
            
            current_users = set(line.split(':')[0] for line in result.stdout.strip().split('\n') if line)
            previous_users = set(self.previous_state.get('users', {}).get('accounts', []))
            
            # Find added users
            added = current_users - previous_users
            # Find removed users
            removed = previous_users - current_users
            
            for user in added:
                detection = {
                    "type": "user_added",
                    "timestamp": datetime.now().isoformat(),
                    "user": user,
                    "action": "added",
                    "severity": "high",
                    "category": "user_management"
                }
                self.detections.append(detection)
                logger.info(f"User added: {user}")
            
            for user in removed:
                detection = {
                    "type": "user_removed",
                    "timestamp": datetime.now().isoformat(),
                    "user": user,
                    "action": "removed",
                    "severity": "critical",
                    "category": "user_management"
                }
                self.detections.append(detection)
                logger.info(f"User removed: {user}")
            
            # Update current state
            self.report_data['users'] = {
                "accounts": list(current_users),
                "last_checked": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking users: {str(e)}")
    
    def assess_severity(self, filepath):
        """Assess severity of a detected change."""
        filepath_str = str(filepath)
        
        # Critical paths
        critical_paths = [
            '/etc/passwd', '/etc/shadow', '/etc/sudoers',
            '/etc/ssh/sshd_config', '/root/', '/etc/cron'
        ]
        
        # High importance paths
        high_paths = [
            '/etc/nginx/', '/etc/apache2/', '/etc/httpd/',
            '/var/www/', '/etc/ansible-managed/'
        ]
        
        for path in critical_paths:
            if filepath_str.startswith(path):
                return "critical"
        
        for path in high_paths:
            if filepath_str.startswith(path):
                return "high"
        
        return "medium"
    
    def run_detection(self):
        """Run all detection checks."""
        logger.info(f"=== Starting drift detection run {self.detection_id} ===")
        
        # Run all detection methods
        self.check_file_changes()
        self.check_service_status()
        self.check_package_changes()
        self.check_user_accounts()
        
        # Update report data
        self.report_data['detections'] = self.detections
        
        # Update summary
        self.report_data['summary']['total_detections'] = len(self.detections)
        
        # Count by severity
        severity_counts = {}
        for detection in self.detections:
            severity = detection['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        self.report_data['summary']['by_severity'] = severity_counts
        
        # Count by category
        category_counts = {}
        for detection in self.detections:
            category = detection['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        self.report_data['summary']['by_category'] = category_counts
        
        # Save current state
        self.save_current_state()
        
        # Generate report
        report_path = self.generate_report()
        
        logger.info(f"=== Detection run complete ===")
        logger.info(f"Total detections: {len(self.detections)}")
        logger.info(f"Report generated: {report_path}")
        
        return self.report_data
    
    def generate_report(self):
        """Generate detection report."""
        # Ensure reports directory exists
        reports_dir = f"reports/daily/{datetime.now().strftime('%Y/%m/%d')}"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate JSON report
        json_report = f"{reports_dir}/detection_{self.detection_id}.json"
        with open(json_report, 'w') as f:
            json.dump(self.report_data, f, indent=2)
        
        # Generate summary report
        summary_report = f"{reports_dir}/summary_{self.detection_id}.md"
        self.generate_markdown_report(summary_report)
        
        # Generate HTML report
        html_report = f"{reports_dir}/report_{self.detection_id}.html"
        self.generate_html_report(html_report)
        
        # Update latest report symlink
        latest_link = "reports/latest.json"
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(os.path.abspath(json_report), latest_link)
        
        return json_report
    
    def generate_markdown_report(self, filepath):
        """Generate markdown summary report."""
        try:
            with open(filepath, 'w') as f:
                f.write(f"# Drift Detection Report\n")
                f.write(f"**Detection ID:** {self.detection_id}\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n")
                f.write(f"**Hostname:** {os.uname().nodename}\n\n")
                
                f.write("## Summary\n")
                f.write(f"- **Total Detections:** {len(self.detections)}\n")
                
                if self.report_data['summary']['by_severity']:
                    f.write("\n### By Severity\n")
                    for severity, count in self.report_data['summary']['by_severity'].items():
                        f.write(f"- **{severity.upper()}:** {count}\n")
                
                if self.report_data['summary']['by_category']:
                    f.write("\n### By Category\n")
                    for category, count in self.report_data['summary']['by_category'].items():
                        f.write(f"- **{category}:** {count}\n")
                
                if self.detections:
                    f.write("\n## Detailed Detections\n")
                    for i, detection in enumerate(self.detections, 1):
                        f.write(f"\n### Detection #{i}\n")
                        f.write(f"- **Type:** {detection['type']}\n")
                        f.write(f"- **Severity:** {detection['severity']}\n")
                        f.write(f"- **Category:** {detection['category']}\n")
                        f.write(f"- **Timestamp:** {detection['timestamp']}\n")
                        
                        if detection['type'] == 'file_change':
                            f.write(f"- **File:** {detection['file']}\n")
                            f.write(f"- **Previous Checksum:** {detection['previous_checksum'][:16]}...\n")
                            f.write(f"- **Current Checksum:** {detection['current_checksum'][:16]}...\n")
                        
                        elif detection['type'] == 'service_status_change':
                            f.write(f"- **Service:** {detection['service']}\n")
                            f.write(f"- **Previous Status:** {detection['previous_status']}\n")
                            f.write(f"- **Current Status:** {detection['current_status']}\n")
                        
                        elif detection['type'] in ['package_added', 'package_removed']:
                            f.write(f"- **Package:** {detection['package']}\n")
                            f.write(f"- **Action:** {detection['action']}\n")
                        
                        elif detection['type'] in ['user_added', 'user_removed']:
                            f.write(f"- **User:** {detection['user']}\n")
                            f.write(f"- **Action:** {detection['action']}\n")
                
                f.write("\n---\n")
                f.write("*Report generated by Configuration Drift Detection Platform*\n")
            
            logger.info(f"Markdown report generated: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to generate markdown report: {str(e)}")
    
    def generate_html_report(self, filepath):
        """Generate HTML report."""
        try:
            html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Drift Detection Report - {detection_id}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                    .summary-box {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 20px; margin: 20px 0; }}
                    .severity-critical {{ color: #dc3545; font-weight: bold; }}
                    .severity-high {{ color: #fd7e14; font-weight: bold; }}
                    .severity-medium {{ color: #ffc107; font-weight: bold; }}
                    .severity-low {{ color: #28a745; font-weight: bold; }}
                    .detection-card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0; background: #f8f9fa; }}
                    .detection-header {{ display: flex; justify-content: space-between; align-items: center; }}
                    .timestamp {{ color: #6c757d; font-size: 0.9em; }}
                    .badge {{ padding: 3px 8px; border-radius: 3px; font-size: 0.8em; }}
                    .badge-critical {{ background: #dc3545; color: white; }}
                    .badge-high {{ background: #fd7e14; color: white; }}
                    .badge-medium {{ background: #ffc107; color: white; }}
                    .badge-low {{ background: #28a745; color: white; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background: #f8f9fa; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚨 Drift Detection Report</h1>
                    
                    <div class="summary-box">
                        <h3>Report Summary</h3>
                        <p><strong>Detection ID:</strong> {detection_id}</p>
                        <p><strong>Timestamp:</strong> {timestamp}</p>
                        <p><strong>Hostname:</strong> {hostname}</p>
                        <p><strong>Total Detections:</strong> {total_detections}</p>
                    </div>
                    
                    {severity_summary}
                    
                    {category_summary}
                    
                    {detections_table}
                    
                    <footer>
                        <p style="text-align: center; color: #6c757d; margin-top: 40px;">
                            Generated by Configuration Drift Detection Platform • {generation_time}
                        </p>
                    </footer>
                </div>
            </body>
            </html>
            """
            
            # Generate severity summary HTML
            severity_html = ""
            if self.report_data['summary']['by_severity']:
                severity_html = "<h3>Detections by Severity</h3><table>"
                severity_html += "<tr><th>Severity</th><th>Count</th></tr>"
                for severity, count in self.report_data['summary']['by_severity'].items():
                    severity_html += f"<tr><td><span class='badge badge-{severity}'>{severity.upper()}</span></td><td>{count}</td></tr>"
                severity_html += "</table>"
            
            # Generate category summary HTML
            category_html = ""
            if self.report_data['summary']['by_category']:
                category_html = "<h3>Detections by Category</h3><table>"
                category_html += "<tr><th>Category</th><th>Count</th></tr>"
                for category, count in self.report_data['summary']['by_category'].items():
                    category_html += f"<tr><td>{category}</td><td>{count}</td></tr>"
                category_html += "</table>"
            
            # Generate detections table HTML
            detections_html = ""
            if self.detections:
                detections_html = "<h2>Detailed Detections</h2>"
                for detection in self.detections:
                    detections_html += f"""
                    <div class="detection-card">
                        <div class="detection-header">
                            <h4>{detection['type'].replace('_', ' ').title()}</h4>
                            <span class="badge badge-{detection['severity']}">{detection['severity'].upper()}</span>
                        </div>
                        <p><strong>Category:</strong> {detection['category']}</p>
                        <p><strong>Timestamp:</strong> {detection['timestamp']}</p>
                    """
                    
                    if detection['type'] == 'file_change':
                        detections_html += f"<p><strong>File:</strong> {detection['file']}</p>"
                        detections_html += f"<p><strong>Checksum Change:</strong> {detection['previous_checksum'][:16]}... → {detection['current_checksum'][:16]}...</p>"
                    
                    elif detection['type'] == 'service_status_change':
                        detections_html += f"<p><strong>Service:</strong> {detection['service']}</p>"
                        detections_html += f"<p><strong>Status Change:</strong> {detection['previous_status']} → {detection['current_status']}</p>"
                    
                    elif detection['type'] in ['package_added', 'package_removed']:
                        detections_html += f"<p><strong>Package:</strong> {detection['package']}</p>"
                        detections_html += f"<p><strong>Action:</strong> {detection['action']}</p>"
                    
                    elif detection['type'] in ['user_added', 'user_removed']:
                        detections_html += f"<p><strong>User:</strong> {detection['user']}</p>"
                        detections_html += f"<p><strong>Action:</strong> {detection['action']}</p>"
                    
                    detections_html += "</div>"
            
            # Fill template
            html_content = html_template.format(
                detection_id=self.detection_id,
                timestamp=datetime.now().isoformat(),
                hostname=os.uname().nodename,
                total_detections=len(self.detections),
                severity_summary=severity_html,
                category_summary=category_html,
                detections_table=detections_html,
                generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {str(e)}")

def main():
    """Main function."""
    config_path = "config/detection_config.yaml"
    
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    detector = DriftDetector(config_path)
    report_data = detector.run_detection()
    
    print("\n" + "="*60)
    print("DRIFT DETECTION COMPLETE")
    print("="*60)
    print(f"Detection ID: {detector.detection_id}")
    print(f"Total Detections: {len(report_data['detections'])}")
    
    if report_data['summary']['by_severity']:
        print("\nBy Severity:")
        for severity, count in report_data['summary']['by_severity'].items():
            print(f"  {severity.upper()}: {count}")
    
    print(f"\nReports generated in: reports/daily/{datetime.now().strftime('%Y/%m/%d')}/")
    print("="*60)
    
    # Return exit code based on detections
    if len(report_data['detections']) > 0:
        return 1  # Changes detected
    else:
        return 0  # No changes detected

if __name__ == "__main__":
    sys.exit(main())
