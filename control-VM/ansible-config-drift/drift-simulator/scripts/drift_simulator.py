#!/usr/bin/env python3
"""
Configuration Drift Simulator
Simulates random unauthorized changes to test detection systems.
"""

import os
import sys
import random
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from faker import Faker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/drift_simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DriftSimulator:
    def __init__(self):
        self.fake = Faker()
        self.drift_log = []
        self.simulation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Define drift scenarios with weights (higher = more likely)
        self.drift_scenarios = [
            {"name": "modify_web_content", "weight": 30, "func": self.modify_web_content},
            {"name": "stop_service", "weight": 20, "func": self.stop_service},
            {"name": "delete_file", "weight": 15, "func": self.delete_file},
            {"name": "add_unauthorized_user", "weight": 10, "func": self.add_unauthorized_user},
            {"name": "change_permissions", "weight": 15, "func": self.change_permissions},
            {"name": "modify_config_file", "weight": 20, "func": self.modify_config_file},
            {"name": "install_unauthorized_package", "weight": 10, "func": self.install_unauthorized_package},
            {"name": "change_firewall_rule", "weight": 5, "func": self.change_firewall_rule},
            {"name": "no_drift", "weight": 5, "func": self.no_drift}  # Sometimes do nothing
        ]
        
        # Target paths that are managed by Ansible
        self.managed_paths = [
            "/var/www",
            "/etc/nginx",
            "/etc/apache2",
            "/etc/httpd",
            "/etc/ansible-managed"
        ]
        
        # Services managed by Ansible
        self.managed_services = ["nginx", "apache2", "httpd", "ssh", "cron"]
    
    def weighted_random_choice(self, scenarios):
        """Select a scenario based on weights."""
        total = sum(s["weight"] for s in scenarios)
        r = random.uniform(0, total)
        upto = 0
        for scenario in scenarios:
            if upto + scenario["weight"] >= r:
                return scenario
            upto += scenario["weight"]
        return scenarios[0]
    
    def log_drift(self, action, target, details, severity="medium"):
        """Log a drift event."""
        drift_event = {
            "timestamp": datetime.now().isoformat(),
            "simulation_id": self.simulation_id,
            "action": action,
            "target": target,
            "details": details,
            "severity": severity,
            "hostname": os.uname().nodename
        }
        
        self.drift_log.append(drift_event)
        logger.info(f"DRIFT: {action} on {target} - {details}")
        
        # Save to individual log file
        log_file = f"logs/drift_{self.simulation_id}.json"
        with open(log_file, 'a') as f:
            f.write(json.dumps(drift_event) + '\n')
        
        return drift_event
    
    def modify_web_content(self):
        """Modify web content (index.html or other files)."""
        web_roots = [
            "/var/www/config-drift-website",
            "/var/www/ubuntu-website", 
            "/var/www/rocky-website"
        ]
        
        for web_root in web_roots:
            if os.path.exists(web_root):
                index_file = os.path.join(web_root, "index.html")
                if os.path.exists(index_file):
                    # Read current content
                    with open(index_file, 'r') as f:
                        content = f.read()
                    
                    # Add a random "hacker" message
                    hacker_messages = [
                        "<!-- HACKED BY DRIFT SIMULATOR -->",
                        f"<!-- Modified by {self.fake.name()} at {datetime.now()} -->",
                        "<script>console.log('Unauthorized change detected!')</script>",
                        "<!-- System compromised for testing purposes -->"
                    ]
                    
                    insert_point = random.randint(0, len(content) // 2)
                    new_content = content[:insert_point] + random.choice(hacker_messages) + content[insert_point:]
                    
                    # Backup original
                    backup_file = f"{index_file}.bak.{self.simulation_id}"
                    with open(backup_file, 'w') as f:
                        f.write(content)
                    
                    # Write modified content
                    with open(index_file, 'w') as f:
                        f.write(new_content)
                    
                    return self.log_drift(
                        "modify_web_content",
                        index_file,
                        f"Added hacker message: {hacker_messages[0][:50]}...",
                        "high"
                    )
        
        return self.log_drift("modify_web_content", "N/A", "No web content found to modify", "low")
    
    def stop_service(self):
        """Stop a managed service."""
        service = random.choice(self.managed_services)
        
        try:
            # Check if service exists and is running
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip() == "active":
                subprocess.run(["sudo", "systemctl", "stop", service], check=True)
                
                return self.log_drift(
                    "stop_service",
                    service,
                    f"Stopped {service} service",
                    "high"
                )
            else:
                return self.log_drift(
                    "stop_service", 
                    service,
                    f"Service {service} not active, nothing to stop",
                    "low"
                )
                
        except Exception as e:
            return self.log_drift(
                "stop_service",
                service,
                f"Failed to stop {service}: {str(e)}",
                "medium"
            )
    
    def delete_file(self):
        """Delete a managed configuration file."""
        for path in self.managed_paths:
            if os.path.exists(path):
                # Find all files in the path
                files = []
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.endswith(('.conf', '.json', '.yml', '.yaml')):
                            files.append(os.path.join(root, filename))
                
                if files:
                    file_to_delete = random.choice(files)
                    
                    # Create backup before deletion
                    backup_file = f"{file_to_delete}.bak.{self.simulation_id}"
                    if os.path.exists(file_to_delete):
                        subprocess.run(["sudo", "cp", file_to_delete, backup_file], check=False)
                        subprocess.run(["sudo", "rm", "-f", file_to_delete], check=False)
                        
                        return self.log_drift(
                            "delete_file",
                            file_to_delete,
                            f"Deleted configuration file (backup: {backup_file})",
                            "critical"
                        )
        
        return self.log_drift("delete_file", "N/A", "No files found to delete", "low")
    
    def add_unauthorized_user(self):
        """Add an unauthorized user account."""
        username = f"testuser_{random.randint(1000, 9999)}"
        
        try:
            # Check if user already exists
            result = subprocess.run(
                ["id", username],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # User doesn't exist, create it
                subprocess.run(
                    ["sudo", "useradd", "-m", "-s", "/bin/bash", username],
                    check=True
                )
                
                # Set a random password
                password = self.fake.password()
                subprocess.run(
                    f"echo '{username}:{password}' | sudo chpasswd",
                    shell=True,
                    check=True
                )
                
                return self.log_drift(
                    "add_unauthorized_user",
                    username,
                    f"Added unauthorized user with password: {password}",
                    "high"
                )
            else:
                return self.log_drift(
                    "add_unauthorized_user",
                    username,
                    f"User {username} already exists",
                    "low"
                )
                
        except Exception as e:
            return self.log_drift(
                "add_unauthorized_user",
                username,
                f"Failed to add user: {str(e)}",
                "medium"
            )
    
    def change_permissions(self):
        """Change permissions on managed files."""
        for path in self.managed_paths:
            if os.path.exists(path):
                # Find files to modify
                files = []
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
                
                if files:
                    file_to_modify = random.choice(files)
                    current_mode = oct(os.stat(file_to_modify).st_mode)[-3:]
                    
                    # Choose a problematic permission
                    bad_permissions = ["777", "666", "000", "444"]
                    new_mode = random.choice(bad_permissions)
                    
                    subprocess.run(["sudo", "chmod", new_mode, file_to_modify], check=False)
                    
                    return self.log_drift(
                        "change_permissions",
                        file_to_modify,
                        f"Changed permissions from {current_mode} to {new_mode}",
                        "medium"
                    )
        
        return self.log_drift("change_permissions", "N/A", "No files found to modify", "low")
    
    def modify_config_file(self):
        """Modify a configuration file with random content."""
        config_files = [
            "/etc/ssh/sshd_config",
            "/etc/hosts",
            "/etc/resolv.conf",
            "/etc/sysctl.conf"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                # Read current content
                with open(config_file, 'r') as f:
                    content = f.readlines()
                
                if content:
                    # Choose a random line to modify or add nonsense
                    if random.choice([True, False]):
                        # Modify existing line
                        line_num = random.randint(0, min(20, len(content)-1))
                        original_line = content[line_num]
                        content[line_num] = f"# DRIFT SIMULATION: {self.fake.sentence()}\n{original_line}"
                    else:
                        # Add nonsense at the end
                        content.append(f"\n# UNAUTHORIZED CHANGE: {self.fake.sentence()}\n")
                    
                    # Backup original
                    backup_file = f"{config_file}.bak.{self.simulation_id}"
                    subprocess.run(["sudo", "cp", config_file, backup_file], check=False)
                    
                    # Write modified content
                    with open(config_file, 'w') as f:
                        f.writelines(content)
                    
                    return self.log_drift(
                        "modify_config_file",
                        config_file,
                        "Added random comments to configuration",
                        "high"
                    )
        
        return self.log_drift("modify_config_file", "N/A", "No config files found", "low")
    
    def install_unauthorized_package(self):
        """Install an unauthorized package."""
        # List of potentially problematic packages
        packages = [
            "cowsay", "fortune", "sl", "cmatrix",
            "hollywood", "bb", "nyancat", "asciiquarium"
        ]
        
        package = random.choice(packages)
        
        try:
            # Check if package is already installed
            result = subprocess.run(
                ["which", package],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Try to install
                subprocess.run(
                    ["sudo", "apt", "install", "-y", package],
                    capture_output=True,
                    text=True
                )
                
                return self.log_drift(
                    "install_unauthorized_package",
                    package,
                    f"Installed unauthorized package: {package}",
                    "medium"
                )
            else:
                return self.log_drift(
                    "install_unauthorized_package",
                    package,
                    f"Package {package} already installed",
                    "low"
                )
                
        except Exception as e:
            # Try with yum/dnf for Rocky
            try:
                subprocess.run(
                    ["sudo", "yum", "install", "-y", package],
                    capture_output=True,
                    text=True
                )
                return self.log_drift(
                    "install_unauthorized_package",
                    package,
                    f"Installed unauthorized package via yum: {package}",
                    "medium"
                )
            except:
                return self.log_drift(
                    "install_unauthorized_package",
                    package,
                    f"Failed to install {package}: {str(e)}",
                    "low"
                )
    
    def change_firewall_rule(self):
        """Add or remove a firewall rule."""
        actions = ["allow", "deny"]
        ports = ["22", "80", "443", "8080", "9000"]
        
        action = random.choice(actions)
        port = random.choice(ports)
        
        try:
            # Try ufw (Ubuntu)
            subprocess.run(
                ["sudo", "ufw", action, port],
                capture_output=True,
                text=True
            )
            
            return self.log_drift(
                "change_firewall_rule",
                f"port {port}",
                f"Changed firewall to {action} port {port}",
                "high"
            )
        except:
            try:
                # Try firewalld (Rocky)
                if action == "allow":
                    subprocess.run(
                        ["sudo", "firewall-cmd", "--add-port", f"{port}/tcp", "--permanent"],
                        capture_output=True,
                        text=True
                    )
                else:
                    subprocess.run(
                        ["sudo", "firewall-cmd", "--remove-port", f"{port}/tcp", "--permanent"],
                        capture_output=True,
                        text=True
                    )
                
                subprocess.run(["sudo", "firewall-cmd", "--reload"])
                
                return self.log_drift(
                    "change_firewall_rule",
                    f"port {port}",
                    f"Changed firewall to {action} port {port} via firewalld",
                    "high"
                )
            except Exception as e:
                return self.log_drift(
                    "change_firewall_rule",
                    f"port {port}",
                    f"Failed to change firewall: {str(e)}",
                    "medium"
                )
    
    def no_drift(self):
        """Simulate no drift (for testing detection of normal state)."""
        return self.log_drift(
            "no_drift",
            "N/A",
            "No drift simulated this cycle",
            "low"
        )
    
    def run_simulation(self):
        """Run one simulation cycle."""
        logger.info(f"=== Starting drift simulation cycle {self.simulation_id} ===")
        
        # Select and run a scenario
        scenario = self.weighted_random_choice(self.drift_scenarios)
        logger.info(f"Selected scenario: {scenario['name']} (weight: {scenario['weight']})")
        
        result = scenario["func"]()
        
        # Log summary
        logger.info(f"=== Simulation cycle {self.simulation_id} complete ===")
        logger.info(f"Action: {result['action']}")
        logger.info(f"Target: {result['target']}")
        logger.info(f"Severity: {result['severity']}")
        
        # Save summary to file
        summary_file = f"logs/summary_{self.simulation_id}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "simulation_id": self.simulation_id,
                "timestamp": datetime.now().isoformat(),
                "scenario": scenario['name'],
                "result": result,
                "total_drifts_logged": len(self.drift_log)
            }, f, indent=2)
        
        return result

def main():
    """Main function to run the drift simulator."""
    simulator = DriftSimulator()
    
    try:
        # Run simulation
        result = simulator.run_simulation()
        
        # Print results
        print("\n" + "="*60)
        print("DRIFT SIMULATION COMPLETE")
        print("="*60)
        print(f"Simulation ID: {simulator.simulation_id}")
        print(f"Action: {result['action']}")
        print(f"Target: {result['target']}")
        print(f"Severity: {result['severity']}")
        print(f"Details: {result['details']}")
        print(f"Log file: logs/drift_{simulator.simulation_id}.json")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
