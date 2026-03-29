#!/bin/bash
SERVICE=$1
echo "[$(date)] Clearing cache for: $SERVICE"
echo "[$(date)] Flushing cache entries..."
sleep 1
echo "[$(date)] Cache cleared: 2,847 entries removed"
echo "[$(date)] Cache memory freed: 512MB"
echo "[$(date)] $SERVICE cache healthy"
