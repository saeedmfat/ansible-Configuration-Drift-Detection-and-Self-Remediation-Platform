#!/bin/bash
# Unified notification system for drift detection platform

# Configuration
SLACK_WEBHOOK=""
EMAIL_TO="admin@localhost"
LOG_FILE="/var/log/drift-notifications.log"
MAX_LOG_SIZE_MB=10

# Parse arguments
EVENT_TYPE="$1"
MESSAGE="$2"
SEVERITY="${3:-info}"
SOURCE="${4:-system}"

# Colors for terminal output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Icons
ICON_CRITICAL="🔴"
ICON_HIGH="🟠"
ICON_MEDIUM="🟡"
ICON_LOW="🟢"
ICON_INFO="ℹ️"
ICON_SUCCESS="✅"

# Log function
log_notification() {
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$TIMESTAMP] [$SEVERITY] [$SOURCE] [$EVENT_TYPE] $MESSAGE" >> "$LOG_FILE"
    
    # Rotate log if too large
    LOG_SIZE=$(du -m "$LOG_FILE" 2>/dev/null | cut -f1)
    if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE_MB" ] 2>/dev/null; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
    fi
}

# Display function
display_notification() {
    case $SEVERITY in
        critical)
            COLOR=$RED
            ICON=$ICON_CRITICAL
            ;;
        high)
            COLOR=$RED
            ICON=$ICON_HIGH
            ;;
        medium)
            COLOR=$YELLOW
            ICON=$ICON_MEDIUM
            ;;
        low)
            COLOR=$GREEN
            ICON=$ICON_LOW
            ;;
        success)
            COLOR=$GREEN
            ICON=$ICON_SUCCESS
            ;;
        *)
            COLOR=$BLUE
            ICON=$ICON_INFO
            ;;
    esac
    
    echo -e "${COLOR}${ICON} [$SEVERITY] $MESSAGE${NC}" >&2
}

# Slack notification function (if webhook configured)
send_slack() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        case $SEVERITY in
            critical) COLOR="danger" ;;
            high) COLOR="danger" ;;
            medium) COLOR="warning" ;;
            low) COLOR="good" ;;
            *) COLOR="#439FE0" ;;
        esac
        
        PAYLOAD=$(cat << SLACKEOF
{
    "attachments": [
        {
            "color": "$COLOR",
            "title": "Drift Detection Alert",
            "fields": [
                {
                    "title": "Event Type",
                    "value": "$EVENT_TYPE",
                    "short": true
                },
                {
                    "title": "Severity",
                    "value": "$SEVERITY",
                    "short": true
                },
                {
                    "title": "Source",
                    "value": "$SOURCE",
                    "short": true
                },
                {
                    "title": "Message",
                    "value": "$MESSAGE",
                    "short": false
                }
            ],
            "footer": "Configuration Drift Platform",
            "ts": $(date +%s)
        }
    ]
}
SLACKEOF
        )
        
        curl -s -X POST -H 'Content-type: application/json' \
            --data "$PAYLOAD" "$SLACK_WEBHOOK" >/dev/null 2>&1 &
    fi
}

# Email notification function
send_email() {
    if [ "$SEVERITY" = "critical" ] || [ "$SEVERITY" = "high" ]; then
        SUBJECT="[DRIFT $SEVERITY] $EVENT_TYPE - $MESSAGE"
        BODY="Drift Detection Alert\n\nEvent: $EVENT_TYPE\nSeverity: $SEVERITY\nSource: $SOURCE\nMessage: $MESSAGE\nTime: $(date)\n\n---\nConfiguration Drift Platform"
        
        echo -e "$BODY" | mail -s "$SUBJECT" "$EMAIL_TO" 2>/dev/null &
    fi
}

# Desktop notification (if running in GUI)
send_desktop() {
    if [ -n "$DISPLAY" ] && command -v notify-send >/dev/null 2>&1; then
        URGENCY="normal"
        case $SEVERITY in
            critical|high) URGENCY="critical" ;;
            medium) URGENCY="normal" ;;
            *) URGENCY="low" ;;
        esac
        
        notify-send "Drift Detection" "$MESSAGE" --urgency="$URGENCY" &
    fi
}

# Main execution
main() {
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <event_type> <message> [severity] [source]"
        echo "Severity: critical, high, medium, low, info, success"
        exit 1
    fi
    
    # Log the notification
    log_notification
    
    # Display to terminal
    display_notification
    
    # Send notifications based on severity
    case $SEVERITY in
        critical|high)
            send_slack
            send_email
            send_desktop
            ;;
        medium)
            send_slack
            send_desktop
            ;;
        low|info|success)
            send_slack
            ;;
    esac
    
    # For critical events, also log to system log
    if [ "$SEVERITY" = "critical" ]; then
        logger -t "drift-detection" "[CRITICAL] $EVENT_TYPE: $MESSAGE"
    fi
}

# Execute main function
main "$@"
