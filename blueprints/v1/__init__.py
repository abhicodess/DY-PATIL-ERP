from .auth.routes import auth_bp
from .students.routes import students_bp
from .attendance.routes import attendance_bp
from api.v1.dashboard import dashboard_bp
from api.v1.student_personal import student_personal_bp
from blueprints.tenant import tenant_bp

BLUEPRINTS = [auth_bp, students_bp, attendance_bp, dashboard_bp, student_personal_bp, tenant_bp]
