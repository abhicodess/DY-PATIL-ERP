import hashlib
import datetime
from flask import request, g
from functools import wraps
from utils.pg_wrapper import qone, exe
from utils.api_response import error_response
from extensions import redis_client

def api_key_required(fn):
    """Decorator to authenticate and rate limit incoming requests using an API Key."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return error_response("Missing API Key in header X-API-Key", "UNAUTHORIZED", 401)

        key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        
        # Look up key in DB
        key_record = qone(
            "SELECT * FROM api_keys WHERE key_hash = :key_hash AND is_active = TRUE",
            {"key_hash": key_hash}
        )
        
        if not key_record:
            return error_response("Invalid API Key", "UNAUTHORIZED", 401)
            
        # Check expiration
        if key_record["expires_at"] and key_record["expires_at"] < datetime.datetime.utcnow():
            return error_response("API Key has expired", "UNAUTHORIZED", 401)

        # Apply rate limit (fixed window per hour)
        current_hour_str = datetime.datetime.utcnow().strftime("%Y%m%d%H")
        redis_key = f"api_key_rate_limit:{key_hash}:{current_hour_str}"
        
        # Count requests
        try:
            req_count = redis_client.incr(redis_key)
            if req_count == 1:
                redis_client.expire(redis_key, 3600)
        except Exception:
            # Fallback if Redis is down
            req_count = 0

        rate_limit = key_record["rate_limit"]
        if req_count > rate_limit:
            response, status = error_response("API Key Rate Limit Exceeded", "RATE_LIMIT_EXCEEDED", 429)
            # Find time until next hour
            now = datetime.datetime.utcnow()
            next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            retry_after = int((next_hour - now).total_seconds())
            response.headers["Retry-After"] = str(retry_after)
            return response, status

        # Update last_used_at
        try:
            exe(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = :id",
                {"id": key_record["id"]}
            )
        except Exception:
            pass

        # Attach key info to Flask g
        g.api_key = key_record
        return fn(*args, **kwargs)
    return wrapper
