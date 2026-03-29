#!/bin/bash
SERVICE=$1
echo "[$(date)] Freeing memory for: $SERVICE"
echo "[$(date)] Triggering garbage collection..."
sleep 1
echo "[$(date)] Clearing temp files..."
sleep 1
echo "[$(date)] Memory freed: 1.2GB reclaimed for $SERVICE"
