from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from utils.tenant_context import get_current_tenant

def tenant_jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({"error": "Missing or invalid token", "details": str(e)}), 401
            
        claims = get_jwt()
        try:
            current_tenant = get_current_tenant()
        except RuntimeError as re:
            return jsonify({"error": "No tenant context found in this request.", "details": str(re)}), 400
            
        # Verify JWT tenant ID matches request subdomain tenant ID
        if claims.get('tenant_id') != current_tenant['id']:
            return jsonify({"error": "Token not valid for this institution"}), 403
            
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask_jwt_extended import get_jwt
            claims = get_jwt()
            role = claims.get('role')
            if role not in roles:
                return jsonify({"error": "Insufficient role permissions"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

