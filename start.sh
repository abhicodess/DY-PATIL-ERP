#!/usr/bin/env bash
# start.sh - Render startup script
set -e

echo "=== Starting College ERP Startup Sequence ==="

# 1. Run Database Initialization
echo "Step 1/2: Running database setup script..."
python scripts/init_db.py

# 2. Start Gunicorn Web Server
echo "Step 2/2: Starting Gunicorn server on port 8000..."
exec gunicorn --config gunicorn.conf.py "app:create_app()"
