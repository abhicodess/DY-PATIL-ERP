from flask import Blueprint

student_timetable_bp = Blueprint('student_timetable', __name__)

from . import routes
