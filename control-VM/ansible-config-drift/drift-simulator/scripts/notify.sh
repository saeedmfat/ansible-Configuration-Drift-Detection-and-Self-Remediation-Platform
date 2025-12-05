#!/bin/bash
# Notification script for drift simulation events

MESSAGE="$1"
EVENT_TYPE="$2"
SEVERITY="${3:-info}"

LOG_FILE="logs/notifications.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Log to file
echo "[$TIMESTAMP] [$SEVERITY] $MESSAGE" >> "$LOG_FILE"

# Display notification based on severity
case $SEVERITY in
    "critical" | "high")
        echo "🔴 CRITICAL: $MESSAGE" >&2
        ;;
    "medium")
        echo "🟡 WARNING: $MESSAGE" >&2
        ;;
    "low" | "info")
        echo "🔵 INFO: $MESSAGE" >&2
        ;;
    *)
        echo "ℹ️  $MESSAGE"
        ;;
esac

# If running in terminal, show desktop notification (if available)
if [ -n "$DISPLAY" ] && command -v notify-send >/dev/null 2>&1; then
    notify-send "Drift Simulator" "$MESSAGE" --urgency="$SEVERITY"
fi
