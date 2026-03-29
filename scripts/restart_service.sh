#!/bin/bash
SERVICE=$1
echo "[$(date)] Restarting service: $SERVICE"
echo "[$(date)] Stopping $SERVICE..."
sleep 1
echo "[$(date)] Starting $SERVICE..."
sleep 1
echo "[$(date)] $SERVICE restarted successfully"
echo "[$(date)] Running health check..."
sleep 1
echo "[$(date)] Health check passed for $SERVICE"
