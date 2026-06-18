from flask import Blueprint, jsonify
from api.utils import ApiResponse

api_errors_bp = Blueprint('api_errors', __name__)

@api_errors_bp.app_errorhandler(400)
def handle_400(e):
    return ApiResponse.error("Bad Request", 400)

@api_errors_bp.app_errorhandler(401)
def handle_401(e):
    return ApiResponse.unauthorized()

@api_errors_bp.app_errorhandler(403)
def handle_403(e):
    return ApiResponse.forbidden()

@api_errors_bp.app_errorhandler(404)
def handle_404(e):
    return ApiResponse.not_found()

@api_errors_bp.app_errorhandler(500)
def handle_500(e):
    return ApiResponse.error("Internal Server Error", 500)
