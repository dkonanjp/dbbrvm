#!/bin/bash
# BRVM Docker entrypoint: runs scraper + indicators
set -e

echo "[$(date)] BRVM container starting..."

# Run indicators immediately (fast, incremental)
echo "[$(date)] Running initial indicators..."
python -u /tmp/indicators_incr.py || echo "Initial indicators failed"

# Start indicator refresh loop in background (every 6h)
(
    while true; do
        sleep 21600
        echo "[$(date)] Background indicators refresh..."
        python -u /tmp/indicators_incr.py || echo "Background indicators failed"
    done
) &

# Run scraper (has its own 15-min loop, blocks forever)
echo "[$(date)] Starting scraper..."
exec python -u /app/scraper.py
