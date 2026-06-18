# backend/core/middleware/rbac_middleware.py
from functools import wraps
from flask import jsonify, g
from backend.core.auth.roles import ROLE_PERMISSIONS

def role_required(allowed_roles):
    """
    Decorator to restrict access to specific roles.
    Example: @role_required([Roles.ADMIN, Roles.FACULTY])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'role'):
                return jsonify({"message": "Authorization context missing"}), 403
            
            if g.role not in allowed_roles:
                return jsonify({"message": "Access denied: insufficient role privileges"}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """
    Decorator to restrict access based on specific functional permissions.
    Example: @permission_required(Permissions.ATTENDANCE_LOCK)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'role'):
                return jsonify({"message": "Authorization context missing"}), 403
            
            # Check if the user's role has the required permission
            user_permissions = ROLE_PERMISSIONS.get(g.role, [])
            if permission not in user_permissions:
                return jsonify({
                    "message": f"Access denied: missing permission '{permission}'",
                    "code": "INSUFFICIENT_PERMISSIONS"
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
