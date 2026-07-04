from flask import Blueprint
from .v1 import v1_bp

api_internal_bp = Blueprint('api_internal', __name__, url_prefix='/api/v1_internal')
api_internal_bp.register_blueprint(v1_bp)
