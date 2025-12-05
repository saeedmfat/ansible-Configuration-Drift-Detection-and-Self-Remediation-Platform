#!/bin/bash
# Simple monitoring dashboard for the drift detection platform

clear
echo "🖥️  CONFIGURATION DRIFT DETECTION PLATFORM - MONITORING DASHBOARD"
echo "================================================================"
echo "Updated: $(date)"
echo ""

# Function to print status with color
print_status() {
    if [ "$1" = "healthy" ]; then
        echo -e "  ✅ $2"
    elif [ "$1" = "warning" ]; then
        echo -e "  ⚠️  $2"
    else
        echo -e "  ❌ $2"
    fi
}

# Section 1: Infrastructure
echo "1. INFRASTRUCTURE STATUS"
echo "-----------------------"

# VM Status
VM_COUNT=$(vagrant status | grep -c "running")
if [ "$VM_COUNT" -eq 4 ]; then
    print_status "healthy" "All 4 VMs running"
else
    print_status "critical" "Only $VM_COUNT/4 VMs running"
fi

# Ansible Connectivity
ANSIBLE_PING=$(ansible all -i inventories/production/hosts.ini -m ping 2>/dev/null | grep -c "SUCCESS")
if [ "$ANSIBLE_PING" -eq 3 ]; then
    print_status "healthy" "Ansible connectivity to all 3 target nodes"
else
    print_status "warning" "Ansible connectivity to $ANSIBLE_PING/3 nodes"
fi

# Section 2: Services
echo ""
echo "2. SERVICE STATUS"
echo "----------------"

for node in target1 target2 target3; do
    WEB_STATUS=$(ansible $node -i inventories/production/hosts.ini -m shell -a \
        "systemctl is-active nginx 2>/dev/null || systemctl is-active httpd 2>/dev/null" | tail -1)
    
    if [ "$WEB_STATUS" = "active" ]; then
        print_status "healthy" "$node: Web server active"
    else
        print_status "critical" "$node: Web server inactive"
    fi
done

# Section 3: Drift Detection
echo ""
echo "3. DRIFT DETECTION"
echo "-----------------"

# Check for recent detection reports
RECENT_REPORTS=$(find detection-system/reports -name "*.json" -mmin -60 2>/dev/null | wc -l)
if [ "$RECENT_REPORTS" -gt 0 ]; then
    print_status "healthy" "Recent detection reports found ($RECENT_REPORTS in last hour)"
else
    print_status "warning" "No detection reports in last hour"
fi

# Check latest report for drifts
LATEST_REPORT=$(find detection-system/reports -name "*.json" -type f -exec ls -t {} + | head -1 2>/dev/null)
if [ -n "$LATEST_REPORT" ]; then
    DRIFT_COUNT=$(jq '.summary.total_detections // 0' "$LATEST_REPORT" 2>/dev/null || echo "0")
    if [ "$DRIFT_COUNT" -eq 0 ]; then
        print_status "healthy" "Latest report: No drifts detected"
    else
        print_status "warning" "Latest report: $DRIFT_COUNT drifts detected"
    fi
else
    print_status "warning" "No detection reports found"
fi

# Section 4: Automation
echo ""
echo "4. AUTOMATION SCHEDULES"
echo "----------------------"

# Check systemd timers
TIMERS_ACTIVE=$(systemctl list-timers --all | grep -c "drift\|ansible-pull")
if [ "$TIMERS_ACTIVE" -gt 0 ]; then
    print_status "healthy" "Systemd timers configured"
else
    print_status "warning" "No systemd timers found"
fi

# Section 5: Recent Activity
echo ""
echo "5. RECENT ACTIVITY"
echo "-----------------"

# Show last 5 log entries from drift simulation
if [ -f "drift-simulator/logs/drift_simulation.log" ]; then
    echo "  Recent drift simulations:"
    tail -3 drift-simulator/logs/drift_simulation.log | while read line; do
        echo "    • $line"
    done
fi

# Show last remediation
if [ -f "/var/log/ansible/remediation.log" ]; then
    echo ""
    echo "  Recent remediations:"
    tail -3 /var/log/ansible/remediation.log 2>/dev/null | while read line; do
        echo "    • $line"
    done
fi

# Section 6: Quick Actions
echo ""
echo "6. QUICK ACTIONS"
echo "---------------"
echo "  1. Run end-to-end workflow demo"
echo "  2. Validate complete system"
echo "  3. Check for drifts manually"
echo "  4. View latest report"
echo "  5. Exit"
echo ""
read -p "Select action (1-5): " action

case $action in
    1)
        ./scripts/run-end-to-end-workflow.sh
        ;;
    2)
        ./scripts/validate-complete-system.sh
        ;;
    3)
        echo "Checking for drifts..."
        cd detection-system
        source venv/bin/activate
        python3 scripts/drift_detector.py
        deactivate
        cd ..
        ;;
    4)
        if [ -n "$LATEST_REPORT" ]; then
            jq '.summary' "$LATEST_REPORT" 2>/dev/null || cat "$LATEST_REPORT" | head -30
        else
            echo "No reports found"
        fi
        ;;
    5)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        ;;
esac

echo ""
echo "Press Enter to refresh dashboard..."
read
exec $0  # Restart script to refresh
