#!/bin/bash
# Validation script for drift detection system

echo "=== Drift Detection System Validation ==="
echo ""

echo "1. Checking Python dependencies..."
cd ~/ansible-config-drift/detection-system
source venv/bin/activate
python3 -c "import flask, yaml, jsondiff; print('✓ All dependencies installed')"

echo ""
echo "2. Testing drift detector..."
python3 scripts/drift_detector.py --help 2>/dev/null && echo "✓ Drift detector works" || echo "✗ Drift detector failed"

echo ""
echo "3. Checking generated reports..."
REPORT_COUNT=$(find reports -name "*.json" -type f 2>/dev/null | wc -l)
echo "Found $REPORT_COUNT reports"

if [ $REPORT_COUNT -gt 0 ]; then
    echo "✓ Reports directory populated"
    LATEST_REPORT=$(find reports -name "*.json" -type f | head -1)
    echo "Latest report: $LATEST_REPORT"
    
    # Check report structure
    if python3 -m json.tool "$LATEST_REPORT" >/dev/null 2>&1; then
        echo "✓ Latest report has valid JSON"
    else
        echo "✗ Latest report has invalid JSON"
    fi
else
    echo "✗ No reports found"
fi

echo ""
echo "4. Testing Git audit trail..."
python3 scripts/git_audit_trail.py 2>&1 | grep -q "Audit Trail Status" && echo "✓ Git audit trail works" || echo "✗ Git audit trail failed"

echo ""
echo "5. Testing API server..."
timeout 5 python3 scripts/report_api.py > /dev/null 2>&1 &
API_PID=$!
sleep 2
if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    echo "✓ API server responds"
    kill $API_PID 2>/dev/null
else
    echo "✗ API server not responding"
    kill $API_PID 2>/dev/null
fi

echo ""
echo "6. Testing Ansible integration..."
cd ~/ansible-config-drift
if ansible-playbook -i inventories/production/hosts.ini playbooks/detect-drift.yml --check >/dev/null 2>&1; then
    echo "✓ Ansible playbook works in check mode"
else
    echo "✗ Ansible playbook failed"
fi

echo ""
echo "=== Validation Complete ==="
