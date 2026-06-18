from flask import jsonify, Blueprint

api_errors_bp = Blueprint('api_errors', __name__)

@api_errors_bp.app_errorhandler(400)
def bad_request(e):
    return jsonify(error="Bad Request", message=str(e)), 400

@api_errors_bp.app_errorhandler(401)
def unauthorized(e):
    return jsonify(error="Unauthorized", message="Authentication required"), 401

@api_errors_bp.app_errorhandler(403)
def forbidden(e):
    return jsonify(error="Forbidden", message="You do not have permission to access this resource"), 403

@api_errors_bp.app_errorhandler(404)
def not_found(e):
    return jsonify(error="Not Found", message="Resource not found"), 404

@api_errors_bp.app_errorhandler(500)
def internal_server_error(e):
    return jsonify(error="Internal Server Error", message="An unexpected error occurred"), 500
