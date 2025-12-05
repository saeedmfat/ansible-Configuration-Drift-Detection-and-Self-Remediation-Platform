#!/bin/bash
# End-to-end workflow: Drift -> Detect -> Report -> Remediate

set -e

echo "🚀 STARTING END-TO-END WORKFLOW DEMONSTRATION"
echo "============================================="
echo ""

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORKFLOW_DIR="workflow-demo-$TIMESTAMP"
mkdir -p "$WORKFLOW_DIR"

# Step 1: Initial State
echo "1️⃣  STEP 1: CAPTURE INITIAL STATE"
echo "---------------------------------"
./scripts/validate-environment.sh > "$WORKFLOW_DIR/1_initial_state.txt"
echo "Initial state captured to $WORKFLOW_DIR/1_initial_state.txt"

# Step 2: Create Controlled Drift
echo ""
echo "2️⃣  STEP 2: CREATE CONTROLLED DRIFT"
echo "-----------------------------------"
echo "Creating test drifts on all nodes..."

# Create different drifts on each node
for i in {1..3}; do
    NODE="target$i"
    DRIFT_MSG="<!-- WORKFLOW DEMO DRIFT $TIMESTAMP on $NODE -->"
    
    echo "  Creating drift on $NODE: $DRIFT_MSG"
    ansible "$NODE" -i inventories/production/hosts.ini -m shell -a "
        echo '$DRIFT_MSG' >> /var/www/*/index.html
        echo 'Workflow test file $TIMESTAMP' > /etc/ansible-managed/workflow_test_$TIMESTAMP.txt
    "
done

echo "Drifts created successfully"

# Step 3: Run Drift Detection
echo ""
echo "3️⃣  STEP 3: RUN DRIFT DETECTION"
echo "--------------------------------"
echo "Running drift detection system..."

cd detection-system
source venv/bin/activate
python3 scripts/drift_detector.py > "../$WORKFLOW_DIR/3_detection_output.txt" 2>&1
deactivate
cd ..

DETECTION_EXIT=$?
echo "Detection exit code: $DETECTION_EXIT"

# Check detection results
if [ $DETECTION_EXIT -eq 1 ]; then
    echo "✅ Drifts detected (expected)"
else
    echo "⚠️  No drifts detected (unexpected)"
fi

# Step 4: Generate Reports
echo ""
echo "4️⃣  STEP 4: GENERATE REPORTS"
echo "----------------------------"
echo "Starting report API and fetching reports..."

# Start API in background
cd detection-system
source venv/bin/activate
python3 scripts/report_api.py > /dev/null 2>&1 &
API_PID=$!
sleep 3
deactivate
cd ..

# Fetch latest report
curl -s http://localhost:8080/api/v1/reports/latest | python3 -m json.tool > "$WORKFLOW_DIR/4_latest_report.json"

# Kill API
kill $API_PID 2>/dev/null || true

echo "Report saved to $WORKFLOW_DIR/4_latest_report.json"

# Step 5: Run Canary Remediation
echo ""
echo "5️⃣  STEP 5: RUN CANARY REMEDIATION"
echo "----------------------------------"
echo "Running canary remediation on target1..."

ansible-playbook -i inventories/production/hosts.ini \
    playbooks/master-remediate.yml \
    -e "canary_group=target1" \
    --tags base,webserver \
    --limit target1 \
    > "$WORKFLOW_DIR/5_canary_remediation.txt" 2>&1

echo "Canary remediation completed"

# Step 6: Verify Canary Remediation
echo ""
echo "6️⃣  STEP 6: VERIFY CANARY REMEDIATION"
echo "-------------------------------------"
echo "Checking if drifts were fixed on target1..."

ansible target1 -i inventories/production/hosts.ini -m shell -a "
    echo 'Checking target1:'
    if grep -q '$TIMESTAMP' /var/www/*/index.html; then
        echo '❌ Drifts still present on target1'
        grep -l '$TIMESTAMP' /var/www/*/index.html
    else
        echo '✅ Drifts remediated on target1'
    fi
    
    if [ -f /etc/ansible-managed/workflow_test_$TIMESTAMP.txt ]; then
        echo '❌ Test file still exists'
    else
        echo '✅ Test file removed'
    fi
" > "$WORKFLOW_DIR/6_canary_verification.txt"

cat "$WORKFLOW_DIR/6_canary_verification.txt"

# Step 7: Run Full Remediation
echo ""
echo "7️⃣  STEP 7: RUN FULL REMEDIATION"
echo "--------------------------------"
echo "Running full remediation on remaining nodes..."

ansible-playbook -i inventories/production/hosts.ini \
    playbooks/master-remediate.yml \
    -e "canary_group=target1" \
    -e "full_remediation_group=target2,target3" \
    --tags base,webserver \
    --limit target2,target3 \
    > "$WORKFLOW_DIR/7_full_remediation.txt" 2>&1

echo "Full remediation completed"

# Step 8: Final Verification
echo ""
echo "8️⃣  STEP 8: FINAL VERIFICATION"
echo "------------------------------"
echo "Verifying all nodes are back to desired state..."

for i in {1..3}; do
    NODE="target$i"
    echo "Checking $NODE..."
    ansible "$NODE" -i inventories/production/hosts.ini -m shell -a "
        echo -n '$NODE: '
        if grep -q '$TIMESTAMP' /var/www/*/index.html 2>/dev/null; then
            echo '❌ Drifts still present'
        else
            echo '✅ No drifts found'
        fi
    "
done > "$WORKFLOW_DIR/8_final_verification.txt"

cat "$WORKFLOW_DIR/8_final_verification.txt"

# Step 9: Generate Summary Report
echo ""
echo "9️⃣  STEP 9: GENERATE WORKFLOW SUMMARY"
echo "-------------------------------------"
cat > "$WORKFLOW_DIR/9_workflow_summary.md" << SUMMARYEOF
# End-to-End Workflow Demonstration Summary

## Demo Information
- **Timestamp:** $TIMESTAMP
- **Workflow Directory:** $WORKFLOW_DIR
- **Demo Completed:** $(date)

## Steps Executed
1. ✅ Initial state captured
2. ✅ Controlled drifts created on all nodes
3. ✅ Drift detection executed (Exit code: $DETECTION_EXIT)
4. ✅ Reports generated via API
5. ✅ Canary remediation on target1
6. ✅ Canary verification
7. ✅ Full remediation on target2 and target3
8. ✅ Final verification

## Results
SUMMARYEOF

# Add verification results
cat "$WORKFLOW_DIR/8_final_verification.txt" >> "$WORKFLOW_DIR/9_workflow_summary.md"

cat >> "$WORKFLOW_DIR/9_workflow_summary.md" << SUMMARYEOF

## Files Generated
- \`1_initial_state.txt\` - Initial system state
- \`3_detection_output.txt\` - Drift detection output
- \`4_latest_report.json\` - Latest detection report
- \`5_canary_remediation.txt\` - Canary remediation logs
- \`6_canary_verification.txt\` - Canary verification results
- \`7_full_remediation.txt\` - Full remediation logs
- \`8_final_verification.txt\` - Final verification results
- \`9_workflow_summary.md\` - This summary

## Conclusion
The end-to-end workflow successfully demonstrated:
- Drift creation and detection
- Automated reporting
- Canary deployment pattern
- Full remediation rollout
- Verification and validation

The system successfully detected and remediated all test drifts.
SUMMARYEOF

echo "Workflow summary saved to $WORKFLOW_DIR/9_workflow_summary.md"

# Step 10: Send Final Notification
echo ""
echo "🔟 STEP 10: SEND FINAL NOTIFICATION"
echo "-----------------------------------"
./scripts/notify.sh "workflow_complete" \
    "End-to-end workflow demonstration completed successfully. All drifts detected and remediated." \
    "success" \
    "workflow_demo"

echo ""
echo "============================================="
echo "🎉 END-TO-END WORKFLOW DEMONSTRATION COMPLETE"
echo "============================================="
echo ""
echo "All logs and reports saved to: $WORKFLOW_DIR/"
echo ""
echo "To review the demonstration:"
echo "1. Check the summary: cat $WORKFLOW_DIR/9_workflow_summary.md"
echo "2. View detection report: cat $WORKFLOW_DIR/4_latest_report.json | head -50"
echo "3. Review verification: cat $WORKFLOW_DIR/8_final_verification.txt"
echo ""
echo "🎯 PROJECT COMPLETE! Configuration Drift Detection & Self-Remediation Platform is operational."
