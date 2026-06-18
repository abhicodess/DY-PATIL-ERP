# backend/core/repositories/attendance_repository.py
from backend.core.repositories.base_repository import BaseRepository

class AttendanceRepository(BaseRepository):
    @staticmethod
    def get_students_for_session(timetable_id):
        """
        Automatic student loading based on timetable context (dept, year, division).
        Ensures perfect alignment between slot and student roster.
        """
        sql = """
            SELECT s.id, s.name, s.roll
            FROM students s
            JOIN subjects sub ON (s.department = sub.department AND s.year = sub.year AND s.division = sub.division)
            JOIN timetable t ON t.subject_id = sub.id
            WHERE t.id = %s
            ORDER BY s.roll
        """
        return AttendanceRepository.fetch_all(sql, (timetable_id,))

    @staticmethod
    def submit_bulk_attendance(session_id, attendance_data):
        """
        Enterprise-grade atomic upsert for attendance.
        Uses Postgres ON CONFLICT to prevent duplicate attendance logs per session.
        """
        sql = """
            INSERT INTO attendance (session_id, student_id, status, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (session_id, student_id) 
            DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()
        """
        # Batch insert optimization
        for record in attendance_data:
            AttendanceRepository.execute(sql, (session_id, record['student_id'], record['status']))
        AttendanceRepository.commit()

    @staticmethod
    def log_session_audit(session_id, user_id, action, meta=None):
        """Persistent audit log entry for session actions."""
        sql = """
            INSERT INTO attendance_audit (session_id, actor_id, action, meta, timestamp)
            VALUES (%s, %s, %s, %s, NOW())
        """
        AttendanceRepository.execute(sql, (session_id, user_id, action, meta))
        AttendanceRepository.commit()
