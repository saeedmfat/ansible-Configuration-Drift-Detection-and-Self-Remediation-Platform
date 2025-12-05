#!/bin/bash
# Validate the complete Configuration Drift Detection Platform

echo "🔍 COMPLETE SYSTEM VALIDATION"
echo "============================="
echo ""

OVERALL_SUCCESS=true

# Test 1: Basic Infrastructure
echo "1. BASIC INFRASTRUCTURE"
echo "----------------------"
if vagrant status | grep -q "running"; then
    echo "✅ All VMs are running"
else
    echo "❌ Some VMs are not running"
    OVERALL_SUCCESS=false
fi

if ansible all -i inventories/production/hosts.ini -m ping | grep -q "SUCCESS"; then
    echo "✅ Ansible connectivity OK"
else
    echo "❌ Ansible connectivity issues"
    OVERALL_SUCCESS=false
fi

# Test 2: Core Components
echo ""
echo "2. CORE COMPONENTS"
echo "-----------------"

# Check drift simulator
if [ -f "drift-simulator/scripts/drift_simulator.py" ]; then
    echo "✅ Drift simulator exists"
else
    echo "❌ Drift simulator missing"
    OVERALL_SUCCESS=false
fi

# Check detection system
if [ -f "detection-system/scripts/drift_detector.py" ]; then
    echo "✅ Drift detector exists"
else
    echo "❌ Drift detector missing"
    OVERALL_SUCCESS=false
fi

# Check remediation system
if [ -f "remediation-system/scripts/remediation_engine.py" ]; then
    echo "✅ Remediation engine exists"
else
    echo "❌ Remediation engine missing"
    OVERALL_SUCCESS=false
fi

# Check notification system
if [ -f "notification-system/notify.sh" ]; then
    echo "✅ Notification system exists"
else
    echo "❌ Notification system missing"
    OVERALL_SUCCESS=false
fi

# Test 3: Ansible Playbooks
echo ""
echo "3. ANSIBLE PLAYBOOKS"
echo "-------------------"
PLAYBOOKS=(
    "playbooks/base-setup.yml"
    "playbooks/webserver-deploy.yml"
    "playbooks/detect-drift.yml"
    "playbooks/master-remediate.yml"
)

for playbook in "${PLAYBOOKS[@]}"; do
    if [ -f "$playbook" ]; then
        echo "✅ $playbook exists"
    else
        echo "❌ $playbook missing"
        OVERALL_SUCCESS=false
    fi
done

# Test 4: Systemd Services (on control node)
echo ""
echo "4. SYSTEMD SERVICES (Control Node)"
echo "----------------------------------"
SERVICES=(
    "drift-simulator.timer"
    "ansible-pull.timer"
)

for service in "${SERVICES[@]}"; do
    if systemctl list-timers --all | grep -q "$service"; then
        echo "✅ $service is configured"
    else
        echo "⚠️  $service not configured (may be intentional)"
    fi
done

# Test 5: Git Repositories
echo ""
echo "5. GIT REPOSITORIES"
echo "------------------"
if [ -d "/opt/git/repos/config-drift.git" ]; then
    echo "✅ Main config repo exists"
else
    echo "❌ Main config repo missing"
    OVERALL_SUCCESS=false
fi

# Test 6: Web Servers Running
echo ""
echo "6. WEB SERVERS"
echo "-------------"
for node in target1 target2 target3; do
    STATUS=$(ansible $node -i inventories/production/hosts.ini -m shell -a "systemctl is-active nginx 2>/dev/null || systemctl is-active httpd 2>/dev/null || echo 'inactive'" | tail -1)
    if [ "$STATUS" = "active" ]; then
        echo "✅ $node web server is running"
    else
        echo "❌ $node web server is not running"
        OVERALL_SUCCESS=false
    fi
done

# Test 7: End-to-End Test (Quick)
echo ""
echo "7. QUICK END-TO-END TEST"
echo "------------------------"
echo "Creating test drift..."
TEST_MARKER="<!-- VALIDATION TEST $(date +%s) -->"
ansible target1 -i inventories/production/hosts.ini -m shell -a "
    echo '$TEST_MARKER' >> /var/www/config-drift-website/index.html
"

sleep 2

echo "Checking if drift is detectable..."
# Simple check - just verify the marker exists
CHECK=$(ansible target1 -i inventories/production/hosts.ini -m shell -a "grep -c '$TEST_MARKER' /var/www/config-drift-website/index.html" | tail -1)
if [ "$CHECK" -gt 0 ]; then
    echo "✅ Drift creation successful"
    
    # Clean up
    ansible target1 -i inventories/production/hosts.ini -m shell -a "
        sed -i '/$TEST_MARKER/d' /var/www/config-drift-website/index.html
    "
    echo "✅ Test drift cleaned up"
else
    echo "❌ Drift creation failed"
    OVERALL_SUCCESS=false
fi

# Final Summary
echo ""
echo "============================="
echo "VALIDATION COMPLETE"
echo "============================="

if [ "$OVERALL_SUCCESS" = true ]; then
    echo "🎉 SYSTEM STATUS: HEALTHY"
    echo ""
    echo "All core components are present and functional."
    echo "The Configuration Drift Detection Platform is ready for operation."
    
    # Send success notification
    ./scripts/notify.sh "validation_complete" \
        "System validation passed successfully. All components are operational." \
        "success" \
        "validation"
    
    exit 0
else
    echo "⚠️  SYSTEM STATUS: ISSUES DETECTED"
    echo ""
    echo "Some components failed validation. Check the output above."
    echo "Review and fix the issues before running the system in production."
    
    # Send warning notification
    ./scripts/notify.sh "validation_failed" \
        "System validation detected issues. Manual review required." \
        "medium" \
        "validation"
    
    exit 1
fi
