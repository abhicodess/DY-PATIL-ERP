from flask import Blueprint
from .v1 import v1_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')
api_bp.register_blueprint(v1_bp)
