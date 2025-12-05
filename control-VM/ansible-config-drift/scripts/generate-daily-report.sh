#!/bin/bash
# Generate daily summary report

DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
REPORT_DIR="/home/vagrant/ansible-config-drift/reports/daily-summary"
LOG_DIR="/home/vagrant/ansible-config-drift/detection-system/reports"

echo "Generating daily report for $YESTERDAY..."

# Create report directory
mkdir -p "$REPORT_DIR"

# Generate report
REPORT_FILE="$REPORT_DIR/summary_$YESTERDAY.md"

cat > "$REPORT_FILE" << REPORTEOF
# Daily Drift Detection Summary
## Date: $YESTERDAY
## Generated: $(date)

## Executive Summary

### Total Detections
REPORTEOF

# Count total detections from yesterday
TOTAL_DETECTIONS=0
if [ -d "$LOG_DIR/daily/$(echo $YESTERDAY | tr '-' '/')" ]; then
    for report in "$LOG_DIR/daily/$(echo $YESTERDAY | tr '-' '/')"/*.json; do
        if [ -f "$report" ]; then
            DETECTIONS=$(jq '.summary.total_detections // 0' "$report")
            TOTAL_DETECTIONS=$((TOTAL_DETECTIONS + DETECTIONS))
        fi
    done
fi

echo "- **Total Drifts Detected:** $TOTAL_DETECTIONS" >> "$REPORT_FILE"

# Add node breakdown
echo "" >> "$REPORT_FILE"
echo "## By Node" >> "$REPORT_FILE"

for node in target1 target2 target3; do
    NODE_DETECTIONS=0
    if [ -d "$LOG_DIR/daily/$(echo $YESTERDAY | tr '-' '/')" ]; then
        for report in "$LOG_DIR/daily/$(echo $YESTERDAY | tr '-' '/')"/*.json; do
            if [ -f "$report" ] && grep -q "$node" "$report"; then
                DETECTIONS=$(jq '.summary.total_detections // 0' "$report")
                NODE_DETECTIONS=$((NODE_DETECTIONS + DETECTIONS))
            fi
        done
    fi
    echo "- **$node:** $NODE_DETECTIONS drifts" >> "$REPORT_FILE"
done

# Add recommendations
echo "" >> "$REPORT_FILE"
echo "## Recommendations" >> "$REPORT_FILE"

if [ $TOTAL_DETECTIONS -eq 0 ]; then
    echo "- ✅ No action required. System is stable." >> "$REPORT_FILE"
elif [ $TOTAL_DETECTIONS -le 5 ]; then
    echo "- ⚠️  Minor drifts detected. Monitor over next 24 hours." >> "$REPORT_FILE"
else
    echo "- 🚨 Significant drifts detected. Consider investigation." >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "*Report generated automatically by Configuration Drift Detection Platform*" >> "$REPORT_FILE"

echo "Daily report generated: $REPORT_FILE"

# Send notification if there were detections
if [ $TOTAL_DETECTIONS -gt 0 ]; then
    if [ -f "/home/vagrant/ansible-config-drift/scripts/notify.sh" ]; then
        /home/vagrant/ansible-config-drift/scripts/notify.sh \
            "Daily Report: $TOTAL_DETECTIONS drifts detected yesterday" \
            "report" \
            "$([ $TOTAL_DETECTIONS -gt 5 ] && echo "high" || echo "medium")"
    fi
fi
