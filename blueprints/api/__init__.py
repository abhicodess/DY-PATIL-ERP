from flask import Blueprint
api_bp = Blueprint('api', __name__)

from .errors import api_errors_bp
from .v1.students import students_api_bp
from .v1.faculty import faculty_api_bp
from .v1.attendance import attendance_api_bp

api_bp.register_blueprint(api_errors_bp)
api_bp.register_blueprint(students_api_bp, url_prefix='/v1/students')
api_bp.register_blueprint(faculty_api_bp, url_prefix='/v1/faculty')
api_bp.register_blueprint(attendance_api_bp, url_prefix='/v1/attendance')
