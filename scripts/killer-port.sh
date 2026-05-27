#!/bin/bash

PORT=5001

# Find the Process ID (PID) listening on the specified port
PID=$(lsof -t -i:"$PORT")

if [ -z "$PID" ]; then
    echo "▶ No process found running on port $PORT."
    exit 0
fi

echo "▶ Found process $PID running on port $PORT."

# Step 1: Attempt a graceful shutdown (SIGTERM)
echo "▶ Sending SIGTERM to process $PID..."
kill -15 "$PID"

# Step 2: Wait and check if the process closed gracefully
TIMEOUT=5
while [ $TIMEOUT -gt 0 ]; do
    sleep 1
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "✔ Process $PID on port $PORT shut down gracefully."
        exit 0
    fi
    ((TIMEOUT--))
done

# Step 3: Force kill if it's still hanging around
echo "⚠ Process $PID did not exit in time. Forcing shutdown (SIGKILL)..."
kill -9 "$PID"

if ! kill -0 "$PID" 2>/dev/null; then
    echo "✔ Process $PID has been forcefully terminated."
else
    echo "❌ Failed to terminate process $PID. You might need to run this script with sudo."
fi