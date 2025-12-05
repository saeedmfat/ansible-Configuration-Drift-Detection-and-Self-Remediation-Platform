#!/bin/bash
# Manual drift simulation test

echo "=== Manual Drift Simulation Test ==="
echo ""

echo "1. Checking current system state..."
# Take snapshot of current state
SNAPSHOT_DIR="snapshots/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SNAPSHOT_DIR"

# Capture current checksums
echo "Taking system snapshot..."
find /var/www -type f -name "*.html" -exec sha256sum {} \; > "$SNAPSHOT_DIR/web_files.sha256" 2>/dev/null || true
find /etc/nginx -type f -name "*.conf" -exec sha256sum {} \; > "$SNAPSHOT_DIR/nginx_conf.sha256" 2>/dev/null || true
find /etc/apache2 -type f -name "*.conf" -exec sha256sum {} \; > "$SNAPSHOT_DIR/apache_conf.sha256" 2>/dev/null || true
systemctl list-units --type=service --state=running > "$SNAPSHOT_DIR/services.running"

echo "Snapshot saved to: $SNAPSHOT_DIR"
echo ""

echo "2. Running drift simulation..."
# Run the simulator
cd "$(dirname "$0")/.."
source venv/bin/activate
python3 scripts/drift_simulator.py

echo ""
echo "3. Verifying drift was introduced..."
echo "Waiting 5 seconds for changes to take effect..."
sleep 5

echo ""
echo "4. Checking for changes..."
# Check web server status
echo "Web server status:"
systemctl is-active nginx 2>/dev/null || systemctl is-active apache2 2>/dev/null || systemctl is-active httpd 2>/dev/null || echo "No web server running"

# Check for recent modifications
echo ""
echo "Recently modified files in managed directories:"
find /var/www /etc/nginx /etc/apache2 /etc/httpd /etc/ansible-managed -type f -mmin -5 2>/dev/null | head -10 || echo "No recent modifications found"

echo ""
echo "=== Test Complete ==="
echo "Run Ansible to detect and remediate the drift!"
echo "Command: ansible-playbook -i ../inventories/production/hosts.ini playbooks/webserver-deploy.yml"
