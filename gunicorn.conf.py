import multiprocessing
import os

# Binding
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Worker configuration (async gevent workers)
worker_class = "gevent"
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
worker_connections = 2000

# Performance & Reliability
max_requests = 2000
max_requests_jitter = 200
timeout = 60
graceful_timeout = 60
keepalive = 10

# Security & Operations
preload_app = False
capture_output = True
daemon = False

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

# Process naming
proc_name = "erp_flask_app"
