# backend/core/middleware/logging_middleware.py
import time
import logging
from flask import request, g

# Configure centralized logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("enterprise_erp.log"),
        logging.StreamHandler()
    ]
)

def log_request_info():
    """
    Middleware function to log request details and timing.
    Should be registered as @app.before_request and @app.after_request.
    """
    g.start_time = time.time()
    
def log_response_info(response):
    """Logs after request completion"""
    duration = time.time() - g.start_time
    user_id = getattr(g, 'user_id', 'Anonymous')
    
    logging.info(
        f"User: {user_id} | Path: {request.path} | Method: {request.method} | "
        f"Status: {response.status_code} | Duration: {duration:.4f}s"
    )
    return response

# Audit Middleware
def audit_log_action(action, target_id, details=None):
    """
    Utility for manual audit logging within services/repositories.
    Persistent storage should be done via a Repository.
    """
    user_id = getattr(g, 'user_id', 'System')
    logging.info(f"AUDIT | Actor: {user_id} | Action: {action} | Target: {target_id} | Data: {details}")
