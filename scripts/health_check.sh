#!/bin/bash
set -e

echo "Running production health checks..."

# 1. Flask API Check
if curl -s -f http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ Flask API: Healthy"
else
    echo "❌ Flask API: Unhealthy"
    exit 1
fi

# 2. PostgreSQL Check (using docker exec to check internal db container)
if docker exec erp_db pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Healthy"
else
    echo "❌ PostgreSQL: Unreachable"
    exit 1
fi

# 3. Redis Check
if docker exec erp_redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Unreachable"
    exit 1
fi

# 4. Celery Worker Check
if docker exec erp_worker celery -A celery_app inspect ping | grep -q "pong"; then
    echo "✅ Celery: Healthy"
else
    echo "❌ Celery: Unresponsive"
    exit 1
fi

echo "All systems operational. 🚀"
exit 0
