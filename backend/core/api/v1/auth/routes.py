# backend/core/api/v1/auth/routes.py
from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import check_password_hash
from backend.core.repositories.auth_repository import AuthRepository
from backend.core.auth.token_service import TokenService

from extensions import redis_client

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/login', methods=['POST'])
def login():
    """
    Enterprise login endpoint.
    Verifies credentials and returns JWTs via HTTP-only cookies and JSON.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    lockout_key = f"lockout:{email}"
    attempts_key = f"attempts:{email}"

    # Check lockout status
    is_locked = False
    try:
        if redis_client.get(lockout_key):
            is_locked = True
    except Exception as e:
        import logging
        logging.warning(f"Redis error during lockout check: {e}")

    if is_locked:
        return jsonify({"error": "Account locked. Try again in 10 minutes."}), 423

    user = AuthRepository.get_user_by_email(email)
    
    if not user or not check_password_hash(user['password_hash'], password):
        # Record failed attempt
        try:
            attempts = redis_client.incr(attempts_key)
            if attempts == 1:
                redis_client.expire(attempts_key, 600)
            if attempts >= 5:
                redis_client.set(lockout_key, 1, ex=600)
                redis_client.delete(attempts_key)
        except Exception as e:
            import logging
            logging.warning(f"Redis error during login failure handling: {e}")
            
        return jsonify({"message": "Invalid credentials"}), 401

    # Reset attempts on success
    try:
        redis_client.delete(attempts_key)
    except Exception as e:
        import logging
        logging.warning(f"Redis error during login success handling: {e}")

    access_token, refresh_token = TokenService.generate_tokens(user['id'], user['role'])
    
    AuthRepository.update_last_login(user['id'])

    # Prepare response with HTTP-only cookies for enhanced security
    resp = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "role": user['role']
        },
        "access_token": access_token # Also provide in JSON for mobile/apps
    }))
    
    # Secure Cookie Settings
    resp.set_cookie('access_token', access_token, httponly=True, secure=True, samesite='Strict')
    resp.set_cookie('refresh_token', refresh_token, httponly=True, secure=True, samesite='Strict')

    return resp

@auth_api.route('/refresh', methods=['POST'])
def refresh():
    """Logic for token rotation via refresh token"""
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        return jsonify({"message": "Refresh token missing"}), 401
        
    payload = TokenService.decode_token(refresh_token)
    if "error" in payload or payload.get("type") != "refresh":
        return jsonify({"message": "Invalid refresh token"}), 401
    
    # Generate new access token
    new_access, _ = TokenService.generate_tokens(payload['sub'], payload.get('role'))
    
    resp = make_response(jsonify({"access_token": new_access}))
    resp.set_cookie('access_token', new_access, httponly=True, secure=True, samesite='Strict')
    return resp
