from repositories.base_repository import BaseRepository
from models.attendance import Attendance
from sqlalchemy import func
from extensions import db

class AttendanceRepository(BaseRepository):
    def __init__(self):
        super().__init__(Attendance)

    def get_stats_by_student(self, student_id):
        total = Attendance.query.filter_by(student_id=student_id).count()
        present = Attendance.query.filter_by(student_id=student_id, status='Present').count()
        percentage = (present / total * 100) if total > 0 else 0
        return {
            'total': total,
            'present': present,
            'percentage': round(percentage, 2)
        }

    def get_defaulters(self, threshold=75):
        """
        Returns a list of students whose attendance percentage is below the threshold.
        """
        # Calculate attendance percentage for all students
        subquery = db.session.query(
            Attendance.student_id,
            func.count(Attendance.id).label('total'),
            func.sum(db.cast(Attendance.status == 'Present', db.Integer)).label('present')
        ).group_by(Attendance.student_id).subquery()

        defaulters = db.session.query(subquery).filter(
            (subquery.c.present * 100.0 / subquery.c.total) < threshold
        ).all()
        
        return defaulters
