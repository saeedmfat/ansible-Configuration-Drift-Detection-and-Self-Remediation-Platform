#!/bin/bash
echo "=== Webserver Role Validation Test ==="
echo ""

echo "1. Testing idempotency on target1..."
ansible-playbook -i inventories/production/hosts.ini playbooks/webserver-deploy.yml --limit target1 | grep -E "changed|ok|failed" | tail -5
echo ""

echo "2. Checking service status on all nodes..."
for node in target1 target2 target3; do
    echo "$node:"
    ansible $node -i inventories/production/hosts.ini -m shell -a "systemctl list-units --type=service --state=running | grep -E 'nginx|apache|httpd'" || true
done
echo ""

echo "3. Testing HTTP connectivity..."
for node in target1 target2 target3; do
    IP=$(ansible-inventory -i inventories/production/hosts.ini --host $node | grep -oP 'ansible_host": "\K[^"]+')
    echo "$node ($IP):"
    curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" --connect-timeout 3 http://$IP/health || echo "  Connection failed"
done
echo ""

echo "4. Checking desired state files..."
ansible all -i inventories/production/hosts.ini -m shell -a "ls -la {{ config_dir }}/*.json 2>/dev/null || echo 'No state files found'"
echo ""

echo "=== Validation Complete ==="
