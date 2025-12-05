#!/bin/bash
# Scheduled drift simulation runner

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
CONFIG_FILE="$SCRIPT_DIR/../configs/simulator_config.yaml"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Load configuration
MAX_DAILY_DRIFTS=$(grep "max_drifts_per_day" "$CONFIG_FILE" | awk '{print $2}' | head -1)
MAX_DAILY_DRIFTS=${MAX_DAILY_DRIFTS:-3}

# Check if we've exceeded daily limit
TODAY=$(date +"%Y%m%d")
TODAYS_DRIFTS=$(find "$LOG_DIR" -name "summary_${TODAY}*.json" 2>/dev/null | wc -l)

if [ "$TODAYS_DRIFTS" -ge "$MAX_DAILY_DRIFTS" ]; then
    echo "Daily drift limit ($MAX_DAILY_DRIFTS) reached. Skipping simulation."
    exit 0
fi

# Activate virtual environment
source "$SCRIPT_DIR/../venv/bin/activate"

# Determine simulation type (local or remote)
SIMULATION_TYPE="local"
if [ -f "$SCRIPT_DIR/remote_drift_simulator.py" ] && [ "$1" = "--remote" ]; then
    SIMULATION_TYPE="remote"
    echo "Running REMOTE drift simulation..."
    python3 "$SCRIPT_DIR/remote_drift_simulator.py"
else
    echo "Running LOCAL drift simulation..."
    python3 "$SCRIPT_DIR/drift_simulator.py"
fi

# Log execution
echo "$(date): $SIMULATION_TYPE simulation completed" >> "$LOG_DIR/execution.log"

# Send notification (if configured)
if [ -f "$SCRIPT_DIR/../scripts/notify.sh" ]; then
    "$SCRIPT_DIR/../scripts/notify.sh" "Drift simulation completed: $SIMULATION_TYPE"
fi
