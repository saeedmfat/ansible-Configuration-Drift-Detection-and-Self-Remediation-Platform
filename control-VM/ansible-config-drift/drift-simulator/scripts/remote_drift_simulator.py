#!/usr/bin/env python3
"""
Remote Drift Simulator - Executes drift scenarios on remote nodes via SSH.
"""

import paramiko
import yaml
import random
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemoteDriftSimulator:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ssh_clients = {}
        self.results = []
    
    def connect_to_node(self, node):
        """Establish SSH connection to a node."""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=node['ip'],
                username='vagrant',
                key_filename=self.config['remote_execution']['ssh_key_path']
            )
            
            self.ssh_clients[node['name']] = ssh
            logger.info(f"Connected to {node['name']} ({node['ip']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {node['name']}: {str(e)}")
            return False
    
    def execute_drift(self, node, command):
        """Execute a drift command on remote node."""
        try:
            ssh = self.ssh_clients[node['name']]
            
            # Add sudo if needed
            if not command.startswith('echo'):
                command = f"sudo {command}"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            result = {
                'node': node['name'],
                'command': command,
                'exit_code': exit_code,
                'output': output,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            
            if exit_code == 0:
                logger.info(f"Drift executed on {node['name']}: {command[:50]}...")
            else:
                logger.warning(f"Drift failed on {node['name']}: {error[:100]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute drift on {node['name']}: {str(e)}")
            return None
    
    def simulate_remote_drifts(self):
        """Simulate drifts on remote nodes."""
        logger.info("Starting remote drift simulation...")
        
        # Connect to all nodes
        for node in self.config['simulator']['target_nodes']:
            self.connect_to_node(node)
        
        # Define remote drift commands
        drift_commands = [
            # Modify web content
            "echo '<!-- DRIFT SIMULATION -->' >> /var/www/*/index.html",
            
            # Add cron job
            "echo '*/5 * * * * root echo \"Drift test\" >> /tmp/drift.log' > /etc/cron.d/drift_test",
            
            # Create test file in managed directory
            "touch /etc/ansible-managed/unauthorized_file.txt",
            
            # Change file permissions
            "chmod 777 /var/www/*/index.html",
            
            # Add test user
            "useradd -m -s /bin/bash test_drift_user",
            
            # Install test package
            "apt-get install -y cowsay 2>/dev/null || yum install -y cowsay 2>/dev/null || true",
            
            # Stop service temporarily
            "systemctl stop nginx 2>/dev/null || systemctl stop httpd 2>/dev/null || true",
            
            # Modify config file
            "echo '# UNAUTHORIZED CHANGE' >> /etc/ssh/sshd_config"
        ]
        
        # Execute random drifts on random nodes
        num_drifts = random.randint(1, 3)
        
        for _ in range(num_drifts):
            node = random.choice(self.config['simulator']['target_nodes'])
            command = random.choice(drift_commands)
            
            if node['name'] in self.ssh_clients:
                self.execute_drift(node, command)
        
        # Save results
        results_file = f"logs/remote_drifts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Remote drift simulation complete. Results saved to {results_file}")
        
        # Close connections
        for ssh in self.ssh_clients.values():
            ssh.close()
        
        return self.results

if __name__ == "__main__":
    simulator = RemoteDriftSimulator("configs/simulator_config.yaml")
    results = simulator.simulate_remote_drifts()
    
    print("\nRemote Drift Simulation Results:")
    print("="*60)
    for result in results:
        status = "✓ SUCCESS" if result['exit_code'] == 0 else "✗ FAILED"
        print(f"{status} - {result['node']}: {result['command'][:50]}...")
