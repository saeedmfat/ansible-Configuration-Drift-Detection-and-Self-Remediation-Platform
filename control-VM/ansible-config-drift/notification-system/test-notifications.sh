#!/bin/bash
# Test all notification levels

echo "Testing notification system..."

# Test different severity levels
./notify.sh "test" "This is a CRITICAL test notification" "critical" "test"
sleep 1
./notify.sh "test" "This is a HIGH severity test" "high" "test"
sleep 1
./notify.sh "test" "This is a MEDIUM severity test" "medium" "test"
sleep 1
./notify.sh "test" "This is a LOW severity test" "low" "test"
sleep 1
./notify.sh "test" "This is an INFO notification" "info" "test"
sleep 1
./notify.sh "test" "This is a SUCCESS notification" "success" "test"

echo ""
echo "Check log file: /var/log/drift-notifications.log"
tail -10 /var/log/drift-notifications.log 2>/dev/null || echo "Log file not created yet"
