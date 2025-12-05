#!/bin/bash
# Test the remediation system

echo "=== Testing Remediation System ==="
echo ""

echo "1. Testing Python remediation engine..."
source venv/bin/activate
python3 scripts/remediation_engine.py --help
if [ $? -eq 0 ]; then
    echo "✓ Remediation engine works"
else
    echo "✗ Remediation engine failed"
fi

echo ""
echo "2. Testing Ansible remediation playbooks..."
cd ~/ansible-config-drift
if ansible-playbook -i inventories/production/hosts.ini playbooks/master-remediate.yml --check --tags backup >/dev/null 2>&1; then
    echo "✓ Ansible playbooks work in check mode"
else
    echo "✗ Ansible playbooks failed"
fi

echo ""
echo "3. Creating test remediation scenario..."
# Create a test drift
TEST_NODE="target1"
echo "Creating test drift on $TEST_NODE..."
ansible $TEST_NODE -i inventories/production/hosts.ini -m shell -a "
    echo '<!-- TEST REMEDIATION -->' >> /var/www/config-drif-website/index.html
    echo 'Test file for remediation' > /etc/ansible-managed/test_remediation.txt
"

echo ""
echo "4. Running canary remediation test..."
ansible-playbook -i inventories/production/hosts.ini \
    playbooks/master-remediate.yml \
    -e "canary_group=target1" \
    --tags base,webserver \
    --limit target1

echo ""
echo "5. Verifying remediation..."
echo "Checking if test file was removed..."
ansible $TEST_NODE -i inventories/production/hosts.ini -m shell -a "
    if [ -f /etc/ansible-managed/test_remediation.txt ]; then
        echo '✗ Test file still exists (remediation may have failed)'
    else
        echo '✓ Test file removed (remediation worked)'
    fi
"

echo ""
echo "=== Test Complete ==="
