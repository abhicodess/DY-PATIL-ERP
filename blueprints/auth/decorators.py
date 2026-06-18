from functools import wraps
from flask import session, flash, redirect, url_for, request

def login_required(arg=None, role=None):
    """
    Unified decorator that can be used as:
    @login_required
    @login_required(role='admin')
    @login_required('admin')
    """
    import functools
    
    # Target role from either positional arg or keyword role
    target_role = role if role else (arg if not callable(arg) else None)

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("role"):
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            
            if target_role:
                allowed = [target_role] if isinstance(target_role, str) else target_role
                if session.get("role") not in allowed:
                    from flask import abort
                    abort(403)
                
            return f(*args, **kwargs)
        return decorated_function

    if callable(arg):
        return decorator(arg)
    return decorator

def admin_required(f):
    return login_required(role="admin")(f)

def faculty_required(f):
    return login_required(role="faculty")(f)

def student_required(f):
    return login_required(role="student")(f)

def jwt_role_required(roles):
    """
    Decorator to enforce JWT authentication and role checking in blueprints.
    """
    import functools
    from flask_jwt_extended import jwt_required, get_jwt
    from utils.api_response import error_response
    
    # Target roles
    target_roles = [roles] if isinstance(roles, str) else roles

    def decorator(f):
        @functools.wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            role = claims.get("role")
            if role not in target_roles:
                return error_response(
                    message="Access forbidden: Insufficient role privileges",
                    code="FORBIDDEN_ROLE",
                    status=403
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

