from flask_smorest import Blueprint
from flask import jsonify, request, current_app, session, make_response
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request
)
from utils.pg_wrapper import qone, exe
from utils.tenant_jwt import tenant_jwt_required
from schemas.auth import LoginSchema, LoginResponseSchema, RefreshResponseSchema, CSRFResponseSchema
from schemas.common import ErrorSchema
from services.student_service import StudentService
from services.faculty_service import FacultyService
from werkzeug.security import check_password_hash
import datetime
import secrets

auth_bp = Blueprint(
    'auth_api_v1', __name__, url_prefix='/api/v1/auth',
    description="Authentication and Session endpoints"
)

student_service = StudentService()
faculty_service = FacultyService()

@auth_bp.route("/csrf", methods=["GET"])
@auth_bp.response(200, CSRFResponseSchema)
@auth_bp.doc(summary="Get CSRF token", tags=["Authentication"])
def get_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["_csrf_token"]}

@auth_bp.route("/login", methods=["POST"])
@auth_bp.arguments(LoginSchema)
@auth_bp.response(200, LoginResponseSchema)
@auth_bp.alt_response(401, schema=ErrorSchema, description="Invalid credentials")
@auth_bp.alt_response(422, schema=ErrorSchema, description="Validation error")
@auth_bp.doc(summary="Generate access and refresh tokens", tags=["Authentication"])
def login(login_data):
    username = login_data.get("username", "").strip()
    password = login_data.get("password", "").strip()
    role = login_data.get("role", "").strip()

    user_id = None
    name = ""
    department = None

    if role == "admin":
        admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
        if admin_hash and username == "admin" and check_password_hash(admin_hash, password):
            user_id = 1
            name = "Administrator"
        else:
            return {"error": "Invalid admin credentials", "code": "INVALID_CREDENTIALS"}, 401

    elif role == "faculty":
        faculty = faculty_service.verify_credentials(username, password)
        if faculty:
            user_id = faculty.id
            name = faculty.name
            department = faculty.department
        else:
            return {"error": "Invalid faculty credentials", "code": "INVALID_CREDENTIALS"}, 401

    elif role == "student":
        student = student_service.verify_credentials(username, password)
        if student:
            user_id = student.id
            name = student.name
            department = student.department
        else:
            return {"error": "Invalid student credentials", "code": "INVALID_CREDENTIALS"}, 401
    else:
        return {"error": "Invalid role specified", "code": "VALIDATION_ERROR"}, 422

    # Generate tokens with tenant context
    from utils.tenant_context import get_current_tenant
    try:
        tenant = get_current_tenant()
        tenant_id = tenant['id']
        tenant_slug = tenant['slug']
    except Exception:
        tenant_id = 1
        tenant_slug = 'default'

    claims = {
        "role": role, 
        "name": name,
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug
    }
    if department:
        claims["department"] = department

    access = create_access_token(identity=str(user_id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user_id), additional_claims=claims)

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
    
    response = make_response(jsonify(resp_data), 200)
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
@auth_bp.arguments(LoginSchema)
@auth_bp.doc(summary="Legacy token endpoint", tags=["Authentication"])
def token(login_data):
    res = login(login_data)
    if isinstance(res, tuple):
        return res
    
    data = res.get_json()
    return jsonify({
        "success": True,
        "message": "Authentication successful",
        "data": {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "role": login_data["role"],
            "user_id": data["user"]["id"]
        }
    })

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
@auth_bp.response(200, RefreshResponseSchema)
@auth_bp.doc(summary="Refresh access token", tags=["Authentication"], security=[{"BearerAuth": []}])
def refresh_token_route():
    identity = get_jwt_identity()
    claims = get_jwt()
    
    new_claims = {
        "role": claims.get("role"),
        "name": claims.get("name"),
        "tenant_id": claims.get("tenant_id"),
        "tenant_slug": claims.get("tenant_slug")
    }
    if "department" in claims:
        new_claims["department"] = claims.get("department")

    access = create_access_token(identity=identity, additional_claims=new_claims)
    return {"access_token": access}

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
@auth_bp.doc(summary="Revoke current token", tags=["Authentication"], security=[{"BearerAuth": []}])
def logout():
    from extensions import redis_client
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    exp = jwt_data["exp"]
    now = datetime.datetime.utcnow().timestamp()
    ttl = int(exp - now)

    if ttl > 0:
        redis_client.setex(f"jwt_blacklist:{jti}", ttl, "true")

    return {"message": "Logged out successfully"}

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
@auth_bp.doc(summary="Get current user details", tags=["Authentication"], security=[{"BearerAuth": []}])
def me():
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

    return {
        "user_id": user_id,
        "username": username,
        "role": role,
        "department": claims.get("department"),
        "name": claims.get("name")
    }
