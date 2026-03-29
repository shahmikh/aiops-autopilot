#!/bin/bash
SERVICE=$1
echo "[$(date)] Scaling up: $SERVICE"
echo "[$(date)] Spawning additional instance..."
sleep 1
echo "[$(date)] Load balancer updated"
echo "[$(date)] $SERVICE scaled to 2 instances"
