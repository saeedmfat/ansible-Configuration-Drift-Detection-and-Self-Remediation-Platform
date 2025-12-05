#!/bin/bash
# Environment validation script

echo "=== Environment Validation Check ==="
echo "Timestamp: $(date)"
echo ""

# Check Ansible version
echo "1. Ansible Version:"
ansible --version | head -1
echo ""

# Check inventory
echo "2. Inventory Status:"
echo "Nodes in inventory:"
ansible-inventory -i inventories/production/hosts.ini --list --yaml | grep -E "hosts|ansible_host" | head -6
echo ""

# Test connectivity
echo "3. Connectivity Test:"
ansible all -i inventories/production/hosts.ini -m ping | grep -E "SUCCESS|UNREACHABLE"
echo ""

# Check Git status
echo "4. Git Repository Status:"
git status --short
echo ""

# Check directory structure
echo "5. Project Structure:"
echo "Key directories:"
ls -la roles/ playbooks/ inventories/ group_vars/
echo ""

echo "=== Validation Complete ==="
