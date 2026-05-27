#!/bin/bash
# GitHub Repository Monitor Scheduler
# This script can be used with cron to schedule regular checks

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$PROJECT_DIR/github_monitor.py"
LOG_DIR="$PROJECT_DIR/output/logs"
CHECK_DAYS=1

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Generate timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/${TIMESTAMP}_monitor.log"

# Run the monitor and log output
echo "=== GitHub Monitor Run: $(date) ===" >> "$LOG_FILE"
cd "$PROJECT_DIR" || exit 1

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found" >> "$LOG_FILE"
    exit 1
fi

# Run the monitor
$PYTHON_CMD "$PYTHON_SCRIPT" --days "$CHECK_DAYS" >> "$LOG_FILE" 2>&1

# Log completion
echo "=== Completed: $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Optional: Keep only last 30 days of logs
find "$LOG_DIR" -name "*.log" -type f -mtime +30 -delete

exit 0

# Made with Bob
