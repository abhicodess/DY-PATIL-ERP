from flask import Blueprint

v1_bp = Blueprint('v1', __name__, url_prefix='/v1')

# Import sub-blueprints
from .auth import auth_bp
from .attendance import attendance_bp
from .students import students_bp
from .faculty import faculty_bp
from .timetable import timetable_bp
from .results import results_bp
from .notifications import notifications_bp
from .dashboard import dashboard_bp
# from .admin import admin_bp
from .student_personal import student_personal_bp
from blueprints.reports.routes import reports_bp

# Register sub-blueprints under v1_bp
v1_bp.register_blueprint(auth_bp, url_prefix='/auth')
v1_bp.register_blueprint(attendance_bp, url_prefix='/attendance')
v1_bp.register_blueprint(students_bp, url_prefix='/students')
v1_bp.register_blueprint(faculty_bp, url_prefix='/faculty')
v1_bp.register_blueprint(timetable_bp, url_prefix='/timetable')
v1_bp.register_blueprint(results_bp, url_prefix='/results')
v1_bp.register_blueprint(notifications_bp, url_prefix='/notifications')
v1_bp.register_blueprint(dashboard_bp, url_prefix='/dashboard')
# v1_bp.register_blueprint(admin_bp, url_prefix='/admin')
v1_bp.register_blueprint(student_personal_bp, url_prefix='/student')
v1_bp.register_blueprint(reports_bp, url_prefix='/reports')

