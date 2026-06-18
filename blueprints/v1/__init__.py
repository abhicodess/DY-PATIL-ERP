from .auth.routes import auth_bp
from .students.routes import students_bp
from .attendance.routes import attendance_bp

BLUEPRINTS = [auth_bp, students_bp, attendance_bp]
