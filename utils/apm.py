import time
import logging
import sqlalchemy as sa
from flask import request, g
from sqlalchemy import event
from extensions import redis_client

logger = logging.getLogger("erp_apm")

def init_apm(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()
        g.query_count = 0

    @event.listens_for(sa.engine.Engine, "before_cursor_execute")
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        if hasattr(g, 'query_count'):
            g.query_count += 1

    @app.after_request
    def log_performance(response):
        if not hasattr(g, 'start_time'):
            return response
            
        duration = time.time() - g.start_time
        endpoint = request.endpoint or "unknown"
        
        # Log slow requests
        if duration > 3.0:
            logger.error(f"CRITICAL SLOW REQUEST: {endpoint} took {duration:.2f}s | Queries: {g.query_count}")
        elif duration > 1.0:
            logger.warning(f"SLOW REQUEST: {endpoint} took {duration:.2f}s | Queries: {g.query_count}")
            
        # Track in Redis for Prometheus metrics
        try:
            redis_client.incr(f"metrics:request_count:{endpoint}")
            redis_client.set(f"metrics:last_duration:{endpoint}", duration)
            if hasattr(g, 'query_count'):
                redis_client.incrby(f"metrics:total_queries:{endpoint}", g.query_count)
                if g.query_count > 20:
                    logger.warning(f"HIGH QUERY COUNT: {endpoint} made {g.query_count} queries")
        except Exception as e:
            logger.error(f"Failed to update APM metrics in Redis: {e}")
                
        return response

    @app.route("/metrics")
    def metrics():
        """Expose basic Prometheus metrics from Redis."""
        lines = []
        try:
            keys = redis_client.keys("metrics:*")
            for key in keys:
                val = redis_client.get(key)
                if val:
                    name = key.decode().replace(":", "_")
                    lines.append(f"{name} {val.decode()}")
        except Exception as e:
            return f"# Error retrieving metrics: {e}", 500
            
        return "\n".join(lines), 200, {'Content-Type': 'text/plain'}
