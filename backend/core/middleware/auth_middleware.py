# backend/core/middleware/auth_middleware.py
from functools import wraps
from flask import request, jsonify, g
from backend.core.auth.token_service import TokenService

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 1. Check Authorization Header (Bearer Token)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2:
                token = parts[1]
        
        # 2. Fallback to HTTP-only Cookie
        if not token:
            token = request.cookies.get("access_token")
            
        if not token:
            return jsonify({"message": "Authentication token is missing"}), 401
        
        payload = TokenService.decode_token(token)
        
        if "error" in payload:
            return jsonify({"message": payload["error"], "code": "AUTH_FAILED"}), 401
            
        # Store user info in Flask global for downstream use (middleware/routes)
        g.user_id = payload.get("sub")
        g.role = payload.get("role")
        
        return f(*args, **kwargs)
    
    return decorated
