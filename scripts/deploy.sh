#!/bin/bash
# Zero-Downtime Deployment Script (Blue-Green / Rolling Style)

set -e

COMPOSE_FILE="docker-compose.yml -f docker-compose.prod.yml"

echo "Starting zero-downtime deployment..."

# 1. Pull latest images
docker-compose -f $COMPOSE_FILE pull

# 2. Scale up (Rolling update via docker-compose update_config)
# Since we have replicas: 3 and order: start-first in the yaml, 
# docker-compose up -d will handle the rolling update natively
docker-compose -f $COMPOSE_FILE up -d --remove-orphans

# 3. Wait for containers to stabilize
echo "Waiting for new containers to stabilize..."
sleep 15

# 4. Run Health Checks
if ./scripts/health_check.sh; then
    echo "Deployment successful! Cleaning up old images..."
    docker image prune -f
else
    echo "Health checks failed! Rolling back..."
    # Rollback implementation would go here (e.g., re-deploying previous tag)
    exit 1
fi
