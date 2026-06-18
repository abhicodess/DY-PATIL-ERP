from flask import Blueprint, request, current_app, session, make_response, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request
)
from functools import wraps
import datetime
import secrets
from werkzeug.security import check_password_hash
from services.student_service import StudentService
from services.faculty_service import FacultyService
from extensions import redis_client, limiter
from utils.pg_wrapper import exe, qone
from utils.api_response import success_response, error_response

auth_bp = Blueprint('auth', __name__)
limiter.limit("10 per minute")(auth_bp)

student_service = StudentService()
faculty_service = FacultyService()

# Custom Decorator for JWT Role Validation
def jwt_role_required(roles):
    """Decorator to enforce JWT authentication and role checking."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            role = claims.get('role')
            if role not in roles:
                return error_response(
                    message="Access forbidden: Insufficient role privileges",
                    code="FORBIDDEN_ROLE",
                    status=403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route("/csrf", methods=["GET"])
def get_csrf_token():
    """
    Get CSRF token.
    """
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return success_response({"csrf_token": session["_csrf_token"]}, "CSRF token retrieved")

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Generate access and refresh tokens for React SPA.
    """
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    role = body.get("role", "").strip()

    if not username or not password or not role:
        return error_response("Missing username, password, or role", "VALIDATION_ERROR", 422)

    user_id = None
    name = ""
    department = None

    if role == "admin":
        admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
        if admin_hash and username == "admin" and check_password_hash(admin_hash, password):
            user_id = 1
            name = "Administrator"
        else:
            return error_response("Invalid admin credentials", "INVALID_CREDENTIALS", 401)

    elif role == "faculty":
        faculty = faculty_service.verify_credentials(username, password)
        if faculty:
            user_id = faculty.id
            name = faculty.name
            department = faculty.department
        else:
            return error_response("Invalid faculty credentials", "INVALID_CREDENTIALS", 401)

    elif role == "student":
        student = student_service.verify_credentials(username, password)
        if student:
            user_id = student.id
            name = student.name
            department = student.department
        else:
            return error_response("Invalid student credentials", "INVALID_CREDENTIALS", 401)
    else:
        return error_response("Invalid role specified", "VALIDATION_ERROR", 422)

    # Generate tokens
    claims = {"role": role, "name": name}
    if department:
        claims["department"] = department

    access = create_access_token(identity=str(user_id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user_id), additional_claims=claims)

    # Log to audit_logs
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        exe(
            "INSERT INTO audit_logs (action, details, role, user_id, ip_addr) VALUES (%s, %s, %s, %s, %s)",
            ("API Login Success", f"Logged in via JWT login endpoint", role, user_id, ip)
        )
    except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")

    # Return standard shape JSON and set cookie for refresh
    resp_data = {
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "id": user_id,
            "name": name,
            "role": role,
            "department": department
        }
    }
    
    payload = {
        "success": True,
        "message": "Authentication successful",
        "data": resp_data,
        "meta": {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "request_id": request.headers.get("X-Request-Id", str(secrets.token_hex(8)))
        }
    }
    response = make_response(jsonify(payload), 200)
    response.set_cookie(
        'refresh_token',
        value=refresh,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite='Lax',
        max_age=30*24*60*60 # 30 days
    )
    return response

@auth_bp.route("/token", methods=["POST"])
def token():
    """
    Generate access and refresh tokens (Legacy endpoint).
    """
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    role = body.get("role", "").strip()

    if not username or not password or not role:
        return error_response("Missing username, password, or role", "VALIDATION_ERROR", 422)

    user_id = None
    name = ""
    department = None

    if role == "admin":
        admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
        if admin_hash and username == "admin" and check_password_hash(admin_hash, password):
            user_id = 1
            name = "Administrator"
        else:
            return error_response("Invalid admin credentials", "INVALID_CREDENTIALS", 401)

    elif role == "faculty":
        faculty = faculty_service.verify_credentials(username, password)
        if faculty:
            user_id = faculty.id
            name = faculty.name
            department = faculty.department
        else:
            return error_response("Invalid faculty credentials", "INVALID_CREDENTIALS", 401)

    elif role == "student":
        student = student_service.verify_credentials(username, password)
        if student:
            user_id = student.id
            name = student.name
            department = student.department
        else:
            return error_response("Invalid student credentials", "INVALID_CREDENTIALS", 401)
    else:
        return error_response("Invalid role specified", "VALIDATION_ERROR", 422)

    # Generate tokens
    claims = {"role": role, "name": name}
    if department:
        claims["department"] = department

    access = create_access_token(identity=str(user_id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user_id), additional_claims=claims)

    # Log to audit_logs
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        exe(
            "INSERT INTO audit_logs (action, details, role, user_id, ip_addr) VALUES (%s, %s, %s, %s, %s)",
            ("API Login Success", f"Logged in via JWT token endpoint", role, user_id, ip)
        )
    except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")

    return success_response({
        "access_token": access,
        "refresh_token": refresh,
        "role": role,
        "user_id": user_id
    }, "Authentication successful")

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token_route():
    """
    Refresh Access Token.
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    responses:
      200:
        description: Token refreshed successfully
      401:
        description: Invalid refresh token
    """
    identity = get_jwt_identity()
    claims = get_jwt()
    
    new_claims = {
        "role": claims.get("role"),
        "name": claims.get("name")
    }
    if "department" in claims:
        new_claims["department"] = claims.get("department")

    access = create_access_token(identity=identity, additional_claims=new_claims)
    return success_response({"access_token": access}, "Token refreshed successfully")

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Revoke current access token.
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    responses:
      200:
        description: Logged out successfully
    """
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    exp = jwt_data["exp"]
    now = datetime.datetime.utcnow().timestamp()
    ttl = int(exp - now)

    if ttl > 0:
        redis_client.setex(f"jwt_blacklist:{jti}", ttl, "true")

    return success_response(None, "Logged out successfully")

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Get current logged in user details.
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    responses:
      200:
        description: User profile retrieved
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role")

    username = "admin"
    if role == "faculty":
        row = qone("SELECT email FROM faculty WHERE id = :id", {"id": user_id})
        username = row["email"] if row else ""
    elif role == "student":
        row = qone("SELECT prn FROM students WHERE id = :id", {"id": user_id})
        username = row["prn"] if row else ""

    return success_response({
        "user_id": user_id,
        "username": username,
        "role": role,
        "department": claims.get("department"),
        "name": claims.get("name")
    }, "Profile retrieved successfully")
